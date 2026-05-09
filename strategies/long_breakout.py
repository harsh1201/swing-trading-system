"""
strategies/long_breakout.py — Coil-breakout strategy: single source of truth.
=========================================================================
ALL signal, filter, and scoring logic lives here.
Both the live screener and the backtest import from this module.
Do NOT duplicate any of these functions elsewhere.

Strategy summary
----------------
  Stage 0  Market regime  : Nifty close > EMA50
  Stage 1  Trend filter   : stock close > EMA50 > EMA200
  Stage 2  Coil filter    : last COIL_CANDLES bars, range < MAX_RANGE_PCT
                            AND close within NEAR_HIGH_PCT of period high
  Stage 3  Volume filter  : latest volume >= VOLUME_MIN_RATIO × 20-bar avg
  Stage 3b Gap-up filter  : today's open must not have gapped > GAP_UP_THRESHOLD
                            above the entry level  [screener only]
  Scoring                 : Risk(30) + Range(30) + Trend(40)  → 0–100
  Trade plan              : entry = period_high,  SL = period_low,
                            target = entry + REWARD_RATIO × risk
"""

from __future__ import annotations

from typing import TypedDict

import pandas as pd

from config.settings import (
    ATR_PERIOD,
    EMA_ULTRA_SHORT,
    EMA_SHORT,
    EMA_LONG,
    USE_ALTERNATIVE_EMA,
    ALT_EMA_SHORT,
    ALT_EMA_LONG,
    REQUIRE_BOTH_EMAS,
    USE_RS_FILTER,
    RS_LOOKBACK,
    RS_THRESHOLD,
    RS_AS_OR,
    COIL_CANDLES,
    MAX_RANGE_PCT,
    NEAR_HIGH_PCT,
    REWARD_RATIO,
    MAX_RISK_PCT,
    SCORE_WEIGHT_RISK,
    SCORE_WEIGHT_RANGE,
    SCORE_WEIGHT_TREND,
    VOLUME_AVG_PERIOD,
    VOLUME_MIN_RATIO,
    MIN_CANDLE_STRENGTH,
    GAP_UP_THRESHOLD,
    MIN_AVG_VOLUME,
    MIN_AVG_TURNOVER,
    MAX_GAP_PCT,
)


# ── Type definitions ─────────────────────────────────────────────────────────

class TrendResult(TypedDict):
    close: float
    ema50: float
    ema200: float


class ConsolidationResult(TypedDict):
    period_high: float
    period_low: float
    range_pct: float
    gap_to_high_pct: float


class VolumeResult(TypedDict):
    latest_volume: int
    avg_volume: int
    surge_ratio: float


class CandleStrengthResult(TypedDict):
    strength: float
    close: float
    low: float
    high: float


class GapUpResult(TypedDict):
    today_open: float
    gap_pct: float
    is_gap_up: bool


class ScoreResult(TypedDict):
    total: float
    risk_score: float
    range_score: float
    trend_score: float
    ema50_gap_pct: float


class TradeSetupResult(TypedDict):
    entry: float
    stop_loss: float
    target: float
    risk: float
    risk_pct: float
    rr_ratio: float
    is_valid: bool


# ── Indicator helpers ─────────────────────────────────────────────────────────

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range (ATR) for the given DataFrame.
    ATR = Average of True Range over 'period' bars.
    True Range = max(High-Low, |High-PrevClose|, |Low-PrevClose|)
    """
    required_cols = {"High", "Low", "Close"}
    if not required_cols.issubset(df.columns):
        return pd.Series([pd.NA] * len(df), index=df.index)
    
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    
    prev_close = close.shift(1)
    
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr


def calculate_rs(df: pd.DataFrame, benchmark_df: pd.DataFrame, lookback: int = 20) -> pd.Series:
    """
    Calculate Relative Strength (RS) of stock vs benchmark.
    RS = Stock Return - Benchmark Return over lookback period.
    
    Returns series of RS values (can be positive or negative).
    """
    if len(df) < lookback + 1:
        return pd.Series([pd.NA] * len(df), index=df.index)
    
    stock_current = df["Close"]
    stock_past = df["Close"].shift(lookback)
    stock_return = ((stock_current / stock_past) - 1) * 100
    
    if benchmark_df is not None and len(benchmark_df) >= lookback + 1:
        benchmark_current = benchmark_df["Close"]
        benchmark_past = benchmark_df["Close"].shift(lookback)
        benchmark_return = ((benchmark_current / benchmark_past) - 1) * 100
        rs = stock_return - benchmark_return
    else:
        rs = stock_return
    
    return rs


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a copy of df with EMA20, EMA50, EMA200 and ATR columns appended.
    Also calculates alternative EMAs if USE_ALTERNATIVE_EMA is enabled.
    Must be called before any check_* or is_market_bullish().
    """
    df = df.copy()
    df["EMA20"]  = df["Close"].ewm(span=EMA_ULTRA_SHORT, adjust=False).mean()
    df["EMA50"]  = df["Close"].ewm(span=EMA_SHORT,       adjust=False).mean()
    df["EMA200"] = df["Close"].ewm(span=EMA_LONG,        adjust=False).mean()
    
    # Calculate alternative EMAs if enabled
    if USE_ALTERNATIVE_EMA:
        df[f"EMA{ALT_EMA_SHORT}"] = df["Close"].ewm(span=ALT_EMA_SHORT, adjust=False).mean()
        df[f"EMA{ALT_EMA_LONG}"] = df["Close"].ewm(span=ALT_EMA_LONG, adjust=False).mean()
    
    df["ATR"]    = calculate_atr(df, ATR_PERIOD)
    return df


# ── Market regime ─────────────────────────────────────────────────────────────

def get_market_regime(df: pd.DataFrame, idx: int = -1, all_data: dict[str, pd.DataFrame] | None = None) -> tuple[bool, str, float]:
    """
    Three-tier market regime detector using EMA20, EMA50, and market breadth.

    Regimes (evaluated in priority order)
    ──────────────────────────────────────
    STRONG_BULL  Condition A  — close > EMA50 AND breadth >= 50
    EARLY_TREND  Condition B  — close > EMA20
                               AND EMA20 is rising (slope > 0 over 5 bars)
                               AND breadth >= 40.
                               Catches early-recovery phases before EMA50
                               is reclaimed; allows cautious participation.
    BEAR         Neither      — below both short MAs or MA slope negative.

    Parameters
    ----------
    df       : DataFrame with EMA20, EMA50 columns (from add_indicators).
    idx      : bar index (-1 = latest bar, i.e. screener mode).
    all_data : dict of {symbol: DataFrame} used to compute market breadth.

    Returns
    -------
    (is_tradeable: bool, label: str, breadth: float)
    """
    if idx == -1:
        idx = len(df) - 1

    if idx < EMA_LONG:
        return False, "BEAR", 0.0

    close = float(df["Close"].iloc[idx])
    ema50 = float(df["EMA50"].iloc[idx])
    ema20 = float(df["EMA20"].iloc[idx])

    breadth = calculate_market_breadth(all_data, idx, df) if all_data else 0.0

    if idx % 100 == 0:
        print(f"[DEBUG] Breadth at idx {idx}: {breadth:.2f}%")

    # ── Condition A: STRONG BULL ─────────────────────────────────────────────
    if close > ema50 and breadth >= 40:
        return True, "STRONG_BULL", breadth

    # ── Condition B: EARLY TREND ──────────────────────────────────────────────
    # Price above short MA and short MA is rising  →  momentum recovering.
    # Only evaluated when enough history exists for slope window.
    slope_window = 5
    if idx >= EMA_LONG + slope_window:
        ema20_prev = float(df["EMA20"].iloc[idx - slope_window])
        if close > ema20 and ema20 > ema20_prev and breadth >= 30:
            return True, "EARLY_TREND", breadth

    return False, "BEAR", breadth


def is_market_bullish(nifty_df: pd.DataFrame, idx: int = -1) -> bool:
    """
    Return True if the market is in any tradeable regime (STRONG_BULL or
    EARLY_TREND).  Delegates to get_market_regime(); backward compatible.
    """
    tradeable, _, _breadth = get_market_regime(nifty_df, idx)
    return tradeable


# ── Stage 1: Trend ────────────────────────────────────────────────────────────

def check_trend(df: pd.DataFrame, idx: int = -1, benchmark_df: pd.DataFrame = None) -> TrendResult | None:
    """
    Evaluate the trend at bar `idx` (default: latest bar).

    Condition: close > EMA50 > EMA200 (default)
    Or alternative: close > ALT_EMA_SHORT > ALT_EMA_LONG (when USE_ALTERNATIVE_EMA=True)
    Or just: close > EMA50 (when REQUIRE_BOTH_EMAS=False)
    
    RS Filter (when USE_RS_FILTER=True):
        - AND mode: Requires BOTH EMA trend AND RS > threshold
        - OR mode: Requires EITHER EMA trend OR RS > threshold
    
    Returns a dict  {"close", "ema50", "ema200", "rs"}  or  None if condition fails.
    Requires add_indicators() to have been called on df first.
    """
    row   = df.iloc[idx]
    close = float(row["Close"])
    
    # Determine which EMA columns to use based on config
    if USE_ALTERNATIVE_EMA:
        short_ema = float(row[f"EMA{ALT_EMA_SHORT}"])
        long_ema = float(row[f"EMA{ALT_EMA_LONG}"])
    else:
        short_ema = float(row["EMA50"])
        long_ema = float(row["EMA200"])
    
    # Check EMA trend condition
    ema_passes = False
    if REQUIRE_BOTH_EMAS:
        ema_passes = close > short_ema > long_ema
    else:
        ema_passes = close > short_ema
    
    # Check RS condition
    rs_passes = True
    rs_value = 0.0
    if USE_RS_FILTER:
        # For backtest: if not enough data for RS, skip RS check (pass)
        if len(df) >= idx + RS_LOOKBACK + 1:
            rs_value = calculate_rs(df, benchmark_df, RS_LOOKBACK).iloc[idx]
            if pd.isna(rs_value):
                rs_passes = True  # Skip RS if can't calculate
            else:
                rs_passes = rs_value > RS_THRESHOLD
        else:
            rs_passes = True  # Skip RS if not enough data
    
    # Apply AND/OR logic
    if RS_AS_OR:
        # OR: Either EMA passes OR RS passes
        if not (ema_passes or rs_passes):
            return None
    else:
        # AND: Both must pass (or RS disabled)
        if not ema_passes:
            return None
        if USE_RS_FILTER and not rs_passes:
            return None
    
    return {
        "close": round(float(close),  2),
        "ema50": round(float(short_ema), 2),
        "ema200":round(float(long_ema), 2),
        "rs": round(float(rs_value), 2) if USE_RS_FILTER else 0.0,
    }


# ── Stage 2: Coil / Consolidation ─────────────────────────────────────────────

def check_consolidation(df: pd.DataFrame, idx: int = -1) -> ConsolidationResult | None:
    """
    Evaluate the last COIL_CANDLES bars ending at `idx` for a tight coil.

    idx = -1  → use the latest bar (screener mode).
    idx = n   → use bar n and the (COIL_CANDLES-1) bars before it (backtest mode).

    Conditions (both must hold):
      range_pct  = (period_high − period_low) / period_low × 100 < MAX_RANGE_PCT
      gap_to_high= (period_high − close) / period_high × 100     < NEAR_HIGH_PCT

    Returns a dict  {"period_high", "period_low", "range_pct", "gap_to_high_pct"}
    or None if either condition is not met.
    """
    if idx == -1:
        idx = len(df) - 1

    start  = max(0, idx - COIL_CANDLES + 1)
    window = df.iloc[start : idx + 1]

    period_high = float(window["High"].max())
    period_low  = float(window["Low"].min())
    close       = float(df["Close"].iloc[idx])

    range_pct    = (period_high - period_low) / period_low  * 100
    gap_to_high  = (period_high - close)      / period_high * 100

    if range_pct > MAX_RANGE_PCT or gap_to_high > NEAR_HIGH_PCT:
        return None

    return {
        "period_high":   round(float(period_high),  2),
        "period_low":    round(float(period_low),   2),
        "range_pct":     round(float(range_pct),    2),
        "gap_to_high_pct": round(float(gap_to_high), 2),
    }


# ── Stage 3: Volume ───────────────────────────────────────────────────────────

def check_volume(df: pd.DataFrame, idx: int = -1) -> VolumeResult | None:
    """
    Compare the bar at `idx` against the rolling volume baseline.

    idx = -1  → latest bar.

    Baseline = mean of Volume over the VOLUME_AVG_PERIOD bars *before* `idx`
               (current bar excluded so it cannot inflate its own average).

    volume_ratio = current_volume / avg_volume

    Returns a dict  {"latest_volume", "avg_volume", "surge_ratio"}
    or None if volume_ratio < VOLUME_MIN_RATIO.
    """
    if idx == -1:
        idx = len(df) - 1

    if idx < VOLUME_AVG_PERIOD:
        return None

    baseline       = df["Volume"].iloc[idx - VOLUME_AVG_PERIOD : idx]
    avg_volume     = float(baseline.mean())
    latest_volume  = float(df["Volume"].iloc[idx])
    surge_ratio    = round(float(latest_volume / avg_volume), 2) if avg_volume > 0 else 0.0

    if surge_ratio < VOLUME_MIN_RATIO:
        return None

    return {
        "latest_volume": int(latest_volume),
        "avg_volume":    int(avg_volume),
        "surge_ratio":   surge_ratio,
    }


def check_candle_strength(df: pd.DataFrame, idx: int = -1) -> CandleStrengthResult | None:
    """
    Measure breakout candle strength using close position within the bar's range.

    For LONG breakout: close should be in top portion of range
    strength = (close - low) / (high - low)

    idx = -1 → latest bar.

    Returns {"strength", "close", "low", "high"} or None if strength < MIN_CANDLE_STRENGTH.
    """
    if idx == -1:
        idx = len(df) - 1

    if idx < 1:
        return None

    row = df.iloc[idx]
    low = float(row["Low"])
    high = float(row["High"])
    close = float(row["Close"])

    if high == low:
        return None

    # For longs: higher = better (close near high = strong)
    strength = (close - low) / (high - low)

    if MIN_CANDLE_STRENGTH > 0 and strength < MIN_CANDLE_STRENGTH:
        return None

    return {
        "strength": round(strength, 2),
        "close": close,
        "low": low,
        "high": high,
    }


# ── Stage 3b: Gap-up guard (screener only) ────────────────────────────────────

def check_gap_up(
    df: pd.DataFrame,
    entry_price: float,
    threshold: float = GAP_UP_THRESHOLD,
) -> GapUpResult:
    """
    Detect whether today's open has already gapped above the entry level.

    Returns {"today_open", "gap_pct", "is_gap_up"}.
    Always returns a dict (never None); caller decides how to act on is_gap_up.
    """
    today_open = round(float(df["Open"].iloc[-1]), 2)
    gap_pct    = round(float((today_open - entry_price) / entry_price * 100), 2)
    return {
        "today_open": today_open,
        "gap_pct":    gap_pct,
        "is_gap_up":  today_open > entry_price * threshold,
    }


def check_gap_condition(
    open_price:  float,
    entry_price: float,
    max_gap_pct: float = MAX_GAP_PCT,
) -> bool:
    """
    Simpler form of the gap-up check for use when you already have the open price.
    Returns True if the gap is acceptable (i.e. no excessive gap-up).
    Not yet enforced in the backtest; ready for future use.
    """
    if entry_price <= 0:
        return True
    gap = (open_price - entry_price) / entry_price
    return gap <= max_gap_pct


# ── Liquidity guard ───────────────────────────────────────────────────────────

def check_liquidity(df: pd.DataFrame, idx: int = -1) -> bool:
    """
    Return True if the stock's average daily turnover meets the minimum
    threshold for acceptable execution quality.

    Turnover proxy
    --------------
      avg_turnover = mean(Volume × Close)  over the VOLUME_AVG_PERIOD bars
                     that end just before bar `idx`
                     (current bar excluded to avoid look-ahead)

    Threshold: MIN_AVG_TURNOVER  (₹5 Cr by default, set in config/settings.py)

    idx = -1  → latest bar (screener mode).
    """
    if idx == -1:
        idx = len(df) - 1

    if idx < VOLUME_AVG_PERIOD:
        return False

    window       = df.iloc[idx - VOLUME_AVG_PERIOD : idx]
    avg_turnover = float((window["Volume"] * window["Close"]).mean())
    return avg_turnover >= MIN_AVG_TURNOVER


# ── Scoring ───────────────────────────────────────────────────────────────────

def _trend_score(ema50_gap_pct: float) -> float:
    """
    Piecewise score (0–SCORE_WEIGHT_TREND pts) for how far close sits above EMA50.

    Zone              Gap           Score
    ──────────────────────────────────────────────────────
    Below EMA50       < 0 %         0
    Too close         0 – 1 %       0 → SCORE_WEIGHT_TREND   (linear ramp)
    Sweet spot        1 – 4 %       SCORE_WEIGHT_TREND       (full marks)
    Mild extension    4 – 6 %       SCORE_WEIGHT_TREND → SCORE_WEIGHT_TREND/2 (linear drop)
    Overextended      > 6 %         SCORE_WEIGHT_TREND/2 → 0  (linear penalty, floor 0)
    """
    if ema50_gap_pct < 0:
        return 0.0
    elif ema50_gap_pct < 1.0:
        return ema50_gap_pct * SCORE_WEIGHT_TREND
    elif ema50_gap_pct <= 4.0:
        return SCORE_WEIGHT_TREND
    elif ema50_gap_pct <= 6.0:
        return SCORE_WEIGHT_TREND - ((ema50_gap_pct - 4.0) / 2.0) * (SCORE_WEIGHT_TREND / 2)
    else:
        return max(0.0, (SCORE_WEIGHT_TREND / 2) - ((ema50_gap_pct - 6.0) / 6.0) * (SCORE_WEIGHT_TREND / 2))


def score_long_breakout(trend: TrendResult, coil: ConsolidationResult) -> ScoreResult:
    """
    Composite score 0–100 for a breakout candidate.

      Component   Weight   Driver
      ─────────────────────────────────────────────
      Risk         30 pts  tighter coil → lower risk → higher score
      Range        30 pts  smaller range_pct → higher score
      Trend        40 pts  piecewise curve; sweet spot 1–4% above EMA50

    Returns {"total", "risk_score", "range_score", "trend_score", "ema50_gap_pct"}.
    """
    # Risk score: derived from how wide the coil box is relative to entry
    risk_pct   = (coil["period_high"] - coil["period_low"]) / coil["period_high"] * 100
    risk_score  = max(0.0, (MAX_RISK_PCT - risk_pct)                    / MAX_RISK_PCT    * SCORE_WEIGHT_RISK)
    range_score = max(0.0, (MAX_RANGE_PCT - coil["range_pct"])          / MAX_RANGE_PCT   * SCORE_WEIGHT_RANGE)

    ema50_gap_pct = (trend["close"] - trend["ema50"]) / trend["ema50"] * 100
    trend_sc      = _trend_score(ema50_gap_pct)

    total = round(float(risk_score + range_score + trend_sc), 1)

    return {
        "total":         total,
        "risk_score":    round(float(risk_score),    1),
        "range_score":   round(float(range_score),   1),
        "trend_score":   round(float(trend_sc),      1),
        "ema50_gap_pct": round(float(ema50_gap_pct), 2),
    }


# ── Trade plan ────────────────────────────────────────────────────────────────

def calculate_trade_setup(
    period_high:  float,
    period_low:   float,
    reward_ratio: float = REWARD_RATIO,
    max_risk_pct: float = MAX_RISK_PCT,
) -> TradeSetupResult:
    """
    Build the complete breakout trade plan from the coil range.

      entry      = period_high          (buy above the box)
      stop_loss  = period_low           (invalidation level)
      risk       = entry − stop_loss
      target     = entry + reward_ratio × risk
      risk_pct   = risk / entry × 100

    Returns {"entry", "stop_loss", "target", "risk", "risk_pct", "rr_ratio", "is_valid"}.
    is_valid is True only if risk_pct <= max_risk_pct.
    """
    entry     = round(float(period_high), 2)
    stop_loss = round(float(period_low),  2)
    risk      = round(float(entry - stop_loss), 2)
    target    = round(float(entry + reward_ratio * risk), 2)
    risk_pct  = round(float(risk / entry * 100), 2)

    return {
        "entry":      entry,
        "stop_loss":  stop_loss,
        "target":     target,
        "risk":       risk,
        "risk_pct":   risk_pct,
        "rr_ratio":   reward_ratio,
        "is_valid":   risk_pct <= max_risk_pct,
    }


# ── Market breadth ────────────────────────────────────────────────────────────

def calculate_market_breadth(all_data: dict[str, pd.DataFrame], idx: int, reference_df: pd.DataFrame) -> float:
    total = 0
    above = 0

    # get reference date
    if idx >= len(reference_df):
        return 0.0

    ref_date = reference_df.index[idx]

    for df in all_data.values():
        if len(df) < 50:
            continue

        # find nearest previous date
        df_slice = df.loc[:ref_date]

        if df_slice.empty:
            continue

        if "EMA50" not in df.columns:
            continue

        row = df_slice.iloc[-1]

        if pd.isna(row["EMA50"]):
            continue

        total += 1

        if row["Close"] > row["EMA50"]:
            above += 1

    if total == 0:
        return 0.0

    return (above / total) * 100

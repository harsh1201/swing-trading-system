"""
strategies/breakout.py — Coil-breakout strategy: single source of truth.
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
  Scoring                 : Risk(40) + Range(35) + Trend(25)  → 0–100
  Trade plan              : entry = period_high,  SL = period_low,
                            target = entry + REWARD_RATIO × risk
"""

from __future__ import annotations

import pandas as pd

from config.settings import (
    EMA_ULTRA_SHORT,
    EMA_SHORT,
    EMA_LONG,
    COIL_CANDLES,
    MAX_RANGE_PCT,
    NEAR_HIGH_PCT,
    REWARD_RATIO,
    MAX_RISK_PCT,
    VOLUME_AVG_PERIOD,
    VOLUME_MIN_RATIO,
    GAP_UP_THRESHOLD,
    MIN_AVG_VOLUME,
    MIN_AVG_TURNOVER,
    MAX_GAP_PCT,
)


# ── Indicator helpers ─────────────────────────────────────────────────────────

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a copy of df with EMA20, EMA50 and EMA200 columns appended.
    Must be called before any check_* or is_market_bullish().
    """
    df = df.copy()
    df["EMA20"]  = df["Close"].ewm(span=EMA_ULTRA_SHORT, adjust=False).mean()
    df["EMA50"]  = df["Close"].ewm(span=EMA_SHORT,       adjust=False).mean()
    df["EMA200"] = df["Close"].ewm(span=EMA_LONG,        adjust=False).mean()
    return df


# ── Market regime ─────────────────────────────────────────────────────────────

def get_market_regime(df: pd.DataFrame, idx: int = -1, all_data: dict = None) -> tuple[bool, str, float]:
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

def check_trend(df: pd.DataFrame, idx: int = -1) -> dict | None:
    """
    Evaluate the trend at bar `idx` (default: latest bar).

    Condition: close > EMA50 > EMA200

    Returns a dict  {"close", "ema50", "ema200"}  or  None if condition fails.
    Requires add_indicators() to have been called on df first.
    """
    row   = df.iloc[idx]
    close = float(row["Close"])
    ema50 = float(row["EMA50"])
    ema200= float(row["EMA200"])
    if not (close > ema50 > ema200):
        return None
    return {
        "close": round(close,  2),
        "ema50": round(ema50,  2),
        "ema200":round(ema200, 2),
    }


# ── Stage 2: Coil / Consolidation ─────────────────────────────────────────────

def check_consolidation(df: pd.DataFrame, idx: int = -1) -> dict | None:
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
        "period_high":   round(period_high,  2),
        "period_low":    round(period_low,   2),
        "range_pct":     round(range_pct,    2),
        "gap_to_high_pct": round(gap_to_high, 2),
    }


# ── Stage 3: Volume ───────────────────────────────────────────────────────────

def check_volume(df: pd.DataFrame, idx: int = -1) -> dict | None:
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
    surge_ratio    = round(latest_volume / avg_volume, 2) if avg_volume > 0 else 0.0

    if surge_ratio < VOLUME_MIN_RATIO:
        return None

    return {
        "latest_volume": int(latest_volume),
        "avg_volume":    int(avg_volume),
        "surge_ratio":   surge_ratio,
    }


# ── Stage 3b: Gap-up guard (screener only) ────────────────────────────────────

def check_gap_up(
    df: pd.DataFrame,
    entry_price: float,
    threshold: float = GAP_UP_THRESHOLD,
) -> dict:
    """
    Detect whether today's open has already gapped above the entry level.

    Returns {"today_open", "gap_pct", "is_gap_up"}.
    Always returns a dict (never None); caller decides how to act on is_gap_up.
    """
    today_open = round(float(df["Open"].iloc[-1]), 2)
    gap_pct    = round((today_open - entry_price) / entry_price * 100, 2)
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
    Piecewise score (0–25 pts) for how far close sits above EMA50.

    Zone              Gap           Score
    ──────────────────────────────────────────────────────
    Below EMA50       < 0 %         0
    Too close         0 – 1 %       0 → 25   (linear ramp)
    Sweet spot        1 – 4 %       25       (full marks)
    Mild extension    4 – 6 %       25 → 12.5 (linear drop)
    Overextended      > 6 %         12.5 → 0  (linear penalty, floor 0)
    """
    if ema50_gap_pct < 0:
        return 0.0
    elif ema50_gap_pct < 1.0:
        return ema50_gap_pct * 25.0
    elif ema50_gap_pct <= 4.0:
        return 25.0
    elif ema50_gap_pct <= 6.0:
        return 25.0 - ((ema50_gap_pct - 4.0) / 2.0) * 12.5
    else:
        return max(0.0, 12.5 - ((ema50_gap_pct - 6.0) / 6.0) * 12.5)


def score_breakout(trend: dict, coil: dict) -> dict:
    """
    Composite score 0–100 for a breakout candidate.

      Component   Weight   Driver
      ─────────────────────────────────────────────
      Risk         40 pts  tighter coil → lower risk → higher score
      Range        35 pts  smaller range_pct → higher score
      Trend        25 pts  piecewise curve; sweet spot 1–4% above EMA50

    Returns {"total", "risk_score", "range_score", "trend_score", "ema50_gap_pct"}.
    """
    # Risk score: derived from how wide the coil box is relative to entry
    risk_pct   = (coil["period_high"] - coil["period_low"]) / coil["period_high"] * 100
    risk_score  = max(0.0, (MAX_RISK_PCT - risk_pct)                    / MAX_RISK_PCT    * 40)
    range_score = max(0.0, (MAX_RANGE_PCT - coil["range_pct"])          / MAX_RANGE_PCT   * 35)

    ema50_gap_pct = (trend["close"] - trend["ema50"]) / trend["ema50"] * 100
    trend_sc      = _trend_score(ema50_gap_pct)

    total = round(risk_score + range_score + trend_sc, 1)

    return {
        "total":         total,
        "risk_score":    round(risk_score,    1),
        "range_score":   round(range_score,   1),
        "trend_score":   round(trend_sc,      1),
        "ema50_gap_pct": round(ema50_gap_pct, 2),
    }


# ── Trade plan ────────────────────────────────────────────────────────────────

def calculate_trade_setup(
    period_high:  float,
    period_low:   float,
    reward_ratio: float = REWARD_RATIO,
    max_risk_pct: float = MAX_RISK_PCT,
) -> dict:
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
    entry     = round(period_high, 2)
    stop_loss = round(period_low,  2)
    risk      = round(entry - stop_loss, 2)
    target    = round(entry + reward_ratio * risk, 2)
    risk_pct  = round(risk / entry * 100, 2)

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

def calculate_market_breadth(all_data, idx, reference_df):
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

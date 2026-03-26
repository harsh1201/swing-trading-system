"""
strategies/short_breakout.py — Short breakdown strategy: mirror of long_breakout.
=========================================================================
ALL signal, filter, and scoring logic for SHORT trades lives here.
Both the live screener and the backtest import from this module.
Do NOT duplicate any of these functions elsewhere.

Strategy summary
----------------
  Stage 0  Market regime  : Nifty close < EMA50  (bearish)
  Stage 1  Trend filter   : stock close < EMA50 < EMA200  (downtrend)
  Stage 2  Coil filter    : last COIL_CANDLES bars, range < MAX_RANGE_PCT
                            AND close within NEAR_HIGH_PCT of period LOW
  Stage 3  Volume filter  : latest volume >= VOLUME_MIN_RATIO × 20-bar avg
  Stage 3b Gap-down filter: today's open must not have gapped > GAP_UP_THRESHOLD
                            below the entry level  [screener only]
  Scoring                 : Risk(40) + Range(35) + Trend(25)  → 0–100
  Trade plan              : entry = period_low,  SL = period_high,
                            target = entry − REWARD_RATIO × risk
"""

from __future__ import annotations

from typing import TypedDict

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

# ── Reuse shared helpers from long_breakout (no duplication) ─────────────────
from strategies.long_breakout import (
    add_indicators,
    check_volume,
    check_liquidity,
    calculate_market_breadth,
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
    gap_to_low_pct: float


class VolumeResult(TypedDict):
    latest_volume: int
    avg_volume: int
    surge_ratio: float


class GapDownResult(TypedDict):
    today_open: float
    gap_pct: float
    is_gap_down: bool


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


# ── Market regime (bearish) ──────────────────────────────────────────────────

def get_market_regime_short(df: pd.DataFrame, idx: int = -1, all_data: dict[str, pd.DataFrame] | None = None) -> tuple[bool, str, float]:
    """
    Three-tier BEARISH market regime detector using EMA20, EMA50, and breadth.

    Regimes (evaluated in priority order)
    ──────────────────────────────────────
    STRONG_BEAR  Condition A  — close < EMA50 AND breadth <= 60
                               (majority of stocks are weak)
    EARLY_BEAR   Condition B  — close < EMA20
                                AND EMA20 is falling (slope < 0 over 5 bars)
                                AND breadth <= 70.
                                Catches early-decline phases before EMA50
                                is broken; allows cautious short participation.
    BULL         Neither      — above both short MAs or MA slope positive.

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
        return False, "BULL", 0.0

    close = float(df["Close"].iloc[idx])
    ema50 = float(df["EMA50"].iloc[idx])
    ema20 = float(df["EMA20"].iloc[idx])

    breadth = calculate_market_breadth(all_data, idx, df) if all_data else 0.0

    if idx % 100 == 0:
        print(f"[DEBUG] Breadth at idx {idx}: {breadth:.2f}%")

    # ── Condition A: STRONG BEAR ─────────────────────────────────────────────
    if close < ema50 and breadth <= 60:
        return True, "STRONG_BEAR", breadth

    # ── Condition B: EARLY BEAR ──────────────────────────────────────────────
    slope_window = 5
    if idx >= EMA_LONG + slope_window:
        ema20_prev = float(df["EMA20"].iloc[idx - slope_window])
        if close < ema20 and ema20 < ema20_prev and breadth <= 70:
            return True, "EARLY_BEAR", breadth

    return False, "BULL", breadth


def is_market_bearish(nifty_df: pd.DataFrame, idx: int = -1) -> bool:
    """
    Return True if the market is in any short-tradeable regime (STRONG_BEAR or
    EARLY_BEAR).  Delegates to get_market_regime_short(); backward compatible.

    Parameters
    ----------
    nifty_df : DataFrame for Nifty index.
    idx      : bar index.
    """
    tradeable, _, _breadth = get_market_regime_short(nifty_df, idx)
    return tradeable


# ── Stage 1: Trend (bearish) ────────────────────────────────────────────────

def check_trend_short(df: pd.DataFrame, idx: int = -1) -> TrendResult | None:
    """
    Evaluate the BEARISH trend at bar `idx` (default: latest bar).

    Condition: close < EMA50 < EMA200  (stock is in a confirmed downtrend)

    Returns a dict  {"close", "ema50", "ema200"}  or  None if condition fails.
    Requires add_indicators() to have been called on df first.
    """
    row   = df.iloc[idx]
    close = float(row["Close"])
    ema50 = float(row["EMA50"])
    ema200= float(row["EMA200"])
    if not (close < ema50 < ema200):
        return None
    return {
        "close": round(float(close),  2),
        "ema50": round(float(ema50),  2),
        "ema200":round(float(ema200), 2),
    }


# ── Stage 2: Coil / Consolidation (near lows) ───────────────────────────────

def check_consolidation_short(df: pd.DataFrame, idx: int = -1) -> ConsolidationResult | None:
    """
    Evaluate the last COIL_CANDLES bars ending at `idx` for a tight coil
    near the LOWS (breakdown setup).

    idx = -1  → use the latest bar (screener mode).
    idx = n   → use bar n and the (COIL_CANDLES-1) bars before it (backtest mode).

    Conditions (both must hold):
      range_pct  = (period_high − period_low) / period_low × 100 < MAX_RANGE_PCT
      gap_to_low = (close − period_low) / period_low × 100       < NEAR_HIGH_PCT

    Returns a dict  {"period_high", "period_low", "range_pct", "gap_to_low_pct"}
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
    gap_to_low   = (close - period_low)       / period_low  * 100

    if range_pct > MAX_RANGE_PCT or gap_to_low > NEAR_HIGH_PCT:
        return None

    return {
        "period_high":   round(float(period_high),  2),
        "period_low":    round(float(period_low),   2),
        "range_pct":     round(float(range_pct),    2),
        "gap_to_low_pct": round(float(gap_to_low),  2),
    }


# ── Stage 3b: Gap-down guard (screener only) ────────────────────────────────

def check_gap_down(
    df: pd.DataFrame,
    entry_price: float,
    threshold: float = GAP_UP_THRESHOLD,
) -> GapDownResult:
    """
    Detect whether today's open has already gapped below the entry level.

    For shorts, entry_price = period_low. If open is already far below
    entry, the breakdown has already happened and chasing is risky.

    Returns {"today_open", "gap_pct", "is_gap_down"}.
    Always returns a dict (never None); caller decides how to act on is_gap_down.
    """
    today_open = round(float(df["Open"].iloc[-1]), 2)
    gap_pct    = round(float((entry_price - today_open) / entry_price * 100), 2)
    # threshold is e.g. 1.02 → 2% gap allowed
    return {
        "today_open": today_open,
        "gap_pct":    gap_pct,
        "is_gap_down": today_open < entry_price / threshold,
    }


# ── Scoring ──────────────────────────────────────────────────────────────────

def _trend_score_short(ema50_gap_pct: float) -> float:
    """
    Piecewise score (0–25 pts) for how far close sits BELOW EMA50.

    ema50_gap_pct here is the absolute gap below EMA50 (positive = further below).

    Zone              Gap           Score
    ──────────────────────────────────────────────────────
    Above EMA50       < 0 %         0
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


def score_short_breakout(trend: TrendResult, coil: ConsolidationResult) -> ScoreResult:
    """
    Composite score 0–100 for a short breakdown candidate.

      Component   Weight   Driver
      ─────────────────────────────────────────────
      Risk         40 pts  tighter coil → lower risk → higher score
      Range        35 pts  smaller range_pct → higher score
      Trend        25 pts  piecewise curve; sweet spot 1–4% below EMA50

    Returns {"total", "risk_score", "range_score", "trend_score", "ema50_gap_pct"}.
    """
    # Risk score: derived from how wide the coil box is relative to entry
    risk_pct   = (coil["period_high"] - coil["period_low"]) / coil["period_low"] * 100
    risk_score  = max(0.0, (MAX_RISK_PCT - risk_pct)                    / MAX_RISK_PCT    * 40)
    range_score = max(0.0, (MAX_RANGE_PCT - coil["range_pct"])          / MAX_RANGE_PCT   * 35)

    # For shorts: how far below EMA50 (positive = good for shorts)
    ema50_gap_pct = (trend["ema50"] - trend["close"]) / trend["ema50"] * 100
    trend_sc      = _trend_score_short(ema50_gap_pct)

    total = round(float(risk_score + range_score + trend_sc), 1)

    return {
        "total":         total,
        "risk_score":    round(float(risk_score),    1),
        "range_score":   round(float(range_score),   1),
        "trend_score":   round(float(trend_sc),      1),
        "ema50_gap_pct": round(float(ema50_gap_pct), 2),
    }


# ── Trade plan ───────────────────────────────────────────────────────────────

def calculate_trade_setup_short(
    period_high:  float,
    period_low:   float,
    reward_ratio: float = REWARD_RATIO,
    max_risk_pct: float = MAX_RISK_PCT,
) -> TradeSetupResult:
    """
    Build the complete short breakdown trade plan from the coil range.

      entry      = period_low           (sell below the box)
      stop_loss  = period_high          (invalidation level — above the box)
      risk       = stop_loss − entry
      target     = entry − reward_ratio × risk  (downside target)
      risk_pct   = risk / entry × 100

    Returns {"entry", "stop_loss", "target", "risk", "risk_pct", "rr_ratio", "is_valid"}.
    is_valid is True only if risk_pct <= max_risk_pct.
    """
    entry     = round(float(period_low),  2)
    stop_loss = round(float(period_high), 2)
    risk      = round(float(stop_loss - entry), 2)
    target    = round(float(entry - reward_ratio * risk), 2)
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

"""
backtest.py — Full-Strategy Swing Trading Backtest  (concurrent positions)
===========================================================================
Mirrors the live screener exactly — all strategy logic is imported from
strategies/long_breakout.py (single source of truth).

Pipeline (each day)
-------------------
  Stage 0  Market regime  : Nifty close > EMA50
  Stage 1  Trend          : stock close > EMA50 > EMA200
  Stage 2  Coil           : range < MAX_RANGE_PCT, close near high
  Stage 3  Volume         : surge ratio >= VOLUME_MIN_RATIO
  Scoring                 : Risk(30) + Range(30) + Trend(40)

Trade mechanics
---------------
  Entry    : period_high — confirmed when next bar closes at or above level
  Stop     : period_low  (box bottom)
  Target   : entry + REWARD_RATIO × risk   (default 1:2 RR)
  Breakeven: SL raised to entry once High >= entry + 1.5R AND Close > entry
  Max hold : trailing stop EMA20 on close

Concurrent positions
--------------------
  Up to MAX_CONCURRENT_TRADES open simultaneously.
  Each new trade risks exactly RISK_PER_TRADE % of current equity.

Usage
-----
  python backtest.py                              # default (long_breakout) strategy
  python backtest.py --strategy long_breakout     # explicit long strategy
  python backtest.py --strategy short_breakout    # short breakdown strategy
"""

import argparse
import sys
from collections import defaultdict
from typing import TypedDict

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── Shared imports ────────────────────────────────────────────────────────────
from datetime import datetime, timedelta
import pytz

try:
    from reports.backtest.version import save_backtest_result
    BACKTEST_VERSIONING = True
except ImportError:
    BACKTEST_VERSIONING = False

from config.settings import (
    ATR_PERIOD,
    BACKTEST_DAYS,
    BACKTEST_FETCH_DAYS,
    COIL_CANDLES,
    COST_PCT,
    EARLY_TREND_MAX_TRADES_FACTOR,
    EMA_LONG,
    MAX_CONCURRENT_TRADES,
    MAX_POSITION_PCT,
    MAX_RANGE_PCT,
    MAX_TRADES_PER_SECTOR,
    MIN_PRICE,
    MIN_SCORE_THRESHOLD,
    NEAR_HIGH_PCT,
    NIFTY_TICKER,
    REWARD_RATIO,
    RISK_PER_TRADE,
    SLIPPAGE_PCT,
    STARTING_EQUITY,
    TRAILING_ATR_MULTIPLIER,
    USE_ATR_TRAILING,
    VOLUME_AVG_PERIOD,
    WALK_FORWARD_SPLIT_YEAR,
    DISCORD_PORTFOLIO_WEBHOOK,
    TIMEZONE,
)
from config.stocks import SECTORS, STOCKS
from data.cache import fetch_ohlcv
from strategies.long_breakout import (
    ConsolidationResult,
    TrendResult,
    add_indicators,
    check_consolidation,
    check_liquidity,
    check_trend,
    check_volume,
    check_candle_strength,
    get_market_regime,
    score_long_breakout,
    calculate_atr,
)
from strategies.short_breakout import (
    check_consolidation_short,
    check_trend_short,
    get_market_regime_short,
    score_short_breakout,
)

# ── Timezone Helper ───────────────────────────────────────────────────────────

def get_now() -> datetime:
    """Return current time in the configured timezone."""
    ist = pytz.timezone(TIMEZONE)
    return datetime.now(ist)

def get_today_str() -> str:
    """Return today's date string in DD-MM-YYYY format in the configured timezone."""
    return get_now().strftime("%d-%m-%Y")


# ── Type definitions ─────────────────────────────────────────────────────────


class Candidate(TypedDict):
    ticker: str
    name: str
    df: pd.DataFrame
    idx: int
    trend: TrendResult
    coil: ConsolidationResult
    entry: float
    stop_loss: float
    target: float
    score: float
    volume_ratio: float


class _TradeBase(TypedDict):
    ticker: str
    name: str
    sector: str
    df: pd.DataFrame
    entry_price: float
    effective_entry: float
    stop_loss: float
    target: float
    active_sl: float
    be_hit: bool
    nifty_entry_idx: int
    signal_date: str
    qty: float
    score: float
    volume_ratio: float


class Trade(_TradeBase, total=False):
    exit_price: float
    exit_date: str
    outcome: str
    pnl_abs: float
    pnl_pct: float
    trade_cost: float
    bars_held: int


class PeriodStats(TypedDict):
    total: int
    wins: int
    losses: int
    breakevens: int
    trails: int
    win_rate: float
    pnl_abs: float
    pnl_pct: float


# ── Sector helper ─────────────────────────────────────────────────────────────


def get_sector(ticker: str) -> str:
    """Return the sector for a ticker (strips .NS/.BO); falls back to 'OTHER'."""
    return SECTORS.get(ticker.split(".")[0], "OTHER")


# ── Data helpers ──────────────────────────────────────────────────────────────


def fetch_ticker(
    ticker: str,
    days: int = BACKTEST_FETCH_DAYS,
    refresh: bool = True,
) -> pd.DataFrame | None:
    """
    Return daily OHLCV for one ticker.  Delegates to data.cache so repeated
    backtest runs skip the API and load from  data/<ticker>.csv  instead.
    Pass refresh=True to force a fresh download (e.g. next-day update).
    """
    return fetch_ohlcv(ticker, days, refresh=refresh)


def fetch_all(tickers: list[str], refresh: bool = True) -> dict[str, pd.DataFrame]:
    """Fetch all tickers, print bar counts, skip failures."""
    data = {}
    for t in tickers:
        print(f"  Fetching {t:<20} ...", end=" ", flush=True)
        df = fetch_ticker(t, refresh=refresh)
        if df is None:
            print("FAILED — skipped")
        else:
            print(f"{len(df)} bars")
            data[t] = df
    return data


# ── Candidate scanner ─────────────────────────────────────────────────────────


def scan_candidates(
    stock_data: dict[str, pd.DataFrame],
    date: pd.Timestamp,
) -> list[Candidate]:
    """
    Return all stocks passing Liquidity + Trend + Coil + Volume filters for
    `date`, each carrying its score and trade levels.  Sorted best-first.

    All filter logic delegates to strategies/long_breakout.py — no duplication.
    """
    candidates: list[Candidate] = []

    for ticker, df in stock_data.items():
        if date not in df.index:
            continue
        idx = df.index.get_loc(date)

        # Need enough history for EMA warm-up, coil window, and volume baseline
        if idx < max(COIL_CANDLES, EMA_LONG, VOLUME_AVG_PERIOD):
            continue

        # Price floor — skip penny stocks below MIN_PRICE
        if float(df["Close"].iloc[idx]) < MIN_PRICE:
            continue

        # Liquidity gate — reject stocks below ₹10 Cr avg daily turnover
        if not check_liquidity(df, idx):
            continue

        trend = check_trend(df, idx)
        if trend is None:
            continue

        coil = check_consolidation(df, idx)
        if coil is None:
            continue

        vol = check_volume(df, idx)
        if vol is None:
            continue

        # Candle strength filter (DISABLED Apr 2022 - hurt performance)
        # candle = check_candle_strength(df, idx)
        # if candle is None:
        #     continue

        entry = coil["period_high"]
        stop_loss = coil["period_low"]
        target = entry + REWARD_RATIO * (entry - stop_loss)
        sc = score_long_breakout(trend, coil)

        # Score gate — skip low-quality setups (set MIN_SCORE_THRESHOLD in settings)
        if sc["total"] < MIN_SCORE_THRESHOLD:
            continue

        candidates.append(
            {
                "ticker": ticker,
                "name": STOCKS.get(ticker, ticker),
                "df": df,
                "idx": idx,
                "trend": trend,
                "coil": coil,
                "entry": entry,
                "stop_loss": stop_loss,
                "target": target,
                "score": sc["total"],
                "volume_ratio": vol["surge_ratio"],
            }
        )

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates


# ── Trade closer (helper) ─────────────────────────────────────────────────────


def _close(
    trade: Trade,
    exit_price: float,
    outcome: str,
    nifty_idx: int,
    closed_trades: list[Trade],
    exit_date: str,
) -> float:
    """
    Finalise an open trade: apply exit slippage, deduct transaction costs,
    record outcome, and print log line.

    :param trade: The Active Trade object
    :param exit_price: The exact level the trade exited at
    :param outcome: Reason for exit (e.g. 'win', 'loss')
    :param nifty_idx: The current day's index
    :param closed_trades: The array to append the finalized trade to
    :param exit_date: The date string (DD-MM-YYYY) of the exit

    Execution model
    ---------------
      effective_entry  : stored on the trade at open (entry filled higher)
      effective_exit   : exit_price * (1 − SLIPPAGE_PCT)  (filled lower)
      cost             : effective_entry × qty × COST_PCT  (brokerage + fees)
      pnl_abs          : (effective_exit − effective_entry) × qty − cost

    Returns pnl_abs so the caller can update running equity.
    """
    eff_entry = float(trade["effective_entry"])
    eff_exit = round(float(exit_price * (1 - SLIPPAGE_PCT)), 2)
    qty = float(trade["qty"])
    cost = round(float(eff_entry * qty * COST_PCT), 2)
    pnl_abs = qty * (eff_exit - eff_entry) - cost
    pnl_pct = round(float(pnl_abs / (eff_entry * qty) * 100), 2) if (eff_entry * qty) != 0 else 0.0
    bars_held = int(nifty_idx - trade["nifty_entry_idx"])

    trade["exit_price"] = round(float(exit_price), 2)
    trade["exit_date"] = exit_date
    trade["outcome"] = outcome
    trade["pnl_abs"] = round(float(pnl_abs), 2)
    trade["pnl_pct"] = pnl_pct
    trade["trade_cost"] = cost
    trade["bars_held"] = bars_held
    closed_trades.append(trade)

    icon = {"win": "WIN ", "loss": "LOSS", "breakeven": "BE  ", "trail": "TRL "}.get(outcome, "????")
    print(
        f"  {trade['signal_date']:<12} "
        f"{exit_date:<12} "
        f"{trade['name']:<20} "
        f"{trade['score']:>5.1f} "
        f"vol {trade['volume_ratio']:>4.2f}x "
        f"Rs.{eff_entry:>7,.0f} "
        f"Rs.{trade['stop_loss']:>7,.0f} "
        f"Rs.{trade['target']:>8,.0f} "
        f"Rs.{eff_exit:>7,.0f} "
        f"{pnl_pct:>+6.2f}%  {icon}"
    )
    return float(pnl_abs)


# ── Backtest engine ───────────────────────────────────────────────────────────


def run_backtest(
    nifty_df: pd.DataFrame,
    stock_data: dict[str, pd.DataFrame],
) -> tuple[list[Trade], float]:
    """
    Concurrent multi-position backtest.

    STEP A (each day) — Update every open trade:
      • Apply breakeven rule (High >= entry + 1.5R and Close > entry).
      • Close on SL hit / target hit / EMA20 trailing stop.
      • Update equity on close.

    STEP B (each day) — Open new trades if slots are available:
      • Market must be bullish (Nifty close > EMA50).
      • Scan all stocks → Trend + Coil + Volume → score.
      • For each candidate (best score first), confirm entry:
          next bar must have High >= entry AND Close >= entry.
      • Size each trade so that a full stop-loss costs RISK_PER_TRADE % equity.
      • Open up to MAX_CONCURRENT_TRADES simultaneous positions.

    Returns (closed_trades, final_equity, max_drawdown).
    """
    all_dates = nifty_df.index
    start_idx = max(EMA_LONG + 10, len(all_dates) - BACKTEST_DAYS)
    equity = float(STARTING_EQUITY)
    peak_equity = equity
    max_drawdown = 0.0

    active_trades: list[Trade] = []
    closed_trades: list[Trade] = []

    # Header
    print(
        f"\n  Backtest range  : {all_dates[start_idx].strftime('%d-%m-%Y')}  ->  {all_dates[-1].strftime('%d-%m-%Y')}"
    )
    print(f"  Bars in period  : {len(all_dates) - start_idx}")
    print(f"  Max concurrent  : {MAX_CONCURRENT_TRADES} trades\n")

    col = (
        f"{'Entry Date':<12} {'Exit Date':<12} {'Name':<20} {'Score':>5} {'Vol':>7} "
        f"{'Entry':>8} {'SL':>8} {'Target':>9} {'Exit':>8} {'PnL%':>6}  Result"
    )
    print("  " + col)
    print("  " + "-" * len(col))

    for i in range(start_idx, len(all_dates)):
        date = all_dates[i]

        # ── STEP A: Update every open trade ───────────────────────────────────
        still_open: list[Trade] = []

        for trade in active_trades:
            if i < trade["nifty_entry_idx"]:
                still_open.append(trade)
                continue

            df = trade["df"]
            entry = trade["entry_price"]
            target = trade["target"]
            risk = entry - trade["stop_loss"]

            if date not in df.index:
                still_open.append(trade)
                continue

            bar = df.index.get_loc(date)
            high_bar = float(df["High"].iloc[bar])
            low_bar = float(df["Low"].iloc[bar])
            close_bar = float(df["Close"].iloc[bar])

            is_entry_bar = i == trade["nifty_entry_idx"]

            # Breakeven: skip on entry bar to prevent same-bar BE trap
            if not is_entry_bar and not trade["be_hit"] and high_bar >= entry + risk * 1.5 and close_bar > entry:
                trade["active_sl"] = entry
                trade["be_hit"] = True

            if low_bar <= trade["active_sl"]:
                outcome = "breakeven" if trade["be_hit"] else "loss"
                equity += _close(trade, trade["active_sl"], outcome, i, closed_trades, date.strftime("%d-%m-%Y"))
                peak_equity = max(peak_equity, equity)
                drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0
                max_drawdown = max(max_drawdown, drawdown)

            elif high_bar >= target:
                equity += _close(trade, target, "win", i, closed_trades, date.strftime("%d-%m-%Y"))
                peak_equity = max(peak_equity, equity)
                drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0
                max_drawdown = max(max_drawdown, drawdown)

            elif is_entry_bar:
                # Entry bar: SL and target already checked; skip TRL
                still_open.append(trade)

            else:
                # Trailing exit check
                trailing_triggered = False
                exit_price = None
                exit_date_str = None

                if USE_ATR_TRAILING and "ATR" in df.columns:
                    # ATR-based trailing: exit if close < (highest_high_since_entry - multiplier × ATR)
                    atr_val = df["ATR"].iloc[bar]
                    if not pd.isna(atr_val):
                        # Get highest high since entry
                        entry_bar = trade.get("entry_bar", bar)
                        highest_since_entry = float(df["High"].iloc[entry_bar:bar + 1].max())
                        trailing_stop = highest_since_entry - (TRAILING_ATR_MULTIPLIER * atr_val)
                        
                        if close_bar < trailing_stop:
                            trailing_triggered = True
                            if bar + 1 < len(df):
                                exit_price = float(df["Open"].iloc[bar + 1])
                                exit_date_str = df.index[bar + 1].strftime("%d-%m-%Y")
                            else:
                                exit_price = float(df["Close"].iloc[bar])
                                exit_date_str = df.index[bar].strftime("%d-%m-%Y")
                else:
                    # EMA-based trailing (default): exit if close < EMA20
                    ema20 = None
                    if "EMA20" in df.columns:
                        val = df["EMA20"].iloc[bar]
                        if not pd.isna(val):
                            ema20 = float(val)

                    if ema20 is not None and close_bar < ema20:
                        trailing_triggered = True
                        if bar + 1 < len(df):
                            exit_price = float(df["Open"].iloc[bar + 1])
                            exit_date_str = df.index[bar + 1].strftime("%d-%m-%Y")
                        else:
                            exit_price = float(df["Close"].iloc[bar])
                            exit_date_str = df.index[bar].strftime("%d-%m-%Y")

                if trailing_triggered and exit_price is not None:
                    equity += _close(trade, exit_price, "trail", i, closed_trades, exit_date_str)
                else:
                    still_open.append(trade)

        active_trades = still_open

        # ── STEP B: Open new trades if slots are available ────────────────────
        if i >= len(all_dates) - 1:
            continue

        # Market regime filter intentionally disabled
        regime_ok = True
        regime_label = "DISABLED"

        effective_max = MAX_CONCURRENT_TRADES

        if len(active_trades) >= effective_max:
            continue

        active_tickers = {t["ticker"] for t in active_trades}
        candidates = scan_candidates(stock_data, date)
        candidates = [c for c in candidates if c["ticker"] not in active_tickers]

        slots = effective_max - len(active_trades)
        added = 0

        # Pre-compute sector occupancy for concentration cap
        active_sector_counts: dict[str, int] = defaultdict(int)
        for t in active_trades:
            active_sector_counts[t.get("sector", "OTHER")] += 1

        for cand in candidates:
            if added >= slots:
                break

            # Sector concentration cap
            sector = get_sector(cand["ticker"])
            if active_sector_counts[sector] >= MAX_TRADES_PER_SECTOR:
                continue

            next_bar = cand["idx"] + 1
            if next_bar >= len(cand["df"]):
                continue

            # Entry confirmation: next bar must close at or above breakout level
            bar_high = float(cand["df"]["High"].iloc[next_bar])
            bar_close = float(cand["df"]["Close"].iloc[next_bar])
            if bar_high < cand["entry"] or bar_close < cand["entry"]:
                continue

            entry_price = round(float(cand["entry"]), 2)
            stop_loss = round(float(cand["stop_loss"]), 2)
            target = round(float(cand["target"]), 2)

            # Slippage: we fill slightly above the signal price on entry
            effective_entry = round(float(entry_price * (1 + SLIPPAGE_PCT)), 2)

            # Risk per share uses the actual fill (effective_entry) vs original SL
            risk_per_share = effective_entry - stop_loss
            if risk_per_share <= 0:
                continue

            # Size so that a full stop-loss = exactly RISK_PER_TRADE % of equity
            qty = (equity * RISK_PER_TRADE / 100) / risk_per_share

            # Position size cap — single trade cannot exceed MAX_POSITION_PCT of equity
            max_qty = (equity * MAX_POSITION_PCT / 100) / effective_entry
            qty = min(qty, max_qty)
            if qty <= 0:
                continue

            entry_stock_date = cand["df"].index[next_bar]
            if entry_stock_date in all_dates:
                nifty_entry_idx = all_dates.get_loc(entry_stock_date)
            else:
                nifty_entry_idx = i + 1

            new_trade: Trade = {
                "ticker": cand["ticker"],
                "name": cand["name"],
                "sector": sector,
                "df": cand["df"],
                "entry_price": entry_price,  # signal / trigger level
                "effective_entry": effective_entry,  # actual fill (used for P&L)
                "stop_loss": stop_loss,
                "target": target,
                "active_sl": stop_loss,
                "be_hit": False,
                "nifty_entry_idx": nifty_entry_idx,
                "signal_date": date.strftime("%d-%m-%Y"),
                "qty": qty,
                "score": cand["score"],
                "volume_ratio": cand["volume_ratio"],
                "entry_bar": next_bar,  # store for ATR trailing
            }
            active_trades.append(new_trade)
            active_tickers.add(cand["ticker"])
            active_sector_counts[sector] += 1  # keep concentration tally current
            added += 1

    # Force-close anything still open at end of data
    last_i = len(all_dates) - 1
    last_date = all_dates[last_i]

    for trade in active_trades:
        df = trade["df"]
        if last_date in df.index:
            last_bar = df.index.get_loc(last_date)
        else:
            past = df.index[df.index < last_date]
            if past.empty:
                continue
            last_bar = df.index.get_loc(past[-1])

        exit_price = float(df["Close"].iloc[last_bar])
        equity += _close(trade, exit_price, "trail", last_i, closed_trades, df.index[last_bar].strftime("%d-%m-%Y"))

    peak_equity = max(peak_equity, equity)
    drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0
    max_drawdown = max(max_drawdown, drawdown)

    return closed_trades, equity, max_drawdown


# ── Analysis helpers ──────────────────────────────────────────────────────────


def _period_stats(ts: list[Trade]) -> PeriodStats:
    """Aggregate trade stats for a list of trades (any subset)."""
    total = len(ts)
    wins = sum(1 for t in ts if t["outcome"] == "win")
    losses = sum(1 for t in ts if t["outcome"] == "loss")
    breakevens = sum(1 for t in ts if t["outcome"] == "breakeven")
    trails = sum(1 for t in ts if t["outcome"] == "trail")
    win_rate = round(float(wins / total * 100), 1) if total else 0.0
    pnl_abs = sum(t.get("pnl_abs", 0) for t in ts)
    pnl_pct = round(float(pnl_abs / STARTING_EQUITY * 100), 2) if STARTING_EQUITY else 0.0
    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "breakevens": breakevens,
        "trails": trails,
        "win_rate": win_rate,
        "pnl_abs": round(float(pnl_abs), 2),
        "pnl_pct": pnl_pct,
    }


def print_year_breakdown(trades: list[Trade], width: int = 62) -> None:
    """Print a compact year-by-year performance table + timeout sub-table."""
    if not trades:
        return

    by_year: dict[int, list[Trade]] = defaultdict(list)
    for t in trades:
        by_year[int(t["signal_date"][-4:])].append(t)

    print()
    print("=" * width)
    print(f"{'YEAR-BY-YEAR BREAKDOWN':^{width}}")
    print("=" * width)
    hdr = f"  {'Year':<6}  {'Trades':>6}  {'Wins':>4}  {'Win%':>5}  {'Approx Net P&L':>18}"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    for year in sorted(by_year):
        s = _period_stats(by_year[year])
        print(
            f"  {year:<6}  {s['total']:>6}  {s['wins']:>4}  "
            f"{s['win_rate']:>4.1f}%  "
            f"{s['pnl_pct']:>+7.2f}%  "
            f"(Rs.{s['pnl_abs']:>+11,.0f})"
        )

    # ── Timeout sub-table (Part 5 — detect regime shifts) ─────────────────────
    print()
    print(f"  {'Trailing exit details by year':^{width - 2}}")
    to_hdr = f"  {'Year':<6}  {'Trailing':>8}  {'Avg TR%':>8}  {'interpretation':>20}"
    print(to_hdr)
    print("  " + "-" * (len(to_hdr) - 2))
    for year in sorted(by_year):
        to_trades = [t for t in by_year[year] if t["outcome"] == "trail"]
        if not to_trades:
            print(f"  {year:<6}  {'—':>8}  {'—':>8}")
            continue
        avg_to = round(float(sum(t["pnl_pct"] for t in to_trades) / len(to_trades)), 2)
        note = "trending" if avg_to >= 1.0 else ("choppy" if avg_to <= -1.0 else "sideways")
        print(f"  {year:<6}  {len(to_trades):>8}  {avg_to:>+8.2f}%  {note:>20}")

    print("=" * width)


def print_volume_analysis(trades: list[Trade], width: int = 62) -> None:
    """
    Compare average entry volume ratio across outcomes.

    A large WIN vs BREAKEVEN gap suggests the volume filter has room to be
    tightened (raise VOLUME_MIN_RATIO) to improve precision.
    A small gap means volume alone is not a strong differentiator.
    """

    def _avg_vol(outcome: str) -> tuple[float, int]:
        ts = [t for t in trades if t["outcome"] == outcome]
        if not ts:
            return 0.0, 0
        return round(float(sum(t.get("volume_ratio", 0) for t in ts) / len(ts)), 2), len(ts)

    vol_win, n_win = _avg_vol("win")
    vol_be, n_be = _avg_vol("breakeven")
    vol_loss, n_loss = _avg_vol("loss")
    vol_to, n_to = _avg_vol("trail")

    diff = round(float(vol_win - vol_be), 2)
    if diff > 0.50:
        interp = "Strong edge  — WIN trades carry noticeably higher volume"
    elif diff > 0.20:
        interp = "Modest edge  — volume partially differentiates wins"
    else:
        interp = "Weak edge    — volume alone doesn't separate wins from BEs"

    print()
    print("=" * width)
    print(f"{'VOLUME ANALYSIS':^{width}}")
    print("=" * width)
    hdr = f"  {'Outcome':<16}  {'Avg Vol Ratio':>13}  {'Count':>6}"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    print(f"  {'WIN':<16}  {vol_win:>12.2f}x  {n_win:>6}")
    print(f"  {'BREAKEVEN':<16}  {vol_be:>12.2f}x  {n_be:>6}")
    print(f"  {'LOSS':<16}  {vol_loss:>12.2f}x  {n_loss:>6}")
    print(f"  {'TRAILING':<16}  {vol_to:>12.2f}x  {n_to:>6}")
    print("  " + "-" * (len(hdr) - 2))
    sign = "+" if diff >= 0 else ""
    print(f"  {'WIN vs BE diff':<16}  {sign}{diff:>12.2f}x")
    print()
    print(f"  {interp}")
    print("=" * width)


def print_walkforward_summary(trades: list[Trade], width: int = 62) -> None:
    """
    Split trades into in-sample (before WALK_FORWARD_SPLIT_YEAR) and
    out-of-sample (from WALK_FORWARD_SPLIT_YEAR onward), then print
    side-by-side stats to assess strategy robustness.

    Note: P&L shown here sums per-trade pnl_abs as an approximation;
    compounding effects mean this differs slightly from the main equity curve.
    """
    train = [t for t in trades if int(t["signal_date"][-4:]) < WALK_FORWARD_SPLIT_YEAR]
    test = [t for t in trades if int(t["signal_date"][-4:]) >= WALK_FORWARD_SPLIT_YEAR]

    print()
    print("=" * width)
    print(f"{'WALK-FORWARD VALIDATION':^{width}}")
    print(f"{'(split year: ' + str(WALK_FORWARD_SPLIT_YEAR) + ')':^{width}}")
    print("=" * width)

    for label, ts in [
        (f"IN-SAMPLE   (train) — before {WALK_FORWARD_SPLIT_YEAR}", train),
        (f"OUT-OF-SAMPLE (test) — from {WALK_FORWARD_SPLIT_YEAR} onward", test),
    ]:
        print(f"\n  {label}")
        print("  " + "-" * (width - 2))
        if not ts:
            print("    No trades in this period.")
            continue
        s = _period_stats(ts)
        print(f"  {'Trades':<28}  {s['total']}")
        print(f"  {'Wins / Losses':<28}  {s['wins']} / {s['losses']}")
        print(f"  {'Breakevens / Trailing':<28}  {s['breakevens']} / {s['trails']}")
        print(f"  {'Win rate':<28}  {s['win_rate']:.1f}%")
        print(f"  {'Approx net P&L':<28}  {s['pnl_pct']:+.2f}%  (Rs.{s['pnl_abs']:>+,.0f})")

    print()
    print("=" * width)


# ── Summary printer ───────────────────────────────────────────────────────────


def print_summary(trades: list[Trade], final_equity: float, max_drawdown: float = 0.0) -> None:
    """Print trade statistics, equity summary, and all robustness sections."""
    width = 62
    total = len(trades)
    wins = sum(1 for t in trades if t["outcome"] == "win")
    losses = sum(1 for t in trades if t["outcome"] == "loss")
    breakevens = sum(1 for t in trades if t["outcome"] == "breakeven")
    trails = sum(1 for t in trades if t["outcome"] == "trail")
    win_rate = round(float(wins / total * 100), 1) if total else 0.0

    net_pct = round(float((final_equity - STARTING_EQUITY) / STARTING_EQUITY * 100), 2)
    net_abs = round(float(final_equity - STARTING_EQUITY), 2)

    avg_win = round(float(sum(t["pnl_pct"] for t in trades if t["outcome"] == "win") / wins), 2) if wins else 0.0
    avg_loss = round(float(sum(t["pnl_pct"] for t in trades if t["outcome"] == "loss") / losses), 2) if losses else 0.0
    avg_be = (
        round(float(sum(t["pnl_pct"] for t in trades if t["outcome"] == "breakeven") / breakevens), 2)
        if breakevens
        else 0.0
    )
    avg_trail = (
        round(float(sum(t["pnl_pct"] for t in trades if t["outcome"] == "trail") / trails), 2) if trails else 0.0
    )
    avg_hold = round(float(sum(t["bars_held"] for t in trades) / total), 1) if total else 0.0
    avg_rr = round(float(-avg_win / avg_loss), 2) if avg_loss != 0 else 0.0
    total_cost = round(float(sum(t.get("trade_cost", 0) for t in trades)), 2)

    print()
    print("=" * width)
    print(f"{'BACKTEST SUMMARY':^{width}}")
    print("=" * width)

    # ── Configuration ──────────────────────────────────────────────────────────
    print(f"  {'Strategy':<30}  Trend + Coil breakout")
    print(f"  {'Market filter':<30}  Nifty close > EMA50")
    print(f"  {'Coil window':<30}  {COIL_CANDLES} candles  |  range < {MAX_RANGE_PCT}%")
    print(f"  {'Entry':<30}  period_high (breakout confirmed)")
    print(f"  {'Stop loss':<30}  period_low")
    print(f"  {'Target':<30}  entry + {int(REWARD_RATIO)}x risk  (1:{int(REWARD_RATIO)} RR)")
    print(f"  {'Breakeven rule':<30}  SL -> entry at high >= 1.5R & close > entry")
    score_note = f">= {MIN_SCORE_THRESHOLD}" if MIN_SCORE_THRESHOLD > 0 else "disabled (0)"
    print(f"  {'Min score filter':<30}  {score_note}")
    print(f"  {'Trailing exit':<30}  Close < EMA20 (exit next open)")
    print(f"  {'Risk per trade':<30}  {RISK_PER_TRADE}% of equity  (per position)")
    print(f"  {'Max concurrent trades':<30}  {MAX_CONCURRENT_TRADES}")
    print(f"  {'Sector cap':<30}  max {MAX_TRADES_PER_SECTOR} open trades per sector")
    print(f"  {'Position cap':<30}  max {MAX_POSITION_PCT}% of equity per trade")
    print(f"  {'Slippage':<30}  {SLIPPAGE_PCT*100:.2f}% per side")
    print(f"  {'Transaction cost':<30}  {COST_PCT*100:.2f}% of trade value")

    # ── Trade counts ───────────────────────────────────────────────────────────
    print("-" * width)
    print(f"  {'Total trades':<30}  {total}")
    print(f"  {'Wins  (target hit)':<30}  {wins}")
    print(f"  {'Losses  (full stop-out)':<30}  {losses}")
    print(f"  {'Breakevens  (SL -> entry)':<30}  {breakevens}")
    print(f"  {'Trailing exits  (<EMA20)':<30}  {trails}")
    print(f"  {'Win rate':<30}  {win_rate}%")

    # ── Per-outcome averages ────────────────────────────────────────────────────
    print("-" * width)
    print(f"  {'Avg win':<30}  +{avg_win}%")
    print(f"  {'Avg loss  (full)':<30}  {avg_loss}%")
    print(f"  {'Avg breakeven exit':<30}  {avg_be:+.2f}%")
    print(f"  {'Avg trailing exit':<30}  {avg_trail:+.2f}%")
    print(f"  {'Realised RR':<30}  1 : {avg_rr}")
    print(f"  {'Avg hold (bars)':<30}  {avg_hold}")

    # ── Equity ─────────────────────────────────────────────────────────────────
    print("-" * width)
    print(f"  {'Starting equity':<30}  Rs. {STARTING_EQUITY:>10,.0f}")
    print(f"  {'Final equity':<30}  Rs. {final_equity:>10,.0f}")
    sign = "+" if net_pct >= 0 else ""
    print(f"  {'Net P&L  (after costs)':<30}  Rs. {net_abs:>+10,.0f}  ({sign}{net_pct}%)")
    print(f"  {'Max drawdown':<30}  {max_drawdown*100:.2f}%")
    print(f"  {'Total costs paid':<30}  Rs. {total_cost:>10,.0f}")
    print("=" * width)

    # ── Extended analysis sections ─────────────────────────────────────────────
    print_year_breakdown(trades, width)
    print_volume_analysis(trades, width)
    print_walkforward_summary(trades, width)
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def send_backtest_to_discord(strategy: str, trades: list[Trade], final_equity: float, max_drawdown: float) -> None:
    """Send backtest summary to Discord if webhook is configured."""
    if not DISCORD_PORTFOLIO_WEBHOOK:
        return
        
    total = len(trades)
    if total == 0:
        return
        
    wins = sum(1 for t in trades if t["outcome"] == "win")
    losses = sum(1 for t in trades if t["outcome"] == "loss")
    win_rate = round(float(wins / total * 100), 1) if total else 0.0
    
    net_pct = round(float((final_equity - STARTING_EQUITY) / STARTING_EQUITY * 100), 2)
    net_abs = round(float(final_equity - STARTING_EQUITY), 2)
    
    avg_win = round(float(sum(t["pnl_pct"] for t in trades if t["outcome"] == "win") / wins), 2) if wins else 0.0
    avg_loss = round(float(sum(t["pnl_pct"] for t in trades if t["outcome"] == "loss") / losses), 2) if losses else 0.0
    avg_rr = round(float(avg_win / avg_loss), 2) if avg_loss != 0 else 0.0
    
    date_str = get_now().strftime("%d %b %Y, %H:%M")
    direction = "LONG" if strategy == "long_breakout" else "SHORT"
    emoji = "🟢" if direction == "LONG" else "🔴"
    
    lines = []
    lines.append(f"{emoji} **BACKTEST SUMMARY ({direction})**")
    lines.append(f"*{date_str}*")
    lines.append("")
    lines.append(f"**Metrics**")
    lines.append(f"• Total Trades: **{total}** (W:{wins} | L:{losses})")
    lines.append(f"• Win Rate: **{win_rate}%**")
    lines.append(f"• Net P&L: **{'+' if net_pct >= 0 else ''}{net_pct}%** (₹{net_abs:,.0f})")
    lines.append(f"• Max Drawdown: **{max_drawdown*100:.2f}%**")
    lines.append(f"• Realized R:R: **1:{avg_rr}**")
    lines.append("")
    lines.append(f"*Note: Detailed trade logs exported to CSV.*")
    
    message = "\n".join(lines)
    
    try:
        import requests
        resp = requests.post(DISCORD_PORTFOLIO_WEBHOOK, json={"content": message}, timeout=10)
        if resp.status_code == 204:
            print("  [+] Backtest summary posted to Discord")
        else:
            print(f"  [!] Failed to post to Discord (HTTP {resp.status_code})")
    except Exception as e:
        print(f"  [!] Discord error: {e}")



def run_backtest_strategy(export: bool = False, refresh: bool = True) -> None:
    """Run the full breakout backtest pipeline."""
    width = 62
    print("=" * width)
    print(f"{'SWING TRADING BACKTEST  —  FULL STRATEGY':^{width}}")
    print(f"{'Universe : ' + str(len(STOCKS)) + ' stocks':^{width}}")
    print(
        f"{f'Coil {COIL_CANDLES}c  Range<{int(MAX_RANGE_PCT)}%  NearHigh<{int(NEAR_HIGH_PCT)}%  RR 1:{int(REWARD_RATIO)}':^{width}}"
    )
    print(f"{'Run date : ' + get_today_str():^{width}}")
    print("=" * width)

    print("\n  Fetching data ...\n")
    all_tickers = [NIFTY_TICKER] + list(STOCKS.keys())
    raw = fetch_all(all_tickers, refresh=refresh)

    if NIFTY_TICKER not in raw:
        print("\n  ERROR: Could not fetch Nifty data. Aborting.")
        return

    nifty_df = add_indicators(raw[NIFTY_TICKER])
    stock_data = {t: add_indicators(df) for t, df in raw.items() if t != NIFTY_TICKER}

    print(f"\n  {len(stock_data)}/{len(STOCKS)} stocks loaded.\n")

    if not stock_data:
        print("  No stock data available. Aborting.")
        return

    print("─" * width)
    print(f"{'TRADE LOG':^{width}}")
    print("─" * width)

    trades, final_equity, max_drawdown = run_backtest(nifty_df, stock_data)

    if not trades:
        print("\n  No trades were generated in the backtest period.")
        print("  Possible reasons:")
        print("    - Market was bearish (Nifty below EMA50) most of the period.")
        print("    - No stock formed a coil tight enough to pass the filter.")
        print("    - Breakout level was never triggered on the next bar.")
        print()
        return

    print_summary(trades, final_equity, max_drawdown)

    # Save to backtest history
    if BACKTEST_VERSIONING:
        total = len(trades)
        wins = sum(1 for t in trades if t["outcome"] == "win")
        losses = sum(1 for t in trades if t["outcome"] == "loss")
        win_rate = round(float(wins / total * 100), 1) if total else 0.0
        
        win_amounts = [abs(t["pnl_pct"]) for t in trades if t["outcome"] == "win"]
        loss_amounts = [abs(t["pnl_pct"]) for t in trades if t["outcome"] == "loss"]
        avg_win = sum(win_amounts) / len(win_amounts) if win_amounts else 0.0
        avg_loss = sum(loss_amounts) / len(loss_amounts) if loss_amounts else 0.0
        avg_rr = round(avg_win / avg_loss, 2) if avg_loss > 0 else 0.0
        
        avg_hold = round(float(sum(t["bars_held"] for t in trades) / total), 1) if total else 0.0
        net_pct = round(float((final_equity - STARTING_EQUITY) / STARTING_EQUITY * 100), 2)
        
        save_backtest_result(
            strategy="long_breakout",
            total_trades=total,
            win_rate=win_rate,
            net_pct=net_pct,
            final_equity=final_equity,
            avg_rr=avg_rr,
            max_drawdown=max_drawdown,
            avg_hold=avg_hold,
            notes=f"Config: COIL={COIL_CANDLES}, RANGE={MAX_RANGE_PCT}%, RR={REWARD_RATIO}",
        )
        send_backtest_to_discord("long_breakout", trades, final_equity, max_drawdown)
        print(f"\n  [+] Saved to backtest history\n")

    if export:
        df_trades = pd.DataFrame(trades)
        if "df" in df_trades.columns:
            df_trades = df_trades.drop(columns=["df"])
        filename = "trades_long.csv"
        df_trades.to_csv(filename, index=False)
        print(f"\n  [+] Exported {len(trades)} trades to {filename}\n")


# ══════════════════════════════════════════════════════════════════════════════
# SHORT BREAKDOWN BACKTEST
# ══════════════════════════════════════════════════════════════════════════════


def scan_candidates_short(
    stock_data: dict[str, pd.DataFrame],
    date: pd.Timestamp,
) -> list[Candidate]:
    """
    Return all stocks passing Liquidity + Bearish Trend + Coil-near-low +
    Volume filters for `date`, each carrying its score and trade levels.
    Sorted best-first.
    """
    candidates: list[Candidate] = []

    for ticker, df in stock_data.items():
        if date not in df.index:
            continue
        idx = df.index.get_loc(date)

        if idx < max(COIL_CANDLES, EMA_LONG, VOLUME_AVG_PERIOD):
            continue

        if float(df["Close"].iloc[idx]) < MIN_PRICE:
            continue

        if not check_liquidity(df, idx):
            continue

        trend = check_trend_short(df, idx)
        if trend is None:
            continue

        coil = check_consolidation_short(df, idx)
        if coil is None:
            continue

        vol = check_volume(df, idx)
        if vol is None:
            continue

        # Candle strength filter for short (DISABLED Apr 2022 - hurt performance)
        # from strategies.short_breakout import check_candle_strength_short
        # candle = check_candle_strength_short(df, idx)
        # if candle is None:
        #     continue

        # Short: entry = period_low, SL = period_high
        entry = coil["period_low"]
        stop_loss = coil["period_high"]
        risk = stop_loss - entry
        target = entry - REWARD_RATIO * risk
        sc = score_short_breakout(trend, coil)

        if sc["total"] < MIN_SCORE_THRESHOLD:
            continue

        candidates.append(
            {
                "ticker": ticker,
                "name": STOCKS.get(ticker, ticker),
                "df": df,
                "idx": idx,
                "trend": trend,
                "coil": coil,
                "entry": entry,
                "stop_loss": stop_loss,
                "target": target,
                "score": sc["total"],
                "volume_ratio": vol["surge_ratio"],
            }
        )

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates


def _close_short(
    trade: Trade,
    exit_price: float,
    outcome: str,
    nifty_idx: int,
    closed_trades: list[Trade],
    exit_date: str,
) -> float:
    """
    Finalise an open SHORT trade: apply exit slippage (higher fill on cover),
    deduct transaction costs, record outcome, and print log line.

    :param trade: The Active Trade object
    :param exit_price: The exact level the trade exited at
    :param outcome: Reason for exit (e.g. 'win', 'loss')
    :param nifty_idx: The current day's index
    :param closed_trades: The array to append the finalized trade to
    :param exit_date: The date string (DD-MM-YYYY) of the exit

    Execution model (SHORT)
    -----------------------
      effective_entry  : stored on the trade at open (shorted lower)
      effective_exit   : exit_price * (1 + SLIPPAGE_PCT)  (covered higher)
      cost             : effective_entry × qty × COST_PCT
      pnl_abs          : (effective_entry − effective_exit) × qty − cost
                         (profit when price falls)
    """
    eff_entry = float(trade["effective_entry"])
    eff_exit = round(float(exit_price * (1 + SLIPPAGE_PCT)), 2)
    qty = float(trade["qty"])
    cost = round(float(eff_entry * qty * COST_PCT), 2)
    pnl_abs = qty * (eff_entry - eff_exit) - cost
    pnl_pct = round(float(pnl_abs / (eff_entry * qty) * 100), 2) if (eff_entry * qty) != 0 else 0.0
    bars_held = int(nifty_idx - trade["nifty_entry_idx"])

    trade["exit_price"] = round(float(exit_price), 2)
    trade["exit_date"] = exit_date
    trade["outcome"] = outcome
    trade["pnl_abs"] = round(float(pnl_abs), 2)
    trade["pnl_pct"] = pnl_pct
    trade["trade_cost"] = cost
    trade["bars_held"] = bars_held
    closed_trades.append(trade)

    icon = {"win": "WIN ", "loss": "LOSS", "breakeven": "BE  ", "trail": "TRL "}.get(outcome, "????")
    print(
        f"  {trade['signal_date']:<12} "
        f"{exit_date:<12} "
        f"{trade['name']:<20} "
        f"{trade['score']:>5.1f} "
        f"vol {trade['volume_ratio']:>4.2f}x "
        f"Rs.{eff_entry:>7,.0f} "
        f"Rs.{trade['stop_loss']:>7,.0f} "
        f"Rs.{trade['target']:>8,.0f} "
        f"Rs.{eff_exit:>7,.0f} "
        f"{pnl_pct:>+6.2f}%  {icon}"
    )
    return float(pnl_abs)


def run_backtest_short(
    nifty_df: pd.DataFrame,
    stock_data: dict[str, pd.DataFrame],
) -> tuple[list[Trade], float]:
    """
    Concurrent multi-position SHORT backtest.

    STEP A (each day) — Update every open short trade:
      • Apply breakeven rule (Low <= entry - 1.5R and Close < entry).
      • Close on SL hit (high >= active_sl) / target hit (low <= target) /
        EMA20 trailing stop (Close > EMA20).
      • Update equity on close.

    STEP B (each day) — Open new short trades if slots are available:
      • Market must be bearish (get_market_regime_short).
      • Scan all stocks → Bearish Trend + Coil-near-low + Volume → score.
      • For each candidate (best score first), confirm entry:
          next bar must have Low <= entry AND Close <= entry.
      • Size each trade so that a full stop-loss costs RISK_PER_TRADE % equity.

    Returns (closed_trades, final_equity, max_drawdown).
    """
    all_dates = nifty_df.index
    start_idx = max(EMA_LONG + 10, len(all_dates) - BACKTEST_DAYS)
    equity = float(STARTING_EQUITY)
    peak_equity = equity
    max_drawdown = 0.0

    active_trades: list[Trade] = []
    closed_trades: list[Trade] = []

    print(
        f"\n  Short Backtest range  : {all_dates[start_idx].strftime('%d-%m-%Y')}  ->  {all_dates[-1].strftime('%d-%m-%Y')}"
    )
    print(f"  Bars in period       : {len(all_dates) - start_idx}")
    print(f"  Max concurrent       : {MAX_CONCURRENT_TRADES} trades\n")

    col = (
        f"{'Entry Date':<12} {'Exit Date':<12} {'Name':<20} {'Score':>5} {'Vol':>7} "
        f"{'Entry':>8} {'SL':>8} {'Target':>9} {'Exit':>8} {'PnL%':>6}  Result"
    )
    print("  " + col)
    print("  " + "-" * len(col))

    for i in range(start_idx, len(all_dates)):
        date = all_dates[i]

        # ── STEP A: Update every open short trade ────────────────────────────
        still_open: list[Trade] = []

        for trade in active_trades:
            if i < trade["nifty_entry_idx"]:
                still_open.append(trade)
                continue

            df = trade["df"]
            entry = trade["entry_price"]
            target = trade["target"]
            risk = trade["stop_loss"] - entry  # risk = SL - entry for shorts

            if date not in df.index:
                still_open.append(trade)
                continue

            bar = df.index.get_loc(date)
            high_bar = float(df["High"].iloc[bar])
            low_bar = float(df["Low"].iloc[bar])
            close_bar = float(df["Close"].iloc[bar])

            is_entry_bar = i == trade["nifty_entry_idx"]

            # Breakeven: skip on entry bar to prevent same-bar BE trap
            if not is_entry_bar and not trade["be_hit"] and low_bar <= entry - risk * 1.5 and close_bar < entry:
                trade["active_sl"] = entry
                trade["be_hit"] = True

            # SL hit: price goes UP to stop loss (short loses when price rises)
            if high_bar >= trade["active_sl"]:
                outcome = "breakeven" if trade["be_hit"] else "loss"
                equity += _close_short(trade, trade["active_sl"], outcome, i, closed_trades, date.strftime("%d-%m-%Y"))
                peak_equity = max(peak_equity, equity)
                drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0
                max_drawdown = max(max_drawdown, drawdown)

            # Target hit: price goes DOWN to target (short wins when price falls)
            elif low_bar <= target:
                equity += _close_short(trade, target, "win", i, closed_trades, date.strftime("%d-%m-%Y"))
                peak_equity = max(peak_equity, equity)
                drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0
                max_drawdown = max(max_drawdown, drawdown)

            elif is_entry_bar:
                # Entry bar: SL and target already checked; skip TRL
                still_open.append(trade)

            else:
                # Trailing exit check
                trailing_triggered = False
                exit_price = None
                exit_date_str = None

                if USE_ATR_TRAILING and "ATR" in df.columns:
                    # ATR-based trailing for shorts: exit if close > (lowest_low_since_entry + multiplier × ATR)
                    atr_val = df["ATR"].iloc[bar]
                    if not pd.isna(atr_val):
                        # Get lowest low since entry
                        entry_bar = trade.get("entry_bar", bar)
                        lowest_since_entry = float(df["Low"].iloc[entry_bar:bar + 1].min())
                        trailing_stop = lowest_since_entry + (TRAILING_ATR_MULTIPLIER * atr_val)
                        
                        if close_bar > trailing_stop:
                            trailing_triggered = True
                            if bar + 1 < len(df):
                                exit_price = float(df["Open"].iloc[bar + 1])
                                exit_date_str = df.index[bar + 1].strftime("%d-%m-%Y")
                            else:
                                exit_price = float(df["Close"].iloc[bar])
                                exit_date_str = df.index[bar].strftime("%d-%m-%Y")
                else:
                    # EMA-based trailing (default): exit if close > EMA20
                    ema20 = None
                    if "EMA20" in df.columns:
                        val = df["EMA20"].iloc[bar]
                        if not pd.isna(val):
                            ema20 = float(val)

                    if ema20 is not None and close_bar > ema20:
                        trailing_triggered = True
                        if bar + 1 < len(df):
                            exit_price = float(df["Open"].iloc[bar + 1])
                            exit_date_str = df.index[bar + 1].strftime("%d-%m-%Y")
                        else:
                            exit_price = float(df["Close"].iloc[bar])
                            exit_date_str = df.index[bar].strftime("%d-%m-%Y")

                if trailing_triggered and exit_price is not None:
                    equity += _close_short(trade, exit_price, "trail", i, closed_trades, exit_date_str)
                    peak_equity = max(peak_equity, equity)
                    drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0
                    max_drawdown = max(max_drawdown, drawdown)
                else:
                    still_open.append(trade)

        active_trades = still_open

        # ── STEP B: Open new short trades if slots are available ─────────────
        if i >= len(all_dates) - 1:
            continue

        # Market regime filter intentionally disabled
        regime_ok = True
        regime_label = "DISABLED"

        effective_max = MAX_CONCURRENT_TRADES

        if len(active_trades) >= effective_max:
            continue

        active_tickers = {t["ticker"] for t in active_trades}
        candidates = scan_candidates_short(stock_data, date)
        candidates = [c for c in candidates if c["ticker"] not in active_tickers]

        slots = effective_max - len(active_trades)
        added = 0

        active_sector_counts: dict[str, int] = defaultdict(int)
        for t in active_trades:
            active_sector_counts[t.get("sector", "OTHER")] += 1

        for cand in candidates:
            if added >= slots:
                break

            sector = get_sector(cand["ticker"])
            if active_sector_counts[sector] >= MAX_TRADES_PER_SECTOR:
                continue

            next_bar = cand["idx"] + 1
            if next_bar >= len(cand["df"]):
                continue

            # Entry confirmation: next bar must break down below entry
            bar_low = float(cand["df"]["Low"].iloc[next_bar])
            bar_close = float(cand["df"]["Close"].iloc[next_bar])
            if bar_low > cand["entry"] or bar_close > cand["entry"]:
                continue

            entry_price = round(float(cand["entry"]), 2)
            stop_loss = round(float(cand["stop_loss"]), 2)
            target = round(float(cand["target"]), 2)

            # Slippage: short entry fills slightly lower than signal price
            effective_entry = round(float(entry_price * (1 - SLIPPAGE_PCT)), 2)

            # Risk per share uses effective_entry vs original SL (above)
            risk_per_share = stop_loss - effective_entry
            if risk_per_share <= 0:
                continue

            qty = (equity * RISK_PER_TRADE / 100) / risk_per_share

            max_qty = (equity * MAX_POSITION_PCT / 100) / effective_entry
            qty = min(qty, max_qty)
            if qty <= 0:
                continue

            entry_stock_date = cand["df"].index[next_bar]
            if entry_stock_date in all_dates:
                nifty_entry_idx = all_dates.get_loc(entry_stock_date)
            else:
                nifty_entry_idx = i + 1

            new_trade: Trade = {
                "ticker": cand["ticker"],
                "name": cand["name"],
                "sector": sector,
                "df": cand["df"],
                "entry_price": entry_price,
                "effective_entry": effective_entry,
                "stop_loss": stop_loss,
                "target": target,
                "active_sl": stop_loss,
                "be_hit": False,
                "nifty_entry_idx": nifty_entry_idx,
                "signal_date": date.strftime("%d-%m-%Y"),
                "qty": qty,
                "score": cand["score"],
                "volume_ratio": cand["volume_ratio"],
                "entry_bar": next_bar,  # store for ATR trailing
            }
            active_trades.append(new_trade)
            active_tickers.add(cand["ticker"])
            active_sector_counts[sector] = active_sector_counts[sector] + 1
            added += 1

    # Force-close anything still open at end of data
    last_i = len(all_dates) - 1
    last_date = all_dates[last_i]

    for trade in active_trades:
        df = trade["df"]
        if last_date in df.index:
            last_bar = df.index.get_loc(last_date)
        else:
            past = df.index[df.index < last_date]
            if past.empty:
                continue
            last_bar = df.index.get_loc(past[-1])

        exit_price = float(df["Close"].iloc[last_bar])
        equity += _close_short(
            trade, exit_price, "trail", last_i, closed_trades, df.index[last_bar].strftime("%d-%m-%Y")
        )

    peak_equity = max(peak_equity, equity)
    drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0
    max_drawdown = max(max_drawdown, drawdown)

    return closed_trades, equity, max_drawdown


def print_summary_short(trades: list[Trade], final_equity: float, max_drawdown: float = 0.0) -> None:
    """Print trade statistics for SHORT backtest."""
    width = 62
    total = len(trades)
    wins = sum(1 for t in trades if t["outcome"] == "win")
    losses = sum(1 for t in trades if t["outcome"] == "loss")
    breakevens = sum(1 for t in trades if t["outcome"] == "breakeven")
    trails = sum(1 for t in trades if t["outcome"] == "trail")
    win_rate = round(float(wins / total * 100), 1) if total else 0.0

    net_pct = round(float((final_equity - STARTING_EQUITY) / STARTING_EQUITY * 100), 2)
    net_abs = round(float(final_equity - STARTING_EQUITY), 2)

    avg_win = round(float(sum(t["pnl_pct"] for t in trades if t["outcome"] == "win") / wins), 2) if wins else 0.0
    avg_loss = round(float(sum(t["pnl_pct"] for t in trades if t["outcome"] == "loss") / losses), 2) if losses else 0.0
    avg_be = (
        round(float(sum(t["pnl_pct"] for t in trades if t["outcome"] == "breakeven") / breakevens), 2)
        if breakevens
        else 0.0
    )
    avg_trail = (
        round(float(sum(t["pnl_pct"] for t in trades if t["outcome"] == "trail") / trails), 2) if trails else 0.0
    )
    avg_hold = round(float(sum(t["bars_held"] for t in trades) / total), 1) if total else 0.0
    avg_rr = round(float(-avg_win / avg_loss), 2) if avg_loss != 0 else 0.0
    total_cost = round(float(sum(t.get("trade_cost", 0) for t in trades)), 2)

    print()
    print("=" * width)
    print(f"{'SHORT BACKTEST SUMMARY':^{width}}")
    print("=" * width)

    print(f"  {'Strategy':<30}  Short Breakdown (Trend + Coil)")
    print(f"  {'Market filter':<30}  Nifty close < EMA50 (bearish)")
    print(f"  {'Coil window':<30}  {COIL_CANDLES} candles  |  range < {MAX_RANGE_PCT}%")
    print(f"  {'Entry':<30}  period_low (breakdown confirmed)")
    print(f"  {'Stop loss':<30}  period_high (box top)")
    print(f"  {'Target':<30}  entry - {int(REWARD_RATIO)}x risk  (1:{int(REWARD_RATIO)} RR)")
    print(f"  {'Breakeven rule':<30}  SL -> entry at low <= entry-1.5R & close < entry")
    score_note = f">= {MIN_SCORE_THRESHOLD}" if MIN_SCORE_THRESHOLD > 0 else "disabled (0)"
    print(f"  {'Min score filter':<30}  {score_note}")
    print(f"  {'Trailing exit':<30}  Close > EMA20 (exit next open)")
    print(f"  {'Risk per trade':<30}  {RISK_PER_TRADE}% of equity  (per position)")
    print(f"  {'Max concurrent trades':<30}  {MAX_CONCURRENT_TRADES}")
    print(f"  {'Sector cap':<30}  max {MAX_TRADES_PER_SECTOR} open trades per sector")
    print(f"  {'Position cap':<30}  max {MAX_POSITION_PCT}% of equity per trade")
    print(f"  {'Slippage':<30}  {SLIPPAGE_PCT*100:.2f}% per side")
    print(f"  {'Transaction cost':<30}  {COST_PCT*100:.2f}% of trade value")

    print("-" * width)
    print(f"  {'Total trades':<30}  {total}")
    print(f"  {'Wins  (target hit)':<30}  {wins}")
    print(f"  {'Losses  (full stop-out)':<30}  {losses}")
    print(f"  {'Breakevens  (SL -> entry)':<30}  {breakevens}")
    print(f"  {'Trailing exits  (>EMA20)':<30}  {trails}")
    print(f"  {'Win rate':<30}  {win_rate}%")

    print("-" * width)
    print(f"  {'Avg win':<30}  +{avg_win}%")
    print(f"  {'Avg loss  (full)':<30}  {avg_loss}%")
    print(f"  {'Avg breakeven exit':<30}  {avg_be:+.2f}%")
    print(f"  {'Avg trailing exit':<30}  {avg_trail:+.2f}%")
    print(f"  {'Realised RR':<30}  1 : {avg_rr}")
    print(f"  {'Avg hold (bars)':<30}  {avg_hold}")

    print("-" * width)
    print(f"  {'Starting equity':<30}  Rs. {STARTING_EQUITY:>10,.0f}")
    print(f"  {'Final equity':<30}  Rs. {final_equity:>10,.0f}")
    sign = "+" if net_pct >= 0 else ""
    print(f"  {'Net P&L  (after costs)':<30}  Rs. {net_abs:>+10,.0f}  ({sign}{net_pct}%)")
    print(f"  {'Max drawdown':<30}  {max_drawdown*100:.2f}%")
    print(f"  {'Total costs paid':<30}  Rs. {total_cost:>10,.0f}")
    print("=" * width)

    print_year_breakdown(trades, width)
    print_volume_analysis(trades, width)
    print_walkforward_summary(trades, width)
    print()


def run_backtest_strategy_short(export: bool = False, refresh: bool = True) -> None:
    """Run the full short breakdown backtest pipeline."""
    width = 62
    print("=" * width)
    print(f"{'SHORT BREAKDOWN BACKTEST  —  FULL STRATEGY':^{width}}")
    print(f"{'Universe : ' + str(len(STOCKS)) + ' stocks':^{width}}")
    print(
        f"{f'Coil {COIL_CANDLES}c  Range<{int(MAX_RANGE_PCT)}%  NearLow<{int(NEAR_HIGH_PCT)}%  RR 1:{int(REWARD_RATIO)}':^{width}}"
    )
    print(f"{'Run date : ' + get_today_str():^{width}}")
    print("=" * width)

    print("\n  Fetching data ...\n")
    all_tickers = [NIFTY_TICKER] + list(STOCKS.keys())
    raw = fetch_all(all_tickers, refresh=refresh)

    if NIFTY_TICKER not in raw:
        print("\n  ERROR: Could not fetch Nifty data. Aborting.")
        return

    nifty_df = add_indicators(raw[NIFTY_TICKER])
    stock_data = {t: add_indicators(df) for t, df in raw.items() if t != NIFTY_TICKER}

    print(f"\n  {len(stock_data)}/{len(STOCKS)} stocks loaded.\n")

    if not stock_data:
        print("  No stock data available. Aborting.")
        return

    print("─" * width)
    print(f"{'SHORT TRADE LOG':^{width}}")
    print("─" * width)

    trades, final_equity, max_drawdown = run_backtest_short(nifty_df, stock_data)

    if not trades:
        print("\n  No short trades were generated in the backtest period.")
        print("  Possible reasons:")
        print("    - Market was bullish (Nifty above EMA50) most of the period.")
        print("    - No stock formed a coil tight enough near lows to pass filter.")
        print("    - Breakdown level was never triggered on the next bar.")
        print()
        return

    print_summary_short(trades, final_equity, max_drawdown)

    # Save to backtest history
    if BACKTEST_VERSIONING:
        total = len(trades)
        wins = sum(1 for t in trades if t["outcome"] == "win")
        losses = sum(1 for t in trades if t["outcome"] == "loss")
        win_rate = round(float(wins / total * 100), 1) if total else 0.0
        
        win_amounts = [abs(t["pnl_pct"]) for t in trades if t["outcome"] == "win"]
        loss_amounts = [abs(t["pnl_pct"]) for t in trades if t["outcome"] == "loss"]
        avg_win = sum(win_amounts) / len(win_amounts) if win_amounts else 0.0
        avg_loss = sum(loss_amounts) / len(loss_amounts) if loss_amounts else 0.0
        avg_rr = round(avg_win / avg_loss, 2) if avg_loss > 0 else 0.0
        
        avg_hold = round(float(sum(t["bars_held"] for t in trades) / total), 1) if total else 0.0
        net_pct = round(float((final_equity - STARTING_EQUITY) / STARTING_EQUITY * 100), 2)
        
        save_backtest_result(
            strategy="short_breakout",
            total_trades=total,
            win_rate=win_rate,
            net_pct=net_pct,
            final_equity=final_equity,
            avg_rr=avg_rr,
            max_drawdown=max_drawdown,
            avg_hold=avg_hold,
            notes=f"Config: COIL={COIL_CANDLES}, RANGE={MAX_RANGE_PCT}%, RR={REWARD_RATIO}",
        )
        send_backtest_to_discord("short_breakout", trades, final_equity, max_drawdown)
        print(f"\n  [+] Saved to backtest history\n")

    if export:
        df_trades = pd.DataFrame(trades)
        if "df" in df_trades.columns:
            df_trades = df_trades.drop(columns=["df"])
        filename = "trades_short.csv"
        df_trades.to_csv(filename, index=False)
        print(f"\n  [+] Exported {len(trades)} trades to {filename}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="NSE Swing Trade Backtest")
    parser.add_argument(
        "--strategy",
        required=True,
        choices=["long_breakout", "short_breakout"],
        help="Strategy to backtest: long_breakout or short_breakout",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export completed trades to CSV",
    )
    parser.add_argument(
        "--no-refresh",
        action="store_true",
        help="Skip refreshing data - use cached data only",
    )
    args = parser.parse_args()

    # Strategy dispatch — add new strategies here as elif branches
    if args.strategy == "long_breakout":
        run_backtest_strategy(export=args.export, refresh=not args.no_refresh)
    elif args.strategy == "short_breakout":
        run_backtest_strategy_short(export=args.export, refresh=not args.no_refresh)
    else:
        print(f"Unknown strategy: {args.strategy}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

"""
screener.py — Live swing-trade screener for Indian NSE stocks.
==============================================================
Scans the full universe defined in config/stocks.py, applies the
multi-stage breakout filter from strategies/long_breakout.py, scores every
valid setup, and prints ranked trade cards for the best opportunities.

Usage
-----
  python screener.py                              # run with default (long_breakout) strategy
  python screener.py --strategy long_breakout     # explicit long strategy
  python screener.py --strategy short_breakout    # short breakdown strategy

Modes (set LIVE_MODE in config/settings.py)
-------------------------------------------
  LIVE_MODE = False  (default) → verbose scan log — ideal for analysis
  LIVE_MODE = True             → clean output + execution brief — daily use

Pipeline
--------
  Stage 0 : Market regime  — Nifty close > EMA50
  Stage 0b: Liquidity      — ₹5 Cr minimum avg daily turnover
  Stage 1 : Trend          — stock close > EMA50 > EMA200
  Stage 2 : Coil           — tight range + price near recent high
  Stage 3a: Risk           — risk (entry−stop) < MAX_RISK_PCT of entry
  Stage 3b: Volume         — latest volume >= VOLUME_MIN_RATIO × 20d avg
  Stage 3c: Gap-up         — today's open must not have gapped above entry
  Stage 3d: Earnings       — no earnings announcement within blackout window
"""

import sys
import argparse
import os
from typing import TypedDict, List

import pandas as pd
from datetime import datetime, timedelta
from data.cache    import fetch_ohlcv, DataCache
from data.earnings import get_earnings_dates

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── Shared imports ────────────────────────────────────────────────────────────
from config.stocks   import STOCKS
from config.settings import (
    NIFTY_TICKER,
    EMA_SHORT,
    COIL_CANDLES,
    MAX_RANGE_PCT,
    NEAR_HIGH_PCT,
    MAX_RISK_PCT,
    REWARD_RATIO,
    VOLUME_AVG_PERIOD,
    VOLUME_MIN_RATIO,
    GAP_UP_THRESHOLD,
    SCREENER_DAYS,
    EARNINGS_LOOKBACK_DAYS,
    EARNINGS_LOOKAHEAD_DAYS,
    LIVE_MODE,
    MAX_CONCURRENT_TRADES,
    RISK_PER_TRADE,
    MIN_AVG_TURNOVER,
    MIN_PRICE,
    DEAD_TICKERS,
    TICKER_ALIASES,
    PENDING_EXPIRY_DAYS,
    CLOSED_CLEANUP_DAYS,
    MAX_ACTIVE_DAYS,
    SCORE_WEIGHT_RISK,
    SCORE_WEIGHT_RANGE,
    SCORE_WEIGHT_TREND,
    DISCORD_PORTFOLIO_WEBHOOK,
    DISCORD_LONG_SIGNALS_WEBHOOK,
    DISCORD_SHORT_SIGNALS_WEBHOOK,
)
from strategies.long_breakout import (
    TrendResult,
    ConsolidationResult,
    TradeSetupResult,
    VolumeResult,
    GapUpResult,
    ScoreResult,
    add_indicators,
    get_market_regime,
    check_trend,
    check_consolidation,
    check_volume,
    check_liquidity,
    check_gap_up,
    score_long_breakout,
    calculate_trade_setup,
)
from strategies.short_breakout import (
    TrendResult as ShortTrendResult,
    ConsolidationResult as ShortConsolidationResult,
    TradeSetupResult as ShortTradeSetupResult,
    GapDownResult,
    ScoreResult as ShortScoreResult,
    get_market_regime_short,
    check_trend_short,
    check_consolidation_short,
    check_gap_down,
    score_short_breakout,
    calculate_trade_setup_short,
)


# ── Type definitions ─────────────────────────────────────────────────────────

class PortfolioTrade(TypedDict):
    ticker: str
    name: str
    strategy: str  # "long_breakout" or "short_breakout"
    status: str    # "PENDING", "ACTIVE", "CLOSED"
    entry: float
    stop_loss: float
    target: float
    date_added: str
    entry_trigger_date: str  # When entry actually triggered (PENDING → ACTIVE)
    exit_date: str
    outcome: str
    r_multiple: float  # Actual R achieved (negative for loss)
    current_price: float  # Latest price for tracking
    score: float  # Setup score at entry time (0-100)

class MarketRegimeInfo(TypedDict):
    close: float | None
    ema20: float | None
    ema50: float | None
    is_bullish: bool
    regime: str
    error: str | None


class ScreenerSetup(TypedDict):
    name: str
    ticker: str
    strategy: str
    signal_date: str
    trend: TrendResult
    cons: ConsolidationResult
    setup: TradeSetupResult
    vol: VolumeResult
    gap: GapUpResult
    score: ScoreResult


# ── Discord Integration ─────────────────────────────────────────────────────────

def post_to_discord(message: str, webhook_url: str) -> bool:
    """Post a message to Discord via webhook. Returns True on success."""
    if not webhook_url:
        print("  [!] Discord webhook URL not configured")
        return False
    
    try:
        import requests
        if len(message) > 2000:
            message = message[:1997] + "..."
        response = requests.post(webhook_url, json={"content": message}, timeout=10)
        if response.status_code == 204:
            return True
        print(f"  [!] Discord error: HTTP {response.status_code}")
        return False
    except Exception as e:
        print(f"  [!] Discord error: {e}")
        return False


def format_trade_row(t: dict) -> str:
    """Format a single trade as a Discord message row."""
    ticker = t["ticker"].replace(".NS", "")
    direction = "LONG" if t.get("strategy") == "long_breakout" else "SHORT"
    status_emoji = {"ACTIVE": "🟢", "PENDING": "⏳", "CLOSED": "✅"}.get(t["status"], "⚪")
    
    entry = t.get("entry", 0)
    sl = t.get("stop_loss", 0)
    target = t.get("target", 0)
    curr_price = t.get("current_price", entry)
    r_val = t.get("r_multiple", 0)
    
    # Date fields
    added_date = t.get("date_added", "")
    trigger_date = t.get("entry_trigger_date", "")
    exit_date = t.get("exit_date", "")
    
    # Calculate days
    from datetime import datetime
    today = datetime.now()
    days_info = ""
    if t["status"] == "PENDING" and added_date:
        try:
            d = datetime.strptime(added_date, "%d-%m-%Y")
            days = (today - d).days
            days_info = f" | +{days}d"
        except:
            pass
    elif t["status"] == "ACTIVE" and trigger_date:
        try:
            d = datetime.strptime(trigger_date, "%d-%m-%Y")
            days = (today - d).days
            days_info = f" | {days}d"
        except:
            pass
    elif t["status"] == "CLOSED" and exit_date:
        outcome = t.get("outcome", "")
        emoji = "✅" if outcome == "WIN" else "❌" if outcome == "LOSS" else "➖"
        days_info = f" | {emoji}"
    
    entry_str = f"₹{entry:,.0f}" if entry and entry > 0 else "--"
    sl_str = f"₹{sl:,.0f}" if sl and sl > 0 else "--"
    target_str = f"₹{target:,.0f}" if target and target > 0 else "--"
    curr_str = f"₹{curr_price:,.0f}" if curr_price and curr_price > 0 else "--"
    r_str = f"{r_val:+.2f}R" if r_val != 0 else "--"

    # Score from setup time
    score_val = t.get("score", 0)
    score_str = f"{score_val:.0f}" if score_val > 0 else "--"

    # Date info - show added for PENDING, triggered for ACTIVE, exit for CLOSED
    if t["status"] == "PENDING" and added_date:
        date_info = f"Added: {added_date}{days_info}"
    elif t["status"] == "ACTIVE" and trigger_date:
        date_info = f"Trig: {trigger_date}{days_info}"
    elif t["status"] == "CLOSED" and exit_date:
        date_info = f"Exit: {exit_date}"
    else:
        date_info = ""
    
    # Two-line format for better readability
    line1 = f"{status_emoji} **{ticker}** [{direction}]"
    line2 = f"   E:{entry_str} | SL:{sl_str} | Tgt:{target_str} | Curr:{curr_str}"
    line3 = f"   {date_info} | S:{score_str} | R:{r_str}"

    return f"{line1}\n{line2}\n{line3}"


def format_portfolio_for_discord(trades: List[PortfolioTrade]) -> str:
    """Format full portfolio with all trades as Discord messages."""
    if not trades:
        return "📭 **Portfolio is empty**"
    
    active = [t for t in trades if t["status"] == "ACTIVE"]
    pending = [t for t in trades if t["status"] == "PENDING"]
    closed = [t for t in trades if t["status"] == "CLOSED"]
    
    closed_wins = [t for t in closed if t.get("outcome") == "WIN"]
    closed_losses = [t for t in closed if t.get("outcome") == "LOSS"]
    
    total_closed = len(closed)
    win_count = len(closed_wins)
    loss_count = len(closed_losses)
    win_rate = (win_count / total_closed * 100) if total_closed > 0 else 0
    
    r_values = [t.get("r_multiple", 0) for t in closed if t.get("r_multiple", 0) != 0]
    avg_r = sum(r_values) / len(r_values) if r_values else 0
    total_r = sum(r_values) if r_values else 0
    
    long_active = len([t for t in active if t.get("strategy") == "long_breakout"])
    short_active = len([t for t in active if t.get("strategy") == "short_breakout"])
    
    date_str = datetime.now().strftime("%d %b %Y, %H:%M")
    
    lines = []
    
    lines.append(f"📊 **SWING TRADING PORTFOLIO**")
    lines.append(f"*{date_str}*")
    lines.append("")
    
    lines.append(f"**═══ SUMMARY ═══**")
    lines.append(f"🟢 Active: **{len(active)}** (L:{long_active} | S:{short_active})")
    lines.append(f"⏳ Pending: **{len(pending)}**")
    lines.append(f"✅ Closed: **{total_closed}** (W:{win_count} | L:{loss_count})")
    if total_closed > 0:
        lines.append(f"📈 Win Rate: **{win_rate:.1f}%** | Avg R: **{avg_r:+.2f}** | Total R: **{total_r:+.2f}R**")
    lines.append("")
    
    if active:
        lines.append(f"**═══ ACTIVE ({len(active)}) ═══**")
        for t in active:
            lines.append(format_trade_row(t))
        lines.append("")
    
    if pending:
        lines.append(f"**═══ PENDING ({len(pending)}) ═══**")
        for t in pending:
            lines.append(format_trade_row(t))
        lines.append("")
    
    if closed:
        lines.append(f"**═══ CLOSED ({len(closed)}) ═══**")
        for t in closed[-10:]:
            lines.append(format_trade_row(t))
        if len(closed) > 10:
            lines.append(f"_... and {len(closed) - 10} more_")
    
    return "\n".join(lines)


def send_portfolio_to_discord(trades: List[PortfolioTrade]) -> None:
    """Send portfolio summary to Discord if webhook is configured."""
    if not DISCORD_PORTFOLIO_WEBHOOK:
        return
    
    message = format_portfolio_for_discord(trades)
    success = post_to_discord(message, DISCORD_PORTFOLIO_WEBHOOK)
    
    if success:
        print("  [+] Portfolio posted to Discord")
    else:
        print("  [!] Failed to post to Discord")


def format_signal_for_discord(setup: dict, rank: int) -> str:
    """Format a single signal as Discord message."""
    t = setup["setup"]
    ticker = setup["ticker"].replace(".NS", "")
    score = setup["score"]
    
    direction = "LONG" if setup.get("strategy") == "long_breakout" else "SHORT"
    emoji = "🟢" if direction == "LONG" else "🔴"
    
    lines = []
    lines.append(f"{emoji} **#{rank} {ticker}** [{direction}]")
    lines.append(f"   Entry: ₹{t['entry']:,.0f} | SL: ₹{t['stop_loss']:,.0f} | Target: ₹{t['target']:,.0f}")
    lines.append(f"   Risk: {t['risk_pct']:.1f}% | Score: {score['total']:.1f}/100")
    lines.append(f"   Added: {setup.get('signal_date', '')}")
    
    return "\n".join(lines)


def send_signals_to_discord(setups: List[dict], strategy: str) -> None:
    """Send trade signals to Discord if webhook is configured."""
    webhook = DISCORD_LONG_SIGNALS_WEBHOOK if strategy == "long_breakout" else DISCORD_SHORT_SIGNALS_WEBHOOK
    
    if not webhook or not setups:
        return
    
    date_str = datetime.now().strftime("%d %b %Y")
    direction = "LONG" if strategy == "long_breakout" else "SHORT"
    emoji = "🟢" if direction == "LONG" else "🔴"
    
    lines = []
    lines.append(f"{emoji} **{direction} TRADE SIGNALS** - {date_str}")
    lines.append(f"Found **{len(setups)}** setup(s)")
    lines.append("")
    
    for i, setup in enumerate(setups[:5], 1):
        lines.append(format_signal_for_discord(setup, i))
        lines.append("")
    
    message = "\n".join(lines)
    success = post_to_discord(message, webhook)
    
    if success:
        print(f"  [+] {direction} signals posted to Discord")
    else:
        print(f"  [!] Failed to post {direction} signals to Discord")


# ── Data helper ───────────────────────────────────────────────────────────────

def _map_ticker(ticker: str) -> str:
    """Apply ticker alias mapping if exists, else return original."""
    return TICKER_ALIASES.get(ticker, ticker)


def fetch_data(
    ticker:  str,
    days:    int  = SCREENER_DAYS,
    refresh: bool = True,
) -> pd.DataFrame | None:
    """
    Return `days` of daily OHLCV data.  Delegates to data.cache so the first
    call downloads and saves  data/<ticker>.csv; subsequent calls load from
    disk.  Pass refresh=True to force a fresh download for today's prices.
    """
    mapped_ticker = _map_ticker(ticker)
    return fetch_ohlcv(mapped_ticker, days, refresh=refresh)


# ── Market regime (screener-specific: fetches its own Nifty data) ─────────────

def check_market_regime(ticker: str = NIFTY_TICKER) -> MarketRegimeInfo:
    """
    Fetch Nifty data, compute EMA20/EMA50, and return full regime details.

    Returns
    -------
    {"close", "ema20", "ema50", "is_bullish", "regime", "error"}
      regime  → "STRONG_BULL" | "EARLY_TREND" | "BEAR"

    On data failure, is_bullish is False and error contains the message.
    """
    df = fetch_data(ticker)
    if df is None:
        return {"close": None, "ema20": None, "ema50": None,
                "is_bullish": False, "regime": "BEAR",
                "error": f"Could not fetch data for {ticker}"}
    df             = add_indicators(df)
    close          = round(float(df["Close"].iloc[-1]),  2)
    ema20          = round(float(df["EMA20"].iloc[-1]),  2)
    ema50          = round(float(df["EMA50"].iloc[-1]),  2)

    # build stock universe for breadth calculation
    all_data = {}
    for t in STOCKS:
        sdf = fetch_data(t, refresh=False)
        if sdf is not None:
            all_data[t] = add_indicators(sdf)

    is_bullish, regime, _breadth = get_market_regime(df, all_data=all_data)
    return {
        "close":      close,
        "ema20":      ema20,
        "ema50":      ema50,
        "is_bullish": is_bullish,
        "regime":     regime,
        "error":      None,
    }


# ── Earnings blackout helper ───────────────────────────────────────────────────

def is_near_earnings(earnings_dates: list[datetime], today: datetime) -> bool:
    """
    Return True if any earnings date falls within the blackout window:
      [today − EARNINGS_LOOKBACK_DAYS, today + EARNINGS_LOOKAHEAD_DAYS]
    """
    if not earnings_dates:
        return False
    window_start = today - timedelta(days=EARNINGS_LOOKBACK_DAYS)
    window_end   = today + timedelta(days=EARNINGS_LOOKAHEAD_DAYS)
    return any(window_start <= d <= window_end for d in earnings_dates)


# ── Display helpers ───────────────────────────────────────────────────────────

def _rank_label(rank: int) -> str:
    if rank == 1:
        return "🔥 BEST TRADE"
    return f"🟡 Backup {rank - 1}"


def _score_bar(score: float, width: int = 20) -> str:
    filled = round(float(score / 100 * width))
    return "[" + "#" * filled + "-" * (width - filled) + f"]  {score:.1f}/100"


def print_trade_card(
    rank:    int,
    name:   str,
    ticker:  str,
    trend:   TrendResult,
    cons:   ConsolidationResult,
    setup:  TradeSetupResult,
    vol:    VolumeResult,
    gap:    GapUpResult,
    score:  ScoreResult,
    width:  int,
) -> None:
    """Print a full ranked trade-setup card for one stock (analysis mode)."""
    upside_pct  = round(float((setup["target"] - setup["entry"]) / setup["entry"] * 100), 2)
    label       = _rank_label(rank)
    vol_tag     = "Volume OK ✅" if vol["surge_ratio"] >= VOLUME_MIN_RATIO else "Weak Volume ⚠️"

    print("=" * width)
    print(f"  {label}  —  Rank #{rank}")
    print(f"  {name}  ({ticker})")
    print("=" * width)

# Score breakdown
    print(f"  {'Overall Score':<22}  {_score_bar(score['total'])}")
    print(f"  {'  Risk score':<22}  {score['risk_score']:>5.1f} / {SCORE_WEIGHT_RISK}"
          f"   (lower risk % is better)")
    print(f"  {'  Range score':<22}  {score['range_score']:>5.1f} / {SCORE_WEIGHT_RANGE}"
          f"   (tighter coil is better)")
    g = score["ema50_gap_pct"]
    if g < 1.0:
        zone = "weak — too close to EMA50"
    elif g <= 4.0:
        zone = "sweet spot (1–4%)"
    elif g <= 6.0:
        zone = "mild extension (4–6%)"
    else:
        zone = "overextended (>6%)"
    print(f"  {'  Trend score':<22}  {score['trend_score']:>5.1f} / {SCORE_WEIGHT_TREND}"
          f"   {g:+.2f}% vs EMA50  [{zone}]")
    print()

    # Market context
    print(f"  {'Current Close':<22}  Rs. {trend['close']:>10,.2f}")
    print(f"  {'EMA 50':<22}  Rs. {trend['ema50']:>10,.2f}"
          f"   (+{(trend['close'] / trend['ema50'] - 1) * 100:.2f}% above)")
    print(f"  {'EMA 200':<22}  Rs. {trend['ema200']:>10,.2f}")
    print()

    # Consolidation
    print(f"  {'Coil Range':<22}  {cons['range_pct']:.2f}%"
          f"   ({COIL_CANDLES}-candle window)")
    print(f"  {'Gap to High':<22}  {cons['gap_to_high_pct']:.2f}%")
    print()

    # Volume
    avg_vol_label = f"Avg Volume ({VOLUME_AVG_PERIOD}d)"
    print(f"  {avg_vol_label:<22}  {vol['avg_volume']:>14,}")
    print(f"  {'Latest Volume':<22}  {vol['latest_volume']:>14,}"
          f"   ({vol['surge_ratio']:.2f}x avg)")
    print(f"  {'Volume Signal':<22}  {vol_tag}")
    print()

    # Gap-up
    gap_sign   = "+" if gap["gap_pct"] >= 0 else ""
    gap_status = "No gap-up ✅" if not gap["is_gap_up"] else "Gap-up detected ❌"
    print(f"  {'Today Open':<22}  Rs. {gap['today_open']:>10,.2f}"
          f"   ({gap_sign}{gap['gap_pct']:.2f}% vs entry)")
    print(f"  {'Gap-Up Status':<22}  {gap_status}")
    print()

    # Trade plan
    print(f"  {'Entry  (breakout)':<22}  Rs. {setup['entry']:>10,.2f}"
          f"   <- buy above this level")
    print(f"  {'Stop Loss':<22}  Rs. {setup['stop_loss']:>10,.2f}"
          f"   <- exit if price closes below")
    print(f"  {'Target  (1:{:.0f} RR)':<22}  Rs. {setup['target']:>10,.2f}"
          f"   <- +{upside_pct:.1f}% from entry".format(setup["rr_ratio"]))
    print(f"  {'Risk per share':<22}  Rs. {setup['risk']:>10,.2f}"
          f"   ({setup['risk_pct']:.2f}% of entry)")


def print_trade_card_compact(
    rank:   int,
    name:   str,
    ticker: str,
    setup:  TradeSetupResult,
    score:  ScoreResult,
    vol:    VolumeResult,
    width:  int,
) -> None:
    """
    Minimal trade card for LIVE_MODE — clean and actionable.
    Contains only the fields a trader needs at execution time.
    """
    label     = _rank_label(rank)
    upside    = round(float((setup["target"] - setup["entry"]) / setup["entry"] * 100), 2)

    print("─" * width)
    print(f"  {label}  —  {name}  ({ticker})")
    print("─" * width)
    print(f"  {'Entry':<14}  Rs. {setup['entry']:>10,.2f}")
    print(f"  {'Stop Loss':<14}  Rs. {setup['stop_loss']:>10,.2f}")
    print(f"  {'Target':<14}  Rs. {setup['target']:>10,.2f}"
          f"   (+{upside:.1f}% upside)")
    print(f"  {'Risk':<14}  {setup['risk_pct']:.2f}%"
          f"   (Rs. {setup['risk']:,.2f} / share)")
    print(f"  {'Score':<14}  {score['total']:.1f} / 100")
    print(f"  {'Volume':<14}  {vol['surge_ratio']:.2f}x avg")


def print_execution_summary(
    setups:       list[ScreenerSetup],
    market_ok:    bool,
    regime_label: str = "STRONG_BULL",
    width:        int  = 72,
) -> None:
    """
    Daily execution brief printed after all trade cards.

    Shows:
    • Safety gate confirmation (regime / liquidity / earnings)
    • Quick reference table of top N setups
    • Capital allocation suggestion
    """
    top_n      = setups[:MAX_CONCURRENT_TRADES]
    total_risk = RISK_PER_TRADE * len(top_n)

    print()
    print("=" * width)
    print(f"{'DAILY EXECUTION BRIEF':^{width}}")
    print("=" * width)

    # ── Safety gate summary (Part 6) ──────────────────────────────────────────
    _reg_display = {
        "STRONG_BULL": ("✅", "STRONG BULL — full capacity"),
        "EARLY_TREND": ("⚡", "EARLY TREND — reduced capacity"),
        "BEAR":        ("🚫", "BEAR — no trades today"),
        "UNKNOWN":     ("⚪", "REGIME OFF — all conditions allowed"),
    }
    r_icon, r_text = _reg_display.get(regime_label, ("⚪", "REGIME OFF"))
    print(f"  Market regime      {r_icon}  {r_text}")
    min_cr = MIN_AVG_TURNOVER // 1_00_00_000
    print(f"  Liquidity filter   ✅  active (min Rs.{min_cr} Cr avg daily turnover)")
    print(f"  Earnings filter    ✅  active "
          f"({EARNINGS_LOOKBACK_DAYS}d lookback / {EARNINGS_LOOKAHEAD_DAYS}d lookahead)")
    print("─" * width)

    print(f"  Setups found today    :  {len(setups)}")
    print(f"  Slots available       :  {MAX_CONCURRENT_TRADES}  (MAX_CONCURRENT_TRADES)")
    print(f"  Actionable (top {MAX_CONCURRENT_TRADES})  :  {len(top_n)}")

    if not top_n:
        print()
        print("  No valid setups today. Stand aside — preserve capital.")
        print("=" * width)
        return

    # ── Quick reference table ──────────────────────────────────────────────────
    print()
    print(f"  {'#':<3}  {'Ticker':<16}  {'Entry':>8}  {'Stop':>8}  "
          f"{'Target':>8}  {'Risk%':>6}  {'Score':>6}")
    print("  " + "─" * (width - 2))
    for i, s in enumerate(top_n, 1):
        sp = s["setup"]
        sc = s["score"]
        print(
            f"  {i:<3}  {s['ticker']:<16}  "
            f"{sp['entry']:>8,.0f}  "
            f"{sp['stop_loss']:>8,.0f}  "
            f"{sp['target']:>8,.0f}  "
            f"{sp['risk_pct']:>5.1f}%  "
            f"{sc['total']:>6.1f}"
        )

    # ── Capital allocation suggestion ──────────────────────────────────────────
    print()
    print(f"  Capital at risk    :  {total_risk:.1f}% of portfolio"
          f"  ({len(top_n)} trade(s) × {RISK_PER_TRADE}% each)")
    action = (
        f"Enter top {len(top_n)} setup(s), risk {RISK_PER_TRADE}% per trade, "
        f"{total_risk:.1f}% total exposure."
    )
    print(f"  Suggested action   :  {action}")
    print("=" * width)


# ── Main ──────────────────────────────────────────────────────────────────────

# ── Portfolio Management ──────────────────────────────────────────────────────

def _get_portfolio_cache() -> DataCache:
    """Return the DataCache instance for the portfolio."""
    # Place it in the same data folder as CSVs
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    return DataCache(os.path.join(data_dir, "portfolio.json"))

def load_portfolio() -> List[PortfolioTrade]:
    """Load tracked trades from disk."""
    cache = _get_portfolio_cache()
    data = cache.load("portfolio")
    return data["trades"] if data and "trades" in data else []

def save_portfolio(trades: List[PortfolioTrade]) -> None:
    """Save tracked trades to disk."""
    cache = _get_portfolio_cache()
    cache.save("portfolio", {"trades": trades})


def _days_since(date_str: str) -> int | None:
    """Return number of days since date_str (DD-MM-YYYY), or None if invalid."""
    if not date_str:
        return None
    try:
        trade_date = datetime.strptime(date_str, "%d-%m-%Y")
        return (datetime.today() - trade_date).days
    except ValueError:
        return None


def cleanup_portfolio(trades: List[PortfolioTrade]) -> tuple[List[PortfolioTrade], dict]:
    """
    Remove stale PENDING trades (> PENDING_EXPIRY_DAYS) and old CLOSED trades (> CLOSED_CLEANUP_DAYS).
    Returns (cleaned_trades, cleanup_stats) where cleanup_stats contains counts of removed trades.
    """
    cleaned = []
    stats = {"pending_expired": 0, "closed_cleaned": 0, "dead_ticker": 0}
    
    for t in trades:
        ticker = t.get("ticker", "")
        
        # Skip dead/delisted tickers
        if ticker in DEAD_TICKERS:
            stats["dead_ticker"] = stats.get("dead_ticker", 0) + 1
            continue
        
        days_added = _days_since(t.get("date_added", ""))
        days_exited = _days_since(t.get("exit_date", ""))
        days_triggered = _days_since(t.get("entry_trigger_date", ""))
        
        if t["status"] == "PENDING":
            if days_added is not None and days_added > PENDING_EXPIRY_DAYS:
                stats["pending_expired"] += 1
                continue
        elif t["status"] == "CLOSED":
            if days_exited is not None and days_exited > CLOSED_CLEANUP_DAYS:
                stats["closed_cleaned"] += 1
                continue
        elif t["status"] == "ACTIVE":
            if days_triggered is None and days_added is not None and days_added > MAX_ACTIVE_DAYS:
                stats["active_stale"] = stats.get("active_stale", 0) + 1
                continue
        
        cleaned.append(t)
    
    return cleaned, stats


def _calculate_r_multiple(strategy: str, entry: float, exit_price: float, stop_loss: float) -> float:
    """Calculate R-multiple based on entry and exit prices."""
    risk = abs(entry - stop_loss)
    if risk == 0:
        return 0.0
    
    if strategy == "long_breakout":
        return (exit_price - entry) / risk
    else:
        return (entry - exit_price) / risk


def _print_portfolio_summary(trades: List[PortfolioTrade]) -> None:
    """Print portfolio summary statistics."""
    if not trades:
        return
    
    active = [t for t in trades if t["status"] == "ACTIVE"]
    pending = [t for t in trades if t["status"] == "PENDING"]
    closed = [t for t in trades if t["status"] == "CLOSED"]
    
    closed_wins = [t for t in closed if t.get("outcome") == "WIN"]
    closed_losses = [t for t in closed if t.get("outcome") == "LOSS"]
    
    total_closed = len(closed)
    win_count = len(closed_wins)
    loss_count = len(closed_losses)
    win_rate = (win_count / total_closed * 100) if total_closed > 0 else 0
    
    r_values = [t.get("r_multiple", 0) for t in closed if t.get("r_multiple", 0) != 0]
    avg_r = sum(r_values) / len(r_values) if r_values else 0
    total_r = sum(r_values) if r_values else 0
    
    long_active = len([t for t in active if t.get("strategy") == "long_breakout"])
    short_active = len([t for t in active if t.get("strategy") == "short_breakout"])
    
    print(f"\n{'─' * 50}")
    print(f"  PORTFOLIO SUMMARY")
    print(f"{'─' * 50}")
    print(f"  Active: {len(active)} (LONG:{long_active} SHORT:{short_active})  |  Pending: {len(pending)}  |  Closed: {total_closed}")
    if total_closed > 0:
        print(f"  Wins: {win_count}  |  Losses: {loss_count}  |  Win Rate: {win_rate:.1f}%")
        print(f"  Avg R: {avg_r:+.2f}  |  Total R: {total_r:+.2f}R")
    print(f"{'─' * 50}")


def update_portfolio() -> None:
    """
    Fetch latest prices for all tracked trades and update their status.
    - Cleans up stale PENDING trades (> PENDING_EXPIRY_DAYS)
    - Cleans up old CLOSED trades (> CLOSED_CLEANUP_DAYS)
    - Tracks entry_trigger_date when entry triggers
    - Calculates r_multiple when trade closes
    Prints a summary of active/pending trades.
    """
    trades = load_portfolio()
    if not trades:
        return

    # Clean up stale trades first
    trades, cleanup_stats = cleanup_portfolio(trades)
    
    parts = []
    if cleanup_stats.get("pending_expired", 0) > 0:
        parts.append(f"{cleanup_stats['pending_expired']} PENDING expired")
    if cleanup_stats.get("closed_cleaned", 0) > 0:
        parts.append(f"{cleanup_stats['closed_cleaned']} CLOSED removed")
    if cleanup_stats.get("dead_ticker", 0) > 0:
        parts.append(f"{cleanup_stats['dead_ticker']} dead/delisted")
    
    if parts:
        print(f"\n  Portfolio cleanup: {', '.join(parts)}")

    print("\n" + "=" * 90)
    print(f"{'CURRENT PORTFOLIO TRACKER':^90}")
    print("=" * 90)
    
    # Print portfolio summary header
    _print_portfolio_summary(trades)
     
    updated_trades = []
    
    # Sort trades: ACTIVE first, then PENDING, then CLOSED
    # Within each status, sort by days since relevant date
    def sort_key(t):
        status_order = {"ACTIVE": 0, "PENDING": 1, "CLOSED": 2}
        status_priority = status_order.get(t["status"], 3)
        
        if t["status"] == "PENDING":
            days = _days_since(t.get("date_added", "")) or 0
        elif t["status"] == "ACTIVE":
            days = _days_since(t.get("entry_trigger_date", "")) or 0
        else:
            days = _days_since(t.get("exit_date", "")) or 0
        
        return (status_priority, days)
    
    trades.sort(key=sort_key)
    
    col = f"{'Ticker':<12} {'Dir':<5} {'Status':<9} {'Added':<11} {'Trigger':<11} {'Exit':<11} {'Days':>4} {'Entry':>8} {'SL':>8} {'Target':>9} {'Current':>9} {'Score':>6} {'R'}"
    print(f"  {col}")
    print(f"  {'-' * len(col)}")

    for t in trades:
        # Ensure all fields exist (backward compatibility)
        if "r_multiple" not in t:
            t["r_multiple"] = 0.0
        if "entry_trigger_date" not in t:
            t["entry_trigger_date"] = ""
        if "date_added" not in t:
            t["date_added"] = ""
        if "exit_date" not in t:
            t["exit_date"] = ""
        if "current_price" not in t:
            t["current_price"] = t.get("entry", 0)
        if "score" not in t:
            t["score"] = 0
        
        # Fetch latest data
        df = fetch_ohlcv(t["ticker"], days=30, refresh=True)
        if df is None or df.empty:
            updated_trades.append(t)
            print(f"  {t['ticker']:<12} {t['status']:<9} [NO DATA]")
            continue

        df = add_indicators(df)
        last_row = df.iloc[-1]
        curr_close = float(last_row["Close"])
        curr_high = float(last_row["High"])
        curr_low = float(last_row["Low"])
        
        t["current_price"] = curr_close
        status_change = ""
        r_display = f"{t['r_multiple']:.2f}" if t["r_multiple"] != 0 else "-"
        
        direction = "LONG" if t["strategy"] == "long_breakout" else "SHORT"
        
        # Date display based on status
        added_date = t.get("date_added", "") or "-"
        trigger_date = t.get("entry_trigger_date", "") or "-"
        exit_date = t.get("exit_date", "") or "-"
        
        if t["status"] == "PENDING":
            days_since = _days_since(t.get("date_added", ""))
        elif t["status"] == "ACTIVE":
            days_since = _days_since(t.get("entry_trigger_date", ""))
        else:
            days_since = _days_since(t.get("exit_date", ""))
        
        days_str = str(days_since) if days_since is not None else "-"
        
        if t["status"] == "PENDING":
            if t["strategy"] == "long_breakout":
                if curr_high >= t["entry"]:
                    t["status"] = "ACTIVE"
                    t["entry_trigger_date"] = df.index[-1].strftime("%d-%m-%Y")
                    trigger_date = t["entry_trigger_date"]
                    status_change = "→ TRIGGERED"
            elif t["strategy"] == "short_breakout":
                if curr_low <= t["entry"]:
                    t["status"] = "ACTIVE"
                    t["entry_trigger_date"] = df.index[-1].strftime("%d-%m-%Y")
                    trigger_date = t["entry_trigger_date"]
                    status_change = "→ TRIGGERED"
        
        exit_price = None
        if t["status"] == "ACTIVE":
            if t["strategy"] == "long_breakout":
                if curr_low <= t["stop_loss"]:
                    t["status"] = "CLOSED"
                    t["outcome"] = "LOSS"
                    exit_price = t["stop_loss"]
                    status_change = "→ SL HIT"
                elif curr_high >= t["target"]:
                    t["status"] = "CLOSED"
                    t["outcome"] = "WIN"
                    exit_price = t["target"]
                    status_change = "→ TARGET HIT"
            elif t["strategy"] == "short_breakout":
                if curr_high >= t["stop_loss"]:
                    t["status"] = "CLOSED"
                    t["outcome"] = "LOSS"
                    exit_price = t["stop_loss"]
                    status_change = "→ SL HIT"
                elif curr_low <= t["target"]:
                    t["status"] = "CLOSED"
                    t["outcome"] = "WIN"
                    exit_price = t["target"]
                    status_change = "→ TARGET HIT"
            
            if exit_price is not None:
                t["exit_date"] = df.index[-1].strftime("%d-%m-%Y")
                exit_date = t["exit_date"]
                t["r_multiple"] = round(_calculate_r_multiple(t["strategy"], t["entry"], exit_price, t["stop_loss"]), 2)
                r_display = f"{t['r_multiple']:.2f}"

        score_display = f"{t['score']:.0f}" if t.get("score", 0) > 0 else "-"
        print(f"  {t['ticker']:<12} {direction:<5} {t['status']:<9} {added_date:<11} {trigger_date:<11} {exit_date:<11} {days_str:>4} {t['entry']:>8.2f} {t['stop_loss']:>8.2f} {t['target']:>9.2f} {curr_close:>9.2f} {score_display:>6} {r_display:>4} {status_change}")
        
        if t["status"] != "CLOSED":
            updated_trades.append(t)

    # Send to Discord
    send_portfolio_to_discord(trades)
    
    save_portfolio(updated_trades)
    print("=" * 90 + "\n")

def add_to_portfolio(ticker: str, name: str, strategy: str, entry: float, sl: float, target: float, score: float = 0) -> None:
    """Add a new setup to the portfolio if it is not already tracked."""
    trades = load_portfolio()

    # Avoid duplicates
    if any(t["ticker"] == ticker and t["strategy"] == strategy for t in trades):
        return

    new_trade: PortfolioTrade = {
        "ticker": ticker,
        "name": name,
        "strategy": strategy,
        "status": "PENDING",
        "entry": entry,
        "stop_loss": sl,
        "target": target,
        "date_added": datetime.today().strftime("%d-%m-%Y"),
        "entry_trigger_date": "",
        "exit_date": "",
        "outcome": "",
        "r_multiple": 0.0,
        "current_price": entry,
        "score": score,
    }
    trades.append(new_trade)
    save_portfolio(trades)

def run_screener() -> None:
    """Execute the full scan and print results."""
    width   = 72
    total   = len(STOCKS)
    today   = datetime.today()
    scanned = skipped = earnings_skipped = 0
    ema_passed = coil_passed = risk_passed = vol_passed = 0
    final_setups: list[ScreenerSetup] = []

    # ── Header ────────────────────────────────────────────────────────────────
    print("=" * width)
    print(f"{'SWING TRADING SCREENER  -  INDIAN STOCKS (NSE)':^{width}}")
    if LIVE_MODE:
        print(f"{'[LIVE MODE — clean output]':^{width}}")
    print(f"{'Stage 0 : Market Regime filter disabled':^{width}}")
    print(f"{'Stage 1 : Close > EMA50 > EMA200':^{width}}")
    print(f"{'Stage 2 : Coil  (range < ' + str(MAX_RANGE_PCT) + '%, near high < ' + str(NEAR_HIGH_PCT) + '%)':^{width}}")
    gap_pct_str = f"{int((GAP_UP_THRESHOLD - 1) * 100)}%"
    print(f"{'Stage 3 : Risk < ' + str(MAX_RISK_PCT) + '%  |  Vol > ' + str(VOLUME_MIN_RATIO) + 'x  |  No gap-up > ' + gap_pct_str + '  |  RR 1:' + str(int(REWARD_RATIO)):^{width}}")
    print(f"{'Stage 3d: Earnings blackout (' + str(EARNINGS_LOOKBACK_DAYS) + 'd / ' + str(EARNINGS_LOOKAHEAD_DAYS) + 'd)':^{width}}")
    print(f"{'Date : ' + today.strftime('%d-%m-%Y  %H:%M'):^{width}}")
    print(f"{'Universe : ' + str(total) + ' stocks':^{width}}")
    print("=" * width)

    # ── Update tracked trades first ───────────────────────────────────────────
    update_portfolio()

# ── Stage 0 : Market regime filter intentionally disabled ──────────────────
    market_ok = True
    regime_label = "UNKNOWN"
    print("\n  Market regime filter disabled — skipping Nifty EMA gate.\n")

    # Load portfolio once at start - we'll update it but NOT skip based on it
    # We need to check entry triggers and close trades first
    portfolio_trades = load_portfolio()

    # Update portfolio (check triggers, SL/Target hits) and save
    update_portfolio()
    
    # Build set of tickers to skip AFTER updating portfolio
    portfolio_trades = load_portfolio()
    portfolio_tickers = {t["ticker"] for t in portfolio_trades}

    # ── Scan progress indicator (LIVE_MODE) ───────────────────────────────────
    if LIVE_MODE:
        print(f"  Scanning {total} stocks ...", flush=True)

    # ── Scan loop ─────────────────────────────────────────────────────────────
    for ticker, name in STOCKS.items():
        # Skip dead/delisted tickers
        if ticker in DEAD_TICKERS:
            skipped += 1
            continue
        
        n = scanned + skipped + 1

        if not LIVE_MODE:
            print(f"  [{n:>3}/{total}]  {name:<26} ({ticker:<16})  ",
                  end="", flush=True)

        try:
            df = fetch_data(ticker)
        except Exception as exc:
            if not LIVE_MODE:
                print(f"FETCH ERROR: {exc}")
            skipped += 1
            continue
        if df is None:
            if not LIVE_MODE:
                print("NO DATA")
            skipped += 1
            continue

        try:
            df = add_indicators(df)
        except Exception as exc:
            if not LIVE_MODE:
                print(f"INDICATOR ERROR: {exc}")
            skipped += 1
            continue
        scanned += 1

        # Price floor — skip penny stocks
        if float(df["Close"].iloc[-1]) < MIN_PRICE:
            if not LIVE_MODE:
                print(f"penny stock (< Rs.{MIN_PRICE}) — skipped")
            continue

        # Stage 0b — liquidity gate (₹10 Cr avg turnover)
        if not check_liquidity(df):
            if not LIVE_MODE:
                print("illiquid — skipped")
            continue

        # Stage 1 — trend
        trend = check_trend(df)
        if trend is None:
            if not LIVE_MODE:
                print("trend fail")
            continue

        ema_passed += 1

        # Stage 2 — coil
        coil = check_consolidation(df)
        if coil is None:
            if not LIVE_MODE:
                print("trend ok | coil fail")
            continue

        coil_passed += 1

        # Stage 3a — risk
        setup = calculate_trade_setup(coil["period_high"], coil["period_low"])
        if not setup["is_valid"]:
            if not LIVE_MODE:
                print(f"trend+coil ok | risk {setup['risk_pct']:.1f}%  -> risk too wide")
            continue

        risk_passed += 1

        # Stage 3b — volume
        vol = check_volume(df)
        if vol is None:
            if not LIVE_MODE:
                print("trend+coil+risk ok | weak volume  -> filtered")
            continue

        vol_passed += 1

        # Stage 3c — gap-up
        gap = check_gap_up(df, setup["entry"])
        if gap["is_gap_up"]:
            if not LIVE_MODE:
                print(f"trend+coil+risk+vol ok | open Rs.{gap['today_open']:,.2f}"
                      f"  gapped +{gap['gap_pct']:.2f}% above entry  -> invalid (gap-up)")
            continue

        # Stage 3d — earnings blackout
        e_dates = get_earnings_dates(ticker)
        if is_near_earnings(e_dates, today):
            earnings_skipped += 1
            if not LIVE_MODE:
                print("skipped — earnings nearby")
            continue

        score = score_long_breakout(trend, coil)

        # Check if already in portfolio (skip PENDING/ACTIVE, allow CLOSED for re-entry)
        in_portfolio = any(t["ticker"] == ticker for t in portfolio_trades)
        if in_portfolio:
            continue
        
        if not LIVE_MODE:
            print(f"SETUP FOUND  |  score {score['total']:.1f}/100  "
                  f"range {coil['range_pct']:.1f}%  "
                  f"risk {setup['risk_pct']:.1f}%  "
                  f"vol {vol['surge_ratio']:.2f}x  "
                  f"open {gap['gap_pct']:+.2f}%")

        signal_date = df.index[-1].strftime("%d-%m-%Y") if hasattr(df.index[-1], "strftime") else str(df.index[-1])
        
        # Track setup in portfolio
        add_to_portfolio(ticker, name, "long_breakout", setup["entry"], setup["stop_loss"], setup["target"], score['total'])

        final_setups.append({
            "name":   name,
            "ticker": ticker,
            "strategy": "breakout",
            "signal_date": signal_date,
            "trend":  trend,
            "cons":   coil,
            "setup":  setup,
            "vol":    vol,
            "gap":    gap,
            "score":  score,
        })

    # ── Sort by score ──────────────────────────────────────────────────────────
    final_setups.sort(key=lambda x: x["score"]["total"], reverse=True)

    # ── Scan summary (suppressed in LIVE_MODE) ────────────────────────────────
    if not LIVE_MODE:
        print()
        print("=" * width)
        print(f"{'SCAN SUMMARY':^{width}}")
        print("=" * width)
        print(f"  Universe              : {total} stocks")
        print(f"  Successfully scanned  : {scanned}")
        print(f"  Skipped (no data)     : {skipped}")
        print(f"  Passed Stage 1  (EMA trend)   : {ema_passed}")
        print(f"  Passed Stage 2  (Coil)        : {coil_passed}")
        print(f"  Passed Stage 3a (Risk)        : {risk_passed}")
        print(f"  Passed Stage 3b (Volume)      : {vol_passed}")
        print(f"  Skipped Stage 3d (Earnings)   : {earnings_skipped}")
        print(f"  Passed all stages             : {len(final_setups)}")

    # ── Trade cards ───────────────────────────────────────────────────────────
    print()
    print("=" * width)
    print(f"{'TRADE SETUPS':^{width}}")
    print("=" * width)

    if final_setups:
        for i, s in enumerate(final_setups, 1):
            if LIVE_MODE:
                print_trade_card_compact(
                    rank=i, name=s["name"], ticker=s["ticker"],
                    setup=s["setup"], score=s["score"], vol=s["vol"],
                    width=width,
                )
            else:
                print_trade_card(
                    rank=i, name=s["name"], ticker=s["ticker"],
                    trend=s["trend"], cons=s["cons"], setup=s["setup"],
                    vol=s["vol"], gap=s["gap"], score=s["score"], width=width,
                )
            print()

        if not LIVE_MODE:
            print(f"  * {len(final_setups)} setup(s) ranked  |  "
                  f"Score = Risk({SCORE_WEIGHT_RISK}) + Range({SCORE_WEIGHT_RANGE}) + Trend({SCORE_WEIGHT_TREND})")
    else:
        print()
        print("  No trade setups found today.")
        if not LIVE_MODE:
            print("  Tip: widen MAX_RANGE_PCT or NEAR_HIGH_PCT in config/settings.py.")

    print("=" * width)

    # ── Execution brief (always shown; full detail only in LIVE_MODE) ─────────
    print_execution_summary(final_setups, market_ok=market_ok,
                            regime_label=regime_label, width=width)
    
    # Send signals to Discord
    if final_setups:
        send_signals_to_discord(final_setups, "long_breakout")
    
    print()


# ── Short screener ───────────────────────────────────────────────────────────

def check_market_regime_bearish(ticker: str = NIFTY_TICKER) -> MarketRegimeInfo:
    """
    Fetch Nifty data, compute EMA20/EMA50, and return bearish regime details.

    Returns
    -------
    {"close", "ema20", "ema50", "is_bullish", "regime", "error"}
      regime  → "STRONG_BEAR" | "EARLY_BEAR" | "BULL"
      is_bullish here means "is_bearish_tradeable" (True when shorts are OK)
    """
    df = fetch_data(ticker)
    if df is None:
        return {"close": None, "ema20": None, "ema50": None,
                "is_bullish": False, "regime": "BULL",
                "error": f"Could not fetch data for {ticker}"}
    df    = add_indicators(df)
    close = round(float(df["Close"].iloc[-1]),  2)
    ema20 = round(float(df["EMA20"].iloc[-1]),  2)
    ema50 = round(float(df["EMA50"].iloc[-1]),  2)

    all_data = {}
    for t in STOCKS:
        sdf = fetch_data(t, refresh=False)
        if sdf is not None:
            all_data[t] = add_indicators(sdf)

    is_bearish, regime, _breadth = get_market_regime_short(df, all_data=all_data)
    return {
        "close":      close,
        "ema20":      ema20,
        "ema50":      ema50,
        "is_bullish": is_bearish,   # reusing field name; True = shorts allowed
        "regime":     regime,
        "error":      None,
    }


def print_trade_card_short(
    rank:   int,
    name:   str,
    ticker: str,
    trend:  ShortTrendResult,
    cons:   ShortConsolidationResult,
    setup:  ShortTradeSetupResult,
    vol:    VolumeResult,
    gap:    GapDownResult,
    score:  ShortScoreResult,
    width:  int,
) -> None:
    """Print a full ranked SHORT trade-setup card for one stock (analysis mode)."""
    downside_pct = round(float((setup["entry"] - setup["target"]) / setup["entry"] * 100), 2)
    label        = _rank_label(rank)
    vol_tag      = "Volume OK ✅" if vol["surge_ratio"] >= VOLUME_MIN_RATIO else "Weak Volume ⚠️"

    print("=" * width)
    print(f"  {label}  —  Rank #{rank}  [SHORT]")
    print(f"  {name}  ({ticker})")
    print("=" * width)

    # Score breakdown
    print(f"  {'Overall Score':<22}  {_score_bar(score['total'])}")
    print(f"  {'  Risk score':<22}  {score['risk_score']:>5.1f} / {SCORE_WEIGHT_RISK}"
          f"   (lower risk % is better)")
    print(f"  {'  Range score':<22}  {score['range_score']:>5.1f} / {SCORE_WEIGHT_RANGE}"
          f"   (tighter coil is better)")
    g = score["ema50_gap_pct"]
    if g < 1.0:
        zone = "weak — too close to EMA50"
    elif g <= 4.0:
        zone = "sweet spot (1–4%)"
    elif g <= 6.0:
        zone = "mild extension (4–6%)"
    else:
        zone = "overextended (>6%)"
    print(f"  {'  Trend score':<22}  {score['trend_score']:>5.1f} / {SCORE_WEIGHT_TREND}"
          f"   {g:+.2f}% below EMA50  [{zone}]")
    print()

    # Market context
    print(f"  {'Current Close':<22}  Rs. {trend['close']:>10,.2f}")
    print(f"  {'EMA 50':<22}  Rs. {trend['ema50']:>10,.2f}"
          f"   ({(trend['close'] / trend['ema50'] - 1) * 100:+.2f}% vs EMA50)")
    print(f"  {'EMA 200':<22}  Rs. {trend['ema200']:>10,.2f}")
    print()

    # Consolidation
    print(f"  {'Coil Range':<22}  {cons['range_pct']:.2f}%"
          f"   ({COIL_CANDLES}-candle window)")
    print(f"  {'Gap to Low':<22}  {cons['gap_to_low_pct']:.2f}%")
    print()

    # Volume
    avg_vol_label = f"Avg Volume ({VOLUME_AVG_PERIOD}d)"
    print(f"  {avg_vol_label:<22}  {vol['avg_volume']:>14,}")
    print(f"  {'Latest Volume':<22}  {vol['latest_volume']:>14,}"
          f"   ({vol['surge_ratio']:.2f}x avg)")
    print(f"  {'Volume Signal':<22}  {vol_tag}")
    print()

    # Gap-down
    gap_sign   = "+" if gap["gap_pct"] >= 0 else ""
    gap_status = "No gap-down ✅" if not gap["is_gap_down"] else "Gap-down detected ❌"
    print(f"  {'Today Open':<22}  Rs. {gap['today_open']:>10,.2f}"
          f"   ({gap_sign}{gap['gap_pct']:.2f}% vs entry)")
    print(f"  {'Gap-Down Status':<22}  {gap_status}")
    print()

    # Trade plan
    print(f"  {'Entry  (breakdown)':<22}  Rs. {setup['entry']:>10,.2f}"
          f"   <- sell below this level")
    print(f"  {'Stop Loss':<22}  Rs. {setup['stop_loss']:>10,.2f}"
          f"   <- exit if price closes above")
    print(f"  {'Target  (1:{:.0f} RR)':<22}  Rs. {setup['target']:>10,.2f}"
          f"   <- {downside_pct:.1f}% downside from entry".format(setup["rr_ratio"]))
    print(f"  {'Risk per share':<22}  Rs. {setup['risk']:>10,.2f}"
          f"   ({setup['risk_pct']:.2f}% of entry)")


def print_trade_card_compact_short(
    rank:   int,
    name:   str,
    ticker: str,
    setup:  ShortTradeSetupResult,
    score:  ShortScoreResult,
    vol:    VolumeResult,
    width:  int,
) -> None:
    """Minimal SHORT trade card for LIVE_MODE."""
    label    = _rank_label(rank)
    downside = round(float((setup["entry"] - setup["target"]) / setup["entry"] * 100), 2)

    print("─" * width)
    print(f"  {label}  —  {name}  ({ticker})  [SHORT]")
    print("─" * width)
    print(f"  {'Entry':<14}  Rs. {setup['entry']:>10,.2f}")
    print(f"  {'Stop Loss':<14}  Rs. {setup['stop_loss']:>10,.2f}")
    print(f"  {'Target':<14}  Rs. {setup['target']:>10,.2f}"
          f"   ({downside:.1f}% downside)")
    print(f"  {'Risk':<14}  {setup['risk_pct']:.2f}%"
          f"   (Rs. {setup['risk']:,.2f} / share)")
    print(f"  {'Score':<14}  {score['total']:.1f} / 100")
    print(f"  {'Volume':<14}  {vol['surge_ratio']:.2f}x avg")


def print_execution_summary_short(
    setups:       list,
    market_ok:    bool,
    regime_label: str = "STRONG_BEAR",
    width:        int  = 72,
) -> None:
    """Daily execution brief for SHORT strategy."""
    top_n      = setups[:MAX_CONCURRENT_TRADES]
    total_risk = RISK_PER_TRADE * len(top_n)

    print()
    print("=" * width)
    print(f"{'DAILY EXECUTION BRIEF  [SHORT STRATEGY]':^{width}}")
    print("=" * width)

    _reg_display = {
        "STRONG_BEAR": ("✅", "STRONG BEAR — full capacity"),
        "EARLY_BEAR": ("⚡", "EARLY BEAR — reduced capacity"),
        "BULL":        ("🚫", "BULL — no shorts today"),
        "UNKNOWN":     ("⚪", "REGIME OFF — all conditions allowed"),
    }
    r_icon, r_text = _reg_display.get(regime_label, ("⚪", "REGIME OFF"))
    print(f"  Market regime      {r_icon}  {r_text}")
    min_cr = MIN_AVG_TURNOVER // 1_00_00_000
    print(f"  Liquidity filter   ✅  active (min Rs.{min_cr} Cr avg daily turnover)")
    print(f"  Earnings filter    ✅  active "
          f"({EARNINGS_LOOKBACK_DAYS}d lookback / {EARNINGS_LOOKAHEAD_DAYS}d lookahead)")
    print("─" * width)

    print(f"  Setups found today    :  {len(setups)}")
    print(f"  Slots available       :  {MAX_CONCURRENT_TRADES}  (MAX_CONCURRENT_TRADES)")
    print(f"  Actionable (top {MAX_CONCURRENT_TRADES})  :  {len(top_n)}")

    if not top_n:
        print()
        print("  No valid short setups today. Stand aside — preserve capital.")
        print("=" * width)
        return

    print()
    print(f"  {'#':<3}  {'Ticker':<16}  {'Entry':>8}  {'Stop':>8}  "
          f"{'Target':>8}  {'Risk%':>6}  {'Score':>6}")
    print("  " + "─" * (width - 2))
    for i, s in enumerate(top_n, 1):
        sp = s["setup"]
        sc = s["score"]
        print(
            f"  {i:<3}  {s['ticker']:<16}  "
            f"{sp['entry']:>8,.0f}  "
            f"{sp['stop_loss']:>8,.0f}  "
            f"{sp['target']:>8,.0f}  "
            f"{sp['risk_pct']:>5.1f}%  "
            f"{sc['total']:>6.1f}"
        )

    print()
    print(f"  Capital at risk    :  {total_risk:.1f}% of portfolio"
          f"  ({len(top_n)} trade(s) × {RISK_PER_TRADE}% each)")
    action = (
        f"Enter top {len(top_n)} short setup(s), risk {RISK_PER_TRADE}% per trade, "
        f"{total_risk:.1f}% total exposure."
    )
    print(f"  Suggested action   :  {action}")
    print("=" * width)


def run_screener_short() -> None:
    """Execute the full SHORT breakdown scan and print results."""
    width   = 72
    total   = len(STOCKS)
    today   = datetime.today()
    scanned = skipped = earnings_skipped = 0
    ema_passed = coil_passed = risk_passed = vol_passed = 0
    final_setups: list[dict] = []

    # ── Header ────────────────────────────────────────────────────────────────
    print("=" * width)
    print(f"{'SHORT BREAKDOWN SCREENER  -  INDIAN STOCKS (NSE)':^{width}}")
    if LIVE_MODE:
        print(f"{'[LIVE MODE — clean output]':^{width}}")
    print(f"{'Stage 0 : Market Regime filter disabled':^{width}}")
    print(f"{'Stage 1 : Close < EMA50 < EMA200  (downtrend)':^{width}}")
    print(f"{'Stage 2 : Coil  (range < ' + str(MAX_RANGE_PCT) + '%, near low < ' + str(NEAR_HIGH_PCT) + '%)':^{width}}")
    gap_pct_str = f"{int((GAP_UP_THRESHOLD - 1) * 100)}%"
    print(f"{'Stage 3 : Risk < ' + str(MAX_RISK_PCT) + '%  |  Vol > ' + str(VOLUME_MIN_RATIO) + 'x  |  No gap-down > ' + gap_pct_str + '  |  RR 1:' + str(int(REWARD_RATIO)):^{width}}")
    print(f"{'Stage 3d: Earnings blackout (' + str(EARNINGS_LOOKBACK_DAYS) + 'd / ' + str(EARNINGS_LOOKAHEAD_DAYS) + 'd)':^{width}}")
    print(f"{'Date : ' + today.strftime('%d-%m-%Y  %H:%M'):^{width}}")
    print(f"{'Universe : ' + str(total) + ' stocks':^{width}}")
    print("=" * width)

    # ── Update tracked trades first ───────────────────────────────────────────
    update_portfolio()
    
    # Load portfolio AFTER update to get fresh data for duplicate check
    portfolio_trades = load_portfolio()
    portfolio_tickers = {t["ticker"] for t in portfolio_trades}

    # ── Stage 0 : Market regime filter intentionally disabled ──────────────────
    market_ok = True
    regime_label = "UNKNOWN"
    print("\n  Market regime filter disabled — skipping Nifty EMA gate.\n")

    if LIVE_MODE:
        print(f"  Scanning {total} stocks ...", flush=True)

    # ── Scan loop ─────────────────────────────────────────────────────────────
    for ticker, name in STOCKS.items():
        # Skip dead/delisted tickers
        if ticker in DEAD_TICKERS:
            skipped += 1
            continue
        
        # Skip if already in portfolio (any status) - prevents duplicate signals
        if ticker in portfolio_tickers:
            skipped += 1
            continue
        
        n = scanned + skipped + 1

        if not LIVE_MODE:
            print(f"  [{n:>3}/{total}]  {name:<26} ({ticker:<16})  ",
                  end="", flush=True)

        try:
            df = fetch_data(ticker)
        except Exception as exc:
            if not LIVE_MODE:
                print(f"FETCH ERROR: {exc}")
            skipped += 1
            continue
        if df is None:
            if not LIVE_MODE:
                print("NO DATA")
            skipped += 1
            continue

        try:
            df = add_indicators(df)
        except Exception as exc:
            if not LIVE_MODE:
                print(f"INDICATOR ERROR: {exc}")
            skipped += 1
            continue
        scanned += 1

        # Price floor — skip penny stocks
        if float(df["Close"].iloc[-1]) < MIN_PRICE:
            if not LIVE_MODE:
                print(f"penny stock (< Rs.{MIN_PRICE}) — skipped")
            continue

        # Stage 0b — liquidity gate
        if not check_liquidity(df):
            if not LIVE_MODE:
                print("illiquid — skipped")
            continue

        # Stage 1 — bearish trend
        trend = check_trend_short(df)
        if trend is None:
            if not LIVE_MODE:
                print("trend fail (not bearish)")
            continue

        ema_passed += 1

        # Stage 2 — coil near lows
        coil = check_consolidation_short(df)
        if coil is None:
            if not LIVE_MODE:
                print("trend ok | coil fail")
            continue

        coil_passed += 1

        # Stage 3a — risk
        setup = calculate_trade_setup_short(coil["period_high"], coil["period_low"])
        if not setup["is_valid"]:
            if not LIVE_MODE:
                print(f"trend+coil ok | risk {setup['risk_pct']:.1f}%  -> risk too wide")
            continue

        risk_passed += 1

        # Stage 3b — volume
        vol = check_volume(df)
        if vol is None:
            if not LIVE_MODE:
                print("trend+coil+risk ok | weak volume  -> filtered")
            continue

        vol_passed += 1

        # Stage 3c — gap-down guard
        gap = check_gap_down(df, setup["entry"])
        if gap["is_gap_down"]:
            if not LIVE_MODE:
                print(f"trend+coil+risk+vol ok | open Rs.{gap['today_open']:,.2f}"
                      f"  gapped {gap['gap_pct']:.2f}% below entry  -> invalid (gap-down)")
            continue

        # Stage 3d — earnings blackout
        e_dates = get_earnings_dates(ticker)
        if is_near_earnings(e_dates, today):
            earnings_skipped += 1
            if not LIVE_MODE:
                print("skipped — earnings nearby")
            continue

        score = score_short_breakout(trend, coil)

        # Check if already in portfolio (skip PENDING/ACTIVE, allow CLOSED for re-entry)
        in_portfolio = any(t["ticker"] == ticker for t in portfolio_trades)
        if in_portfolio:
            continue
        
        if not LIVE_MODE:
            print(f"SHORT SETUP  |  score {score['total']:.1f}/100  "
                  f"range {coil['range_pct']:.1f}%  "
                  f"risk {setup['risk_pct']:.1f}%  "
                  f"vol {vol['surge_ratio']:.2f}x  "
                  f"open {gap['gap_pct']:+.2f}%")

        signal_date = df.index[-1].strftime("%d-%m-%Y") if hasattr(df.index[-1], "strftime") else str(df.index[-1])

        # Track setup in portfolio
        add_to_portfolio(ticker, name, "short_breakout", setup["entry"], setup["stop_loss"], setup["target"], score['total'])

        final_setups.append({
            "name":   name,
            "ticker": ticker,
            "strategy": "short_breakout",
            "signal_date": signal_date,
            "trend":  trend,
            "cons":   coil,
            "setup":  setup,
            "vol":    vol,
            "gap":    gap,
            "score":  score,
        })

    # ── Sort by score ────────────────────────────────────────────────────────
    final_setups.sort(key=lambda x: x["score"]["total"], reverse=True)

    # ── Scan summary ─────────────────────────────────────────────────────────
    if not LIVE_MODE:
        print()
        print("=" * width)
        print(f"{'SCAN SUMMARY  [SHORT]':^{width}}")
        print("=" * width)
        print(f"  Universe              : {total} stocks")
        print(f"  Successfully scanned  : {scanned}")
        print(f"  Skipped (no data)     : {skipped}")
        print(f"  Passed Stage 1  (Bearish trend)  : {ema_passed}")
        print(f"  Passed Stage 2  (Coil near low)  : {coil_passed}")
        print(f"  Passed Stage 3a (Risk)           : {risk_passed}")
        print(f"  Passed Stage 3b (Volume)         : {vol_passed}")
        print(f"  Skipped Stage 3d (Earnings)      : {earnings_skipped}")
        print(f"  Passed all stages                : {len(final_setups)}")

    # ── Trade cards ──────────────────────────────────────────────────────────
    print()
    print("=" * width)
    print(f"{'SHORT TRADE SETUPS':^{width}}")
    print("=" * width)

    if final_setups:
        for i, s in enumerate(final_setups, 1):
            if LIVE_MODE:
                print_trade_card_compact_short(
                    rank=i, name=s["name"], ticker=s["ticker"],
                    setup=s["setup"], score=s["score"], vol=s["vol"],
                    width=width,
                )
            else:
                print_trade_card_short(
                    rank=i, name=s["name"], ticker=s["ticker"],
                    trend=s["trend"], cons=s["cons"], setup=s["setup"],
                    vol=s["vol"], gap=s["gap"], score=s["score"], width=width,
                )
            print()

        if not LIVE_MODE:
            print(f"  * {len(final_setups)} short setup(s) ranked  |  "
                  f"Score = Risk({SCORE_WEIGHT_RISK}) + Range({SCORE_WEIGHT_RANGE}) + Trend({SCORE_WEIGHT_TREND})")
    else:
        print()
        print("  No short trade setups found today.")
        if not LIVE_MODE:
            print("  Tip: widen MAX_RANGE_PCT or NEAR_HIGH_PCT in config/settings.py.")

    print("=" * width)

    print_execution_summary_short(final_setups, market_ok=market_ok,
                                  regime_label=regime_label, width=width)
    
    # Send signals to Discord
    if final_setups:
        send_signals_to_discord(final_setups, "short_breakout")
    
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="NSE Swing Trade Screener")
    parser.add_argument(
        "--strategy",
        required=True,
        choices=["long_breakout", "short_breakout"],
        help="Strategy to run: long_breakout or short_breakout",
    )
    args = parser.parse_args()

    if args.strategy == "long_breakout":
        run_screener()
    elif args.strategy == "short_breakout":
        run_screener_short()
    else:
        print(f"Unknown strategy: {args.strategy}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

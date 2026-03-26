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
from typing import TypedDict

import pandas as pd
from datetime import datetime, timedelta
from data.cache    import fetch_ohlcv
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
    trend: TrendResult
    cons: ConsolidationResult
    setup: TradeSetupResult
    vol: VolumeResult
    gap: GapUpResult
    score: ScoreResult


# ── Data helper ───────────────────────────────────────────────────────────────

def fetch_data(
    ticker:  str,
    days:    int  = SCREENER_DAYS,
    refresh: bool = False,
) -> pd.DataFrame | None:
    """
    Return `days` of daily OHLCV data.  Delegates to data.cache so the first
    call downloads and saves  data/<ticker>.csv; subsequent calls load from
    disk.  Pass refresh=True to force a fresh download for today's prices.
    """
    return fetch_ohlcv(ticker, days, refresh=refresh)


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
    rank:   int,
    name:   str,
    ticker: str,
    trend:  TrendResult,
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
    print(f"  {'  Risk score':<22}  {score['risk_score']:>5.1f} / 40"
          f"   (lower risk % is better)")
    print(f"  {'  Range score':<22}  {score['range_score']:>5.1f} / 35"
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
    print(f"  {'  Trend score':<22}  {score['trend_score']:>5.1f} / 25"
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
        "UNKNOWN":     ("❓", "unknown — proceeding with caution"),
    }
    r_icon, r_text = _reg_display.get(regime_label, ("❓", regime_label))
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
    print(f"{'Stage 0 : Market Regime  (Nifty 50 > EMA50)':^{width}}")
    print(f"{'Stage 1 : Close > EMA50 > EMA200':^{width}}")
    print(f"{'Stage 2 : Coil  (range < ' + str(MAX_RANGE_PCT) + '%, near high < ' + str(NEAR_HIGH_PCT) + '%)':^{width}}")
    gap_pct_str = f"{int((GAP_UP_THRESHOLD - 1) * 100)}%"
    print(f"{'Stage 3 : Risk < ' + str(MAX_RISK_PCT) + '%  |  Vol > ' + str(VOLUME_MIN_RATIO) + 'x  |  No gap-up > ' + gap_pct_str + '  |  RR 1:' + str(int(REWARD_RATIO)):^{width}}")
    print(f"{'Stage 3d: Earnings blackout (' + str(EARNINGS_LOOKBACK_DAYS) + 'd / ' + str(EARNINGS_LOOKAHEAD_DAYS) + 'd)':^{width}}")
    print(f"{'Date : ' + today.strftime('%d %b %Y  %H:%M'):^{width}}")
    print(f"{'Universe : ' + str(total) + ' stocks':^{width}}")
    print("=" * width)

    # ── Stage 0: Market regime ────────────────────────────────────────────────
    print(f"\n  Checking market regime ({NIFTY_TICKER}) ...", end="  ", flush=True)
    regime = check_market_regime()
    print("done.\n")

    print("=" * width)
    print(f"{'MARKET REGIME  —  NIFTY 50':^{width}}")
    print("=" * width)

    if regime["error"]:
        print(f"  WARNING: {regime['error']}")
        print("  Proceeding without market filter (data unavailable).")
        market_ok    = True
        regime_label = "UNKNOWN"
    else:
        _regime_map = {
            "STRONG_BULL": ("✅", "STRONG BULL"),
            "EARLY_TREND": ("⚡", "EARLY TREND  (EMA20 recovery, reduced conviction)"),
            "BEAR":        ("🚫", "BEAR"),
        }
        r_icon, r_text = _regime_map.get(regime["regime"], ("❓", regime["regime"]))

        assert regime["close"] is not None
        assert regime["ema20"] is not None
        assert regime["ema50"] is not None
        gap50     = round(float((regime["close"] - regime["ema50"]) / regime["ema50"] * 100), 2)
        gap50_sign = "+" if gap50 >= 0 else ""
        gap20      = round(float((regime["close"] - regime["ema20"]) / regime["ema20"] * 100), 2)
        gap20_sign = "+" if gap20 >= 0 else ""

        print(f"  {'Nifty Close':<22}  {regime['close']:>10,.2f}")
        print(f"  {'Nifty EMA 20':<22}  {regime['ema20']:>10,.2f}"
              f"   ({gap20_sign}{gap20:.2f}%)")
        print(f"  {'Nifty EMA 50':<22}  {regime['ema50']:>10,.2f}"
              f"   ({gap50_sign}{gap50:.2f}%)")
        print(f"  {'Market Status':<22}  {r_icon}  {r_text}")
        market_ok    = regime["is_bullish"]
        regime_label = regime["regime"]

    print("=" * width)

    if not market_ok:
        print()
        print("  Market is NOT favorable — Nifty is below EMA50 and EMA20 slope "
              "is negative.")
        print("  No individual stock trades allowed in a BEAR regime.")
        print("  Re-run when Nifty shows early recovery (EMA20 slope turns up).")
        print()
        if LIVE_MODE:
            print_execution_summary([], market_ok=False,
                                    regime_label="BEAR", width=width)
        return

    print()

    # ── Scan progress indicator (LIVE_MODE) ───────────────────────────────────
    if LIVE_MODE:
        print(f"  Scanning {total} stocks ...", flush=True)

    # ── Scan loop ─────────────────────────────────────────────────────────────
    for ticker, name in STOCKS.items():
        n = scanned + skipped + 1

        if not LIVE_MODE:
            print(f"  [{n:>3}/{total}]  {name:<26} ({ticker:<16})  ",
                  end="", flush=True)

        df = fetch_data(ticker)
        if df is None:
            if not LIVE_MODE:
                print("NO DATA")
            skipped += 1
            continue

        df = add_indicators(df)
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

        if not LIVE_MODE:
            print(f"SETUP FOUND  |  score {score['total']:.1f}/100  "
                  f"range {coil['range_pct']:.1f}%  "
                  f"risk {setup['risk_pct']:.1f}%  "
                  f"vol {vol['surge_ratio']:.2f}x  "
                  f"open {gap['gap_pct']:+.2f}%")

        final_setups.append({
            "name":   name,
            "ticker": ticker,
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
                  f"Score = Risk(40) + Range(35) + Trend(25)")
    else:
        print()
        print("  No trade setups found today.")
        if not LIVE_MODE:
            print("  Tip: widen MAX_RANGE_PCT or NEAR_HIGH_PCT in config/settings.py.")

    print("=" * width)

    # ── Execution brief (always shown; full detail only in LIVE_MODE) ─────────
    print_execution_summary(final_setups, market_ok=market_ok,
                            regime_label=regime_label, width=width)
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
    print(f"  {'  Risk score':<22}  {score['risk_score']:>5.1f} / 40"
          f"   (lower risk % is better)")
    print(f"  {'  Range score':<22}  {score['range_score']:>5.1f} / 35"
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
    print(f"  {'  Trend score':<22}  {score['trend_score']:>5.1f} / 25"
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
        "STRONG_BEAR": ("✅", "STRONG BEAR — full short capacity"),
        "EARLY_BEAR":  ("⚡", "EARLY BEAR — reduced short capacity"),
        "BULL":        ("🚫", "BULL — no short trades today"),
        "UNKNOWN":     ("❓", "unknown — proceeding with caution"),
    }
    r_icon, r_text = _reg_display.get(regime_label, ("❓", regime_label))
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
    print(f"{'Stage 0 : Market Regime  (Nifty 50 < EMA50 — bearish)':^{width}}")
    print(f"{'Stage 1 : Close < EMA50 < EMA200  (downtrend)':^{width}}")
    print(f"{'Stage 2 : Coil  (range < ' + str(MAX_RANGE_PCT) + '%, near low < ' + str(NEAR_HIGH_PCT) + '%)':^{width}}")
    gap_pct_str = f"{int((GAP_UP_THRESHOLD - 1) * 100)}%"
    print(f"{'Stage 3 : Risk < ' + str(MAX_RISK_PCT) + '%  |  Vol > ' + str(VOLUME_MIN_RATIO) + 'x  |  No gap-down > ' + gap_pct_str + '  |  RR 1:' + str(int(REWARD_RATIO)):^{width}}")
    print(f"{'Stage 3d: Earnings blackout (' + str(EARNINGS_LOOKBACK_DAYS) + 'd / ' + str(EARNINGS_LOOKAHEAD_DAYS) + 'd)':^{width}}")
    print(f"{'Date : ' + today.strftime('%d %b %Y  %H:%M'):^{width}}")
    print(f"{'Universe : ' + str(total) + ' stocks':^{width}}")
    print("=" * width)

    # ── Stage 0: Market regime (bearish) ─────────────────────────────────────
    print(f"\n  Checking market regime ({NIFTY_TICKER}) ...", end="  ", flush=True)
    regime = check_market_regime_bearish()
    print("done.\n")

    print("=" * width)
    print(f"{'MARKET REGIME  —  NIFTY 50  [SHORT]':^{width}}")
    print("=" * width)

    if regime["error"]:
        print(f"  WARNING: {regime['error']}")
        print("  Proceeding without market filter (data unavailable).")
        market_ok    = True
        regime_label = "UNKNOWN"
    else:
        _regime_map = {
            "STRONG_BEAR": ("✅", "STRONG BEAR — shorts allowed"),
            "EARLY_BEAR":  ("⚡", "EARLY BEAR  (EMA20 declining, reduced conviction)"),
            "BULL":        ("🚫", "BULL — no shorts"),
        }
        r_icon, r_text = _regime_map.get(regime["regime"], ("❓", regime["regime"]))

        assert regime["close"] is not None
        assert regime["ema20"] is not None
        assert regime["ema50"] is not None
        gap50      = round(float((regime["close"] - regime["ema50"]) / regime["ema50"] * 100), 2)
        gap50_sign = "+" if gap50 >= 0 else ""
        gap20      = round(float((regime["close"] - regime["ema20"]) / regime["ema20"] * 100), 2)
        gap20_sign = "+" if gap20 >= 0 else ""

        print(f"  {'Nifty Close':<22}  {regime['close']:>10,.2f}")
        print(f"  {'Nifty EMA 20':<22}  {regime['ema20']:>10,.2f}"
              f"   ({gap20_sign}{gap20:.2f}%)")
        print(f"  {'Nifty EMA 50':<22}  {regime['ema50']:>10,.2f}"
              f"   ({gap50_sign}{gap50:.2f}%)")
        print(f"  {'Market Status':<22}  {r_icon}  {r_text}")
        market_ok    = regime["is_bullish"]   # True = bearish-tradeable
        regime_label = regime["regime"]

    print("=" * width)

    if not market_ok:
        print()
        print("  Market is NOT bearish enough — Nifty is above EMA50 or breadth "
              "is too strong.")
        print("  No short trades allowed in a BULL regime.")
        print("  Re-run when Nifty shows bearish breakdown (close < EMA50).")
        print()
        if LIVE_MODE:
            print_execution_summary_short([], market_ok=False,
                                          regime_label="BULL", width=width)
        return

    print()

    if LIVE_MODE:
        print(f"  Scanning {total} stocks ...", flush=True)

    # ── Scan loop ─────────────────────────────────────────────────────────────
    for ticker, name in STOCKS.items():
        n = scanned + skipped + 1

        if not LIVE_MODE:
            print(f"  [{n:>3}/{total}]  {name:<26} ({ticker:<16})  ",
                  end="", flush=True)

        df = fetch_data(ticker)
        if df is None:
            if not LIVE_MODE:
                print("NO DATA")
            skipped += 1
            continue

        df = add_indicators(df)
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

        if not LIVE_MODE:
            print(f"SHORT SETUP  |  score {score['total']:.1f}/100  "
                  f"range {coil['range_pct']:.1f}%  "
                  f"risk {setup['risk_pct']:.1f}%  "
                  f"vol {vol['surge_ratio']:.2f}x  "
                  f"open {gap['gap_pct']:+.2f}%")

        final_setups.append({
            "name":   name,
            "ticker": ticker,
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
                  f"Score = Risk(40) + Range(35) + Trend(25)")
    else:
        print()
        print("  No short trade setups found today.")
        if not LIVE_MODE:
            print("  Tip: widen MAX_RANGE_PCT or NEAR_HIGH_PCT in config/settings.py.")

    print("=" * width)

    print_execution_summary_short(final_setups, market_ok=market_ok,
                                  regime_label=regime_label, width=width)
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

"""
DEPRECATED — this file is kept for reference only.
Use  screener.py  instead:

    python screener.py
    python screener.py --strategy breakout

The full strategy logic has been moved to strategies/breakout.py and
all shared settings live in config/settings.py.
───────────────────────────────────────────────────────────────────────
Swing Trading Screener - Indian Stocks (NSE)
Scans ~75 NSE stocks, fetches 14 months of daily OHLCV data,
computes EMA 50 & EMA 200, checks for price consolidation, then
builds a complete trade setup for every stock that passes.

Market regime gate (runs first):
  0. Nifty 50 close must be above its EMA50 — broad market must be bullish.
     If not, all stock scans are skipped.

Three-stage stock filter:
  1. Trend   : Close > EMA50 > EMA200
  2. Coil    : Range of last N candles < MAX_RANGE_PCT
               AND Close within NEAR_HIGH_PCT of the period high
  3. Risk    : risk (entry - stop) < MAX_RISK_PCT of entry price
"""

import sys
from typing import TypedDict

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ── Type definitions ─────────────────────────────────────────────────────────

class MarketRegimeResult(TypedDict):
    close: float | None
    ema50: float | None
    is_bullish: bool
    error: str | None


class TrendResult(TypedDict):
    close: float
    ema50: float
    ema200: float
    is_bullish: bool


class ConsolidationResult(TypedDict):
    period_high: float
    period_low: float
    range_pct: float
    gap_to_high_pct: float
    near_high: bool
    is_consolidating: bool


class VolumeResult(TypedDict):
    latest_volume: int
    avg_volume: int
    surge_ratio: float
    volume_ok: bool


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


class SetupEntry(TypedDict):
    name: str
    ticker: str
    trend: TrendResult
    cons: ConsolidationResult
    setup: TradeSetupResult
    vol: VolumeResult
    gap: GapUpResult
    score: ScoreResult


# ── Configuration ─────────────────────────────────────────────────────────────

STOCKS = {
    # Large-cap / Index heavyweights
    "RELIANCE.NS":   "Reliance Ind.",
    "TCS.NS":        "TCS",
    "HDFCBANK.NS":   "HDFC Bank",
    "INFY.NS":       "Infosys",
    "ICICIBANK.NS":  "ICICI Bank",
    "HINDUNILVR.NS": "Hindustan Unilever",
    "SBIN.NS":       "SBI",
    "BHARTIARTL.NS": "Bharti Airtel",
    "ITC.NS":        "ITC",
    "KOTAKBANK.NS":  "Kotak Bank",
    "LT.NS":         "L&T",
    "AXISBANK.NS":   "Axis Bank",
    "ASIANPAINT.NS": "Asian Paints",
    "MARUTI.NS":     "Maruti Suzuki",
    "TITAN.NS":      "Titan",
    "SUNPHARMA.NS":  "Sun Pharma",
    "BAJFINANCE.NS": "Bajaj Finance",
    "NESTLEIND.NS":  "Nestle India",
    "WIPRO.NS":      "Wipro",
    "HCLTECH.NS":    "HCL Tech",
    "ONGC.NS":       "ONGC",
    "NTPC.NS":       "NTPC",
    "POWERGRID.NS":  "Power Grid",
    "TECHM.NS":      "Tech Mahindra",
    "ULTRACEMCO.NS": "UltraTech Cement",
    "JSWSTEEL.NS":   "JSW Steel",
    "TATASTEEL.NS":  "Tata Steel",
    "TATAMOTOR.NS":  "Tata Motors",
    "M&M.NS":        "M&M",
    "ADANIENT.NS":   "Adani Ent.",
    "ADANIPORTS.NS": "Adani Ports",
    "BAJAJFINSV.NS": "Bajaj Finserv",
    "INDUSINDBK.NS": "IndusInd Bank",
    "EICHERMOT.NS":  "Eicher Motors",
    "DRREDDY.NS":    "Dr. Reddy's",
    "CIPLA.NS":      "Cipla",
    "DIVISLAB.NS":   "Divi's Labs",
    "APOLLOHOSP.NS": "Apollo Hospitals",
    "HEROMOTOCO.NS": "Hero MotoCorp",
    "TATACONSUM.NS": "Tata Consumer",
    # Mid-cap
    "PIDILITIND.NS": "Pidilite Ind.",
    "HAVELLS.NS":    "Havells",
    "VOLTAS.NS":     "Voltas",
    "MUTHOOTFIN.NS": "Muthoot Finance",
    "PIIND.NS":      "Piramal Ind.",
    "LUPIN.NS":      "Lupin",
    "TORNTPHARM.NS": "Torrent Pharma",
    "BIOCON.NS":     "Biocon",
    "MOTHERSON.NS":  "Samvardhana Mother.",
    "BALKRISIND.NS": "Balkrishna Ind.",
    "ASTRAL.NS":     "Astral",
    "POLYCAB.NS":    "Polycab India",
    "TRENT.NS":      "Trent",
    "DMART.NS":      "Avenue Supermarts",
    "NAUKRI.NS":     "Info Edge",
    "PAYTM.NS":      "Paytm",
    "NYKAA.NS":      "Nykaa",
    "IRCTC.NS":      "IRCTC",
    "LINDEINDIA.NS": "Linde India",
    "AUROPHARMA.NS": "Aurobindo Pharma",
    "GLAND.NS":      "Gland Pharma",
    "SYNGENE.NS":    "Syngene Int.",
    "CHOLAFIN.NS":   "Cholamandalam Fin.",
    "MANAPPURAM.NS": "Manappuram Fin.",
    "ABCAPITAL.NS":  "Aditya Birla Cap.",
    "ICICIGI.NS":    "ICICI Lombard",
    "SBILIFE.NS":    "SBI Life",
    "HDFCLIFE.NS":   "HDFC Life",
    "LICI.NS":       "LIC India",
    "COALINDIA.NS":  "Coal India",
    "SAIL.NS":       "SAIL",
    "NMDC.NS":       "NMDC",
    "GRASIM.NS":     "Grasim Ind.",
    "SHREECEM.NS":   "Shree Cement",
    "AMBUJACEM.NS":  "Ambuja Cement",
}

EMA_SHORT      = 50
EMA_LONG       = 200
PERIOD_DAYS    = 420    # ~14 months of calendar days → >200 trading bars

CONSOLIDATION_CANDLES  = 12    # look-back window (10–15 candles)
MAX_RANGE_PCT          = 8.0   # consolidation band must be tighter than this %
NEAR_HIGH_PCT          = 5.0   # close must be within this % of the period high

REWARD_RATIO    = 2.0   # target = entry + REWARD_RATIO * risk  (1:2 RR)
MAX_RISK_PCT    = 10.0  # skip setup if risk > this % of entry price

VOLUME_AVG_PERIOD   = 20    # rolling window for average volume
VOLUME_SURGE_FACTOR = 1.3   # latest volume must exceed avg by this multiple

GAP_UP_THRESHOLD    = 1.02  # if today's open > entry * this, the setup is invalid

NIFTY_TICKER    = "^NSEI"   # Nifty 50 index on Yahoo Finance


# ── Functions ─────────────────────────────────────────────────────────────────

def fetch_data(ticker: str, days: int = PERIOD_DAYS) -> pd.DataFrame | None:
    """Download `days` of daily OHLCV data for a ticker. Returns None on failure."""
    end   = datetime.today()
    start = end - timedelta(days=days)

    try:
        df = yf.download(
            ticker,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval="1d",
            progress=False,
            auto_adjust=True,
        )
    except Exception:
        return None

    if df.empty:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    return df


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Return the Exponential Moving Average of `series` for `period` bars."""
    return series.ewm(span=period, adjust=False).mean()


def check_market_regime(
    ticker: str = NIFTY_TICKER,
    ema_period: int = EMA_SHORT,
    days: int = PERIOD_DAYS,
) -> MarketRegimeResult:
    """
    Fetch the index and determine whether the broad market is bullish.

    Bullish regime : latest close > EMA50 of the index
    Bearish regime : latest close <= EMA50 — individual stock trades suppressed

    Returns: close, ema50, is_bullish, error (str | None)
    """
    df = fetch_data(ticker, days=days)

    if df is None:
        return {"close": None, "ema50": None, "is_bullish": False,
                "error": f"Could not fetch data for {ticker}"}

    close = round(float(df["Close"].iloc[-1]), 2)
    ema50 = round(float(calculate_ema(df["Close"], ema_period).iloc[-1]), 2)

    return {
        "close":      close,
        "ema50":      ema50,
        "is_bullish": close > ema50,
        "error":      None,
    }


def check_bullish_trend(df: pd.DataFrame) -> TrendResult:
    """
    Compute EMA50 & EMA200 and evaluate the latest bar.

    Returns: close, ema50, ema200, is_bullish
    """
    df = df.copy()
    df["EMA50"]  = calculate_ema(df["Close"], EMA_SHORT)
    df["EMA200"] = calculate_ema(df["Close"], EMA_LONG)

    latest = df.iloc[-1]
    close  = round(float(latest["Close"]),  2)
    ema50  = round(float(latest["EMA50"]),  2)
    ema200 = round(float(latest["EMA200"]), 2)

    return {
        "close":      close,
        "ema50":      ema50,
        "ema200":     ema200,
        "is_bullish": close > ema50 > ema200,
    }


def check_consolidation(
    df: pd.DataFrame,
    candles:       int   = CONSOLIDATION_CANDLES,
    max_range_pct: float = MAX_RANGE_PCT,
    near_high_pct: float = NEAR_HIGH_PCT,
) -> ConsolidationResult:
    """
    Analyse the last `candles` bars for a tight consolidation pattern.

    Logic:
      - period_high  = max(High)  over the window
      - period_low   = min(Low)   over the window
      - range_pct    = (period_high - period_low) / period_low * 100
      - near_high    = close is within `near_high_pct`% below period_high

    Returns: period_high, period_low, range_pct, near_high, is_consolidating
    """
    window = df.tail(candles)

    period_high = round(float(window["High"].max()), 2)
    period_low  = round(float(window["Low"].min()),  2)
    close       = round(float(df["Close"].iloc[-1]), 2)

    range_pct   = round(float((period_high - period_low) / period_low * 100), 2)
    # How far is close below the recent high, expressed as %
    gap_to_high = round(float((period_high - close) / period_high * 100), 2)
    near_high   = gap_to_high <= near_high_pct

    is_consolidating = (range_pct <= max_range_pct) and near_high

    return {
        "period_high":      period_high,
        "period_low":       period_low,
        "range_pct":        range_pct,
        "gap_to_high_pct":  gap_to_high,
        "near_high":        near_high,
        "is_consolidating": is_consolidating,
    }


def check_volume(
    df: pd.DataFrame,
    avg_period:    int   = VOLUME_AVG_PERIOD,
    surge_factor:  float = VOLUME_SURGE_FACTOR,
) -> VolumeResult:
    """
    Compare the latest candle's volume against the rolling average.

      avg_volume     = mean(Volume) over the last `avg_period` bars
                       (excludes the latest bar so we measure the baseline
                        before the potential breakout candle)
      latest_volume  = Volume on the most recent bar
      surge_ratio    = latest_volume / avg_volume
      volume_ok      = surge_ratio >= surge_factor

    Returns: latest_volume, avg_volume, surge_ratio, volume_ok
    """
    # Exclude the last bar from the baseline so it can't inflate its own average
    baseline       = df["Volume"].iloc[-(avg_period + 1):-1]
    avg_volume     = round(float(baseline.mean()), 0)
    latest_volume  = round(float(df["Volume"].iloc[-1]), 0)
    surge_ratio    = round(float(latest_volume / avg_volume), 2) if avg_volume > 0 else 0.0

    return {
        "latest_volume": int(latest_volume),
        "avg_volume":    int(avg_volume),
        "surge_ratio":   surge_ratio,
        "volume_ok":     surge_ratio >= surge_factor,
    }


def check_gap_up(
    df: pd.DataFrame,
    entry_price:   float,
    threshold:     float = GAP_UP_THRESHOLD,
) -> GapUpResult:
    """
    Detect whether today's open has already gapped above the entry level.

    A gap-up beyond the threshold means the stock opened above the breakout
    point by more than the allowed buffer — chasing at this price gives a
    poor risk/reward and the setup is considered invalid.

      today_open  = Open of the most recent bar
      gap_pct     = (today_open - entry_price) / entry_price * 100
      is_gap_up   = today_open > entry_price * threshold

    Returns: today_open, gap_pct, is_gap_up
    """
    today_open = round(float(df["Open"].iloc[-1]), 2)
    gap_pct    = round(float((today_open - entry_price) / entry_price * 100), 2)

    return {
        "today_open": today_open,
        "gap_pct":    gap_pct,
        "is_gap_up":  today_open > entry_price * threshold,
    }


def _trend_score(ema50_gap_pct: float) -> float:
    """
    Piecewise score (0–25 pts) for how far close sits above EMA50.

    Zone              Gap %       Score
    ──────────────────────────────────────────────────────
    Too close / weak  0  – 1 %   0 → 25  (linear ramp-up)
    Sweet spot        1  – 4 %   25       (full marks)
    Slightly extended 4  – 6 %   25 → 12.5  (linear decline)
    Overextended      6 %+       12.5 → 0   (linear penalty, floor 0)
    """
    if ema50_gap_pct < 0:
        return 0.0
    elif ema50_gap_pct < 1.0:
        # ramp up: 0% gap → 0 pts, 1% gap → 25 pts
        return ema50_gap_pct / 1.0 * 25.0
    elif ema50_gap_pct <= 4.0:
        # sweet spot: full score
        return 25.0
    elif ema50_gap_pct <= 6.0:
        # mild extension: 4% → 25 pts, 6% → 12.5 pts
        return 25.0 - ((ema50_gap_pct - 4.0) / 2.0) * 12.5
    else:
        # overextended: 6% → 12.5 pts, 12% → 0 pts
        return max(0.0, 12.5 - ((ema50_gap_pct - 6.0) / 6.0) * 12.5)


def score_setup(trend: TrendResult, cons: ConsolidationResult, setup: TradeSetupResult) -> ScoreResult:
    """
    Score a trade setup out of 100 using three components.

    Component         Weight   Logic
    ──────────────────────────────────────────────────────────────
    Risk score           40    lower risk_pct → higher score
    Range score          35    tighter consolidation → higher score
    Trend score          25    optimal EMA50 gap of 1–4%
                               (<1% weak, >6% penalised as overextended)

    Returns: total, risk_score, range_score, trend_score, ema50_gap_pct
    """
    # 0–40 pts:  risk_pct=0 → 40, risk_pct=MAX_RISK_PCT → 0
    risk_score = max(0.0, (MAX_RISK_PCT - setup["risk_pct"]) / MAX_RISK_PCT * 40)

    # 0–35 pts:  range_pct=0 → 35, range_pct=MAX_RANGE_PCT → 0
    range_score = max(0.0, (MAX_RANGE_PCT - cons["range_pct"]) / MAX_RANGE_PCT * 35)

    # 0–25 pts:  piecewise curve — rewards 1–4% above EMA50, penalises >6%
    ema50_gap_pct = (trend["close"] - trend["ema50"]) / trend["ema50"] * 100
    trend_score   = _trend_score(ema50_gap_pct)

    total = round(float(risk_score + range_score + trend_score), 1)

    return {
        "total":          total,
        "risk_score":     round(float(risk_score),     1),
        "range_score":    round(float(range_score),    1),
        "trend_score":    round(float(trend_score),    1),
        "ema50_gap_pct":  round(float(ema50_gap_pct),  2),
    }


def calculate_trade_setup(
    period_high:  float,
    period_low:   float,
    reward_ratio: float = REWARD_RATIO,
    max_risk_pct: float = MAX_RISK_PCT,
) -> TradeSetupResult:
    """
    Build a breakout trade plan from the consolidation range.

      entry      = period_high          (buy above the box)
      stop_loss  = period_low           (invalidation level)
      risk       = entry - stop_loss
      target     = entry + reward_ratio * risk   (default 1:2 RR)
      risk_pct   = risk / entry * 100

    Returns: entry, stop_loss, target, risk, risk_pct, rr_ratio, is_valid
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


# ── Main ──────────────────────────────────────────────────────────────────────

def _rank_label(rank: int) -> str:
    """Return an emoji rank label for a given position."""
    if rank == 1:
        return "🔥 BEST TRADE"
    return f"🟡 Backup {rank - 1}"


def _score_bar(score: float, width: int = 20) -> str:
    """Render a simple ASCII progress bar for a 0–100 score."""
    filled = round(float(score / 100 * width))
    return "[" + "#" * filled + "-" * (width - filled) + f"]  {score:.1f}/100"


def print_trade_card(rank: int, name: str, ticker: str,
                     trend: TrendResult, cons: ConsolidationResult, setup: TradeSetupResult,
                     vol: VolumeResult, gap: GapUpResult, score: ScoreResult, width: int) -> None:
    """Print a ranked, scored trade setup card for a single stock."""
    upside_pct  = round(float((setup["target"] - setup["entry"]) / setup["entry"] * 100), 2)
    label       = _rank_label(rank)
    vol_tag     = "Volume OK ✅" if vol["volume_ok"] else "Weak Volume ⚠️"

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
          f"   (+{(trend['close']/trend['ema50']-1)*100:.2f}% above)")
    print(f"  {'EMA 200':<22}  Rs. {trend['ema200']:>10,.2f}")
    print()

    # Consolidation
    print(f"  {'Coil Range':<22}  {cons['range_pct']:.2f}%"
          f"   ({CONSOLIDATION_CANDLES}-candle window)")
    print(f"  {'Gap to High':<22}  {cons['gap_to_high_pct']:.2f}%")
    print()

    # Volume confirmation
    avg_vol_label = f"Avg Volume ({VOLUME_AVG_PERIOD}d)"
    print(f"  {avg_vol_label:<22}  {vol['avg_volume']:>14,}")
    print(f"  {'Latest Volume':<22}  {vol['latest_volume']:>14,}"
          f"   ({vol['surge_ratio']:.2f}x avg)")
    print(f"  {'Volume Signal':<22}  {vol_tag}")
    print()

    # Gap-up check
    gap_sign = "+" if gap["gap_pct"] >= 0 else ""
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


def main() -> None:
    width   = 72
    total   = len(STOCKS)
    scanned = 0
    skipped = 0
    ema_passed   = 0
    coil_passed  = 0
    risk_passed  = 0
    vol_passed   = 0
    final_setups: list[SetupEntry] = []

    # ── Header ────────────────────────────────────────────────────────────────
    print("=" * width)
    print(f"{'SWING TRADING SCREENER  -  INDIAN STOCKS (NSE)':^{width}}")
    print(f"{'Stage 0 : Market Regime  (Nifty 50 > EMA50)':^{width}}")
    print(f"{'Stage 1 : Close > EMA50 > EMA200':^{width}}")
    print(f"{'Stage 2 : Coil  (range < ' + str(MAX_RANGE_PCT) + '%, near high < ' + str(NEAR_HIGH_PCT) + '%)':^{width}}")
    gap_pct_str = f"{int((GAP_UP_THRESHOLD - 1) * 100)}%"
    print(f"{'Stage 3 : Risk < ' + str(MAX_RISK_PCT) + '%  |  Vol > ' + str(VOLUME_SURGE_FACTOR) + 'x  |  No gap-up > ' + gap_pct_str + '  |  RR 1:' + str(int(REWARD_RATIO)):^{width}}")
    print(f"{'Date : ' + datetime.today().strftime('%d-%m-%Y  %H:%M'):^{width}}")
    print(f"{'Universe : ' + str(total) + ' stocks':^{width}}")
    print("=" * width)

    # ── Stage 0 : Market regime ───────────────────────────────────────────────
    print(f"\n  Checking market regime ({NIFTY_TICKER}) ...", end="  ", flush=True)
    regime = check_market_regime()
    print("done.\n")

    print("=" * width)
    print(f"{'MARKET REGIME  —  NIFTY 50':^{width}}")
    print("=" * width)

    if regime["error"]:
        print(f"  WARNING: {regime['error']}")
        print(f"  Proceeding without market filter (data unavailable).")
        market_ok = True                          # fail-open so scan still runs
    else:
        status      = "BULLISH" if regime["is_bullish"] else "BEARISH"
        status_icon = "✅" if regime["is_bullish"] else "🚫"
        assert regime["close"] is not None
        assert regime["ema50"] is not None
        gap_pct     = round(float((regime["close"] - regime["ema50"]) / regime["ema50"] * 100), 2)
        gap_sign    = "+" if gap_pct >= 0 else ""

        print(f"  {'Nifty Close':<22}  {regime['close']:>10,.2f}")
        print(f"  {'Nifty EMA 50':<22}  {regime['ema50']:>10,.2f}"
              f"   ({gap_sign}{gap_pct:.2f}%)")
        print(f"  {'Market Status':<22}  {status_icon} {status}")
        market_ok = regime["is_bullish"]

    print("=" * width)

    if not market_ok:
        print()
        print("  Market is NOT favorable — Nifty is below its EMA50.")
        print("  No individual stock trades allowed in a bearish regime.")
        print("  Re-run when Nifty reclaims EMA50.")
        print()
        return

    print()

    # ── Scan loop ─────────────────────────────────────────────────────────────
    for ticker, name in STOCKS.items():
        n = scanned + skipped + 1
        print(f"  [{n:>2}/{total}]  {name:<24} ({ticker:<14})  ", end="", flush=True)

        df = fetch_data(ticker)
        if df is None:
            print("NO DATA")
            skipped += 1
            continue

        scanned += 1

        # Stage 1 — trend
        trend = check_bullish_trend(df)
        if not trend["is_bullish"]:
            print("trend fail")
            continue

        ema_passed += 1

        # Stage 2 — consolidation
        cons = check_consolidation(df)
        if not cons["is_consolidating"]:
            near_tag = "near-hi ok" if cons["near_high"] else f"gap {cons['gap_to_high_pct']:.1f}%"
            print(f"trend ok | range {cons['range_pct']:.1f}%  {near_tag}  -> coil fail")
            continue

        coil_passed += 1

        # Stage 3a — risk filter
        setup = calculate_trade_setup(cons["period_high"], cons["period_low"])
        if not setup["is_valid"]:
            print(f"trend+coil ok | risk {setup['risk_pct']:.1f}%  -> risk too wide")
            continue

        risk_passed += 1

        # Stage 3b — volume confirmation
        vol = check_volume(df)
        if not vol["volume_ok"]:
            print(f"trend+coil+risk ok | vol ratio {vol['surge_ratio']:.2f}x"
                  f"  (need {VOLUME_SURGE_FACTOR}x)  -> weak volume")
            continue

        vol_passed += 1

        # Stage 3c — gap-up validation
        gap = check_gap_up(df, setup["entry"])
        if gap["is_gap_up"]:
            print(f"trend+coil+risk+vol ok | open Rs.{gap['today_open']:,.2f}"
                  f"  gapped +{gap['gap_pct']:.2f}% above entry"
                  f"  -> invalid (gap-up)")
            continue

        score = score_setup(trend, cons, setup)
        print(f"SETUP FOUND  |  score {score['total']:.1f}/100  "
              f"range {cons['range_pct']:.1f}%  "
              f"risk {setup['risk_pct']:.1f}%  "
              f"vol {vol['surge_ratio']:.2f}x  "
              f"open {gap['gap_pct']:+.2f}%")
        final_setups.append({
            "name":   name,
            "ticker": ticker,
            "trend":  trend,
            "cons":   cons,
            "setup":  setup,
            "vol":    vol,
            "gap":    gap,
            "score":  score,
        })

    # ── Counters ──────────────────────────────────────────────────────────────
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
    print(f"  Passed Stage 3c (No gap-up)   : {len(final_setups)}")

    # ── Trade cards ───────────────────────────────────────────────────────────
    print()
    print("=" * width)
    print(f"{'TRADE SETUPS':^{width}}")
    print("=" * width)

    if final_setups:
        # Highest score first → best conviction setup at the top
        final_setups.sort(key=lambda x: x["score"]["total"], reverse=True)

        for i, s in enumerate(final_setups, 1):
            print_trade_card(
                rank=i,
                name=s["name"],
                ticker=s["ticker"],
                trend=s["trend"],
                cons=s["cons"],
                setup=s["setup"],
                vol=s["vol"],
                gap=s["gap"],
                score=s["score"],
                width=width,
            )
            print()

        print(f"  * {len(final_setups)} setup(s) ranked  |  "
              f"Score = Risk(40) + Range(35) + Trend(25)")
    else:
        print()
        print("  No trade setups found today.")
        print("  Tip: widen MAX_RANGE_PCT or NEAR_HIGH_PCT in configuration.")

    print("=" * width)
    print()


if __name__ == "__main__":
    main()

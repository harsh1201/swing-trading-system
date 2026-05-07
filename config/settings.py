"""
config/settings.py — All tunable constants for the swing-trading system.

Import from here in every module; never hard-code these values elsewhere.
"""

# ── Timezone ──────────────────────────────────────────────────────────────────
TIMEZONE = "Asia/Kolkata"

# ── Index ──────────────────────────────────────────────────────────────────────
NIFTY_TICKER = "^NSEI"

# ── Indicator periods ──────────────────────────────────────────────────────────
EMA_ULTRA_SHORT = 20    # fast EMA — used for early-trend regime detection
EMA_SHORT       = 50    # Stage 1 trend filter (medium-term)
EMA_LONG        = 200   # Stage 1 trend filter (long-term)

# ── Relative Strength (RS) Filter ────────────────────────────────────────────────
USE_RS_FILTER = True           # True = use RS filter (ADOPTED - improves WR, lowers DD)
RS_LOOKBACK = 20             # Days to calculate RS (20 = ~1 month)
RS_THRESHOLD = 0             # Stock must beat benchmark by this % (0 = any positive RS)
RS_AS_OR = False            # True = OR logic with EMA, False = AND logic

# ── EMA Stage 1 Test Parameters (not adopted - for testing only) ────────────────
USE_ALTERNATIVE_EMA = False          # True = use alternative EMA config below (for testing)
ALT_EMA_SHORT = 50                   # Alternative medium-term EMA
ALT_EMA_LONG = 200                   # Alternative long-term EMA
REQUIRE_BOTH_EMAS = True              # True = require both EMAs, False = EMA50 only

# ── ATR Trailing Exit ───────────────────────────────────────────────────────────
USE_ATR_TRAILING = False     # True = ATR-based trailing, False = EMA-based trailing
ATR_PERIOD = 14              # ATR lookback period
TRAILING_ATR_MULTIPLIER = 2.0  # Trail stop = highest_high - (multiplier × ATR)

# ── Consolidation / Coil ───────────────────────────────────────────────────────
COIL_CANDLES  = 10    # look-back window (bars) — more candidates, better performance
MAX_RANGE_PCT = 8.0  # max high-low range across the window (%) — relaxed for more candidates
NEAR_HIGH_PCT = 5.0  # close must be within this % of the period high — relaxed

# ── Trade setup ────────────────────────────────────────────────────────────────
REWARD_RATIO = 2.0    # target = entry + REWARD_RATIO × risk  (1:1.5 RR) - BEST TESTED
MAX_RISK_PCT = 12.0   # skip setup if risk > this % of entry price (relaxed from 10%)

# ── Position sizing ────────────────────────────────────────────────────────────
STARTING_EQUITY       = 100_000   # INR — starting equity for backtest
RISK_PER_TRADE        = 1.0       # % of current equity risked per open trade
MAX_CONCURRENT_TRADES = 5         # maximum simultaneous open positions

# ── Trade management ───────────────────────────────────────────────────────────



# ── Risk controls ──────────────────────────────────────────────────────────────
MAX_TRADES_PER_SECTOR        = 2    # max simultaneous open positions per sector
MAX_POSITION_PCT             = 25   # single position value <= this % of equity
EARLY_TREND_MAX_TRADES_FACTOR = 1.0  # reduce MAX_CONCURRENT_TRADES in EARLY_TREND
                                      # 1.0 = no reduction (default)
                                      # 0.6 = allow only 60% of normal slots

# ── Walk-forward validation ────────────────────────────────────────────────────
WALK_FORWARD_SPLIT_YEAR = 2023   # trades before year → in-sample (train)
                                  # trades from year onward → out-of-sample (test)

# ── Portfolio cleanup settings ──────────────────────────────────────────────────
PENDING_EXPIRY_DAYS = 5    # Remove PENDING trades after this many days
CLOSED_CLEANUP_DAYS = 15   # Remove CLOSED trades after this many days
MAX_ACTIVE_DAYS = 30       # Remove stale ACTIVE trades after this many days (no trigger date)

# ── Scoring weights ────────────────────────────────────────────────────────────
# Total = 100 points
SCORE_WEIGHT_RISK = 30   # Risk component (lower risk % = higher score)
SCORE_WEIGHT_RANGE = 30   # Range/consolidation component (tighter = higher score)
SCORE_WEIGHT_TREND = 40   # Trend component (sweet spot above EMA50 = higher score)

# ── Volume filter ──────────────────────────────────────────────────────────────
VOLUME_AVG_PERIOD = 20    # rolling baseline window (bars before current bar)
VOLUME_MIN_RATIO  = 1.0   # latest volume must be >= this multiple of the avg (1.0 = no surge required)

# ── Candle Strength filter (TESTED - DISABLED) ───────────────────────
MIN_CANDLE_STRENGTH = 0   # 0.65 = strong close, 0 = disabled (no filter), 1.0 = full body candle
                              # TESTED Apr 2026: filter reduced trades by 26% but P&L dropped 74% - DISABLED

# ── Gap-up filter (screener) ───────────────────────────────────────────────────
GAP_UP_THRESHOLD = 1.02   # today's open > entry × threshold → invalid

# ── Earnings blackout (screener) ───────────────────────────────────────────────
EARNINGS_LOOKBACK_DAYS  = 5    # skip if earnings fell within this many days past
EARNINGS_LOOKAHEAD_DAYS = 15   # skip if earnings are within this many days ahead
                                # window = [today − LOOKBACK, today + LOOKAHEAD]

# ── Deployment mode ───────────────────────────────────────────────────────────
LIVE_MODE = False   # True  → clean, minimal output for daily execution
                    # False → verbose scan log (debugging / analysis)

# ── Execution costs (backtest only) ───────────────────────────────────────────
SLIPPAGE_PCT = 0.0015   # 0.15% per side — entry fills higher, exits fill lower
COST_PCT     = 0.0025   # 0.25% of trade value — brokerage + STT + exchange fees

# ── Liquidity & price filters ─────────────────────────────────────────────────
MIN_AVG_TURNOVER = 5_00_00_000    # ₹5 Cr minimum avg daily turnover (20-day)                      # lowered from ₹10 Cr to increase candidates
MIN_PRICE        = 15              # skip stocks priced below ₹15

# ── Score threshold (backtest candidate filter) ───────────────────────────────
MIN_SCORE_THRESHOLD = 0       # skip candidates scoring below this (0 = no filter)
                              # test values: 0 (baseline) / 40 / 50 / 60 / 70

# ── Future safeguards (not yet enforced) ──────────────────────────────────────
MIN_AVG_VOLUME      = 0       # reserved — use MIN_AVG_TURNOVER instead
MAX_GAP_PCT         = 0.02    # maximum acceptable gap-up fraction (future use)

# ── Data-fetching windows ──────────────────────────────────────────────────────
SCREENER_DAYS        = 420    # calendar days for screener (~14 months)
BACKTEST_FETCH_DAYS  = 3000   # calendar days fetched (~8.2 yrs incl. EMA warmup)
                              # 7 eval yrs × 365 ≈ 2555 + 200-bar EMA warmup ≈ 2835
                              # rounded to 3000 for comfortable margin
BACKTEST_DAYS        = 1750   # trading bars in evaluation window (~7 yrs: 2019–2025)
                              # 7 × 250 = 1750; leaves ≥200 bars for EMA warmup

# ── Discord Webhooks ───────────────────────────────────────────────────────────
# Set via environment variable: export DISCORD_WEBHOOK_URL="https://..."
# Or create .env file in project root with DISCORD_WEBHOOK_URL=your_url_here
import os
from pathlib import Path

# Load .env file if exists
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key, val)

DISCORD_PORTFOLIO_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "")
DISCORD_LONG_SIGNALS_WEBHOOK = os.environ.get("DISCORD_LONG_WEBHOOK_URL", "")
DISCORD_SHORT_SIGNALS_WEBHOOK = os.environ.get("DISCORD_SHORT_WEBHOOK_URL", "")

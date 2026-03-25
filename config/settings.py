"""
config/settings.py — All tunable constants for the swing-trading system.

Import from here in every module; never hard-code these values elsewhere.
"""

# ── Index ──────────────────────────────────────────────────────────────────────
NIFTY_TICKER = "^NSEI"

# ── Indicator periods ──────────────────────────────────────────────────────────
EMA_ULTRA_SHORT = 20    # fast EMA — used for early-trend regime detection
EMA_SHORT       = 50
EMA_LONG        = 200

# ── Consolidation / Coil ───────────────────────────────────────────────────────
COIL_CANDLES  = 12    # look-back window (bars)
MAX_RANGE_PCT = 8.0   # max high-low range across the window (%)
NEAR_HIGH_PCT = 5.0   # close must be within this % of the period high

# ── Trade setup ────────────────────────────────────────────────────────────────
REWARD_RATIO = 2.0    # target = entry + REWARD_RATIO × risk  (1:2 RR)
MAX_RISK_PCT = 10.0   # skip setup if risk > this % of entry price

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

# ── Volume filter ──────────────────────────────────────────────────────────────
VOLUME_AVG_PERIOD = 20    # rolling baseline window (bars before current bar)
VOLUME_MIN_RATIO  = 1.5   # latest volume must be >= this multiple of the avg

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
MIN_AVG_TURNOVER = 10_00_00_000   # ₹10 Cr minimum avg daily turnover (20-day)
                                   # raised from 5 Cr — keeps only genuinely liquid
MIN_PRICE        = 50              # skip stocks priced below ₹50 (penny-stock guard)

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

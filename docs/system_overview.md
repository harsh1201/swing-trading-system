# 📈 SWING TRADING SYSTEM — FINAL OVERVIEW (March 2026)

---

## 🧠 SYSTEM TYPE

Trend-following swing trading system based on:
- Breakout + consolidation structure
- Market regime filtering
- Risk-defined execution
- Low win-rate, high RR model

---

## 🎯 CORE STRATEGY

### Setup: Trend + Consolidation Breakout

- Trend condition:
  - Close > EMA50 > EMA200
- Consolidation:
  - Last 12 candles range < 8%
  - Price near highs (<5% from breakout level)

---

### Entry

- Buy above **period high (breakout level)**
- Entry triggered on breakout confirmation

---

### Stop Loss

- Set at **period low (coil low)**

---

### Target

- Fixed **2R (Risk:Reward = 1:2)**

---

### Risk Management

- Risk per trade: **1% of total capital**
- Max concurrent trades: **5**
- Max allocation per trade: **25% capital**
- Sector cap: **max 2 trades per sector**

---

## 🔁 TRADE MANAGEMENT (FINAL)

### Breakeven Rule

Move SL → Entry ONLY IF:
- Price reaches **≥ 1.5R (intraday high)**
- AND daily **close > entry**
- 🛡️ *Entry-Bar Guard*: This rule is **skipped on the day of entry** to prevent premature exits due to initial volatility ("same-bar traps"). Trades must have at least one day to develop.

---

### Trailing Exit (FINAL)

- Exit when:
  - **Close < EMA20**
- Exit executed at:
  - **Next day open**
- 🛡️ *Entry-Bar Guard*: Like the Breakeven rule, the trailing stop is **skipped on the day of entry**. Only hard Stop Loss and Target act as exits on Day 1.

---

### Max Hold

- ❌ Removed
- Fully replaced by EMA20 trailing logic

---

## 🧭 MARKET REGIME SYSTEM

### Indicators Used:
- EMA20 (short-term trend)
- EMA50 (primary trend)
- Market Breadth (% stocks above EMA50)

---

### Regime Classification

#### ✅ STRONG_BULL
- Close > EMA50
- Breadth ≥ 40%

#### ⚡ EARLY_TREND
- Close ≤ EMA50 but > EMA20
- EMA20 slope positive (last 5 bars)
- Breadth ≥ 30%

#### 🚫 BEAR
- All other conditions

---

### Execution Rule

- STRONG_BULL → Trade normally
- EARLY_TREND → Trade allowed
- BEAR → ❌ No trades

---

## 🌐 MARKET BREADTH (CRITICAL)

### Definition:
- % of stocks in universe where:
  - Close > EMA50

---

### Implementation Details:

- Date-aligned across all stocks
- Uses:
  - `df.loc[:date].iloc[-1]` (nearest previous candle)
- Handles:
  - Missing data
  - Non-trading days
  - Different listing histories

---

## 🧾 UNIVERSE & FILTERS

### Universe:
- ~482 NSE stocks (expanding toward 1000+)

---

### Filters:

- Liquidity:
  - Minimum ₹10 Cr daily turnover

- Price:
  - Minimum ₹50 (avoid penny stocks)

- Volume:
  - ≥ 1.5x average volume

- Gap filter:
  - Skip if gap-up > 2%

- Risk filter:
  - Trade risk < 10%

---

## 💸 COST MODELING

- Slippage: **0.15% per side**
- Transaction cost: **0.25% per trade**

👉 Fully included in backtest

---

## 📊 PERFORMANCE SUMMARY

- Total trades: ~343
- Win rate: ~24–27%
- Avg RR: ~1 : 1.8
- Net return: ~140%
- Walk-forward validated:
  - Stable in-sample vs out-of-sample
  - No overfitting detected

---

## 🧠 SYSTEM PHILOSOPHY

- Low win rate is **expected**
- Edge comes from:
  - Risk-reward asymmetry
  - Trend capture
  - Letting winners run

---

### Expected Behavior:

- Many small losses
- Few large winners
- Long inactive periods

---

## 🗂️ DATA INFRASTRUCTURE

### Storage:
- Local CSV-based OHLCV data

---

### Modes:

#### Backtest
- `refresh=False`
- Stable, cached data

#### Screener
- Recommended: `refresh=False`
- Use `refresh=True` only for periodic updates

---

### Data Reality:

- Yahoo Finance API is unreliable
- Some stocks may fail to download
- System is designed to:
  - Skip failed stocks safely
  - Continue execution

---

## 🔄 DAILY WORKFLOW

### Step 1 — Data Refresh (once daily)
refresh=True


---

### Step 2 — Run Screener

refresh=False
LIVE_MODE=True


---

### Step 3 — Market Check

- If BEAR → ❌ No trades
- Else → proceed

---

### Step 4 — Trade Selection

- Select max 5 trades
- Respect sector caps

---

### Step 5 — Position Sizing


Position Size = (1% capital) / (Entry - SL)


---

### Step 6 — Order Placement

- Buy stop at breakout
- SL placed immediately

---

### Step 7 — Daily Management

- Apply:
  - Breakeven rule
  - EMA20 trailing

---

### Step 8 — Journal

Track:
- Entry Date & Price
- Exit Date & Price
- Exit reason (SL / BE / Trail / Target)

👉 Note: You can use `python backtest.py --strategy <strategy> --export` to automatically generate a CSV journal of all historical trades, complete with specific entry and exit dates.

---

## 🚨 GOLDEN RULES

- ❌ Do not trade in BEAR regime
- ❌ Do not override system rules
- ❌ Do not increase risk
- ❌ Do not chase missed trades

---

## 🚀 FUTURE ROADMAP

### Multi-Strategy Expansion:

1. Breakout (current system)
2. Pullback in trend (next)
3. Mean reversion (sideways markets)

---

## 🧩 FINAL NOTE

This system is:

- Mechanically defined
- Statistically validated
- Execution dependent

👉 Success depends on:
- Discipline
- Consistency
- Emotional control

---

**You are not predicting the market.  
You are executing a statistical edge.**
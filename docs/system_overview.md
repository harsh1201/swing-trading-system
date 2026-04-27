# 📈 SWING TRADING SYSTEM — CURRENT OVERVIEW (April 2026)

---

## 🧠 SYSTEM TYPE

Trend-following swing trading system based on:
- Breakout + consolidation structure
- EMA trend filtering (regime filter DISABLED - manual verification required)
- Relative Strength (RS) Filter (ADOPTED v1.11 - stock must outperform Nifty)
- Risk-defined execution
- Low win-rate (~25%), high RR (1:2) model

---

## 🎯 CORE STRATEGY

### Setup: Trend + Consolidation Breakout

- Trend condition:
  - Close > EMA50 > EMA200
- Consolidation:
  - Last 10 candles range < 8%
  - Price near highs (<5% from breakout level)
- RS Filter:
  - Longs: RS > 0 (Stock return > Nifty return over 20 days)
  - Shorts: RS < 0 (Stock return < Nifty return over 20 days)

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

## 🧭 MARKET REGIME SYSTEM (DISABLED)

### Status: REGIME FILTER IS NOW DISABLED

The regime filter has been removed from all strategies. Manual verification of market conditions is now required before trading.

### Historical (for reference):

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
- ~654 NSE stocks

---

### Filters (Current):

- Liquidity:
  - Minimum ₹5 Cr daily turnover (relaxed from ₹10 Cr)

- Price:
  - Minimum ₹15 (avoid penny stocks)

- Volume:
  - ≥ 1.0x average volume (latest volume must be at least equal to 20d avg)

- Gap filter:
  - Skip if gap-up > 2% (Long) or gap-down > 2% (Short)

- Risk filter:
  - Trade risk < 12% of entry price

---

## 💸 COST MODELING

- Slippage: **0.15% per side**
- Transaction cost: **0.25% per trade**

👉 Fully included in backtest

---

## 📊 PERFORMANCE SUMMARY (Current)

- Total trades: ~666 (long), ~468 (short)
- Win rate: ~29% (long), ~21% (short)
- Avg RR: ~1 : 2.0
- Net return: +568% (long), +31% (short)
- Test coverage: 80%

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

- ❌ Do not trade without verifying market conditions (regime filter disabled)
- ❌ Do not override system rules
- ❌ Do not exceed 1% risk per trade
- ❌ Do not chase missed trades
- ✅ Run screener daily during market hours

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
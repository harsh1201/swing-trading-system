# 📈 Usage Guide — Swing Trading System

This guide covers how to effectively use the screener and backtest scripts.

---

## 📊 Live Screener (`screener.py`)

The screener is designed for daily use to identify potential swing-trade setups in the NSE (National Stock Exchange) of India.

### **Common Commands**
```bash
# Run with default (breakout) strategy
python screener.py

# Run in LIVE_MODE (cleaner output for daily use)
# Note: Set LIVE_MODE = True in config/settings.py
python screener.py --strategy breakout
```

### **Interpreting Results**
The screener generates **Trade Cards** for identified setups. Each card includes:
-   **Rank**: How high the setup scores based on the strategy.
-   **Entry**: The breakout price level to place a buy order.
-   **Stop Loss**: The exit level to protect capital.
-   **Target**: The profit-taking objective (typically 2.0x risk).
-   **Overall Score**: A metric of quality (out of 100).
-   **Volume Surge**: How much today's volume is above the 20-day average.

---

## 🧪 Backtesting Engine (`backtest.py`)

Use the backtester to validate the strategy across historical data before deploying capital.

### **Common Commands**
```bash
# Run the full breakout backtest
python backtest.py
```

### **Output Reports**
The backtester provides a comprehensive summary after simulating years of data:
-   **Win Rate**: Percentage of winning trades.
-   **Net PnL**: Total return on capital after slippage and costs.
-   **Realized RR**: Actual risk/reward ratio achieved.
-   **Yearly Breakdown**: Profitability for each calendar year.
-   **Walk-Forward Validation**: Comparison of in-sample versus out-of-sample data.

---

## 🧭 Daily Workflow (Recommended)

1.  **Market Check (Morning)**: Run `screener.py` to check the **Market Regime**.
2.  **Scan Loop**: Review the top 5 ranked trade setups.
3.  **Order Placement**: Place buy-stop orders for the best setups.
4.  **Position Management**: Apply trailing stop rules (Close < EMA20) as detailed in `docs/system_overview.md`.

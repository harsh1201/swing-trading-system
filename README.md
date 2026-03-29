# 📈 NSE India Swing Trading System

> A rule-based, statistically validated swing trading framework for the Indian stock market (NSE).

---

## 🚀 Overview

This repository provides a complete system for finding and backtesting breakout strategies in the Indian stock market. It combines **market regime filtering**, **tight consolidation (coils)**, and **volume analysis** to identify high-probability swing trading setups.

-   **Live Screener**: Automatically scan the NSE universe for daily trade setups.
-   **Backtest Engine**: Rigorous historical validation with concurrent positions and risk management.
-   **Rule-Based Logic**: 100% mechanical strategy based on EMA trends and volatility contraction.

---

## ✨ Key Features

-   **Market Regime Filter**: Automatically stand aside in BEAR regimes (Nifty 50 < EMA50).
-   **Precision Scanners**: Filter stocks based on custom trend, coil, and volume rules.
-   **Risk-Defined Sizing**: Automatically calculates position sizes based on a 1% portfolio risk model.
-   **Cost Modeling**: Real-world backtesting including slippage and transaction costs.
-   **Walk-Forward Validation**: Built-in robustness testing across years of market data.

---

## 🏛 System Architecture

The system is modular and designed for easy extension:

1.  **`screener.py`**: Daily live execution tool.
2.  **`backtest.py`**: Strategy research and verification.
3.  **`strategies/long_breakout.py`**: Long-only breakout logic.
4.  **`strategies/short_breakout.py`**: Short-side breakdown logic.
5.  **`config/settings.py`**: User-defined risk and system parameters.

👉 See the full [Architecture Documentation](docs/architecture.md) for more details.

---

## 🛠 Quick Start

### 1. **Install**
```bash
pip install -r requirements.txt
```

### 2. **Run Screener**
Check today's trade setups for both directions:
```bash
# Long breakout strategy
python screener.py --strategy long_breakout

# Short breakdown strategy
python screener.py --strategy short_breakout
```

### 3. **Run Backtest**
Validate strategy performance historically:
```bash
# Long breakout strategy
python backtest.py --strategy long_breakout

# Short breakdown strategy
python backtest.py --strategy short_breakout

# Export completed trades to CSV (optional)
python backtest.py --strategy long_breakout --export
```

---

## 📚 Detailed Documentation

-   [🏛 System Architecture](docs/architecture.md)
-   [🧠 Strategy Overview](docs/system_overview.md)
-   [⚙️ Installation Guide](docs/installation.md)
-   [📈 Usage Guide](docs/usage_guide.md)

---

## 📊 Performance Expectations

This system expects a **low win rate (~25%)** but achieves profitability through a **high Risk-to-Reward ratio (1:2)**. Success depends on:
1.  **Discipline**: Never override the system.
2.  **Consistency**: Execute every "GO" signal in BULL regimes.
3.  **Risk Management**: Always respect the 1% risk per trade.

---

## ⚖️ Disclaimer

*Trading in the stock market involves significant risk. This software is for educational and research purposes only. Always consult with a certified financial advisor before making any investment decisions.*
# 📈 NSE India Swing Trading System

> A rule-based, statistically validated swing trading framework for the Indian stock market (NSE).
> **Version:** 1.15 (2026-04-27)

---

## 🚀 Overview

This repository provides a complete system for finding and backtesting breakout strategies in the Indian stock market. It combines **tight consolidation (coils)**, **EMA trend filtering**, and **volume analysis** to identify high-probability swing trading setups.

-   **Live Screener**: Automatically scan the NSE universe for daily trade setups.
-   **Backtest Engine**: Rigorous historical validation with concurrent positions and risk management.
-   **Rule-Based Logic**: 100% mechanical strategy based on EMA trends and volatility contraction.

---

## ✨ Key Features

-   **Trend-Following Breakout**: Trade breakouts from consolidation patterns (coils).
-   **Precision Scanners**: Filter stocks based on custom trend, coil, and volume rules.
-   **Risk-Defined Sizing**: Automatically calculates position sizes based on a 1% portfolio risk model.
-   **Cost Modeling**: Real-world backtesting including slippage and transaction costs.
-   **Walk-Forward Validation**: Built-in robustness testing across years of market data.
-   **Discord Integration**: Auto-posts portfolio + separate long/short signals to Discord.

---

## 🏛 System Architecture

The system is modular and designed for easy extension:

1.  **`screener.py`**: Daily live execution tool.
2.  **`backtest.py`**: Strategy research and verification.
3.  **`strategies/long_breakout.py`**: Long-only breakout logic.
4.  **`strategies/short_breakout.py`**: Short-side breakdown logic.
5.  **`config/settings.py`**: User-defined risk and system parameters.
6.  **`tests/`**: 107 unit tests (80%+ coverage).

👉 See the full [Architecture Documentation](docs/architecture.md) for more details.

---

## 🛠 Quick Start
### 0. **Activate virtual environment**
```bash
source .venv/bin/activate
```

### 1. **Install**
```bash
pip install -r requirements.txt
```

### 2. **Configure Discord (Optional)**
Create a `.env` file in the root directory to receive trade alerts.  
*See `.env.example` for the template:*

```bash
# General Portfolio execution results
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."

# Strategy-specific signal alerts
DISCORD_LONG_WEBHOOK_URL="https://discord.com/api/webhooks/..."
DISCORD_SHORT_WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

### 3. **Run Screener**

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

## 🚀 Deployment (Fly.io)

This repository is ready for deployment to [Fly.io](https://fly.io/) as a scheduled task.

### 1. **Prerequisites**
- [Install flyctl](https://fly.io/docs/hands-on/install-flyctl/)
- Log in: `fly auth login`

### 2. **Initial Setup**
Initialize the app (choose a unique name) but prevent it from deploying a default 24/7 machine:
```bash
fly launch --no-deploy
```
*Note: If prompted to overwrite `fly.toml`, choose **No**.*

### 3. **Set Secrets**
Configure your Discord webhooks as secure environment variables:
```bash
fly secrets set \
  DISCORD_WEBHOOK_URL="your_url" \
  DISCORD_LONG_WEBHOOK_URL="your_long_url" \
  DISCORD_SHORT_WEBHOOK_URL="your_short_url"
```

### 4. **Run Screener (Manual Trigger)**
The system is configured to run immediately whenever the Fly.io deployment is restarted.

1. **Deploy the app:**
   ```bash
   fly deploy
   ```

2. **Re-trigger the screener:**
   Whenever you want to run the scan (e.g., after market close), simply restart the app via the Fly.io dashboard or CLI:
   ```bash
   fly apps restart swing-trading-system
   ```
   The `scheduler.py` will run both LONG and SHORT strategies once and then enter standby mode.

### 5. **Persistence**
The system uses a Fly Volume named `swing_data` mounted at `/app/data`. This ensures your `portfolio.json` file is **preserved** even when the app is restarted or redeployed.

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
2.  **Manual Verification**: Verify market conditions before trading (regime filter is disabled).
3.  **Risk Management**: Always respect the 1% risk per trade.

---

## ⚠️ Paper Trading Only

**This system is for paper trading and backtesting ONLY.**
- Use for research, strategy validation, and educational purposes
- For live trading with real money, a reliable data API (Dhan API, Angel One API) is required
- Yahoo Finance data can be delayed/unreliable

---

## ⚖️ Disclaimer

*Trading in the stock market involves significant risk. This software is for educational and research purposes only. Always consult with a certified financial advisor before making any investment decisions.*
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

---

## [1.6] - 2026-04-20 (Test Coverage)

### Added
- **Test Coverage**: data/cache.py now at 100% coverage
- 5 new tests added for cache edge cases (corrupt cache, download exceptions, empty data, duplicate columns, MultiIndex)

### Changed
- **Test Coverage**: 84% overall (up from 80%)

---

## [1.5] - 2026-04-20

### Added
- **max_drawdown tracking**: Backtest now calculates peak equity and max drawdown on each trade close
- **Discord error logging**: Shows specific error (HTTP code or exception)

### Changed
- **.env fix**: Removed extra quotes around webhook URL values
- **Backtest Results**: REWARD_RATIO=2.0, Long: 666 trades, 29.3% WR, +584.47%, Max DD 7.69%

---

## [Unreleased] (placeholder)

### Added
- **Ticker Aliases**: Added mapping for stocks with symbol changes (IIFLSEC→IIFLCAPS, CANFIN→CANFINHOME, REPCO→REPCOHOME, VIJAYAETL→VIJAYA)
- **DEAD_TICKERS**: Added KENNAMET.NS, WELSPUNIND.NS, TATAMOTORS.NS to handle delisted/demerged stocks

### Changed
- **Regime Filter**: DISABLED for both long and short strategies (manual verification required)
- **Test Coverage**: 80% overall

---

## [1.4] - 2026-04-19 (Fully Rebuilt)

### Added
- **Portfolio Features**: 
  - `cleanup_portfolio()` - removes stale PENDING/CLOSED trades
  - `entry_trigger_date` tracking
  - `r_multiple` calculation
  - Auto-cleanup: PENDING expires after 5 days, CLOSED cleaned after 15 days, stale ACTIVE after 30 days
- **Discord Integration**: 
  - `post_to_discord()` - webhook posting
  - `format_portfolio_for_discord()` - portfolio formatting
  - Auto-posts portfolio summary on each run
- **Backtest Versioning**: Results saved to `reports/backtest/history.json`

### Changed
- **Regime Filter Removed**: From all strategies (screener & backtest, long & short)
- **Scoring**: Now uses config values (SCORE_WEIGHT_RISK/RANGE/TREND)
- **Ticker Mapping**: Added `_map_ticker()` function in data fetching
- **DEAD_TICKERS**: Skip in scan loop

### Performance
- Long: 666 trades, 29.1% WR, +568.51%
- Short: 468 trades, 20.7% WR, +30.61%

---

## [1.3] - 2026-04-16

### Added
- **Portfolio Display**: LONG/SHORT indicator, entry_trigger_date, days since trigger
- **Portfolio Sorting**: ACTIVE first, then PENDING, then CLOSED
- **Portfolio Summary**: Active/Pending/Closed counts, Win Rate, Avg R, Total R
- **Discord Integration**: Full portfolio posted to webhook
- **Backtest History**: Short strategy results saved

### Changed
- **Scoring Display**: Shows correct 30/30/40 weights
- **Stale Cleanup**: Active trades without trigger date removed after 30 days
- **Config**: PENDING_EXPIRY_DAYS, CLOSED_CLEANUP_DAYS, MAX_ACTIVE_DAYS moved to settings.py
- **Score Weights**: 30/30/40 moved to settings.py
- **Ticker**: Removed duplicate ANUPAM.NS

---

## [1.2] - 2026-04-15

### Added
- **Relaxed Parameters**: For increased candidate output
  - VOLUME_MIN_RATIO: 1.0 (was 1.2)
  - MIN_AVG_TURNOVER: ₹5 Cr (was ₹10 Cr)
  - COIL_CANDLES: 10 (was 12)
  - MAX_RANGE_PCT: 10% (was 8%)
  - NEAR_HIGH_PCT: 8% (was 5%)
  - MAX_RISK_PCT: 15% (was 10%)
- **DEAD_TICKERS**: Skip delisted stocks
- **Cache Age Validation**: Auto-refresh if >1 day old
- **TICKER_ALIASES**: Mapping for symbol changes

---

## [1.1] - Earlier Versions

### Added
- **Short Strategy**: Breakdown logic for short positions
- **Cost Modeling**: Slippage and transaction costs
- **Walk-Forward Validation**: In-sample vs out-of-sample testing
- **Trade Export**: CSV export for trades

### Changed
- **Coil Parameters**: Tuned for Indian market
- **Volume Filters**: Adjusted for liquidity
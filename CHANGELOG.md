# Changelog

All notable changes to this project will be documented in this file.

## [1.17] - 2026-05-07

### Added
- **IST Timezone Support**: Integrated `pytz` and added `TIMEZONE` setting (default: "Asia/Kolkata") to ensure all system outputs (Discord alerts, backtest summaries, console logs) are correctly localized to India Standard Time.

### Fixed
- **Timezone Inconsistency**: Resolved observed UTC-based time display in Discord alerts and console reports by using timezone-aware datetime objects.
- **Naive/Aware Datetime Comparisons**: Fixed potential crashes in `screener.py` by ensuring all stored and current dates are consistently timezone-aware (IST) before comparison.

## [1.16] - 2026-05-07

### Fixed
- **Discord Formatting Fix**: Implemented code-block aware chunking in `post_to_discord`. Large messages are now split such that ` ```yaml ` blocks are properly closed before a split and re-opened in the next chunk.
- **Improved Chunking Stability**: Added unit test `test_post_to_discord_chunking` to verify formatting preservation across message boundaries.

## [1.15] - 2026-04-27

### Added
- **Unified Discord Portfolio Updates**: `screener.py` now posts portfolio summaries to Discord for both Long and Short strategies after execution.
- **Improved Signal Formatting**: Discord signals now use a 3-line format for better readability and mobile visibility.
- **Portfolio Tracker Fixes**: `update_portfolio()` now accepts a strategy argument to prevent cross-strategy data contamination.

### Added (2026-04-23)
- **Discord Integration (TASK-001)**:
  - Webhook routing based on `--strategy` argument (`DISCORD_LONG_WEBHOOK_URL`, `DISCORD_SHORT_WEBHOOK_URL`).
  - `send_backtest_to_discord` utility for summarized performance stats.

### Added (2026-04-22)
- **Candle Strength Filter**: TESTED AND DISABLED (hurt performance)
  - MIN_CANDLE_STRENGTH = 0 initially, now set to 0 (disabled)
  - For longs: strength = (close - low) / (high - low)
  - For shorts: strength = (high - close) / (high - low)
  - Added check_candle_strength() in strategies

### DISABLED (2026-04-22)
- **Candle Strength Filter DISABLED**: After testing, filter hurt performance
  - LONGS: 598 trades → 440 trades (-26%), WR 30.6% → 25.0%, P&L +653% → +169% (-74% drop)
  - Filter too restrictive - rejected too many valid setups
  - Reverted to v1.12 logic (candle filter disabled)
  - MIN_CANDLE_STRENGTH set to 0 in config/settings.py
  - Commented out candle filter calls in backtest.py and screener.py

### Changed (2026-04-22)
- **Portfolio Score**: Track setup score at entry time
  - Added `score` field to PortfolioTrade TypedDict
  - `add_to_portfolio()` accepts score parameter
  - Score displayed in Discord trade row as `S:XX`
  - Score displayed in screener tracker as new column
- **backtest.py --no-refresh flag**: Toggle to use cached data
  - Default: refresh=True (always download fresh data)
  - --no-refresh: Use cached data only for faster re-runs
- **Short score display fix**: Changed hardcoded weights (40/35/25) to config values (30/30/40)
- **Short Score Display Fix**: Changed hardcoded weights (40/35/25) to config values (30/30/40)
  - Fixed in screener.py:1247, 1249, 1260
  - Previously LONG was fixed in v1.8, SHORT was missed

### Changed (2026-04-22)
- **Relative Strength (RS) Filter**: Filters stocks based on relative performance vs benchmark
  - RS = Stock Return - Nifty Return over lookback period
  - For longs: Only trade stocks with positive RS (outperforming)
  - For shorts: Only trade stocks with negative RS (underperforming)
  - Added config parameters: USE_RS_FILTER, RS_LOOKBACK, RS_THRESHOLD, RS_AS_OR
  - Implemented in both long_breakout.py and short_breakout.py

### Tested (Not Adopted - EMA combinations with RS)
- EMA50>EMA200 + RS: 598 trades, 30.6% WR, +653% P&L, 6.29% Max DD (BEST)

### Tested (Adopted)
- **RS Filter (ADOPTED v1.11)**: 
  - Baseline (no RS): 658 trades, 28.9% WR, +552% P&L, 7.69% Max DD
  - RS > 0 (AND): 598 trades, 30.6% WR, +653% P&L, 6.29% Max DD ← CURRENT BASELINE

### Tested EMA + RS Combinations (Not Adopted)
- **EMA50>EMA200 + RS** (baseline): 598 trades, 30.6% WR, +653% P&L, 6.29% Max DD ← BEST
- **EMA50-only + RS**: 628 trades, 27.9% WR, +428% P&L, 7.67% Max DD
- **EMA100>EMA200 + RS**: 620 trades, 28.7% WR, +475% P&L, 8.37% Max DD
- **EMA50>EMA150 + RS**: 628 trades, 27.9% WR, +428% P&L, 7.67% Max DD

**Conclusion: EMA50>EMA200 + RS remains the optimal configuration**

---

## [1.10] - 2026-04-22
  - EMA20 (baseline): 667 trades, 29.2% WR, +576% P&L, 7.69% Max DD
  - EMA15: 743 trades, 26.8% WR, +652% P&L, 14.48% Max DD
  - Conclusion: EMA15 has higher returns but 2x drawdown risk. Reverted to EMA20.

- **REWARD_RATIO (target) comparison**:
  - RR 1.5: 792 trades, 38.0% WR, +540% P&L
  - RR 2.0 (baseline): 667 trades, 29.2% WR, +576% P&L, 7.69% Max DD
  - RR 2.5: 618 trades, 20.7% WR, +374% P&L
  - Conclusion: RR 2.0 is the sweet spot - best balance of win rate and returns.

- **ATR trailing exit comparison**:
  - ATR 1.5×: 921 trades, 16.8% WR, +659% P&L, 10.58% Max DD
  - ATR 2.0×: 688 trades, 26.7% WR, +519% P&L, 16.02% Max DD
  - ATR 2.5×: 524 trades, 35.1% WR, +502% P&L, 12.52% Max DD
  - ATR 3.0×: 469 trades, 40.3% WR, +542% P&L, 10.00% Max DD
  - Conclusion: ATR does not outperform EMA20. EMA20 has lowest drawdown and best risk-adjusted returns.

- **EMA Stage 1 trend filter comparison** (2026-04-22):
  - EMA50 > EMA200 (baseline): 658 trades, 28.9% WR, +552% P&L, 7.69% Max DD
  - EMA50 only (skip EMA200): 674 trades, 29.7% WR, +701% P&L, 9.48% Max DD
  - EMA100 > EMA200: 691 trades, 29.4% WR, +643% P&L, 9.82% Max DD
  - EMA50 > EMA150: 658 trades, 28.7% WR, +545% P&L, 8.77% Max DD
  - Conclusion: EMA50>EMA200 remains optimal - lowest drawdown with similar risk-adjusted returns

- **Relative Strength (RS) Filter** (2026-04-22):
  - RS > 0 (AND mode): 596 trades, 30.7% WR, +648% P&L, 6.29% Max DD
  - RS > 3%: 506 trades, 28.7% WR, +325% P&L, 6.00% Max DD
  - RS > 5%: 459 trades, 25.9% WR, +192% P&L, 7.43% Max DD
  - RS AS OR: 703 trades, 29.2% WR, +642% P&L, 10.77% Max DD
  - Conclusion: RS > 0 (AND mode) best - higher WR (30.7% vs 28.9%), lower drawdown (6.29% vs 7.69%)

### Added
- **ATR trailing config**: Added `USE_ATR_TRAILING`, `ATR_PERIOD`, `TRAILING_ATR_MULTIPLIER` in config/settings.py
- **ATR indicator**: Added `calculate_atr()` function in strategies/long_breakout.py

### Fixed
- **Discord direction bug**: Short trades were showing as LONG in Discord messages
- **Score weights hardcoded bug**: Score calculations used hardcoded weights (40/35/25) instead of config values (30/30/40)
- **Discord trade row format**: Improved readability - now 3 lines instead of 1 congested line
  - Shows "Trigger:" for ACTIVE, "Added:" for PENDING, "Exit:" for CLOSED
  - Uses "--" instead of "-" for empty values
- **Market regime display**: Changed "❓ unknown" to "⚪ REGIME OFF" when regime is disabled

---

## [1.7] - 2026-04-21 (Discord Fix)

### Fixed
- **Duplicate signal bug**: ANURAS.NS showed twice in screener output (once as ACTIVE portfolio, once as new signal)
- **Portfolio ticker skip**: Now skips PENDING/ACTIVE tickers during scan (allows CLOSED for re-entry)
- **Discord separate webhooks**: Added separate long/short signal webhooks in .env

### Added
- **Dates to Discord**: Added added_date, trigger_date, days_held to portfolio formatting
- **send_signals_to_discord()**: Separate function for long/short signal posting

### Tested
- All 3 Discord webhooks verified working (Portfolio, Long Signals, Short Signals return 204)
- Screener verified: ANURAS.NS no longer shows as duplicate signal

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
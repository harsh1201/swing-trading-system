# AGENTS.md - Swing Trading System Context

> **Last Updated:** 2026-04-20  
> **Version:** 1.5 (max_drawdown + Discord fix)  
> **Maintainer:** Project Owner

---

## Project Overview

A rule-based, statistically validated swing trading framework for the Indian stock market (NSE). Uses consolidation breakouts, trend filters, and volume analysis to identify trade setups.

### Strategy Philosophy
- **Low win rate (~25%)**, high Risk:Reward (1:2)
- Trend-following breakout model
- Market regime filter DISABLED (manual verification of market conditions required)
- 1% risk per trade, max 5 concurrent trades

---

## Current Configuration (2026-04-20)

### Relaxed Parameters (tested)
| Parameter | Value | Previous | Notes |
|-----------|-------|----------|-------|
| `VOLUME_MIN_RATIO` | 1.0 | 1.2 | No volume surge required |
| `MIN_AVG_TURNOVER` | ₹5 Cr | ₹10 Cr | Lowered liquidity threshold |
| `COIL_CANDLES` | **10** | 12 | Tested: 10 candles = +568% vs 12 candles = +365% |
| `MAX_RANGE_PCT` | 8% | 10% | Tighter consolidation |
| `NEAR_HIGH_PCT` | 5% | 8% | Near breakout level |
| `MAX_RISK_PCT` | 15% | 10% | Allow wider stop losses |

### Core Strategy Parameters
| Parameter | Value | Description |
|-----------|-------|-------------|
| `EMA_SHORT` | 50 | Medium-term trend |
| `EMA_LONG` | 200 | Long-term trend |
| `REWARD_RATIO` | 2.0 | 1:2 Risk:Reward |
| `GAP_UP_THRESHOLD` | 1.02 | Skip if gap-up > 2% |

### Scoring Weight (2026-04-16)
| Component | Weight | Description |
|-----------|--------|-------------|
| Risk | 30 pts | Tighter coil = lower risk = higher score |
| Range | 30 pts | Tighter consolidation = higher score |
| Trend | 40 pts | Sweet spot 1-4% above EMA50 = max score |

### Position Sizing
| Parameter | Value | Description |
|-----------|-------|-------------|
| `RISK_PER_TRADE` | 1.0% | Capital at risk per trade |
| `MAX_CONCURRENT_TRADES` | 5 | Max open positions |
| `MAX_POSITION_PCT` | 25% | Max position size |
| `MAX_TRADES_PER_SECTOR` | 2 | Sector diversification |

### Portfolio Cleanup
| Parameter | Value | Description |
|-----------|-------|-------------|
| `PENDING_EXPIRY_DAYS` | 5 | Auto-remove PENDING setups after 5 days |
| `CLOSED_CLEANUP_DAYS` | 15 | Auto-remove CLOSED trades after 15 days |
| `MAX_ACTIVE_DAYS` | 30 | Remove stale ACTIVE trades (no trigger date) after 30 days |

---

## Known Issues & Limitations

### Data Layer
- **yfinance reliability**: Yahoo Finance data can be delayed or fail
  - **Recommendation**: Use for backtesting only. For live trading, consider Dhan API or Angel One API.
- **Ticker symbol changes**: Many stocks changed symbols (verified via NSE/BSE)
  - **Mitigation**: `TICKER_ALIASES` in `config/settings.py` maps old → new symbols
- **Cache staleness**: Old data may persist
  - **Mitigation**: Auto-refresh if cache > 1 day old
- **Intraday data not available**: yfinance provides EOD (end-of-day) data only
  - **Impact**: Cannot detect exact moment when SL/Target was hit
  - **Impact**: Cannot model intraday price movements
- **Split-adjusted data mismatch**: yfinance may return adjusted closes but raw highs/lows
  - **Impact**: R-multiple calculations may be slightly inaccurate
  - **Mitigation**: Use for direction/trend only, not precise R calculations

### Portfolio/Live Trading Limitations
- **Daily execution required**: Screener must be run each trading day to update ACTIVE positions
  - **Impact**: If SL/Target hit while away, trade stays ACTIVE until next run
  - **Impact**: R-multiple may be inaccurate if price moved after actual hit
  - **Mitigation**: Run screener daily during market hours
- **Earnings not tracked for ACTIVE trades**: Setup screening skips earnings, but ACTIVE positions are not auto-closed before earnings
  - **Impact**: Position may take unexpected loss post-earnings
  - **Mitigation**: Manual review before earnings season
- **Corporate actions not detected**: Splits, bonuses, rights issues not handled
  - **Impact**: Entry/SL/Target become meaningless after corporate action
  - **Mitigation**: Monitor for corporate announcements, manually adjust
- **Same ticker LONG + SHORT**: Both strategies can hold same ticker simultaneously
  - **Impact**: Risk management treats them as separate positions
  - **Impact**: Commission wasted if both closed
  - **Mitigation**: Manual review before adding opposing positions

### Strategy Limitations
- **Volume filter too loose**: `VOLUME_MIN_RATIO = 1.0` means no volume surge required
- **No time-based exit**: Only SL/Target/breakeven triggers
- **Market regime filter**: DISABLED for both long and short strategies (manual verification of market conditions required)
- **Gap opens beyond SL/Target**: Weekend/overnight gaps may open below SL or above Target
  - **Impact**: Actual exit price differs from SL/Target, affecting R-accuracy
  - **Impact**: May see larger loss than risk% suggests

### System Design Assumptions
- **Full fills assumed**: No modeling of partial fills
- **After-hours not modeled**: Assume EOD closes determine trade outcomes
- **No position scaling**: Fixed position sizing, no pyramid/tranche entry

---

## Verified Ticker Mappings (NSE/BSE)

All aliases verified via web search (NSE website, TradingView, Yahoo Finance):

| Old Symbol | New Symbol | Company | Verified |
|------------|------------|---------|----------|
| TEJAS.NS | TEJASNET.NS | Tejas Networks | ✅ |
| MCDOWELL-N.NS | UNITDSPR.NS | United Spirits | ✅ |
| STRIDES.NS | STAR.NS | Strides Pharma | ✅ |
| DIXONTECH.NS | DIXON.NS | Dixon Technologies | ✅ |
| TCIEXPRES.NS | TCIEXP.NS | TCI Express | ✅ |
| GOKALDAS.NS | GOKEX.NS | Gokaldas Exports | ✅ |
| KAVERI.NS | KSCL.NS | Kaveri Seeds | ✅ |
| KAJARIA.NS | KAJARIACER.NS | Kajaria Ceramics | ✅ |
| PRAJ.NS | PRAJIND.NS | Praj Industries | ✅ |
| JKBANK.NS | J&KBANK.NS | J&K Bank | ✅ |
| GMRINFRA-EQ.NS | GMRINFRA.NS | GMR Infra | ✅ |
| MACROTECH.NS | LODHA.NS | Macrotech → Lodha | ✅ |
| LTIM.NS | LTM.NS | LTIMindtree → LTM | ✅ |

**Removed/DEAD tickers**: CANFIN.NS, KAJARIA.NS, PRAJ.NS, MACROTECH.NS, LTIM.NS, ANUPAM.NS, MCDOWELL-N.NS (yfinance fails for these - in DEAD_TICKERS)
**Added**: PRAJIND.NS, LODHA.NS, LTM.NS

## Additional Ticker Aliases (2026-04-16 Verification)

| Old Symbol | New Symbol | Company | Status |
|-----------|------------|---------|--------|
| IIFLSEC.NS | IIFLSEC.NS | IIFL Capital (name change Nov 2024) | ✅ Active |
| REPCO.NS | REPCOHOME.NS | Repco Home Finance | ✅ Active (wrong ticker) |
| ERISLIFE.NS | ERIS.NS | Eris Lifesciences | ✅ Active (wrong ticker) |
| WOCKHARDT.NS | WOCKPHARMA.NS | Wockhardt | ✅ Active (symbol change) |
| UNICHEM.NS | UNICHEMLAB.NS | Unichem Laboratories | ✅ Active (wrong ticker) |
| HESTER.NS | HESTERBIO.NS | Hester Biosciences | ✅ Active (wrong ticker) |
| JUBLILFOOD.NS | JUBLFOOD.NS | Jubilant FoodWorks | ✅ Active (wrong ticker) |
| HERITAGE.NS | HERITGFOOD.NS | Heritage Foods | ✅ Active (wrong ticker) |
| SOMANYCER.NS | SOMANYCERA.NS | Somany Ceramics | ✅ Active (wrong ticker) |
| TRIVENITRB.NS | TRITURBINE.NS | Triveni Turbine | ✅ Active (wrong ticker) |
| HAPPYFORG.NS | HAPPYFORGE.NS | Happy Forgings | ✅ Active (wrong ticker) |
| FINOLEXPIPE.NS | FINPIPE.NS | Finolex Industries | ✅ Active (wrong ticker) |
| ANUPAM.NS | ANURAS.NS | Anupam Rasayan | ✅ Active (wrong ticker) |
| GFL.NS | GFLLIMITED.NS | GFL (formerly Gujarat Fluorochemicals) | ✅ Active (wrong ticker) |
| GDL.NS | GDLLEAS.NS | GDL Leasing & Finance | ✅ Active (wrong ticker) |
| AEGIS.NS | AEGISLOG.NS | Aegis Logistics | ✅ Active (wrong ticker) |
| VEDANT.NS | MANYAVAR.NS | Vedant Fashions | ✅ Active (wrong ticker) |
| VARDHMAN.NS | VTL.NS | Vardhman Textiles | ✅ Active (wrong ticker) |
| WELSPUNIND.NS | - | Welspun India | ⚠️ Added to DEAD_TICKERS (yfinance fails) |
| CPCL.NS | CHENNPETRO.NS | Chennai Petroleum | ✅ Active (wrong ticker) |
| JUBILANT.NS | JUBLINGREA.NS | Jubilant Ingrevia | ✅ Active (wrong ticker) |
| GMRINFRA.NS | GMRINFRA.NS | GMR Airports (renamed) | ✅ Active |
| IIFLSEC.NS | IIFLCAPS.NS | IIFL Capital Services | ⚠️ Name change Nov 2024 |
| CANFIN.NS | CANFINHOME.NS | Can Fin Homes | ⚠️ Added alias |
| REPCO.NS | REPCOHOME.NS | Repco Home Finance | ⚠️ Added alias |
| VIJAYAETL.NS | VIJAYA.NS | Vijaya Diagnostic | ⚠️ Added alias |

## Delisted/Merged Tickers (Add to DEAD_TICKERS)

| Symbol | Reason | Date |
|--------|--------|-------|
| GATI.NS | Merged with ALLCARGO - Delisted Nov 2025 | Nov 2025 |
| VIJAYAWADAETL.NS | Vijayawada Bottling - Not listed on NSE | N/A |
| KENNAMET.NS | No data since Feb 2025 | N/A |
| WELSPUNIND.NS | yfinance fails | N/A |
| TATAMOTORS.NS | Demerged into TMPV + TMCV | Oct 2025 |
| ANUPAM.NS | Symbol changed to ANURAS.NS | N/A |
| MCDOWELL-N.NS | Symbol changed to UNITDSPR.NS | N/A |

## Ticker Changes Requiring Alias Updates

| Old Symbol | New Symbol | Company | Date |
|-----------|------------|---------|-------|
| BARBEQUE.NS | UFBL.NS | Barbeque Nation → United Foodbrands | Oct 2025 |
| ADANITRANS.NS | ADANIENSOL.NS | Adani Transmission → Adani Energy Solutions | 2023 |
| TATAMOTORS.NS | TMPV.NS / TMCV.NS | Demerger Oct 2025 | Oct 2025 |

**Note**: TATAMOTORS demerger - TMPV (PV/EV/JLR) listed Oct 2025, TMCV (CV) listed Nov 2025. For backtesting use historical data. For live trading, decide based on thesis.

---

## File Structure

```
swing-trading-system/
├── screener.py          # Live screening - scan universe for setups
├── backtest.py          # Historical validation with concurrent positions
├── config/
│   ├── settings.py      # All tunable parameters
│   └── stocks.py        # Stock universe (~654 stocks)
├── strategies/
│   ├── long_breakout.py # Long setup logic (source of truth)
│   └── short_breakout.py# Short setup logic
├── data/
│   ├── cache.py         # CSV cache with auto-refresh
│   └── earnings.py      # Earnings date lookup
└── tests/               # Unit tests (74% coverage target: 100%)
```

---

## Running the System

### Screener (Live)
```bash
python screener.py --strategy long_breakout   # Long setups
python screener.py --strategy short_breakout  # Short setups
```

### Backtest
```bash
python backtest.py --strategy long_breakout
python backtest.py --strategy long_breakout --export  # Export to CSV
```

### Backtest Versioning
```bash
python reports/backtest/version.py          # View history
python reports/backtest/version.py --compare # Compare last 2 runs
```

### Discord Integration
Portfolio summary auto-posts to Discord when screener runs.
- Webhook URLs configured in `config/settings.py`
- Posts full portfolio with all trades (Active, Pending, Closed)
- Shows Entry, SL, Target, Current Price, R-multiple

---

## Important Notes for AI Agents

1. **DO NOT change `DEAD_TICKERS`** without verifying ticker status
2. **Cache auto-refreshes** daily - no manual refresh needed for live screening
3. **Strategy logic is centralized** in `strategies/long_breakout.py` - don't duplicate
4. **Test coverage target**: 100% for strategies, 90%+ for CLI scripts
5. **Data source**: yfinance (free, but unreliable). For real money, use paid API.

---

## Changelog

### 2026-04-20 (v1.5 - max_drawdown + Discord fix)
- Added max_drawdown tracking in backtest (both long & short strategies)
- Now calculates peak equity and max drawdown on each trade close
- Added Discord error logging: shows specific error (HTTP code or exception)
- Fixed .env file: removed extra quotes around webhook URL values
- Updated test suite: 98 passing, 1 skipped
- Long backtest results: 666 trades, 29.3% WR, +584.47%, Max DD 7.69%
- Short backtest results: 467 trades, 20.8% WR, +30.99%, Max DD 26.84%

### 2026-04-19 (v1.4 - Fully Rebuilt)
- Complete system rebuild after staging loss
- Regime filter removed from all strategies (long & short, screener & backtest)
- Ticker alias mapping added (_map_ticker function in fetch_data)
- DEAD_TICKERS skip in scan loop (both long & short strategies)
- Scoring weights now use config values (SCORE_WEIGHT_RISK/RANGE/TREND)
- Backtest versioning integrated (auto-saves to history.json)
- Portfolio features rebuilt: cleanup_portfolio, r_multiple, entry_trigger_date
- Discord integration: post_toDiscord, format_portfolio_for_discord
- Test suite: 26 portfolio/Discord tests added (total ~40 passing)
- Long backtest results: 666 trades, 29.1% WR, +568.51% (RANGE=8.0%, RR=2.0)

### 2026-04-16 (v1.3)
- Portfolio display enhanced with LONG/SHORT indicator, entry_trigger_date, and days since trigger
- Portfolio sorting: ACTIVE first, then PENDING, then CLOSED
- Portfolio summary header: Shows Active/Pending/Closed counts, Win Rate, Avg R, Total R
- Discord integration: Full portfolio posted to webhook with all trades
- Scoring display fixed: Now shows correct 30/30/40 instead of 40/35/25
- Stale ACTIVE cleanup: Old trades without trigger date removed after 30 days
- Config moved: PENDING_EXPIRY_DAYS, CLOSED_CLEANUP_DAYS, MAX_ACTIVE_DAYS to config/settings.py
- Score weights (30/30/40) moved to config/settings.py
- Removed duplicate ticker ANUPAM.NS (same as ANURAS.NS)
- Backtest history now saves short strategy results
- Added 4 new tests for Discord integration (147 total passing)

### 2026-04-15
- Config relaxed for increased candidate output
- Added `DEAD_TICKERS` to skip delisted stocks
- Added cache age validation (auto-refresh if >1 day old)
- Marked `DataCache` class as deprecated

---

## TODO

- [x] Implement test cases for strategy logic (106 tests passing)
- [x] Fix ticker symbol changes (TICKER_ALIASES added)
- [x] Add cache age validation (auto-refresh if >1 day old)
- [x] Verify ticker mappings via NSE/BSE (all verified)
- [x] Verify additional ticker aliases via web search (all verified 2026-04-16)
- [x] Add missing ticker aliases (BARBEQUE→UFBL, ADANITRANS→ADANIENSOL)
- [x] Add GATI.NS and VIJAYAWADAETL.NS to DEAD_TICKERS
- [x] Add critical cache tests (4 added for NaN handling)
- [x] Remove market regime filter for all strategies (both backtest and screener)
- [x] Test minimum volume filter (MIN_AVG_VOLUME) - tested and reverted (redundant with MIN_AVG_TURNOVER)
- [x] Handle TATAMOTORS demerger (use TMPV/TMCV for live)
- [x] Portfolio cleanup (PENDING 5 days, CLOSED 15 days, ACTIVE stale 30 days)
- [x] Portfolio tracking (entry_trigger_date, r_multiple)
- [x] Comprehensive limitations documented
- [ ] Consider moving to Dhan API for live trading
- [ ] Auto-close ACTIVE positions before earnings announcements
- [ ] Detect and handle corporate actions (splits, bonuses)

## Test Suite Status (2026-04-20)

**103 tests passing** across all modules:
- `test_backtest.py`: 9 tests ✓
- `test_data_cache.py`: 12 tests ✓ (100% coverage)
- `test_data_earnings.py`: 4 tests ✓
- `test_long_breakout.py`: 23 tests ✓
- `test_screener.py`: 40 tests ✓
- `test_short_breakout.py`: 15 tests ✓

**Overall coverage: 80%**
- strategies/long_breakout.py: 100%
- strategies/short_breakout.py: 100%
- backtest.py: 81%
- screener.py: 73%
- data/cache.py: ~95%
- data/earnings.py: ~100%

**Note:** Screener at 73% - remaining gaps are mostly print functions requiring full integration tests

## Strategy Rating (2026-04-20)

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Strategy Logic** | 7.5/10 | Solid breakout concept with proper risk management |
| **Risk Management** | 8/10 | 1% per trade, proper SL/TP, trailing stop |
| **Code Quality** | 8/10 | Clean, modular, well-tested (90 tests, 80% coverage) |
| **Test Coverage** | 8/10 | 90 tests passing, 80% coverage |
| **Data Reliability** | 5/10 | yfinance is the weak link - use Dhan API for live |
| **Backtest Results** | 7.5/10 | +568% long, +31% short (regime disabled) |
| **Out-of-Sample** | 7/10 | ~25% win rate (regime filter removed) |

**Overall: 7.5/10** - Ready for paper trading. Switch to Dhan API for real money.

### Key Metrics (Current Config)
- Total Trades: ~700 (long)
- Win Rate: 28.6%
- Realized RR: 1:1.90
- Net P&L: +720.92%
- Avg Hold: 10.4 bars
- Out-of-Sample Win Rate: 25.5%

# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **Backtesting Engine (`backtest.py`)**: Added an `--export` flag to allow exporting all completed trades to a CSV file (`trades_long.csv` and `trades_short.csv`) for further analysis or charting platform import.
- **Trade Output Log (`backtest.py`)**: Added `exit_date` field tracking to correctly log the exit date for all completed trades (target hit, stop loss hit, breakeven, and trailing exits) along with the existing signal date (entry date). Both dates are now printed in the standard Trade Log and exported to the CSV files.

### Changed
- **Unit Tests (`tests/unit/test_backtest.py`)**: Updated the parameter signature for `_close` and `_close_short` mock tests to include the new `exit_date` string. Updated the dummy `ts` (trades) array to include an `exit_date` to correctly test the logging functionality.
- **Backtesting Engine (`backtest.py`)**: Implemented an entry-bar guard to suppress Breakeven (BE) and Trailing Stop (TRL) triggers on the exact day of entry. This prevents "same-bar traps" where initial volatile price movement immediately exits a trade before it has time to develop, while keeping basic Stop Loss and Target triggers active.

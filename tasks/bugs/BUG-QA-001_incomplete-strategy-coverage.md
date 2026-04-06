# BUG-QA-001: Incomplete Strategy Coverage

## Description
Current test suite covers 91% of strategy logic in `strategies/long_breakout.py` and `strategies/short_breakout.py`. ADR-TEST-001 requires 100% coverage for strategy and calculation logic.

## Failing Files
- `strategies/long_breakout.py`: 91%
- `strategies/short_breakout.py`: 91%

## Missing Lines
- `long_breakout.py`: 135, 144, 167, 168, 252, 255, 305, 331, 440, 446, 452, 455, 460, 468
- `short_breakout.py`: 127, 130, 146, 147, 148, 149, 150, 152, 165, 166

## Reproduction
Run `pytest --cov=. tests/unit/test_long_breakout.py tests/unit/test_short_breakout.py`

## Recommendation
Add unit tests for missing branches in `strategies/` to achieve 100% coverage.

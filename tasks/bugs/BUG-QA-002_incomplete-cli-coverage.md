# BUG-QA-002: Incomplete CLI Script Coverage

## Description
Current test suite covers 84% and 73% of CLI script logic in `backtest.py` and `screener.py` respectively, which is below the 90%+ requirement in ADR-TEST-001.

## Failing Files
- `backtest.py`: 84%
- `screener.py`: 73%

## Missing Lines
- `backtest.py`: 115 lines (multiple blocks in main loop and logic)
- `screener.py`: 163 lines (bulk of execution logic and display functions)

## Reproduction
Run `pytest --cov=. tests/unit/test_backtest.py tests/unit/test_screener.py`

## Recommendation
Implement additional unit and integration tests to cover the main execution functions and error handling logic in CLI scripts.

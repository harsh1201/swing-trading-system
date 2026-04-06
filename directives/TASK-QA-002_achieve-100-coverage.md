# TASK-QA-002 Achieve 100% Test Coverage
**Date:** 2026-04-06
**Status:** in-progress

## Goal
Success is defined as 100% line coverage for all strategy, backtesting, screening, and data modules in the repository, with zero regression in existing functionality.

## Inputs
- Existing test suite in `tests/`.
- Coverage reports from `reports/qa/`.
- Project ADR-TEST-001 (Testing Architecture).

## Tools / Scripts to Use
- `pytest`
- `pytest-cov`
- `rm` (for dead code cleanup)

## Expected Output
- 100% Green coverage report.
- Zero passing test failures.
- Cleanup of any `old_*` or dead files identified during audit.

## Acceptance Criteria
- `pytest --cov=.` returns 100% for all tracked files.
- Bug reports `BUG-QA-001` and `BUG-QA-002` are closed.
- `CHANGELOG.md` updated with audit completion.

## Edge Cases
- Handling of `__init__.py` and configuration files (should be 100% by default).
- Ensuring mocks for `yfinance` and `pandas` dataframes cover all conditional branches.

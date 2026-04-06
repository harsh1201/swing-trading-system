# QA Report Card — TASK-QA-001
**Date:** 2026-04-06
**Verdict:** ❌ FAIL

## Coverage Summary
| Metric | Required | Actual | Status |
|--------|----------|--------|--------|
| Line Coverage (Strategies) | 100% | 91% | ❌ FAIL |
| Line Coverage (CLI Scripts) | 90% | 73% - 84% | ❌ FAIL |
| Total Project Coverage | 80%* | 74% | ❌ FAIL |

*\*Project-wide default threshold from QA Agent rules.*

## New Tests Written
- `No new tests written.` (The focus was on baseline assessment.)

## Failing Tests
- **All 46 tests passed.** ✅
- **Issue**: The codebase has significant gaps in test coverage despite all existing tests passing.

## Identified Coverage Gaps
### BUG-QA-001: Incomplete Strategy Coverage
**Severity**: ⚠️ Medium
**Files**: `strategies/long_breakout.py`, `strategies/short_breakout.py`
**Description**: Both strategies are missing unit tests for specific regime checks and breadth calculations.

### BUG-QA-002: Incomplete CLI Coverage
**Severity**: ⚠️ High
**Files**: `backtest.py`, `screener.py`
**Description**: Significant portions of the screening engine and display logic are not exercised by current tests.

## Regression Analysis
- **Baseline**: No previous baseline found. This run will be used as the new baseline in `reports/qa/baseline.json`.

## Recommendation
- **Block Merge**: Coverage is below the thresholds set in `ADR-TEST-001`.
- **Action Required**: Code Generator should add unit tests for missing branches in `strategies/` and integration tests for `screener.py` to cover the main execution flow.

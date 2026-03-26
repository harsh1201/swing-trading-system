# Problem Brief — TASK-TEST-001
**Date:** 2026-03-27
**Status:** draft

## Problem Statement (Original)
"I want to write test cases for this entire repo, and make the coverage to 100%"

## Problem Statement (Simplified)
We need to create a robust, end-to-end test suite for the swing-trading-system to ensure every line of code is verified and the system status is 100% covered.

## What We Know
- The repository was recently refactored (long-breakout) and has no existing `tests/` directory.
- Core logic is in `backtest.py`, `screener.py`, and `strategies/`.
- External dependencies like `yfinance` and `pandas` need careful mocking for deterministic testing.
- The user has established agentic patterns and expects a professional, high-standard test suite.

## What We Don't Know (Assumptions to Validate)
- Preferred testing framework? (Assuming `pytest`)
- CI/CD integration requirements?
- Specific trade scenarios to test (Gap-ups, sideways markets, etc)?

## Edge Cases Identified
- Stock delimiters and NSE suffix (`.NS`) handling.
- Calculation of ATR, EMA on insufficient history.
- Handling of non-trading days/weekends.
- Strategy signal edge cases (Score 0, Score 100).

## Recommended Next Step
→ **Software Architect Agent** to define the test architecture and ADR.

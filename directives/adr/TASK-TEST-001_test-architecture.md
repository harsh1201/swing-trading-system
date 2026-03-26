# ADR-TEST-001 Testing Architecture — TASK-TEST-001
**Date:** 2026-03-27
**Status:** accepted

## Problem Statement
The swing-trading-system requires a robust automated testing infrastructure to achieve 100% code coverage and prevent regressions during ongoing strategy development.

## Decision
We will standardize on `pytest` as the primary testing framework, leveraging its flexible fixtures and extensive plugin ecosystem (`pytest-cov`, `pytest-mock`).

## Rationale
-   **Pytest** is the industry standard for Python development, offering less boilerplate than `unittest`.
-   **Pytest-cov** provides automated coverage reporting compatible with CI workflows.
-   **Pytest-mock** simplifies the mocking of external dependencies (`yfinance`, `pandas`).

## Core Architecture
-   **Directory Structure**:
    -   `tests/unit/`: Testing component logic in isolation (`strategies/`, `backtest.py` functions).
    -   `tests/integration/`: End-to-end flows for backtesting and screening.
    -   `tests/fixtures/`: Central repository for common data mocks.
-   **Mocking Policy**:
    -   `yahooquery` and `yfinance` must be mocked to avoid network calls.
    -   Indicator calculations (`TA-Lib` or manual) will be verified against pre-calculated baselines.
-   **Coverage Policy**:
    -   Target: 100% line coverage for strategy and calculation logic.
    -   Target: 90%+ for CLI scripts (`backtest.py`, `screener.py`).

## Alternatives Considered
-   **`unittest`**: Rejected due to higher boilerplate and less powerful fixture management.
-   **`robotframework`**: Rejected as overly complex for a purely algorithmic codebase.

## Performance Considerations
-   Integration tests should run against narrowed stock universes (1-5 tickers) to maintain fast execution.
-   Tests must be deterministic and run entirely offline.

## Definition of Done
-   Passing test suite with `pytest`.
-   Coverage report showing 100% (or max feasible) coverage.
-   Successful regression against a known historical signal.

# Sprint Plan
**Date:** 2026-04-27
**Target Version:** Next iteration (Live Trading Integration)

## 1. Goal
Transition the system from relyong on Yahoo Finance backend simulation data to live API data to ensure accurate minute-data and reliable entry/stops for real accounts (Dhan / Angel One APIs).

## 2. In Scope
- Determine the scope of API migration.
- Replace `yfinance` in `data.cache.fetch_ohlcv` with live alternatives.
- Research handling of corporate actions automatically.

## 3. Out of Scope
- Intraday strategies. The system remains EOD (End of Day).
- UI/Dashboard (CLI and Discord only).

## 4. Work Areas
1. **API Selection (Architect)**: Review Dhan API and compare authentication requirements.
2. **Implementation (Code Generator/Data Engineer)**: Rewrite data layer. Extend `screener.py` functionality with accurate execution logic based on live bids.
3. **Docs (Documentation Manager)**: Update setup guides with new API key requirements.

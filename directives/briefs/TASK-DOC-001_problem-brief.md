# Problem Brief — TASK-DOC-001
**Date:** 2026-03-26
**Status:** approved

## Problem Statement (Original)
i want to update the readme file, the current version is way too basic, please go through the entire repo and create detailed documentations about this repo

## Problem Statement (Simplified)
The current repository documentation is insufficient for a technical user to understand, install, and operate the swing trading system. We need a comprehensive README and detailed documentation covering architecture, configuration, data flow, and usage.

## What We Know
- The repository is a rule-based swing trading system for NSE India stocks.
- Core components: `screener.py` (live scanning) and `backtest.py` (historical validation).
- Strategy logic is encapsulated in `strategies/breakout.py`.
- Configuration is managed in `config/settings.py` and `config/stocks.py`.
- Data is fetched (likely from Yahoo Finance) and cached in `data/`.
- There is an existing `docs/system_overview.md` which focuses on the trading strategy but lacks technical/operational details.

## Proposed Strategy
- Create a multi-layered documentation system in `docs/`.
- Revamp the root `README.md` to be modern and informative.
- Organize documentation by role: Installation, Architecture, Usage, Strategy.

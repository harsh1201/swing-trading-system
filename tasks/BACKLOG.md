# Project Backlog — Swing Trading System

## High Priority
- [x] TASK-QA-002: Test coverage at 80% (target 90%+)
- [x] Implement ticker aliases for symbol changes
- [x] Add dead ticker handling (DEAD_TICKERS)
- [ ] Consider moving to Dhan API for live trading reliability

## Medium Priority
- [ ] Auto-close ACTIVE positions before earnings announcements
- [ ] Detect and handle corporate actions (splits, bonuses)
- [ ] Refactor backtest.py for Monte Carlo simulations

## Low Priority
- [ ] UI/Dashboard for backtest visualization
- [ ] Support for international markets

---

## Completed (v1.15)
- [x] Adopted RS Filter (Relative Strength)
- [x] Disabled regime filter permanently (requires manual review)
- [x] Disabled candle strength filter (hurt overall performance)
- [x] Separate Discord webhooks for Long/Short signals
- [x] Corrected score display logic for shorts
- [x] Added tracking for peak equity and max drawdown

---

## Completed (v1.4)
- [x] Portfolio features (cleanup, r_multiple, tracking)
- [x] Discord integration (webhook posting)
- [x] Backtest versioning (history.json)
- [x] Ticker alias mapping (_map_ticker function)
- [x] Dead ticker handling

---

*Maintained by PM Agent. Last updated: 2026-04-19*
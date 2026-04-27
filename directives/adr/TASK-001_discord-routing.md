# TASK-001 Discord Routing ADR
**Date:** 2026-04-23

## Problem Statement
The user requested that output runs of the long setup (`screener.py --strategy long_breakout`) route entirely to the long Discord webhook.
Similarly, `short_breakout` screener runs should route entirely to the short Discord webhook. 
Lastly, `backtest.py` should post its summary to the primary/general Discord webhook.

## Decision Made
1. **Screener Routing:** We will modify `screener.py` so that the `send_portfolio_to_discord()` function accepts `webhook_url` as an argument. In `run_screener()` and `run_screener_short()`, we will pass `DISCORD_LONG_SIGNALS_WEBHOOK` or `DISCORD_SHORT_SIGNALS_WEBHOOK` (depending on the strategy) to all Discord posting functions (both portfolio and signals). This ensures *all* output for a specific screener strategy goes specifically to its designated channel.
2. **Backtest Routing:** We will import `post_to_discord` and `DISCORD_PORTFOLIO_WEBHOOK` into `backtest.py`. We will create a new function `send_backtest_to_discord(strategy, ...)` that formats the overall historical backtest summary metrics (Win rate, total Pnl, max drawdown) and posts them to `DISCORD_PORTFOLIO_WEBHOOK`.

## Components / Files Modified
- `screener.py`: Update `send_portfolio_to_discord` signature. Modify `send_portfolio_to_discord` calls in `run_screener` and `run_screener_short` to use the strategy-specific webhook instead of `DISCORD_PORTFOLIO_WEBHOOK`.
- `backtest.py`: Add a formatting function to construct a discord message summarizing the run. Send it to `DISCORD_PORTFOLIO_WEBHOOK`.

## Alternatives Considered
- **Posting individual backtest trades to Discord:** Rejected because hitting Discord for 500+ trades per backtest runs afoul of rate limit guidelines. Summaries avoid this entirely while keeping the trader informed.
- **Skipping portfolio update in screener:** Rejected. Suppressing the portfolio limits info. Moving it to the strategy specific webhook satisfies the user's requirement.

## Performance and Security Considerations
Discord posts will use a `timeout=10` parameter in `requests.post()` exactly as implemented in `screener.py`, to prevent `backtest.py` from hanging if the network fails. 

## Definition of Done
When `--strategy long_breakout` is run on `screener.py`, output goes strictly to `DISCORD_LONG_SIGNALS_WEBHOOK`.
When `--strategy short_breakout` is run on `screener.py`, output goes strictly to `DISCORD_SHORT_SIGNALS_WEBHOOK`.
When `--strategy long_breakout / short_breakout` is run on `backtest.py`, the summary goes to `DISCORD_PORTFOLIO_WEBHOOK`.

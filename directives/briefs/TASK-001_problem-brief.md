# Problem Brief — TASK-001
**Date:** 2026-04-23
**Status:** draft

## Problem Statement (Original)
when i run python screener.py --strategy long_breakout command i want the output to be diplayed in DISCORD_LONG_WEBHOOK_URL
when i run python screener.py --strategy short_breakout i want it to be displayed in DISCORD_SHORT_WEBHOOK_URL
and when i run backtest backtest.py --strategy long or short i want it to be displayed in DISCORD_WEBHOOK_URL

## Problem Statement (Simplified)
Re-route and configure the Discord integrations so that:
1. Long Screener outputs strictly map to the `DISCORD_LONG_WEBHOOK_URL`.
2. Short Screener outputs strictly map to the `DISCORD_SHORT_WEBHOOK_URL`.
3. Backtest outputs (for either strategy) map to the general `DISCORD_WEBHOOK_URL`. 

## What We Know
- `screener.py` currently posts the portfolio summary to `DISCORD_PORTFOLIO_WEBHOOK` (which reads from `DISCORD_WEBHOOK_URL` in `.env`).
- `screener.py` also correctly posts new signals to `DISCORD_LONG_WEBHOOK_URL` and `DISCORD_SHORT_WEBHOOK_URL`.
- `backtest.py` currently has **no Discord integration** implemented.
- Discord has message rate limits and a hard 2000 character limit per single message endpoint.
- The system expects arguments like `--strategy long_breakout` and `--strategy short_breakout`.

## What We Don't Know (Assumptions to Validate)
- If the screener only posts to long/short webhooks, should we completely disable the "Total Portfolio Summary" post? Currently, it prints the active/pending trades on every screener run.
- Because a backtest simulates years of data, sending hundreds of individual trades to Discord would trigger API rate limits and spam the channel. We must assume the user only wants the **final backtest summary metrics** (Drawdown, P&L, Win Rate, etc.) sent to Discord.
- The user requested `--strategy long` or `short`. We don't know if they want actual CLI aliases created.

## Edge Cases Identified
- **Discord Character/Rate Limits:** `backtest.py` output can easily exceed Discord's 2000 character limit if trade logs are included. It needs a special summary formatter.
- **Missing Webhooks:** If someone runs `backtest.py` locally and hasn't set `.env`, it will silently fail to post unless we add warning messages.

## Clarifying Questions (max 3)
1. For `screener.py`, do you want to **disable the daily Portfolio Summary** message to avoid spam, so that it *only* posts the exact Long/Short signals to their respective channels?
2. For `backtest.py`, since a run contains hundreds of trades, should we build a **Backtest Summary Card** containing just the top-level stats (Win Rate, Total Return, Max Drawdown) to post to Discord?
3. Would you like us to add `--strategy long` and `--strategy short` as valid CLI aliases, or will you continue using `long_breakout` / `short_breakout`?

## Recommended Next Step
Human validates the assumptions. Once confirmed, **Product Manager Agent** finalizes the directive, and **Code Generator Agent** modifies `screener.py`, `backtest.py`, and `config/settings.py` for implementation.

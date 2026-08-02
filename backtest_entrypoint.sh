#!/bin/bash
# backtest_entrypoint.sh - Run backtest on demand (for Fly.io 2nd machine)

echo "🚀 Starting Swing Trading System Backtest..."
echo "📅 Date: $(date)"

echo "📊 Running LONG breakout backtest..."
python -u backtest.py --strategy long_breakout

echo "📊 Running SHORT breakout backtest..."
python -u backtest.py --strategy short_breakout

echo "✅ Backtest runs complete."
echo "📅 Finished at: $(date)"

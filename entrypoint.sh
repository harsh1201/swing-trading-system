#!/bin/bash
# entrypoint.sh - Run screener on deployment and stay alive

echo "🚀 Starting Swing Trading System Screener..."
echo "📅 Date: $(date)"

# Run LONG strategy
echo "🔍 Running LONG breakout strategy..."
python -u screener.py --strategy long_breakout

# Run SHORT strategy
echo "🔍 Running SHORT breakout strategy..."
python -u screener.py --strategy short_breakout

echo "✅ Screener runs complete."
echo "📅 Finished at: $(date)"
# No sleep here - Fly.io scheduler will restart this at the next interval.
# Exiting allows the machine to stop and save resources.

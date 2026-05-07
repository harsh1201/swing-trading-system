"""
reports/backtest/version.py — Backtest result versioning and comparison.

Saves backtest results with timestamps and allows comparison between runs.
"""

import json
import os
from datetime import datetime
import pytz
from typing import Any

REPORTS_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(REPORTS_DIR, "history.json")

# Import TIMEZONE inside the function to avoid circular imports if any
def get_ist_now():
    from config.settings import TIMEZONE
    ist = pytz.timezone(TIMEZONE)
    return datetime.now(ist)


def save_backtest_result(
    strategy: str,
    total_trades: int,
    win_rate: float,
    net_pct: float,
    final_equity: float,
    avg_rr: float,
    max_drawdown: float = 0.0,
    avg_hold: float = 0.0,
    notes: str = "",
) -> dict[str, Any]:
    """
    Save a backtest result with timestamp and config snapshot.
    
    Returns the saved result dict.
    """
    result = {
        "timestamp": get_ist_now().isoformat(),
        "strategy": strategy,
        "metrics": {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "net_pct": net_pct,
            "final_equity": final_equity,
            "avg_rr": avg_rr,
            "max_drawdown": max_drawdown,
            "avg_hold": avg_hold,
        },
        "notes": notes,
    }
    
    history = load_history()
    history.append(result)
    
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)
    
    return result


def load_history() -> list[dict[str, Any]]:
    """Load all historical backtest results."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def compare_runs(run1_idx: int = -2, run2_idx: int = -1) -> dict[str, Any]:
    """
    Compare two backtest runs by index (default: last two runs).
    
    Returns comparison dict with deltas.
    """
    history = load_history()
    
    if len(history) < 2:
        return {"error": "Not enough historical runs to compare"}
    
    if abs(run1_idx) > len(history) or abs(run2_idx) > len(history):
        return {"error": "Invalid run index"}
    
    r1 = history[run1_idx]
    r2 = history[run2_idx]
    
    comparison = {
        "run1": {"timestamp": r1["timestamp"], "strategy": r1["strategy"]},
        "run2": {"timestamp": r2["timestamp"], "strategy": r2["strategy"]},
        "deltas": {},
    }
    
    for key in r1["metrics"]:
        delta = r2["metrics"][key] - r1["metrics"][key]
        delta_pct = (delta / r1["metrics"][key] * 100) if r1["metrics"][key] != 0 else 0
        comparison["deltas"][key] = {
            "run1": r1["metrics"][key],
            "run2": r2["metrics"][key],
            "delta": round(delta, 2),
            "delta_pct": round(delta_pct, 2),
        }
    
    return comparison


def print_comparison() -> None:
    """Print a comparison of the last two backtest runs."""
    comparison = compare_runs()
    
    if "error" in comparison:
        print(f"Error: {comparison['error']}")
        return
    
    print()
    print("=" * 70)
    print("BACKTEST COMPARISON")
    print("=" * 70)
    
    print(f"  Previous run: {comparison['run1']['timestamp'][:19]}")
    print(f"  Latest run:   {comparison['run2']['timestamp'][:19]}")
    print()
    print("-" * 70)
    print(f"  {'Metric':<20} {'Previous':>12} {'Latest':>12} {'Delta':>12} {'Change':>10}")
    print("-" * 70)
    
    for key, vals in comparison["deltas"].items():
        delta_sign = "+" if vals["delta"] >= 0 else ""
        change_sign = "▲" if vals["delta"] >= 0 else "▼"
        print(f"  {key:<20} {vals['run1']:>12.2f} {vals['run2']:>12.2f} {delta_sign}{vals['delta']:>11.2f} {change_sign} {vals['delta_pct']:>7.1f}%")
    
    print("-" * 70)
    print()


def print_history() -> None:
    """Print all historical backtest runs."""
    history = load_history()
    
    if not history:
        print("No backtest history found.")
        return
    
    print()
    print("=" * 70)
    print("BACKTEST HISTORY")
    print("=" * 70)
    print(f"  {'#':<4} {'Date':<20} {'Strategy':<15} {'Trades':>7} {'Win%':>7} {'Net%':>8} {'RR':>6}")
    print("-" * 70)
    
    for i, run in enumerate(history):
        ts = run["timestamp"][:19]
        strat = run["strategy"][:14]
        m = run["metrics"]
        print(f"  {len(history)-i:<4} {ts:<20} {strat:<15} {m['total_trades']:>7} {m['win_rate']:>7.1f} {m['net_pct']:>+8.2f} {m['avg_rr']:>6.2f}")
    
    print("-" * 70)
    print(f"  Total runs: {len(history)}")
    print()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--compare":
        print_comparison()
    else:
        print_history()

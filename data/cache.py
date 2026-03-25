"""
data/cache.py — Shared CSV cache for yfinance downloads.

Each ticker is stored as  data/<TICKER>.csv  the first time it is fetched.
Subsequent calls load directly from disk, avoiding redundant API calls.

Usage
-----
  from data.cache import fetch_ohlcv

  df = fetch_ohlcv("RELIANCE.NS", days=2200)           # cache-first
  df = fetch_ohlcv("RELIANCE.NS", days=2200, refresh=True)  # force fresh

Cache notes
-----------
• The file stores the full date-range fetched on first call.
• Pass refresh=True to overwrite a stale file (e.g. next day's screener run,
  or after the first backtest fetch to capture new bars).
• Corrupt / empty CSV files are silently re-downloaded.
• The data/ folder is the only write target — strategy code is untouched.
"""

import os
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

# Absolute path to this folder so imports work from any cwd
_DIR = os.path.dirname(os.path.abspath(__file__))


def _cache_path(ticker: str) -> str:
    """Return the canonical CSV path for a ticker."""
    safe = ticker.replace("^", "_").replace("/", "_")
    return os.path.join(_DIR, f"{safe}.csv")


def fetch_ohlcv(
    ticker:  str,
    days:    int,
    refresh: bool = False,
) -> pd.DataFrame | None:
    """
    Return a daily OHLCV DataFrame for `ticker` covering the last `days`
    calendar days.

    Parameters
    ----------
    ticker  : Yahoo Finance symbol, e.g. "RELIANCE.NS" or "^NSEI"
    days    : calendar-day look-back window
    refresh : if True, ignore any cached file and download fresh data

    Returns
    -------
    DataFrame with DatetimeIndex and columns [Open, High, Low, Close, Volume],
    or None if the download fails or returns no data.
    """
    filepath = _cache_path(ticker)

    # ── Load from cache ──────────────────────────────────────────────────────
    if not refresh and os.path.exists(filepath):
        try:
            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            if not df.empty:
                return df
        except Exception:
            pass    # corrupt file → fall through to fresh download

    # ── Fresh download ───────────────────────────────────────────────────────
    end   = datetime.today()
    start = end - timedelta(days=days)
    try:
        df = yf.download(
            ticker,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval="1d",
            progress=False,
            auto_adjust=True,
        )
    except Exception:
        return None

    if df.empty:
        return None

    # Flatten multi-level columns that yfinance sometimes returns
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.to_csv(filepath)
    return df

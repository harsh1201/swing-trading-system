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

# Absolute path to a dedicated storage folder to prevent hiding python files when mounted
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DIR = os.path.join(_BASE_DIR, "storage")
os.makedirs(_DIR, exist_ok=True)


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

    # Remove duplicate columns (yfinance can produce them after flattening)
    if df.columns.duplicated().any():
        df = df.loc[:, ~df.columns.duplicated()]

    df.to_csv(filepath)
    return df

import json

class DataCache:
    def __init__(self, filepath: str):
        self.filepath = filepath

    def save(self, key: str, data: dict):
        try:
            with open(self.filepath, 'r') as f:
                cache_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            cache_data = {}
        
        cache_data[key] = data
        with open(self.filepath, 'w') as f:
            # allow_nan=False will raise an error if NaN is found, 
            # but it's better to clean the data first or use a custom encoder.
            # For simplicity, we'll use a hack to ensure valid JSON.
            json_str = json.dumps(cache_data, allow_nan=True)
            # Replace literal NaN with null
            json_str = json_str.replace(": NaN", ": null")
            f.write(json_str)

    def load(self, key: str) -> dict | None:
        try:
            with open(self.filepath, 'r') as f:
                cache_data = json.load(f)
            return cache_data.get(key)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def clear(self):
        try:
            os.remove(self.filepath)
        except FileNotFoundError:
            pass

"""
data/earnings.py — Earnings-date blackout filter.

Prevents the screener from entering trades in the high-gap-risk window
surrounding a company's earnings announcement.

Data source (priority order)
-----------------------------
1. data/earnings.csv  — manual or API-populated file (optional).
2. Empty list          — safe fallback; all stocks pass if file is absent.

earnings.csv format
-------------------
  ticker,date
  RELIANCE,2025-01-20
  TCS,2025-01-15
  HDFCBANK,2025-04-22

  Rules:
  • Use the base ticker WITHOUT the .NS suffix.
  • One row per earnings date (multiple rows per ticker are fine).
  • Dates must be in YYYY-MM-DD format.
  • Lines starting with '#' or blank lines are ignored.

Extending to a live API
-----------------------
Replace _load_csv() with a function that calls a data provider, then cache
the result the same way.  The rest of the screener code is untouched.
"""

import os
from datetime import datetime

_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "earnings.csv")

# Module-level cache — CSV is parsed at most once per process run.
_CACHE: dict[str, list[datetime]] | None = None


def _load_csv() -> dict[str, list[datetime]]:
    """
    Parse earnings.csv into  {base_ticker: [datetime, ...]}

    Returns an empty dict if the file is missing or unreadable —
    the system treats every stock as earnings-free in that case.
    """
    mapping: dict[str, list[datetime]] = {}
    if not os.path.exists(_CSV_PATH):
        return mapping

    try:
        with open(_CSV_PATH, newline="", encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                # Skip blank lines, comments, and the header row
                if not line or line.startswith("#") or line.lower().startswith("ticker"):
                    continue
                parts = line.split(",")
                if len(parts) < 2:
                    continue
                ticker = parts[0].strip().upper()
                try:
                    d = datetime.strptime(parts[1].strip(), "%Y-%m-%d")
                    mapping.setdefault(ticker, []).append(d)
                except ValueError:
                    continue    # skip rows with unparseable dates
    except Exception:
        pass    # I/O error — return whatever was parsed so far

    return mapping


def get_earnings_dates(ticker: str) -> list[datetime]:
    """
    Return a list of known earnings announcement dates for `ticker`.

    Parameters
    ----------
    ticker : str
        Yahoo Finance symbol (e.g. "RELIANCE.NS") or plain base ticker
        ("RELIANCE").  The .NS / .BO suffix is stripped automatically.

    Returns
    -------
    list[datetime]
        Known earnings dates.  Empty list if none are found — the caller
        should treat an empty list as "no blackout required".
    """
    global _CACHE
    if _CACHE is None:
        _CACHE = _load_csv()

    base = ticker.split(".")[0].upper()
    return _CACHE.get(base, [])


def reload() -> None:
    """
    Force a fresh parse of earnings.csv on the next call to
    get_earnings_dates().  Useful if the file is updated between runs
    without restarting the process.
    """
    global _CACHE
    _CACHE = None

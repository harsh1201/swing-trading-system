"""data/symbols.py — Dynamic NSE symbol sourcing.

Provides live symbol fetching from NSE via nsepython.
"""

from nsepython import nse_eq_symbols, fnolist

def _normalise_nse_ticker(code: str) -> str | None:
    symbol = code.strip().upper()
    if not symbol or any(ch.isspace() for ch in symbol):
        return None
    if symbol.endswith(".NS"):
        return symbol
    return f"{symbol}.NS"


def _normalise_symbols(codes) -> set[str]:
    symbols = set()
    for code in codes:
        if not isinstance(code, str):
            continue
        symbol = _normalise_nse_ticker(code)
        if symbol:
            symbols.add(symbol)
    return symbols


def get_nse_symbols() -> list[str]:
    """Fetch all NSE equity symbols.

    Returns sorted list of tickers with .NS suffix,
    e.g. ["RELIANCE.NS", "TCS.NS", ...].
    """
    try:
        codes = nse_eq_symbols()
        return sorted(_normalise_symbols(codes))
    except Exception:
        return []


def get_fno_symbols() -> set[str]:
    """Fetch NSE F&O (futures & options) symbols.

    Returns a set of tickers with .NS suffix.
    Falls back to an empty set on any error.
    """
    try:
        codes = fnolist()
        return _normalise_symbols(codes)
    except Exception:
        return set()

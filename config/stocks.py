"""config/stocks.py — Dynamic stock universe sourced live from NSE.

STOCKS: dict[str, str]  — All NSE equity symbols with .NS suffix, display name = ticker stem.
FNO_SYMBOLS: set[str]   — F&O-eligible symbols (subset of STOCKS keys).
"""

from data.symbols import get_nse_symbols, get_fno_symbols

_NSE_CODES = get_nse_symbols()
FNO_SYMBOLS = get_fno_symbols()

STOCKS: dict[str, str] = {
    sym: sym.replace(".NS", "") for sym in _NSE_CODES
}

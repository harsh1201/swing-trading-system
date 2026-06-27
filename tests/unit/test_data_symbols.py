"""Tests for dynamic NSE symbol normalization."""

from data.symbols import _normalise_symbols


def test_normalise_symbols_keeps_valid_nse_codes():
    symbols = _normalise_symbols(["HEROMOTOCO", "M&M", "BAJAJ-AUTO", "3MINDIA"])

    assert symbols == {
        "HEROMOTOCO.NS",
        "M&M.NS",
        "BAJAJ-AUTO.NS",
        "3MINDIA.NS",
    }


def test_normalise_symbols_drops_empty_and_spaced_codes():
    symbols = _normalise_symbols(["", " ", "NIFTY 50", None, "RELIANCE.NS"])

    assert symbols == {"RELIANCE.NS"}

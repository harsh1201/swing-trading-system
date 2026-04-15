import os
import pytest
import pandas as pd
from datetime import datetime
from unittest import mock
from data.earnings import get_earnings_dates, reload

def test_get_earnings_dates_empty(monkeypatch, tmp_path):
    # line 48-49
    monkeypatch.setattr("data.earnings._CSV_PATH", str(tmp_path / "nonexistent.csv"))
    reload()
    assert get_earnings_dates("TEST") == []

def test_get_earnings_load_minimal_csv(monkeypatch, tmp_path):
    # setup a fake earnings csv
    csv_path = tmp_path / "earnings.csv"
    csv_path.write_text("ticker,date\nAAPL,2024-01-01\nGOOG,invalid-date\nBAD_LINE\n") # lines 60, 65-66
    
    monkeypatch.setattr("data.earnings._CSV_PATH", str(csv_path))
    reload()
    
    assert len(get_earnings_dates("AAPL")) == 1
    assert get_earnings_dates("GOOG") == []
    assert get_earnings_dates("BAD_LINE") == []

def test_get_earnings_load_exception(monkeypatch, tmp_path):
    # line 67-68
    csv_path = tmp_path / "earnings.csv"
    csv_path.write_text("ticker,date\nAAPL,2024-01-01")
    monkeypatch.setattr("data.earnings._CSV_PATH", str(csv_path))
    reload()

    with mock.patch("builtins.open", side_effect=Exception("BOOM")):
        # reloading should trigger the exception block
        reload()
        assert get_earnings_dates("AAPL") == []

def test_get_earnings_dates_caching(monkeypatch, tmp_path):
    csv_path = tmp_path / "earnings.csv"
    csv_path.write_text("ticker,date\nAAPL,2024-01-01")
    monkeypatch.setattr("data.earnings._CSV_PATH", str(csv_path))
    reload()
    
    dates1 = get_earnings_dates("AAPL")
    # modify file but don't reload
    csv_path.write_text("ticker,date\nAAPL,2025-01-01")
    dates2 = get_earnings_dates("AAPL")
    assert dates1 == dates2
    
    # reload and check again
    reload()
    dates3 = get_earnings_dates("AAPL")
    assert dates3 != dates1
    assert dates3[0].year == 2025

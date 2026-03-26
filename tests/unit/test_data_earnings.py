import pytest
import pandas as pd
import os
from datetime import datetime
from data.earnings import get_earnings_dates, reload

def test_get_earnings_dates_empty(monkeypatch, tmp_path):
    monkeypatch.setattr("data.earnings._CSV_PATH", str(tmp_path / "nonexistent.csv"))
    reload()
    assert get_earnings_dates("TEST") == []

def test_get_earnings_dates_cached(monkeypatch, tmp_path):
    csv_path = tmp_path / "earnings.csv"
    monkeypatch.setattr("data.earnings._CSV_PATH", str(csv_path))
    
    # Create mock earnings csv 
    with open(csv_path, "w") as f:
        f.write("ticker,date\n")
        f.write("RELIANCE,2023-01-20\n")
    
    reload()
    dates = get_earnings_dates("RELIANCE.NS")
    assert len(dates) == 1
    assert dates[0] == datetime(2023, 1, 20)

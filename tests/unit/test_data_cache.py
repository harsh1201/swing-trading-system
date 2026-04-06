import pytest
import pandas as pd
import os
import yfinance as yf
from data.cache import DataCache, fetch_ohlcv

def test_fetch_ohlcv_cache_hit(monkeypatch, tmp_path):
    # Mock _DIR in data.cache to be a temp path
    monkeypatch.setattr("data.cache._DIR", str(tmp_path))
    
    ticker = "TEST"
    df = pd.DataFrame({"Close": [100.0]}, index=[pd.Timestamp("2023-01-01")])
    
    # Save to "cache"
    csv_path = tmp_path / f"{ticker}.csv"
    df.to_csv(csv_path)
    
    # Call fetch_ohlcv (refresh=False)
    res = fetch_ohlcv(ticker, days=10, refresh=False)
    assert res is not None
    assert float(res["Close"].iloc[0]) == 100.0

def test_cache_save_load(tmp_path):
    cache_file = tmp_path / "test_cache.json"
    cache = DataCache(str(cache_file))
    data = {"key": "value"}
    cache.save("test", data)
    assert cache.load("test") == data

def test_cache_missing_file_load(tmp_path):
    # line 67-68
    cache_file = tmp_path / "non_existent.json"
    cache = DataCache(str(cache_file))
    assert cache.load("any") is None

def test_cache_clear(tmp_path):
    # line 82-83, 86
    cache_file = tmp_path / "test_cache.json"
    cache = DataCache(str(cache_file))
    cache.save("test", {"a": 1})
    assert cache_file.exists()
    cache.clear()
    assert not cache_file.exists()
    cache.clear() # line 86 (non-existent)

def test_cache_load_corrupt_json(tmp_path):
    # line 90-94
    cache_file = tmp_path / "corrupt.json"
    cache_file.write_text("invalid json")
    cache = DataCache(str(cache_file))
    assert cache.load("any") is None

def test_fetch_ohlcv_download(monkeypatch, tmp_path):
    monkeypatch.setattr("data.cache._DIR", str(tmp_path))
    
    # Mock yfinance download
    def mock_download(*args, **kwargs):
        return pd.DataFrame({
            "Open": [190.0], "High": [210.0], "Low": [180.0], "Close": [200.0], "Volume": [1000]
        }, index=pd.DatetimeIndex([pd.Timestamp("2023-02-01")]))
            
    monkeypatch.setattr("yfinance.download", mock_download)
    
    res = fetch_ohlcv("NEW_TICKER", days=5, refresh=True)
    assert res is not None
    assert float(res["Close"].iloc[0]) == 200.0
    # verify it was saved
    assert os.path.exists(tmp_path / "NEW_TICKER.csv")

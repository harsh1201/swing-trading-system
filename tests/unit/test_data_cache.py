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

def test_fetch_ohlcv_corrupt_cache(monkeypatch, tmp_path):
    # lines 67-68: corrupt CSV file should fall through to download
    monkeypatch.setattr("data.cache._DIR", str(tmp_path))
    
    ticker = "CORRUPT"
    csv_path = tmp_path / f"{ticker}.csv"
    csv_path.write_text("not,a,valid,csv,file")
    
    def mock_read_csv_error(*args, **kwargs):
        raise Exception("CSV parse error")
    
    import pandas as pd
    original_read_csv = pd.read_csv
    
    def mock_read_csv(*args, **kwargs):
        if str(tmp_path) in str(args[0]):
            raise Exception("Corrupt CSV")
        return original_read_csv(*args, **kwargs)
    
    def mock_download(*args, **kwargs):
        return pd.DataFrame({
            "Open": [100.0], "High": [110.0], "Low": [90.0], "Close": [105.0], "Volume": [1000]
        }, index=pd.DatetimeIndex([pd.Timestamp("2023-01-01")]))
    
    monkeypatch.setattr("pandas.read_csv", mock_read_csv)
    monkeypatch.setattr("yfinance.download", mock_download)
    
    res = fetch_ohlcv(ticker, days=10, refresh=False)
    assert res is not None
    assert float(res["Close"].iloc[0]) == 105.0

def test_fetch_ohlcv_download_exception(monkeypatch, tmp_path):
    # lines 82-83: yfinance exception should return None
    monkeypatch.setattr("data.cache._DIR", str(tmp_path))
    
    def mock_download_fail(*args, **kwargs):
        raise Exception("Network error")
    
    monkeypatch.setattr("yfinance.download", mock_download_fail)
    
    res = fetch_ohlcv("FAIL_TICKER", days=10, refresh=True)
    assert res is None

def test_fetch_ohlcv_empty_dataframe(monkeypatch, tmp_path):
    # line 86: empty dataframe should return None
    monkeypatch.setattr("data.cache._DIR", str(tmp_path))
    
    def mock_download_empty(*args, **kwargs):
        return pd.DataFrame()
    
    monkeypatch.setattr("yfinance.download", mock_download_empty)
    
    res = fetch_ohlcv("EMPTY_TICKER", days=10, refresh=True)
    assert res is None

def test_fetch_ohlcv_duplicate_columns(monkeypatch, tmp_path):
    # line 94: duplicate columns should be handled
    monkeypatch.setattr("data.cache._DIR", str(tmp_path))

    def mock_download_duplicates(*args, **kwargs):
        df = pd.DataFrame({
            "Open": [100.0, 101.0],
            "High": [110.0, 111.0],
            "Low": [90.0, 91.0],
            "Close": [105.0, 106.0],
            "Volume": [1000, 1100]
        }, index=pd.DatetimeIndex([pd.Timestamp("2023-01-01"), pd.Timestamp("2023-01-02")]))
        df = pd.concat([df, df], axis=1)
        assert df.columns.duplicated().any()
        return df

    monkeypatch.setattr("yfinance.download", mock_download_duplicates)

    res = fetch_ohlcv("DUP_TICKER", days=10, refresh=True)
    assert res is not None
    assert "Close" in res.columns
    assert len(res) == 2

def test_fetch_ohlcv_multiindex_columns(monkeypatch, tmp_path):
    # line 90: MultiIndex columns should be flattened
    monkeypatch.setattr("data.cache._DIR", str(tmp_path))

    def mock_download_multiindex(*args, **kwargs):
        df = pd.DataFrame({
            "Open": [100.0],
            "High": [110.0],
            "Low": [90.0],
            "Close": [105.0],
            "Volume": [1000]
        }, index=pd.DatetimeIndex([pd.Timestamp("2023-01-01")]))
        df.columns = pd.MultiIndex.from_tuples([
            ("Open", "TEST"), ("High", "TEST"), ("Low", "TEST"), ("Close", "TEST"), ("Volume", "TEST")
        ])
        return df

    monkeypatch.setattr("yfinance.download", mock_download_multiindex)

    res = fetch_ohlcv("MULTI_TICKER", days=10, refresh=True)
    assert res is not None
    assert "Close" in res.columns
    assert not isinstance(res.columns, pd.MultiIndex)

def test_cache_save_existing_file(monkeypatch, tmp_path):
    # line 108: save to existing cache file should load existing data first
    cache_file = tmp_path / "existing_cache.json"
    cache_file.write_text('{"existing_key": "existing_value"}')
    
    cache = DataCache(str(cache_file))
    cache.save("new_key", {"new": "data"})
    
    import json
    with open(cache_file) as f:
        result = json.load(f)
    
    assert "existing_key" in result
    assert "new_key" in result

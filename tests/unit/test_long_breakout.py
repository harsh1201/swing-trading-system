import pytest
import pandas as pd
import numpy as np
from strategies.long_breakout import (
    add_indicators,
    check_trend,
    check_consolidation,
    check_volume,
    score_long_breakout,
    calculate_trade_setup,
    get_market_regime,
    is_market_bullish,
    check_liquidity,
    check_gap_up,
    check_gap_condition,
    _trend_score,
    calculate_market_breadth
)

@pytest.fixture
def sample_df():
    """Create a sample dataframe for trend and consolidation testing."""
    dates = pd.date_range(start="2023-01-01", periods=300)
    data = {
        "Open": np.linspace(100, 200, 300),
        "High": np.linspace(105, 205, 300),
        "Low": np.linspace(95, 195, 300),
        "Close": np.linspace(100, 200, 300),
        "Volume": [1000] * 300
    }
    df = pd.DataFrame(data, index=dates)
    return add_indicators(df)

def test_add_indicators(sample_df):
    assert "EMA20" in sample_df.columns
    assert "EMA50" in sample_df.columns
    assert "EMA200" in sample_df.columns

def test_check_trend_passing(sample_df):
    result = check_trend(sample_df)
    assert result is not None
    assert result["close"] > result["ema50"]

def test_check_trend_failing():
    dates = pd.date_range(start="2023-01-01", periods=250)
    data = {"Close": [100] * 250, "Volume": [1000] * 250}
    df = pd.DataFrame(data, index=dates)
    df["EMA50"] = 150
    df["EMA200"] = 120
    assert check_trend(df) is None

def test_check_consolidation_passing(sample_df):
    idx = 200
    window_start = idx - 11 
    sample_df.loc[sample_df.index[window_start:idx+1], "High"] = 160
    sample_df.loc[sample_df.index[window_start:idx+1], "Low"] = 158
    sample_df.loc[sample_df.index[window_start:idx+1], "Close"] = 159
    
    result = check_consolidation(sample_df, idx=idx)
    assert result is not None
    assert result["range_pct"] < 8.0

def test_check_consolidation_failing(sample_df):
    idx = 200
    sample_df.loc[sample_df.index[idx-11:idx+1], "High"] = 180
    sample_df.loc[sample_df.index[idx-11:idx+1], "Low"] = 150
    result = check_consolidation(sample_df, idx=idx)
    assert result is None
    
    sample_df.loc[sample_df.index[idx], "Close"] = 150
    assert check_consolidation(sample_df, idx=idx) is None

def test_check_volume_passing(sample_df):
    idx = 100
    sample_df.loc[sample_df.index[idx], "Volume"] = 3000
    result = check_volume(sample_df, idx=idx)
    assert result is not None
    assert result["surge_ratio"] >= 1.5

def test_check_volume_failing(sample_df):
    idx = 100
    sample_df.loc[sample_df.index[idx], "Volume"] = 100
    result = check_volume(sample_df, idx=idx)
    assert result is None

def test_get_market_regime(sample_df):
    # STRONG_BULL
    idx = 250
    sample_df.loc[sample_df.index[idx], "Close"] = 300
    sample_df.loc[sample_df.index[idx], "EMA50"] = 100
    # Create another stock for breadth
    stock2 = sample_df.copy()
    stock2.loc[stock2.index[idx], "Close"] = 300
    stock2.loc[stock2.index[idx], "EMA50"] = 100
    all_data = {"S1": sample_df, "S2": stock2}
    
    is_tradeable, label, breadth = get_market_regime(sample_df, idx=idx, all_data=all_data)
    assert is_tradeable is True
    assert label == "STRONG_BULL"

    # EARLY_TREND (close > EMA20, EMA20 rising, breadth >= 30, and idx >= 200+5)
    # This specific stock is NOT above EMA50 (Close 350 < EMA50 400)
    sample_df.loc[sample_df.index[idx], "EMA50"] = 400
    sample_df.loc[sample_df.index[idx], "Close"] = 350
    sample_df.loc[sample_df.index[idx], "EMA20"] = 340
    sample_df.loc[sample_df.index[idx-5], "EMA20"] = 300 
    # But breadh is derived from stock2 which IS above EMA50
    is_tradeable, label, breadth = get_market_regime(sample_df, idx=idx, all_data=all_data)
    assert is_tradeable is True
    assert label == "EARLY_TREND"

    # BEAR
    sample_df.loc[sample_df.index[idx], "Close"] = 50
    # Also breadh is 0 if no stock is above EMA50
    stock2.loc[stock2.index[idx], "Close"] = 50
    is_tradeable, label, breadth = get_market_regime(sample_df, idx=idx, all_data=all_data)
    assert is_tradeable is False
    assert label == "BEAR"

def test_check_liquidity(sample_df):
    idx = 100
    sample_df.loc[sample_df.index[idx-20:idx], "Volume"] = 1_000_000
    sample_df.loc[sample_df.index[idx-20:idx], "Close"] = 200
    assert check_liquidity(sample_df, idx=idx) is True

def test_check_gap_up(sample_df):
    entry_price = 150
    sample_df.loc[sample_df.index[-1], "Open"] = 160
    result = check_gap_up(sample_df, entry_price)
    assert result["is_gap_up"] is True

def test_check_gap_condition():
    assert check_gap_condition(101, 100, max_gap_pct=0.02) is True
    assert check_gap_condition(105, 100, max_gap_pct=0.02) is False

def test_trend_score_variations():
    assert _trend_score(-1) == 0.0
    assert _trend_score(0.5) == 12.5
    assert _trend_score(2.0) == 25.0
    assert _trend_score(5.0) == 18.75
    assert round(_trend_score(10.0), 2) == 4.17

def test_calculate_market_breadth(sample_df):
    stock2 = sample_df.copy()
    stock2.loc[stock2.index[200], "Close"] = 0
    all_data = {"S1": sample_df, "S2": stock2}
    breadth = calculate_market_breadth(all_data, 200, sample_df)
    assert breadth == 50.0

def test_score_long_breakout():
    trend = {"close": 105, "ema50": 100, "ema200": 90}
    coil = {"period_high": 102, "period_low": 100, "range_pct": 2.0, "gap_to_high_pct": 1.0}
    result = score_long_breakout(trend, coil)
    assert result["total"] > 0

def test_calculate_trade_setup():
    result = calculate_trade_setup(110, 100)
    assert result["entry"] == 110
    assert result["is_valid"] is True

import pytest
import pandas as pd
import numpy as np
from strategies.short_breakout import (
    get_market_regime_short,
    check_trend_short,
    check_consolidation_short,
    check_gap_down,
    _trend_score_short,
    score_short_breakout,
    calculate_trade_setup_short
)
from strategies.long_breakout import add_indicators

@pytest.fixture
def sample_df_short():
    """Create a sample dataframe for trend and consolidation testing (bearish)."""
    dates = pd.date_range(start="2023-01-01", periods=250)
    data = {
        "Open": np.linspace(200, 100, 250),
        "High": np.linspace(205, 105, 250),
        "Low": np.linspace(195, 95, 250),
        "Close": np.linspace(200, 100, 250),
        "Volume": [1000] * 250
    }
    df = pd.DataFrame(data, index=dates)
    return add_indicators(df)

def test_check_trend_short_passing(sample_df_short):
    result = check_trend_short(sample_df_short)
    assert result is not None
    assert result["close"] < result["ema50"]
    assert result["ema50"] < result["ema200"]

def test_check_trend_short_failing(sample_df_short):
    # Above EMA50
    sample_df_short.loc[sample_df_short.index[-1], "Close"] = 300
    sample_df_short.loc[sample_df_short.index[-1], "EMA50"] = 100
    assert check_trend_short(sample_df_short) is None

def test_check_consolidation_short_passing(sample_df_short):
    idx = 200
    window_start = idx - 11 
    sample_df_short.loc[sample_df_short.index[window_start:idx+1], "High"] = 120
    sample_df_short.loc[sample_df_short.index[window_start:idx+1], "Low"] = 118
    sample_df_short.loc[sample_df_short.index[window_start:idx+1], "Close"] = 119
    
    result = check_consolidation_short(sample_df_short, idx=idx)
    assert result is not None
    assert result["range_pct"] < 8.0

def test_check_consolidation_short_failing(sample_df_short):
    idx = 200
    # Range too wide
    sample_df_short.loc[sample_df_short.index[idx-11:idx+1], "High"] = 150
    sample_df_short.loc[sample_df_short.index[idx-11:idx+1], "Low"] = 100
    assert check_consolidation_short(sample_df_short, idx=idx) is None

def test_get_market_regime_short(sample_df_short):
    idx = 200
    sample_df_short.loc[sample_df_short.index[idx], "Close"] = 50
    sample_df_short.loc[sample_df_short.index[idx], "EMA50"] = 100
    all_data = {"TEST.NS": sample_df_short}
    is_tradeable, label, breadth = get_market_regime_short(sample_df_short, idx=idx, all_data=all_data)
    assert is_tradeable is True
    assert label == "STRONG_BEAR"

def test_check_gap_down(sample_df_short):
    entry_price = 120
    sample_df_short.loc[sample_df_short.index[-1], "Open"] = 110
    result = check_gap_down(sample_df_short, entry_price, threshold=1.02)
    assert result["is_gap_down"] is True
    assert result["gap_pct"] > 0

def test_trend_score_short_variations():
    assert _trend_score_short(-1) == 0.0
    assert _trend_score_short(0.5) == 12.5
    assert _trend_score_short(2.0) == 25.0
    assert _trend_score_short(5.0) == 18.75
    assert round(_trend_score_short(10.0), 2) == 4.17

def test_score_short_breakout():
    trend = {"close": 95, "ema50": 100, "ema200": 110}
    coil = {
        "period_high": 102,
        "period_low": 100,
        "range_pct": 2.0,
        "gap_to_low_pct": 1.0
    }
    result = score_short_breakout(trend, coil)
    assert "total" in result
    assert result["total"] > 0

def test_calculate_trade_setup_short():
    result = calculate_trade_setup_short(110, 100)
    assert result["entry"] == 100
    assert result["stop_loss"] == 110
    assert result["risk"] == 10
    assert result["is_valid"] is True

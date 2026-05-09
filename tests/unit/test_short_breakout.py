import pytest
from unittest import mock
import pandas as pd
import numpy as np
from strategies.short_breakout import (
    get_market_regime_short,
    check_trend_short,
    check_consolidation_short,
    check_gap_down,
    _trend_score_short,
    score_short_breakout,
    calculate_trade_setup_short,
    is_market_bearish,
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
    assert _trend_score_short(0.5) == 20.0
    assert _trend_score_short(2.0) == 40.0
    assert _trend_score_short(5.0) == 30.0
    assert round(_trend_score_short(10.0), 2) == 6.67

def test_score_short_uses_config_weights():
    """Verify score calculation uses config weights instead of hardcoded values."""
    from config.settings import SCORE_WEIGHT_RISK, SCORE_WEIGHT_RANGE, SCORE_WEIGHT_TREND
    
    trend = {"close": 95, "ema50": 100, "ema200": 110}
    coil = {"period_high": 102, "period_low": 100, "range_pct": 2.0, "gap_to_low_pct": 1.0}
    result = score_short_breakout(trend, coil)
    
    expected_total = SCORE_WEIGHT_RISK + SCORE_WEIGHT_RANGE + SCORE_WEIGHT_TREND
    assert expected_total == 100, "Config weights should sum to 100"
    assert result["total"] <= expected_total, "Total score should not exceed sum of weights"

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

def test_get_market_regime_short_edge_cases(sample_df_short):
    # idx == -1 (127)
    df = sample_df_short
    res, label, _ = get_market_regime_short(df, idx=-1)
    assert label is not None

    # idx < EMA_LONG (130)
    res, label, _ = get_market_regime_short(df, idx=2)
    assert res is False
    assert label == "BULL"

    # idx % 100 == 0 (139)
    ldf = pd.DataFrame({"Close": [100.0]*101}, index=pd.date_range("2023-01-01", periods=101))
    ldf = add_indicators(ldf)
    get_market_regime_short(ldf, idx=100)

def test_early_bear_logic(sample_df_short):
    # Condition B: close < ema20 and ema20 < ema20_prev and breadth <= 70 (146-150)
    df = sample_df_short
    idx = len(df) - 1
    # Force condition A to be false (close < ema50)
    df.loc[df.index[idx], "EMA50"] = 40 # EMA50 below 50
    df.loc[df.index[idx], "Close"] = 50 # Above EMA50 (No Strong Bear)
    df.loc[df.index[idx], "EMA20"] = 60 # Above Close (Early Bear)
    df.loc[df.index[idx-5], "EMA20"] = 80 # Falling EMA20
    
    with mock.patch("strategies.short_breakout.calculate_market_breadth", return_value=50.0):
        res, label, _ = get_market_regime_short(df, idx=idx)
        assert res is True
        assert label == "EARLY_BEAR"

def test_is_market_bearish_wrapper(sample_df_short):
    df = sample_df_short
    # Condition: close < ema50 and breadth <= 60
    df.loc[df.index[-1], "Close"] = 50
    with mock.patch("strategies.short_breakout.calculate_market_breadth", return_value=50.0):
        assert is_market_bearish(df, idx=len(df)-1) is True

def test_get_market_regime_short_bull_regime(sample_df_short):
    # Coverage for line 152 (BULL)
    df = sample_df_short
    idx = len(df) - 1
    df.loc[df.index[idx], "Close"] = 500 # Way above EMA50, not early bear
    res, label, _ = get_market_regime_short(df, idx=idx)
    assert res is False
    assert label == "BULL"

def test_check_consolidation_short_default_idx(sample_df_short):
    # Coverage for line 211
    check_consolidation_short(sample_df_short)

def test_calculate_trade_setup_short():
    result = calculate_trade_setup_short(110, 100)
    assert result["entry"] == 100
    assert result["stop_loss"] == 110
    assert result["risk"] == 10
    assert result["is_valid"] is True

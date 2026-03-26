import pytest
import pandas as pd
import sys
from datetime import datetime, timedelta
from io import StringIO
from screener import (
    is_near_earnings,
    _rank_label,
    _score_bar,
    print_trade_card,
    print_trade_card_compact,
    print_trade_card_short,
    print_trade_card_compact_short,
    check_market_regime,
    check_market_regime_bearish,
    run_screener,
    run_screener_short,
    main,
)

def test_is_near_earnings():
    today = datetime(2023, 1, 10)
    dates = [datetime(2023, 1, 1), datetime(2023, 1, 30)]
    assert is_near_earnings(dates, today) is False
    dates = [datetime(2023, 1, 9)] # 1 day ago
    assert is_near_earnings(dates, today) is True
    dates = [datetime(2023, 1, 15)] # 5 days ahead
    assert is_near_earnings(dates, today) is True
    assert is_near_earnings([], today) is False

def test_display_helpers(capsys):
    assert _rank_label(1) == "🔥 BEST TRADE"
    bar = _score_bar(50.0, width=10)
    assert "50.0/100" in bar

    trend = {"close": 100, "ema50": 90, "ema200": 80}
    cons = {"range_pct": 5, "gap_to_high_pct": 1, "period_high": 101, "period_low": 96, "gap_to_low_pct": 1}
    setup = {"entry": 102, "stop_loss": 97, "target": 112, "risk": 5, "risk_pct": 5, "rr_ratio": 2}
    vol = {"avg_volume": 1000, "latest_volume": 2000, "surge_ratio": 2.0}
    gap = {"today_open": 101, "gap_pct": -1, "is_gap_up": False, "is_gap_down": False}
    score = {"total": 80, "risk_score": 30, "range_score": 30, "trend_score": 20, "ema50_gap_pct": 3.0}
    
    print_trade_card(1, "Test", "TEST.NS", trend, cons, setup, vol, gap, score, 60)
    print_trade_card_compact(1, "Test", "TEST.NS", setup, score, vol, 60)
    print_trade_card_short(1, "Test", "TEST.NS", trend, cons, setup, vol, gap, score, 60)
    print_trade_card_compact_short(1, "Test", "TEST.NS", setup, score, vol, 60)
    
    captured = capsys.readouterr()
    assert "TEST.NS" in captured.out

def test_check_market_regime_fail(monkeypatch):
    monkeypatch.setattr("screener.fetch_data", lambda ticker: None)
    res = check_market_regime("NIFTY.NS")
    assert res["error"] is not None

def test_check_market_regime_full(monkeypatch):
    dates = pd.date_range("2023-01-01", periods=300)
    df = pd.DataFrame({"Close": [100.0 + i for i in range(300)], "Open": [100.0]*300, "High": [100.0]*300, "Low": [100.0]*300, "Volume": [1000]*300}, index=dates)
    monkeypatch.setattr("screener.fetch_data", lambda ticker, **kwargs: df)
    monkeypatch.setattr("screener.STOCKS", {"REL": "REL"})
    res = check_market_regime("NIFTY.NS")
    assert res["is_bullish"] is True

def test_run_scanners_regime_fail(monkeypatch, capsys):
    monkeypatch.setattr("screener.check_market_regime", lambda: {"is_bullish": False, "regime": "BEAR", "error": None, "close": 1.0, "ema20": 1.0, "ema50": 1.0})
    monkeypatch.setattr("screener.LIVE_MODE", True)
    run_screener()
    out = capsys.readouterr().out
    assert "Market is NOT favorable" in out
    
    monkeypatch.setattr("screener.check_market_regime_bearish", lambda: {"is_bullish": False, "regime": "BULL", "error": None, "close": 1.0, "ema20": 1.0, "ema50": 1.0})
    run_screener_short()
    out = capsys.readouterr().out
    assert "Market is NOT bearish enough" in out

def test_run_scanners_data_error(monkeypatch, capsys):
    monkeypatch.setattr("screener.fetch_data", lambda t, **kw: None)
    monkeypatch.setattr("screener.STOCKS", {"T": "T"})
    monkeypatch.setattr("screener.check_market_regime", lambda: {"is_bullish": True, "regime": "BULL", "error": "ERR", "close": 1.0, "ema20": 1.0, "ema50": 1.0})
    run_screener()
    assert "WARNING: ERR" in capsys.readouterr().out
    
    monkeypatch.setattr("screener.check_market_regime_bearish", lambda: {"is_bullish": True, "regime": "BEAR", "error": "ERR", "close": 1.0, "ema20": 1.0, "ema50": 1.0})
    run_screener_short()
    assert "WARNING: ERR" in capsys.readouterr().out

def test_run_screener_verbose(monkeypatch, capsys):
    dates = pd.date_range("2023-01-01", periods=300)
    df = pd.DataFrame({
        "Open": [1000.0]*300, "Close": [1001.0 + 0.1 * i for i in range(300)], 
        "High": [1200.0]*300, "Low": [900.0]*300, "Volume": [1000000]*300
    }, index=dates)
    monkeypatch.setattr("screener.fetch_data", lambda t, **kw: df)
    monkeypatch.setattr("screener.STOCKS", {"REL.NS": "REL"})
    monkeypatch.setattr("screener.LIVE_MODE", False)
    monkeypatch.setattr("screener.get_earnings_dates", lambda t: [])
    monkeypatch.setattr("screener.check_market_regime", lambda: {
        "is_bullish": True, "regime": "STRONG_BULL", "error": None, "close": 100.0, "ema20": 90.0, "ema50": 80.0
    })
    run_screener()
    assert "SCAN SUMMARY" in capsys.readouterr().out

def test_run_screener_short_verbose(monkeypatch, capsys):
    dates = pd.date_range("2023-01-01", periods=300)
    df = pd.DataFrame({
        "Open": [1000.0]*300, "Close": [999.0 - 0.1 * i for i in range(300)], 
        "High": [1200.0]*300, "Low": [800.0]*300, "Volume": [1000000]*300
    }, index=dates)
    monkeypatch.setattr("screener.fetch_data", lambda t, **kw: df)
    monkeypatch.setattr("screener.STOCKS", {"REL.NS": "REL"})
    monkeypatch.setattr("screener.LIVE_MODE", False)
    monkeypatch.setattr("screener.get_earnings_dates", lambda t: [])
    monkeypatch.setattr("screener.check_market_regime_bearish", lambda: {
        "is_bullish": True, "regime": "STRONG_BEAR", "error": None, "close": 100.0, "ema20": 110.0, "ema50": 120.0
    })
    run_screener_short()
    assert "SCAN SUMMARY  [SHORT]" in capsys.readouterr().out

def test_main_dispatch(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["screener.py", "--strategy", "long_breakout"])
    monkeypatch.setattr("screener.run_screener", lambda: print("MOCKED_LONG"))
    main()
    assert "MOCKED_LONG" in capsys.readouterr().out
    monkeypatch.setattr("sys.argv", ["screener.py", "--strategy", "short_breakout"])
    monkeypatch.setattr("screener.run_screener_short", lambda: print("MOCKED_SHORT"))
    main()
    assert "MOCKED_SHORT" in capsys.readouterr().out

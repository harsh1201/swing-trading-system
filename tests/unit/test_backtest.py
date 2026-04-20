import pytest
import pandas as pd
import sys
from collections import defaultdict
from backtest import (
    get_sector,
    _close,
    _close_short,
    scan_candidates,
    scan_candidates_short,
    Trade,
    _period_stats,
    run_backtest,
    run_backtest_short,
    print_year_breakdown,
    print_volume_analysis,
    print_summary,
    print_summary_short,
    print_walkforward_summary,
    fetch_all,
    run_backtest_strategy,
    run_backtest_strategy_short,
    main,
)

def test_get_sector():
    assert get_sector("HDFCBANK.NS") == "BANKING"
    assert get_sector("UNKNOWN.NS") == "OTHER"

def test_close_logic():
    trade: Trade = {
        "ticker": "T", "name": "T", "sector": "S", "df": pd.DataFrame(),
        "entry_price": 100, "effective_entry": 101, "stop_loss": 90, "target": 120,
        "active_sl": 90, "be_hit": False, "nifty_entry_idx": 1, "signal_date": "01-01-2023",
        "qty": 10, "score": 80, "volume_ratio": 2
    }
    closed = []
    _close(trade, 120, "win", 10, closed, "05-01-2023")
    _close_short(trade, 80, "win", 10, closed, "05-01-2023")
    assert len(closed) == 2

def test_period_stats():
    ts = [{"outcome": "win", "pnl_abs": 100, "pnl_pct": 2.0}]
    s = _period_stats(ts)
    assert s["total"] == 1

def test_scan_candidates_full(monkeypatch):
    monkeypatch.setattr("backtest.check_liquidity", lambda df, idx: True)
    monkeypatch.setattr("backtest.check_trend", lambda df, idx: {"close": 100})
    monkeypatch.setattr("backtest.check_trend_short", lambda df, idx: {"close": 100})
    monkeypatch.setattr("backtest.check_consolidation", lambda df, idx: {"period_high": 105, "period_low": 95})
    monkeypatch.setattr("backtest.check_consolidation_short", lambda df, idx: {"period_high": 105, "period_low": 95})
    monkeypatch.setattr("backtest.check_volume", lambda df, idx: {"surge_ratio": 2})
    monkeypatch.setattr("backtest.score_long_breakout", lambda t, c: {"total": 80})
    monkeypatch.setattr("backtest.score_short_breakout", lambda t, c: {"total": 80})
    
    d = pd.date_range("2023-01-01", periods=300)
    df = pd.DataFrame({"Close": [100.0]*300, "High": [100.0]*300, "Low": [100.0]*300, "Open": [100.0]*300, "Volume": [1000]*300}, index=d)
    sdata = {"T": df}
    assert len(scan_candidates(sdata, d[250])) == 1
    assert len(scan_candidates_short(sdata, d[250])) == 1

def test_engines(monkeypatch):
    monkeypatch.setattr("backtest.BACKTEST_DAYS", 10)
    monkeypatch.setattr("backtest.EMA_LONG", 5)
    d = pd.date_range("2023-01-01", periods=50)
    ndf = pd.DataFrame({"Close": [100.0]*50}, index=d)
    # 6 columns: Close, High, Low, Open, Volume, EMA20
    sdf = pd.DataFrame({
        "Close": [100.0]*50, "High": [100.0]*50, "Low": [100.0]*50, "Open": [100.0]*50, "Volume": [1000]*50, "EMA20": [90.0]*50
    }, index=d)
    sdata = {"T": sdf}
    
    monkeypatch.setattr("backtest.get_market_regime", lambda n, i, s: (True, "STRONG_BULL", 50))
    monkeypatch.setattr("backtest.get_market_regime_short", lambda n, i, s: (True, "STRONG_BEAR", 50))
    
    # scan_candidates mock
    def mock_scan(s, d_cur):
        if d_cur == d[40]:
            return [{"ticker": "T", "name": "T", "idx": 40, "df": s["T"], "entry": 105, "stop_loss": 95, "target": 125, "score": 80, "volume_ratio": 2}]
        return []
    monkeypatch.setattr("backtest.scan_candidates", mock_scan)
    
    def mock_scan_short(s, d_cur):
        if d_cur == d[40]:
            return [{"ticker": "T", "name": "T", "idx": 40, "df": s["T"], "entry": 95, "stop_loss": 105, "target": 75, "score": 80, "volume_ratio": 2}]
        return []
    monkeypatch.setattr("backtest.scan_candidates_short", mock_scan_short)
    
    # ── LONG RUN ─────────────────────────────────────────────────────────────
    sdf.iloc[41, 0:6] = [106.0, 107.0, 105.0, 106.0, 1000.0, 91.0]
    sdf.iloc[45, 0:6] = [126.0, 127.0, 125.0, 126.0, 1000.0, 110.0]
    run_backtest(ndf, sdata)
    
    # ── SHORT RUN ────────────────────────────────────────────────────────────
    sdf.iloc[41, 0:6] = [94.0, 95.0, 93.0, 94.0, 1000.0, 109.0]
    sdf.iloc[45, 0:6] = [74.0, 76.0, 73.0, 74.0, 1000.0, 85.0]
    run_backtest_short(ndf, sdata)

def test_summaries(capsys):
    ts = [{"ticker": "T", "signal_date": "01-01-2023", "exit_date": "05-01-2023", "outcome": "win", "pnl_abs": 100, "pnl_pct": 2.0, "bars_held": 5, "volume_ratio": 2.0, "name": "T", "score": 80}]
    print_summary(ts, 1100)
    print_summary_short(ts, 1100)
    print_year_breakdown(ts)
    print_volume_analysis(ts)
    print_walkforward_summary(ts)
    assert "SUMMARY" in capsys.readouterr().out

def test_wrappers(monkeypatch):
    d = pd.date_range("2023-01-01", periods=10)
    df = pd.DataFrame({"Close": [100.0]*10}, index=d)
    monkeypatch.setattr("backtest.fetch_ohlcv", lambda t, d6, refresh=False: df)
    monkeypatch.setattr("backtest.run_backtest", lambda n, s: ([], 100.0, 0.0))
    monkeypatch.setattr("backtest.run_backtest_short", lambda n, s: ([], 100.0, 0.0))
    run_backtest_strategy()
    run_backtest_strategy_short()

def test_main(monkeypatch):
    monkeypatch.setattr("sys.argv", ["backtest.py", "--strategy", "long_breakout"])
    monkeypatch.setattr("backtest.run_backtest_strategy", lambda **kw: None)
    main()

def test_same_bar_protection(monkeypatch):
    # Verify BE and Trail rules are skipped on the entry bar
    monkeypatch.setattr("backtest.BACKTEST_DAYS", 30)
    monkeypatch.setattr("backtest.EMA_LONG", 5)
    
    d = pd.date_range("2023-01-01", periods=30)
    ndf = pd.DataFrame({"Close": [100.0]*30}, index=d)
    sdf = pd.DataFrame({
        "Close": [100.0]*30, "High": [100.0]*30, "Low": [100.0]*30, "Open": [100.0]*30, "Volume": [1000]*30, "EMA20": [90.0]*30
    }, index=d)
    sdata = {"T": sdf}
    monkeypatch.setattr("backtest.get_market_regime", lambda n, i, s: (True, "STRONG_BULL", 50))
    
    # scan candidate mock -> trigger trade on index 15
    def mock_scan(s, d_cur):
        if d_cur == d[15]:
            return [{"ticker": "T", "name": "T", "idx": 15, "df": s["T"], "entry": 105.0, "stop_loss": 95.0, "target": 125.0, "score": 80, "volume_ratio": 2}]
        return []
    monkeypatch.setattr("backtest.scan_candidates", mock_scan)
    
    # On scan bar (idx=15)
    sdf.iloc[15, 0:6] = [100.0, 102.0, 99.0, 100.0, 1000.0, 90.0]

    # ENTRY BAR (idx=16): Next bar must close above entry.
    # We spike High to 121 to conditionally trigger BE rule: (high >= entry + 1.5R = 120)
    # But because it's the entry bar, BE manager should skip it.
    sdf.iloc[16, 0:6] = [106.0, 121.0, 105.0, 106.0, 1000.0, 92.0]
    
    # NEXT BAR (idx=17): Price drops to 100 which is > 95 SL but < 105 BE level.
    # If BE was hit on idx=16, this would incorrectly be a breakeven exit.
    sdf.iloc[17, 0:6] = [100.0, 100.0, 100.0, 100.0, 1000.0, 93.0]

    # TARGET BAR (idx=18): Price hits target
    sdf.iloc[18, 0:6] = [130.0, 131.0, 125.0, 126.0, 1000.0, 110.0]
    
    closed_trades, eq, max_dd = run_backtest(ndf, sdata)
    assert len(closed_trades) == 1
    assert closed_trades[0]["outcome"] == "win"

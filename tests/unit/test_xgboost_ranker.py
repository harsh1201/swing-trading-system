"""
Unit tests for strategies/xgboost_ranker.py — the pure prediction/plumbing
paths that don't require a trained model on disk. These lock the contracts the
screener's quality gate depends on (clamping, the None-model fallback, feature
validation).
"""
import numpy as np
import pandas as pd
import pytest

from strategies.xgboost_ranker import (
    predict,
    _validate_features,
    _model_path,
    load_model,
    FEATURES,
)
from config.settings import XGB_MIN_R, XGB_MAX_R


def _feature_row() -> dict:
    """A complete feature dict (values irrelevant — the fake models ignore them)."""
    return {name: 0.0 for name in FEATURES}


# ── predict(): None-model fallback ────────────────────────────────────────────
def test_predict_none_model_returns_zero_regression():
    assert predict(None, _feature_row(), mode="regression") == 0.0


def test_predict_none_model_returns_zero_classification():
    # RED FLAG: a missing/failed model yields 0.0, which the screener's
    # passes_quality() treats as "ML missing" → the gate silently degrades to
    # score-only. This test documents the 0.0 contract that makes that happen.
    assert predict(None, _feature_row(), mode="classification") == 0.0


# ── predict(): classification returns P(win) ─────────────────────────────────
def test_predict_classification_returns_win_probability():
    class _FakeClf:
        def predict_proba(self, X):
            assert list(X.columns) == FEATURES   # correct column order
            return np.array([[0.28, 0.72]])       # P(win) = 0.72
    assert predict(_FakeClf(), _feature_row(), mode="classification") == 0.72


# ── predict(): regression clamps to [MIN_R, MAX_R] ───────────────────────────
def test_predict_regression_clamps_high():
    class _FakeReg:
        def predict(self, X):
            return np.array([XGB_MAX_R + 5.0])
    assert predict(_FakeReg(), _feature_row(), mode="regression") == XGB_MAX_R


def test_predict_regression_clamps_low():
    class _FakeReg:
        def predict(self, X):
            return np.array([XGB_MIN_R - 5.0])
    assert predict(_FakeReg(), _feature_row(), mode="regression") == XGB_MIN_R


def test_predict_regression_passes_through_in_range():
    mid = (XGB_MIN_R + XGB_MAX_R) / 2

    class _FakeReg:
        def predict(self, X):
            return np.array([mid])
    assert predict(_FakeReg(), _feature_row(), mode="regression") == mid


# ── _validate_features() ─────────────────────────────────────────────────────
def test_validate_features_ok():
    df = pd.DataFrame([_feature_row()])
    assert _validate_features(df) is None   # no raise


def test_validate_features_missing_raises():
    df = pd.DataFrame([{"coil_range_pct": 1.0}])   # missing the rest
    with pytest.raises(ValueError, match="Missing feature columns"):
        _validate_features(df)


# ── _model_path() naming ─────────────────────────────────────────────────────
def test_model_path_classification_vs_regression():
    clf = _model_path("long", "classification")
    reg = _model_path("short", "regression")
    assert clf.name == "xgb_classifier_long.json"
    assert reg.name == "xgb_target_short.json"


# ── load_model() missing file ────────────────────────────────────────────────
def test_load_model_missing_returns_none(monkeypatch, tmp_path):
    import strategies.xgboost_ranker as ranker
    monkeypatch.setattr(ranker, "MODEL_DIR", tmp_path)
    assert ranker.load_model("long", "classification") is None


# ── prepare_training_data(): chronological ordering ──────────────────────────
def _training_csv(tmp_path, dates, outcomes, r_multiples):
    """Write a minimal training CSV with the real column layout."""
    rows = []
    for d, o, r in zip(dates, outcomes, r_multiples):
        row = {name: 1.0 for name in FEATURES}
        row.update(signal_date=d, outcome=o, r_multiple=r, ticker="X.NS")
        rows.append(row)
    path = tmp_path / "train.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return str(path)


def test_prepare_training_data_sorts_chronologically(tmp_path):
    """The split downstream is a time-series split, so an out-of-order CSV must
    be reordered — otherwise later trades leak into the training slice."""
    from strategies.xgboost_ranker import prepare_training_data

    csv = _training_csv(
        tmp_path,
        dates=["05-06-2024", "01-01-2023", "03-03-2024"],   # DD-MM-YYYY, shuffled
        outcomes=["win", "loss", "win"],
        r_multiples=[2.0, 1.0, 3.0],
    )
    df = prepare_training_data(csv, "long", "classification")
    assert list(df["signal_date"]) == ["01-01-2023", "03-03-2024", "05-06-2024"]


def test_regression_training_accepts_continuous_targets(tmp_path, monkeypatch):
    """Regression previously crashed applying binary class weights to continuous
    r_multiple. Training must run and produce a model."""
    import strategies.xgboost_ranker as ranker

    n = 60
    csv = _training_csv(
        tmp_path,
        dates=[f"{(i % 28) + 1:02d}-01-2024" for i in range(n)],
        outcomes=["win"] * n,
        r_multiples=[1.0 + (i % 5) * 0.5 for i in range(n)],
    )
    monkeypatch.setattr(ranker, "MODEL_DIR", tmp_path)
    model = ranker.train_model(csv, "long", "regression", force_retrain=True)
    assert model is not None
    assert (tmp_path / "xgb_target_long.json").exists()


def test_test_slice_is_disjoint_from_early_stopping_val_slice():
    """The reported metrics must come from data early stopping never saw."""
    n = 100
    train_idx, val_idx = int(n * 0.6), int(n * 0.8)
    train, val, test = range(train_idx), range(train_idx, val_idx), range(val_idx, n)
    assert not set(test) & set(val)
    assert not set(test) & set(train)
    assert len(test) > 0


# ── Volatility-regime filter ─────────────────────────────────────────────────
def _ohlc(n=300, atr_spike=False):
    """Synthetic OHLCV with optional late volatility spike."""
    import strategies.long_breakout as lb
    close = pd.Series(np.linspace(100, 140, n))
    span = pd.Series([1.0] * n)
    if atr_spike:
        span.iloc[-30:] = 12.0          # recent bars far more volatile
    df = pd.DataFrame({
        "Close": close, "Open": close,
        "High": close + span, "Low": close - span,
        "Volume": 1_000_000,
    })
    return lb.add_indicators(df)


def test_vol_regime_flags_turbulence():
    """A late volatility spike must read as turbulent (>1), calm data as ~1."""
    import strategies.long_breakout as lb
    calm = lb.calculate_vol_regime(_ohlc(), 299)
    spiked = lb.calculate_vol_regime(_ohlc(atr_spike=True), 299)
    assert spiked > calm
    assert spiked > 1.5, f"spike should read well above its own median, got {spiked}"


def test_vol_regime_neutral_without_history():
    """Too little history must return neutral 1.0, never reject blindly."""
    import strategies.long_breakout as lb
    assert lb.calculate_vol_regime(_ohlc(), 50) == 1.0


def test_vol_regime_gate_is_long_only(monkeypatch):
    """Shorts show no effect (p=0.33) and lose return when gated — the filter
    must not apply to them even when enabled."""
    import strategies.long_breakout as lb
    df = _ohlc(atr_spike=True)
    monkeypatch.setattr(lb, "USE_VOL_REGIME_FILTER", True)
    monkeypatch.setattr(lb, "MAX_VOL_REGIME", 0.0)      # reject everything gated
    assert lb.passes_vol_regime(df, 299, "long") is False
    assert lb.passes_vol_regime(df, 299, "short") is True


def test_vol_regime_gate_disabled_passes_everything(monkeypatch):
    import strategies.long_breakout as lb
    monkeypatch.setattr(lb, "USE_VOL_REGIME_FILTER", False)
    monkeypatch.setattr(lb, "MAX_VOL_REGIME", 0.0)
    assert lb.passes_vol_regime(_ohlc(atr_spike=True), 299, "long") is True

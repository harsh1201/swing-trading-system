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

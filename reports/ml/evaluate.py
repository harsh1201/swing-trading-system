"""Walk-forward evaluation of feature sets, with a permutation test.

Pooled out-of-fold predictions from an expanding window, so every prediction is
made by a model that never saw that row or anything after it.
"""
import sys
import numpy as np
import pandas as pd
import xgboost as xgb
import warnings
warnings.filterwarnings("ignore")
from sklearn.utils import class_weight
from sklearn.metrics import roc_auc_score
from scipy.stats import spearmanr

sys.path.insert(0, ".")
from config.settings import XGB_FEATURE_NAMES
sys.path.insert(0, "/private/tmp/claude-501/-Users-manmadeanyme-Documents-Work-swing-trading-system/11ae5db3-420c-4579-805b-047a31a3ea93/scratchpad")
from candidate_features import CANDIDATES

BASE = list(XGB_FEATURE_NAMES)
RNG = np.random.default_rng(0)
FOLDS = 5


def _prep(strategy):
    d = pd.read_csv(f"reports/ml/training_data_{strategy}_enriched.csv")
    d = d[d.outcome.isin(["win", "loss", "trail"])]
    d = d.dropna(subset=BASE + CANDIDATES + ["r_multiple"])
    d["_dt"] = pd.to_datetime(d.signal_date, dayfirst=True, format="mixed")
    return d.sort_values("_dt").reset_index(drop=True)


def _oof(d, feats, task):
    X = d[feats]
    y = (d.outcome == "win").astype(int).values if task == "clf" else d.r_multiple.values
    n = len(d); size = n // (FOLDS + 1)
    P, Y = [], []
    for k in range(1, FOLDS + 1):
        a, b = k * size, (k + 1) * size
        if task == "clf":
            if len(np.unique(y[:a])) < 2:
                continue
            w = class_weight.compute_class_weight("balanced", classes=np.array([0, 1]), y=y[:a])
            m = xgb.XGBClassifier(n_estimators=200, learning_rate=0.05, max_depth=3,
                min_child_weight=5, subsample=0.8, colsample_bytree=0.7, reg_lambda=2.0,
                tree_method="hist", random_state=42, verbosity=0)
            m.fit(X[:a], y[:a], sample_weight=np.where(y[:a] == 1, w[1], w[0]), verbose=False)
            P.append(m.predict_proba(X[a:b])[:, 1])
        else:
            m = xgb.XGBRegressor(n_estimators=200, learning_rate=0.05, max_depth=3,
                min_child_weight=5, subsample=0.8, colsample_bytree=0.7, reg_lambda=2.0,
                tree_method="hist", random_state=42, verbosity=0)
            m.fit(X[:a], y[:a], verbose=False)
            P.append(m.predict(X[a:b]))
        Y.append(y[a:b])
    return np.concatenate(P), np.concatenate(Y)


def report(strategy):
    d = _prep(strategy)
    print(f"\n{'='*74}\n{strategy.upper()}  n={len(d)}  "
          f"{d._dt.min().date()} -> {d._dt.max().date()}\n{'='*74}")

    sets = {
        "baseline (10 geometry)": BASE,
        "candidates only (10 context)": CANDIDATES,
        "baseline + candidates (20)": BASE + CANDIDATES,
    }

    print(f"\n  CLASSIFIER — pooled out-of-fold AUC (2000-draw permutation test)")
    print(f"  {'feature set':<30} {'AUC':>6} {'null 95%':>16} {'p':>7}  verdict")
    print(f"  {'-'*30} {'-'*6} {'-'*16} {'-'*7}  {'-'*8}")
    for name, feats in sets.items():
        p, y = _oof(d, feats, "clf")
        auc = roc_auc_score(y, p)
        null = np.array([roc_auc_score(y, RNG.permutation(p)) for _ in range(2000)])
        pv = (null >= auc).mean()
        lo, hi = np.percentile(null, [2.5, 97.5])
        print(f"  {name:<30} {auc:>6.3f} [{lo:.3f}, {hi:.3f}] {pv:>7.3f}  "
              f"{'SIGNIFICANT' if pv < 0.05 else 'chance'}")

    print(f"\n  REGRESSOR (MFE) — rank correlation + top/bottom-half lift")
    print(f"  {'feature set':<30} {'spearman':>9} {'p':>7} {'lift':>8}")
    print(f"  {'-'*30} {'-'*9} {'-'*7} {'-'*8}")
    for name, feats in sets.items():
        p, y = _oof(d, feats, "reg")
        rho, pv = spearmanr(p, y)
        lift = y[p >= np.median(p)].mean() - y[p < np.median(p)].mean()
        print(f"  {name:<30} {rho:>+9.3f} {pv:>7.3f} {lift:>+7.2f}R")


for s in ("long", "short"):
    report(s)

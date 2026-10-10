"""
strategies/xgboost_ranker.py — XGBoost entry ranker & target predictor.

Two modes:
  classification  Predict win-probability (0–100%) for ranking setups.
  regression      Predict expected R-multiple for dynamic target sizing.

Supports both Long and Short swing trade strategies.

CLI Usage
---------
    # Train specific model
    python -m strategies.xgboost_ranker --train reports/ml/training_data_long.csv --strategy long --mode classification
    python -m strategies.xgboost_ranker --train reports/ml/training_data_short.csv --strategy short --mode classification

    # Train all 4 models (long/short classification & regression) automatically
    python -m strategies.xgboost_ranker --train-all --force

    # Feature importance
    python -m strategies.xgboost_ranker --importance --strategy long --mode classification
    python -m strategies.xgboost_ranker --importance --strategy all

    # Predict
    python -m strategies.xgboost_ranker --predict <feature_csv> --strategy long --mode classification
"""

from __future__ import annotations

import argparse
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)

from config.settings import (
    XGB_FEATURE_NAMES,
    XGB_MAX_R,
    XGB_MIN_R,
)

FEATURES = list(XGB_FEATURE_NAMES)
MODEL_DIR = Path(__file__).parent.parent / "models"


def _patch_xgboost_compatibility() -> None:
    """Ensure XGBRegressor and XGBClassifier have _estimator_type defined for scikit-learn 1.6+ compatibility."""
    try:
        import xgboost as xgb
        if not hasattr(xgb.XGBRegressor, "_estimator_type") or xgb.XGBRegressor._estimator_type is None:
            xgb.XGBRegressor._estimator_type = "regressor"
        if not hasattr(xgb.XGBClassifier, "_estimator_type") or xgb.XGBClassifier._estimator_type is None:
            xgb.XGBClassifier._estimator_type = "classifier"
    except ImportError:
        pass


_patch_xgboost_compatibility()


def _model_path(strategy: str = "long", mode: str = "regression") -> Path:
    suffix = "classifier" if mode == "classification" else "target"
    return MODEL_DIR / f"xgb_{suffix}_{strategy}.json"


def _validate_features(df: pd.DataFrame) -> None:
    missing = [c for c in FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")


def load_model(strategy: str = "long", mode: str = "regression"):
    """Load a trained XGBoost model from disk. Returns None if missing."""
    path = _model_path(strategy, mode)
    if not path.exists():
        return None

    try:
        import xgboost as xgb
        _patch_xgboost_compatibility()

        klass = xgb.XGBClassifier if mode == "classification" else xgb.XGBRegressor
        model = klass()
        model._estimator_type = "classifier" if mode == "classification" else "regressor"
        model.load_model(str(path))
        return model
    except Exception as e:
        print(f"  [WARN] Failed to load XGBoost model from {path}: {e}")
        return None


def predict(model, features: dict[str, float], mode: str = "regression") -> float:
    """
    Predict for a single candidate.
      regression:      clamped R-multiple  [XGB_MIN_R, XGB_MAX_R]
      classification:  win probability     [0.0, 1.0]
    """
    if model is None:
        return 0.0

    row = pd.DataFrame([features])[FEATURES]
    if mode == "classification":
        prob = float(model.predict_proba(row)[0, 1])  # probability of class 1 (win)
        return round(prob, 4)
    pred = float(model.predict(row)[0])
    return float(np.clip(pred, XGB_MIN_R, XGB_MAX_R))


def prepare_training_data(
    csv_path: str,
    strategy: str = "long",
    mode: str = "regression",
) -> pd.DataFrame:
    """Load & clean the training CSV."""
    df = pd.read_csv(csv_path)

    # Drop breakeven trades (noisy)
    if "outcome" in df.columns:
        before = len(df)
        df = df[df["outcome"].isin(["win", "loss", "trail"])]
        if len(df) < before:
            print(f"  Dropped {before - len(df)} breakeven trades")

    missing_features = [c for c in FEATURES if c not in df.columns]
    if missing_features:
        raise ValueError(f"CSV missing feature columns: {missing_features}")

    df = df.dropna(subset=FEATURES)

    # Chronological order is load-bearing: the train/val/test split below is a
    # time-series split, and an unsorted CSV would leak the future into training.
    if "signal_date" in df.columns:
        df = df.assign(
            _dt=pd.to_datetime(df["signal_date"], dayfirst=True, format="mixed")
        ).sort_values("_dt").drop(columns="_dt")

    if mode == "classification":
        # Binary label: 1 = hit target (win), 0 = everything else
        df["label"] = (df["outcome"] == "win").astype(int)
        print(f"  Label distribution: wins={df['label'].sum():.0f}  "
              f"others={(1-df['label']).sum():.0f}")
        df = df.dropna(subset=["label"])

        from sklearn.utils import class_weight
        classes = np.array([0, 1])
        weights = class_weight.compute_class_weight("balanced", classes=classes, y=df["label"])
        print(f"  Class weights: others={weights[0]:.2f}, wins={weights[1]:.2f}")
    else:
        df = df.dropna(subset=["r_multiple"])
        df = df[df["r_multiple"] > 0.0]
        df["r_multiple"] = df["r_multiple"].clip(upper=XGB_MAX_R)

    print(f"  Training samples: {len(df)}")
    return df


def train_model(
    csv_path: str | None = None,
    strategy: str = "long",
    mode: str = "regression",
    force_retrain: bool = False,
) -> object | None:
    """Train an XGBoost model on historical trade data."""
    if csv_path is None:
        csv_path = f"reports/ml/training_data_{strategy}.csv"

    path = _model_path(strategy, mode)
    if path.exists() and not force_retrain:
        print(f"  Model already exists at {path}. Use --force to retrain.")
        return load_model(strategy, mode)

    if not os.path.exists(csv_path):
        print(f"  [ERROR] Training data file not found: {csv_path}")
        print(f"  Export training data first with: python backtest.py --strategy {strategy}_breakout --export-ml-data")
        return None

    df = prepare_training_data(csv_path, strategy, mode)

    if len(df) < 50:
        print(f"  [WARN] Only {len(df)} samples — insufficient data for reliable training.")
        if len(df) == 0:
            return None
    elif len(df) < 200:
        print(f"  [WARN] Only {len(df)} samples — XGBoost needs >= 500 for reliable results.")

    # Keep the DataFrame (not .values) so the booster records real feature names —
    # otherwise importance prints f0..f9 and inference passes named columns to an
    # unnamed model.
    X = df[FEATURES]
    y = df["label"].values if mode == "classification" else df["r_multiple"].values

    # Three-way chronological split. Early stopping consumes `val`, so `test` stays
    # untouched and the reported metrics are honest out-of-sample numbers.
    train_idx = int(len(df) * 0.6)
    val_idx = int(len(df) * 0.8)
    X_train, y_train = X.iloc[:train_idx], y[:train_idx]
    X_val, y_val = X.iloc[train_idx:val_idx], y[train_idx:val_idx]
    X_test, y_test = X.iloc[val_idx:], y[val_idx:]

    print(f"  Train: {len(X_train)}  Val: {len(X_val)}  Test: {len(X_test)} samples")

    try:
        import xgboost as xgb
        _patch_xgboost_compatibility()
    except ImportError:
        print("  [ERROR] xgboost not installed. Run: pip install xgboost")
        return None

    if mode == "classification":
        from sklearn.utils import class_weight
        if len(np.unique(y_train)) < 2:
            sample_weights = None
        else:
            weights = class_weight.compute_class_weight(
                "balanced", classes=np.array([0, 1]), y=y_train
            )
            sample_weights = np.where(y_train == 1, weights[1], weights[0])
    else:
        sample_weights = None  # class weights are meaningless for continuous R

    if mode == "classification":
        model = xgb.XGBClassifier(
            n_estimators=500,
            learning_rate=0.03,
            max_depth=4,
            min_child_weight=2,
            subsample=0.8,
            colsample_bytree=0.7,
            gamma=0.5,
            reg_lambda=1.0,
            reg_alpha=0.0,
            eval_metric="logloss",
            early_stopping_rounds=50,
            tree_method="hist",
            random_state=42,
            verbosity=0,
        )
        model._estimator_type = "classifier"
        eval_metric_name = "LogLoss"
    else:
        model = xgb.XGBRegressor(
            n_estimators=500,
            learning_rate=0.03,
            max_depth=6,
            min_child_weight=2,
            subsample=0.8,
            colsample_bytree=0.7,
            gamma=0.0,
            reg_lambda=1.0,
            reg_alpha=0.0,
            eval_metric="mae",
            early_stopping_rounds=50,
            tree_method="hist",
            random_state=42,
            verbosity=0,
        )
        model._estimator_type = "regressor"
        eval_metric_name = "MAE"

    model._estimator_type = "classifier" if mode == "classification" else "regressor"

    model.fit(
        X_train, y_train,
        sample_weight=sample_weights,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    # Evaluate out-of-sample
    from sklearn.metrics import (
        accuracy_score, roc_auc_score, confusion_matrix,
        mean_absolute_error, mean_squared_error, r2_score, f1_score
    )

    y_pred = model.predict(X_test)
    if mode == "classification":
        acc = accuracy_score(y_test, y_pred)
        try:
            auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
        except Exception:
            auc = 0.5
        cm = confusion_matrix(y_test, y_pred)
        if cm.shape == (2, 2):
            tn, fp, fn, tp = cm.ravel()
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        else:
            tp, fp, fn, tn = 0, 0, 0, 0
            precision, recall = 0.0, 0.0
        f1 = f1_score(y_test, y_pred, zero_division=0)
        print(f"  Test Accuracy : {acc:.1%}")
        print(f"  Test AUC-ROC  : {auc:.3f}")
        print(f"  Precision     : {precision:.1%}  ({tp}/{tp+fp})")
        print(f"  Recall        : {recall:.1%}  ({tp}/{tp+fn})")
        print(f"  F1 Score      : {f1:.3f}")
    else:
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred) if len(y_test) > 1 else 0.0
        print(f"  Test {eval_metric_name} : {mae:.3f}R")
        print(f"  Test RMSE     : {rmse:.3f}R")
        print(f"  Test R2 Score : {r2:.3f}")

    print(f"  Best iteration: {model.best_iteration}")

    path.parent.mkdir(parents=True, exist_ok=True)
    
    if not hasattr(model, "_estimator_type") or model._estimator_type is None:
        model._estimator_type = "regressor" if mode == "regression" else "classifier"
        
    model.save_model(str(path))
    print(f"  [+] Model saved: {path}")

    return model


def train_all_models(
    data_dir: str = "reports/ml",
    force_retrain: bool = False,
) -> dict[str, object | None]:
    """Train all 4 models: long/short classification & regression."""
    results = {}
    combos = [
        ("long", "classification"),
        ("long", "regression"),
        ("short", "classification"),
        ("short", "regression"),
    ]

    print("\n" + "=" * 60)
    print(" TRAINING ALL SWING TRADE XGBOOST MODELS (LONG & SHORT)")
    print("=" * 60)

    for strategy, mode in combos:
        csv_path = os.path.join(data_dir, f"training_data_{strategy}.csv")
        print(f"\n--- Training {strategy.upper()} [{mode.upper()}] ---")
        print(f"  Dataset: {csv_path}")
        model = train_model(
            csv_path=csv_path,
            strategy=strategy,
            mode=mode,
            force_retrain=force_retrain,
        )
        results[f"{strategy}_{mode}"] = model

    print("\n" + "=" * 60)
    print(" TRAINING COMPLETE SUMMARY")
    print("=" * 60)
    for key, model in results.items():
        status = "SUCCESS" if model is not None else "FAILED / SKIPPED"
        print(f"  {key:<25} : {status}")

    return results


def show_importance(strategy: str = "long", mode: str = "regression") -> None:
    """Display feature importance from the trained model."""
    strategies = ["long", "short"] if strategy == "all" else [strategy]
    modes = ["classification", "regression"] if mode == "all" else [mode]

    for strat in strategies:
        for m in modes:
            model = load_model(strat, m)
            if model is None:
                print(f"  No trained model found for {m} ({strat}).")
                continue

            importance = model.get_booster().get_score(importance_type="gain")
            # Map legacy f0..f9 indices to real feature names if needed
            mapped_importance = {}
            for feat, gain in importance.items():
                if feat.startswith("f") and feat[1:].isdigit() and int(feat[1:]) < len(FEATURES):
                    feat_name = FEATURES[int(feat[1:])]
                else:
                    feat_name = feat
                mapped_importance[feat_name] = gain
            importance = mapped_importance

            total = sum(importance.values()) or 1.0

            label = "Classifier" if m == "classification" else "Regressor"
            print(f"\n  Feature Importance ({label} — {strat.upper()})")
            print(f"  {'Feature':<22} {'Gain':>8}  {'Share':>6}")
            print(f"  {'-'*22} {'-'*8}  {'-'*6}")
            for feat, gain in sorted(importance.items(), key=lambda x: x[1], reverse=True):
                pct = gain / total * 100
                print(f"  {feat:<22} {gain:>8.1f}  {pct:>5.1f}%")

            if hasattr(model, "feature_importances_") and hasattr(model, "feature_names_in_"):
                print(f"\n  Built-in Importance ({label} — {strat.upper()})")
                print(f"  {'Feature':<22} {'Importance':>10}")
                print(f"  {'-'*22} {'-'*10}")
                for feat, gain in sorted(
                    zip(model.feature_names_in_, model.feature_importances_),
                    key=lambda x: x[1],
                    reverse=True,
                ):
                    print(f"  {feat:<22} {gain:>10.4f}")


def predict_from_csv(csv_path: str, strategy: str = "long", mode: str = "regression") -> pd.DataFrame | None:
    """Score candidates from a CSV and print predictions."""
    model = load_model(strategy, mode)
    if model is None:
        print(f"  No trained model found for {mode} ({strategy}). Train first with --train")
        return None

    df = pd.read_csv(csv_path)
    _validate_features(df)
    df = df.dropna(subset=FEATURES)
    X = df[FEATURES]

    if mode == "classification":
        preds = model.predict_proba(X)[:, 1]
        col_name = "win_prob"
        header = "Win Prob"
        fmt = "{:>10.1%}"
    else:
        preds = np.clip(model.predict(X), XGB_MIN_R, XGB_MAX_R)
        col_name = "predicted_r"
        header = "Predicted R"
        fmt = "{:>10.2f}R"

    result = df.copy()
    result[col_name] = [round(float(p), 4) for p in preds]

    ticker_col = "ticker" if "ticker" in result.columns else "symbol"
    print(f"\n  Predictions ({len(result)} candidates — {strategy.upper()} {mode.upper()})")
    print(f"  {'Ticker':<16} {header:>12}")
    print(f"  {'-'*16} {'-'*12}")
    for _, row in result.iterrows():
        ticker = row.get(ticker_col, "?")
        val = fmt.format(row[col_name])
        print(f"  {ticker:<16} {val}")

    out_path = csv_path.replace(".csv", f"_{col_name}.csv")
    result.to_csv(out_path, index=False)
    print(f"\n  Saved: {out_path}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="XGBoost Entry Ranker & Target Predictor for Swing Trading (Long & Short)"
    )
    parser.add_argument(
        "--train", nargs="?", const="", default=None, metavar="CSV",
        help="Path to training data CSV (or omit path to use default reports/ml/training_data_{strategy}.csv)",
    )
    parser.add_argument(
        "--train-all", action="store_true",
        help="Train all 4 models: long and short, classification and regression",
    )
    parser.add_argument(
        "--strategy", choices=["long", "short", "all"], default="long",
        help="Strategy side (default: long)",
    )
    parser.add_argument(
        "--mode", choices=["regression", "classification", "all"], default="classification",
        help="Model mode (default: classification)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Force retrain even if model exists",
    )
    parser.add_argument(
        "--importance", action="store_true",
        help="Show feature importance from trained model",
    )
    parser.add_argument(
        "--predict", metavar="CSV",
        help="Score candidates from a feature CSV",
    )

    args = parser.parse_args()

    if args.train_all:
        train_all_models(force_retrain=args.force)
    elif args.importance:
        show_importance(args.strategy, args.mode)
    elif args.predict:
        predict_from_csv(args.predict, args.strategy, args.mode)
    elif args.train is not None:
        strategies = ["long", "short"] if args.strategy == "all" else [args.strategy]
        modes = ["classification", "regression"] if args.mode == "all" else [args.mode]
        for strat in strategies:
            for m in modes:
                csv_path = args.train if args.train else f"reports/ml/training_data_{strat}.csv"
                train_model(csv_path, strat, m, force_retrain=args.force)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

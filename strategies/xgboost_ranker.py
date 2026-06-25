"""
strategies/xgboost_ranker.py — XGBoost entry ranker & target predictor.

Two modes:
  classification  Predict win-probability (0–100%) for ranking setups.
  regression      Predict expected R-multiple for dynamic target sizing.

CLI Usage
---------
    python -m strategies.xgboost_ranker --train <csv> --mode classification --strategy long
    python -m strategies.xgboost_ranker --importance --strategy long
    python -m strategies.xgboost_ranker --predict <feature_csv> --strategy long
"""

from __future__ import annotations

import argparse
import os
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


def _model_path(strategy: str = "long", mode: str = "regression") -> Path:
    suffix = "classifier" if mode == "classification" else "target"
    return MODEL_DIR / f"xgb_{suffix}_{strategy}.json"


def _validate_features(df: pd.DataFrame) -> None:
    missing = [c for c in FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")


def load_model(strategy: str = "long", mode: str = "regression"):
    """Load a trained XGBoost model from disk.  Returns None if missing."""
    path = _model_path(strategy, mode)
    if not path.exists():
        return None

    try:
        import xgboost as xgb

        klass = xgb.XGBClassifier if mode == "classification" else xgb.XGBRegressor
        model = klass()
        model.load_model(str(path))
        return model
    except Exception as e:
        print(f"  [WARN] Failed to load XGBoost model: {e}")
        return None


def predict(model, features: dict[str, float], mode: str = "regression") -> float:
    """
    Predict for a single candidate.
      regression:      clamped R-multiple  [XGB_MIN_R, XGB_MAX_R]
      classification:  win probability  [0.0, 1.0]
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
    csv_path: str,
    strategy: str = "long",
    mode: str = "regression",
    force_retrain: bool = False,
) -> object | None:
    """Train an XGBoost model on historical trade data."""
    path = _model_path(strategy, mode)
    if path.exists() and not force_retrain:
        print(f"  Model already exists at {path}. Use --force to retrain.")
        return load_model(strategy, mode)

    df = prepare_training_data(csv_path, strategy, mode)

    if len(df) < 200:
        print(f"  [WARN] Only {len(df)} samples — XGBoost needs >= 500 for reliable results.")

    X = df[FEATURES].values
    y = df["label"].values if mode == "classification" else df["r_multiple"].values

    split_idx = int(len(df) * 0.8)
    X_train, y_train = X[:split_idx], y[:split_idx]
    X_test, y_test = X[split_idx:], y[split_idx:]

    print(f"  Train: {len(X_train)} samples, Test: {len(X_test)} samples")

    try:
        import xgboost as xgb
    except ImportError:
        print("  [ERROR] xgboost not installed. Run: pip install xgboost")
        return None

    from sklearn.utils import class_weight
    classes = np.array([0, 1])
    weights = class_weight.compute_class_weight("balanced", classes=classes, y=y_train)
    sample_weights = np.where(y_train == 1, weights[1], weights[0])

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
        eval_metric_name = "MAE"

    model.fit(
        X_train, y_train,
        sample_weight=sample_weights,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    # Evaluate
    from sklearn.metrics import (
        accuracy_score, roc_auc_score, confusion_matrix,
        mean_absolute_error, mean_squared_error,
    )

    y_pred = model.predict(X_test)
    if mode == "classification":
        acc = accuracy_score(y_test, y_pred)
        auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
        tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        print(f"  Test Accuracy : {acc:.1%}")
        print(f"  Test AUC-ROC  : {auc:.3f}")
        print(f"  Precision     : {precision:.1%}  ({tp}/{tp+fp})")
        print(f"  Recall        : {recall:.1%}  ({tp}/{tp+fn})")
    else:
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        print(f"  Test {eval_metric_name} : {mae:.3f}R")
        print(f"  Test RMSE: {rmse:.3f}R")

    print(f"  Best iteration: {model.best_iteration}")

    path.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(path))
    print(f"  Model saved: {path}")

    return model


def show_importance(strategy: str = "long", mode: str = "regression") -> None:
    """Display feature importance from the trained model."""
    model = load_model(strategy, mode)
    if model is None:
        print(f"  No trained model found for {mode} ({strategy}).")
        return

    importance = model.get_booster().get_score(importance_type="gain")
    total = sum(importance.values()) or 1.0

    label = "Classifier" if mode == "classification" else "Regressor"
    print(f"\n  Feature Importance ({label} — {strategy})")
    print(f"  {'Feature':<22} {'Gain':>8}  {'Share':>6}")
    print(f"  {'-'*22} {'-'*8}  {'-'*6}")
    for feat, gain in sorted(importance.items(), key=lambda x: x[1], reverse=True):
        pct = gain / total * 100
        print(f"  {feat:<22} {gain:>8.1f}  {pct:>5.1f}%")

    if hasattr(model, "feature_importances_") and hasattr(model, "feature_names_in_"):
        print(f"\n  Built-in Importance ({label} — {strategy})")
        print(f"  {'Feature':<22} {'Gain':>8}")
        print(f"  {'-'*22} {'-'*8}")
        for feat, gain in sorted(
            zip(model.feature_names_in_, model.feature_importances_),
            key=lambda x: x[1],
            reverse=True,
        ):
            print(f"  {feat:<22} {gain:>8.4f}")


def predict_from_csv(csv_path: str, strategy: str = "long", mode: str = "regression") -> None:
    """Score candidates from a CSV and print predictions."""
    model = load_model(strategy, mode)
    if model is None:
        print(f"  No trained model found for {mode} ({strategy}). Train first with --train")
        return

    df = pd.read_csv(csv_path)
    _validate_features(df)
    df = df.dropna(subset=FEATURES)
    X = df[FEATURES].values

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
    result[col_name] = [round(p, 4) for p in preds]

    ticker_col = "ticker" if "ticker" in result.columns else "symbol"
    print(f"\n  Predictions ({len(result)} candidates)")
    print(f"  {'Ticker':<16} {header:>12}")
    print(f"  {'-'*16} {'-'*12}")
    for _, row in result.iterrows():
        ticker = row.get(ticker_col, "?")
        val = fmt.format(row[col_name])
        print(f"  {ticker:<16} {val}")

    out_path = csv_path.replace(".csv", f"_{col_name}.csv")
    result.to_csv(out_path, index=False)
    print(f"\n  Saved: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="XGBoost Entry Ranker & Target Predictor for Swing Trading"
    )
    parser.add_argument(
        "--train", metavar="CSV",
        help="Path to training data CSV (from backtest --export-ml-data)",
    )
    parser.add_argument(
        "--strategy", choices=["long", "short"], default="long",
        help="Strategy side (default: long)",
    )
    parser.add_argument(
        "--mode", choices=["regression", "classification"], default="regression",
        help="Model mode (default: regression)",
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

    if args.importance:
        show_importance(args.strategy, args.mode)
    elif args.predict:
        predict_from_csv(args.predict, args.strategy, args.mode)
    elif args.train:
        train_model(args.train, args.strategy, args.mode, force_retrain=args.force)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

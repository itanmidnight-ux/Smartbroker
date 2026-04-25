from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.dataset import build_training_frame
from ml.model_registry import save_model

FEATURES = ["ret_1", "ret_3", "ret_10", "vol_10", "ma_spread"]
REGIMES = ["trending", "ranging", "high_volatility"]


def _base_estimator() -> Pipeline:
    return Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )


def _build_trainable_model(y: pd.Series):
    min_count = int(y.value_counts().min()) if y.nunique() > 1 else 0
    if min_count >= 3:
        return CalibratedClassifierCV(_base_estimator(), cv=3, method="sigmoid")
    return _base_estimator()


def _timeseries_cv_metrics(x: pd.DataFrame, y: pd.Series, n_splits: int = 5) -> dict:
    splitter = TimeSeriesSplit(n_splits=n_splits)
    acc_scores: list[float] = []
    f1_scores: list[float] = []

    for train_idx, test_idx in splitter.split(x):
        x_train, x_test = x.iloc[train_idx], x.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        if y_train.nunique() < 2 or y_test.nunique() < 2:
            continue

        model = _build_trainable_model(y_train)
        model.fit(x_train, y_train)
        pred = model.predict(x_test)

        acc_scores.append(float(accuracy_score(y_test, pred)))
        f1_scores.append(float(f1_score(y_test, pred, zero_division=0)))

    if not acc_scores:
        return {"cv_splits": 0, "walk_forward_accuracy": 0.0, "accuracy_std": 0.0, "f1_mean": 0.0, "f1_std": 0.0}

    return {
        "cv_splits": len(acc_scores),
        "walk_forward_accuracy": float(np.mean(acc_scores)),
        "accuracy_std": float(np.std(acc_scores)),
        "f1_mean": float(np.mean(f1_scores)),
        "f1_std": float(np.std(f1_scores)),
    }


def _regime_label(frame: pd.DataFrame) -> pd.Series:
    vol_q = frame["vol_10"].quantile(0.75)
    cond_hv = frame["vol_10"] >= vol_q
    cond_trend = frame["ma_spread"].abs() >= frame["ma_spread"].abs().median()

    regime = pd.Series("ranging", index=frame.index)
    regime.loc[cond_hv] = "high_volatility"
    regime.loc[~cond_hv & cond_trend] = "trending"
    return regime


def _fit_and_save(symbol_key: str, frame: pd.DataFrame) -> dict:
    x = frame[FEATURES]
    y = frame["target"]
    if y.nunique() < 2:
        return {
            "ok": False,
            "symbol": symbol_key,
            "train_rows": len(frame),
            "features": FEATURES,
            "metrics": {"walk_forward_accuracy": 0.0, "f1_mean": 0.0},
            "registry": {},
            "green_flag": False,
            "reason": "single_class_target",
        }

    metrics = _timeseries_cv_metrics(x, y, n_splits=5)

    model = _build_trainable_model(y)
    model.fit(x, y)

    payload = {
        "model": model,
        "features": FEATURES,
        "metrics": metrics,
        "train_rows": len(frame),
        "symbol": symbol_key,
    }
    registry_meta = save_model(symbol_key, payload)

    return {
        "ok": True,
        "symbol": symbol_key,
        "train_rows": len(frame),
        "features": FEATURES,
        "metrics": metrics,
        "registry": registry_meta,
        "green_flag": metrics["walk_forward_accuracy"] >= 0.50,
    }


def train_and_register(symbol: str, ohlcv_df: pd.DataFrame) -> dict:
    frame = build_training_frame(ohlcv_df)
    frame = frame.copy()
    frame["regime"] = _regime_label(frame)

    main_result = _fit_and_save(symbol, frame)

    regime_results = {}
    for regime in REGIMES:
        sub = frame[frame["regime"] == regime]
        if len(sub) < 150:
            regime_results[regime] = {"ok": False, "reason": "insufficient_rows", "rows": int(len(sub)), "green_flag": False}
            continue
        regime_results[regime] = _fit_and_save(f"{symbol}_{regime}", sub)

    return {
        **main_result,
        "regime_models": regime_results,
        "green_flag": main_result.get("green_flag", False),
    }

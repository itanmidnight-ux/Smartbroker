from __future__ import annotations

import pandas as pd

from ml.dataset import build_training_frame
from ml.model_registry import load_latest_model


def _infer_regime(latest: pd.Series) -> str:
    if float(latest["vol_10"]) >= 0.02:
        return "high_volatility"
    if abs(float(latest["ma_spread"])) >= 0.0005:
        return "trending"
    return "ranging"


def _load_model_for_regime(symbol: str, regime: str) -> tuple[dict, str]:
    key = f"{symbol}_{regime}"
    try:
        return load_latest_model(key), key
    except Exception:
        return load_latest_model(symbol), symbol


def predict_latest(symbol: str, ohlcv_df: pd.DataFrame) -> dict:
    frame = build_training_frame(ohlcv_df)
    latest = frame.iloc[-1:]
    latest_row = latest.iloc[0]
    regime = _infer_regime(latest_row)

    payload, model_key = _load_model_for_regime(symbol, regime)
    model = payload["model"]
    features = payload["features"]

    x = latest[features]
    prob_up = float(model.predict_proba(x)[0][1])
    action = "buy" if prob_up >= 0.55 else "sell" if prob_up <= 0.45 else "hold"

    return {
        "symbol": symbol,
        "model_key": model_key,
        "regime": regime,
        "timestamp": str(latest_row["time"]),
        "prob_up": prob_up,
        "action": action,
        "indicator_5m": "BUY" if prob_up >= 0.55 else "SELL" if prob_up <= 0.45 else "HOLD",
        "green_flag": True,
    }

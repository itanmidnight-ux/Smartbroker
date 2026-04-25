from __future__ import annotations

import pandas as pd


def build_training_frame(ohlcv: pd.DataFrame) -> pd.DataFrame:
    if ohlcv.empty:
        raise ValueError("OHLCV vacío")

    df = ohlcv.copy()
    df = df.sort_values("time").reset_index(drop=True)

    df["ret_1"] = df["close"].pct_change(1)
    df["ret_3"] = df["close"].pct_change(3)
    df["ret_10"] = df["close"].pct_change(10)
    df["vol_10"] = df["ret_1"].rolling(10).std()
    df["ma_10"] = df["close"].rolling(10).mean()
    df["ma_30"] = df["close"].rolling(30).mean()
    df["ma_spread"] = (df["ma_10"] - df["ma_30"]) / df["close"].replace(0, 1)

    df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)

    keep = ["time", "ret_1", "ret_3", "ret_10", "vol_10", "ma_spread", "target"]
    out = df[keep].dropna().reset_index(drop=True)

    if len(out) < 120:
        raise ValueError("Datos insuficientes para entrenamiento (mínimo recomendado: 120 filas)")

    return out

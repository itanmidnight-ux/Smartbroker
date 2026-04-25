import pandas as pd


def build_basic_features(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["ret_1"] = data["close"].pct_change(1)
    data["ret_5"] = data["close"].pct_change(5)
    data["vol_10"] = data["ret_1"].rolling(10).std()
    data["ma_fast"] = data["close"].rolling(10).mean()
    data["ma_slow"] = data["close"].rolling(30).mean()
    data["trend"] = (data["ma_fast"] > data["ma_slow"]).astype(int)
    return data.dropna().reset_index(drop=True)

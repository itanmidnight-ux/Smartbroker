from data.mt5_data_feed import synthetic_ohlcv
from ml.dataset import build_training_frame
from ml.train import train_and_register
from ml.predict import predict_latest


def test_ml_training_and_prediction_synthetic() -> None:
    symbol = "XAUUSD"
    ohlcv = synthetic_ohlcv(symbol, rows=900)
    frame = build_training_frame(ohlcv)
    assert len(frame) >= 120

    train_result = train_and_register(symbol, ohlcv)
    assert train_result["ok"]
    assert "metrics" in train_result

    pred = predict_latest(symbol, ohlcv)
    assert pred["green_flag"]
    assert pred["action"] in {"buy", "sell", "hold"}

from fastapi.testclient import TestClient
from services.api import app


client = TestClient(app)


def test_validate_data_green_flag() -> None:
    res = client.get('/ml/validate/data', params={'symbol': 'XAUUSD', 'bars': 300, 'source': 'synthetic'})
    assert res.status_code == 200
    payload = res.json()
    assert payload['green_flag'] is True


def test_train_predict_green_flag() -> None:
    train = client.post('/ml/train', json={'symbol': 'XAUUSD', 'bars': 900, 'source': 'synthetic'})
    assert train.status_code == 200
    assert train.json()['green_flag'] in {True, False}

    validate = client.get('/ml/validate/model', params={'symbol': 'XAUUSD'})
    assert validate.status_code == 200
    assert validate.json()['green_flag'] is True

    pred = client.post('/ml/predict', json={'symbol': 'XAUUSD', 'bars': 400, 'source': 'synthetic'})
    assert pred.status_code == 200
    assert pred.json()['green_flag'] is True

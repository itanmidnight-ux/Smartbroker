from fastapi.testclient import TestClient
from services.api import app


client = TestClient(app)


def test_strategy_toggle_and_indicator() -> None:
    off = client.post('/strategy/toggle', json={'enabled': False})
    assert off.status_code == 200
    assert off.json()['simulation_mode'] is True

    on = client.post('/strategy/toggle', json={'enabled': True})
    assert on.status_code == 200
    assert on.json()['strategy_enabled'] is True

    ind = client.get('/signal/indicator5m', params={'symbol': 'XAUUSD', 'source': 'synthetic'})
    assert ind.status_code == 200
    assert ind.json()['indicator_5m'] in {'BUY', 'SELL', 'HOLD'}


def test_signal_creates_sim_trade_and_overlay() -> None:
    client.post('/strategy/toggle', json={'enabled': False})

    sig = client.post('/signal', json={
        'symbol': 'XAUUSD',
        'volatility': 0.01,
        'trend_strength': 0.7,
        'trend': 1,
        'source': 'test',
    })
    assert sig.status_code == 200
    payload = sig.json()
    assert payload['execution_mode'] == 'SIM'
    assert payload['trade_id'] > 0

    trades = client.get('/trades/recent', params={'limit': 5})
    assert trades.status_code == 200
    assert trades.json()['count'] >= 1

    overlay = client.get('/signals/overlay', params={'symbol': 'XAUUSD', 'limit': 20})
    assert overlay.status_code == 200
    assert overlay.json()['green_flag'] is True

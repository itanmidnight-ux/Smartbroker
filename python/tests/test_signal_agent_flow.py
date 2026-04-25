from fastapi.testclient import TestClient
from services.api import app


client = TestClient(app)


def test_signal_ingest_analyze_and_feedback() -> None:
    sig = client.post(
        '/signal',
        json={
            'symbol': 'XAUUSD',
            'volatility': 0.01,
            'trend_strength': 0.7,
            'trend': 1,
            'source': 'test',
        },
    )
    assert sig.status_code == 200
    payload = sig.json()
    assert payload['green_flag'] is True
    signal_id = payload['signal_id']

    recent = client.get('/signals/recent', params={'limit': 10})
    assert recent.status_code == 200
    assert recent.json()['count'] >= 1

    analysis = client.get('/signals/analyze', params={'limit': 50})
    assert analysis.status_code == 200
    assert analysis.json()['green_flag'] is True

    fb = client.post('/signals/feedback', json={'signal_id': signal_id, 'regime': payload['regime'], 'action': payload['final_action'], 'reward': 0.05})
    assert fb.status_code == 200
    assert fb.json()['green_flag'] is True

    agent_val = client.get('/agent/validate')
    assert agent_val.status_code == 200
    assert agent_val.json()['green_flag'] is True

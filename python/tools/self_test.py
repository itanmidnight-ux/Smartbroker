from __future__ import annotations

from fastapi.testclient import TestClient
from services.api import app


def main() -> None:
    client = TestClient(app)

    checks = []
    checks.append(("health", client.get("/health").status_code == 200))
    checks.append(("agent_validate", client.get("/agent/validate").status_code == 200))
    checks.append(("ml_validate_data", client.get("/ml/validate/data", params={"symbol": "XAUUSD", "source": "synthetic", "bars": 500}).json().get("green_flag") is True))
    checks.append(("system_validate", client.get("/system/validate").status_code == 200))
    checks.append(("indicator_5m", client.get("/signal/indicator5m", params={"symbol": "XAUUSD", "source": "synthetic"}).status_code == 200))

    for name, ok in checks:
        print(f"[self-test] {name}={'OK' if ok else 'FAIL'}")

    if not all(ok for _, ok in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

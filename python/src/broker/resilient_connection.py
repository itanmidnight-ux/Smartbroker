import time
from dataclasses import dataclass
from typing import Optional

from broker.mt5_connection import MT5ConnectionManager, BrokerSession


@dataclass
class RetryPolicy:
    max_attempts: int = 5
    backoff_seconds: float = 1.5


class ResilientMT5Connector:
    def __init__(self, manager: MT5ConnectionManager, policy: Optional[RetryPolicy] = None) -> None:
        self.manager = manager
        self.policy = policy or RetryPolicy()

    def connect_with_retry(self) -> BrokerSession:
        last_exception: Optional[Exception] = None

        for attempt in range(1, self.policy.max_attempts + 1):
            try:
                return self.manager.connect()
            except Exception as exc:  # noqa: BLE001
                last_exception = exc
                if attempt == self.policy.max_attempts:
                    break
                time.sleep(self.policy.backoff_seconds * attempt)

        raise RuntimeError(f"No fue posible conectar a MT5 luego de {self.policy.max_attempts} intentos.") from last_exception

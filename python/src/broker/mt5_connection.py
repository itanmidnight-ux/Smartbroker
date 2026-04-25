import os
from dataclasses import dataclass
from typing import Optional

try:
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover
    mt5 = None


@dataclass
class BrokerSession:
    name: str
    server: str
    terminal_path: str
    login: int
    mode: str


class MT5ConnectionManager:
    def __init__(self, profile: dict) -> None:
        self.profile = profile
        self.session: Optional[BrokerSession] = None

    def connect(self) -> BrokerSession:
        if mt5 is None:
            raise RuntimeError("MetaTrader5 package no instalado.")

        login = int(os.getenv(self.profile["login_env"], "0"))
        password = os.getenv(self.profile["password_env"], "")
        server = os.getenv("MT5_SERVER", self.profile["server"])
        terminal_path = os.getenv("MT5_TERMINAL_PATH", self.profile["terminal_path"])
        timeout = int(os.getenv("MT5_TIMEOUT_MS", "10000"))

        initialized = mt5.initialize(path=terminal_path, login=login, password=password, server=server, timeout=timeout)
        if not initialized:
            raise RuntimeError(f"No se pudo inicializar MT5: {mt5.last_error()}")

        self.session = BrokerSession(
            name=self.profile["name"],
            server=server,
            terminal_path=terminal_path,
            login=login,
            mode=self.profile["mode"],
        )
        return self.session

    def shutdown(self) -> None:
        if mt5 is not None:
            mt5.shutdown()

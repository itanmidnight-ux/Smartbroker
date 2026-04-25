from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RuntimeState:
    connected: bool = False
    broker_profile: str = ""
    broker_mode: str = ""
    server: str = ""
    live_armed: bool = False
    strategy_enabled: bool = False
    simulation_mode: bool = True
    last_error: str = ""
    last_signal_action: str = "hold"
    last_signal_probability: float = 0.0
    last_regime: str = "unknown"
    last_update_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def touch(self) -> None:
        self.last_update_utc = datetime.now(timezone.utc).isoformat()


runtime_state = RuntimeState()

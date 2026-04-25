from risk.risk_limits import validate_limits
from risk.kill_switch import kill_switch_triggered


def test_validate_limits_ok() -> None:
    assert validate_limits(1.0, 5.0, 2.0, 8.0)


def test_kill_switch_for_spread() -> None:
    assert kill_switch_triggered(80, 50, 0, 3)

from execution.planner import build_execution_plan


def test_execution_plan_allowed() -> None:
    plan = build_execution_plan(
        symbol="XAUUSD",
        action="buy",
        probability=0.7,
        spread_points=30,
        max_spread_points=60,
        balance=10000,
        risk_pct=0.5,
        stop_loss_points=250,
        take_profit_points=500,
        point_value=1.0,
    )
    assert plan["green_flag"] is True
    assert plan["lot_size"] > 0


def test_execution_plan_blocked_by_spread() -> None:
    plan = build_execution_plan(
        symbol="XAUUSD",
        action="buy",
        probability=0.7,
        spread_points=90,
        max_spread_points=60,
        balance=10000,
        risk_pct=0.5,
        stop_loss_points=250,
        take_profit_points=500,
        point_value=1.0,
    )
    assert plan["green_flag"] is False
    assert plan["lot_size"] == 0.0

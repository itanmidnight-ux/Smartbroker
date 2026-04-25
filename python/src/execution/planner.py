from __future__ import annotations


def lot_size_by_risk(balance: float, risk_pct: float, stop_loss_points: float, point_value: float) -> float:
    if stop_loss_points <= 0 or point_value <= 0:
        return 0.0
    risk_amount = balance * (risk_pct / 100.0)
    size = risk_amount / (stop_loss_points * point_value)
    return max(round(size, 2), 0.0)


def build_execution_plan(
    symbol: str,
    action: str,
    probability: float,
    spread_points: float,
    max_spread_points: float,
    balance: float,
    risk_pct: float,
    stop_loss_points: float,
    take_profit_points: float,
    point_value: float = 1.0,
) -> dict:
    spread_ok = spread_points <= max_spread_points
    confidence_ok = probability >= 0.55
    action_ok = action in {"buy", "sell"}
    allowed = spread_ok and confidence_ok and action_ok

    lot = lot_size_by_risk(balance, risk_pct, stop_loss_points, point_value) if allowed else 0.0

    return {
        "symbol": symbol,
        "action": action,
        "probability": probability,
        "spread_points": spread_points,
        "spread_ok": spread_ok,
        "confidence_ok": confidence_ok,
        "action_ok": action_ok,
        "allowed": allowed,
        "lot_size": lot,
        "stop_loss_points": stop_loss_points,
        "take_profit_points": take_profit_points,
        "rr_ratio": round((take_profit_points / stop_loss_points), 2) if stop_loss_points > 0 else 0.0,
        "green_flag": allowed,
    }

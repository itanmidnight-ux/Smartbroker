def validate_limits(daily_loss_pct: float, drawdown_pct: float, max_daily_loss_pct: float, max_drawdown_pct: float) -> bool:
    return daily_loss_pct <= max_daily_loss_pct and drawdown_pct <= max_drawdown_pct

def kill_switch_triggered(
    spread_points: int,
    max_spread_points: int,
    consecutive_rejections: int,
    max_consecutive_rejections: int,
) -> bool:
    if spread_points > max_spread_points:
        return True
    if consecutive_rejections >= max_consecutive_rejections:
        return True
    return False

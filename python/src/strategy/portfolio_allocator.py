from dataclasses import dataclass


@dataclass
class Allocation:
    strategy: str
    weight: float


def allocate_by_regime(regime: str) -> list[Allocation]:
    if regime == "trending":
        return [Allocation("trend_follow", 0.7), Allocation("mean_reversion", 0.3)]
    if regime == "ranging":
        return [Allocation("trend_follow", 0.3), Allocation("mean_reversion", 0.7)]
    return [Allocation("trend_follow", 0.2), Allocation("mean_reversion", 0.2), Allocation("risk_off", 0.6)]

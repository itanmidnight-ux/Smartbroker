from dataclasses import dataclass


@dataclass
class RegimeState:
    name: str
    confidence: float


def detect_regime(volatility: float, trend_strength: float) -> RegimeState:
    if volatility > 0.02:
        return RegimeState("high_volatility", 0.8)
    if trend_strength > 0.6:
        return RegimeState("trending", 0.75)
    return RegimeState("ranging", 0.7)

from dataclasses import dataclass


@dataclass
class TradingMetrics:
    win_rate: float
    expectancy: float
    max_drawdown: float
    avg_latency_ms: float

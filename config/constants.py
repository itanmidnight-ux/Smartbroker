"""
Constants used throughout the trading system.
"""
from enum import Enum
from typing import Dict, List


class OrderType(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class TradeDirection(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class MarketRegime(Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"


class Timeframe(Enum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"


# MT5 Timeframe mapping
MT5_TIMEFRAMES: Dict[Timeframe, int] = {
    Timeframe.M1: 1,
    Timeframe.M5: 5,
    Timeframe.M15: 15,
    Timeframe.H1: 60,
    Timeframe.H4: 240,
    Timeframe.D1: 1440,
}

# Symbol constants
MAJOR_PAIRS: List[str] = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCHF",
    "AUDUSD",
    "USDCAD",
    "NZDUSD",
]

# Risk constants
DEFAULT_STOP_LOSS_PIPS = 50.0
DEFAULT_TAKE_PROFIT_PIPS = 100.0
MAX_DRAWDOWN_THRESHOLD = 0.05  # 5%
KILL_SWITCH_DRAWDOWN = 0.10  # 10%

# ML constants
FEATURE_COLUMNS = [
    "rsi",
    "macd",
    "macd_signal",
    "macd_hist",
    "bb_upper",
    "bb_middle",
    "bb_lower",
    "bb_width",
    "stoch_k",
    "stoch_d",
    "atr",
    "price_change_pct",
    "volume_change_pct",
    "regime_score",
]

REGIME_LABELS = [
    MarketRegime.TRENDING_UP,
    MarketRegime.TRENDING_DOWN,
    MarketRegime.RANGING,
    MarketRegime.HIGH_VOLATILITY,
    MarketRegime.LOW_VOLATILITY,
]

# Scoring thresholds
MIN_SIGNAL_SCORE = 60  # Minimum score to execute trade
HIGH_CONFIDENCE_SCORE = 80
VERY_HIGH_CONFIDENCE_SCORE = 90

# Strategy weights (dynamic, will be adjusted by optimizer)
DEFAULT_STRATEGY_WEIGHTS = {
    "trend": 0.4,
    "mean_reversion": 0.3,
    "breakout": 0.3,
}

# Database table names
TABLE_TRADES = "trades"
TABLE_SIGNALS = "signals"
TABLE_PERFORMANCE = "performance"
TABLE_MODEL_METRICS = "model_metrics"
TABLE_REGIMES = "regimes"

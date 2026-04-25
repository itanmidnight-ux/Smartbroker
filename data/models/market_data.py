"""
Data models for market data.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class OHLCV(BaseModel):
    """OHLCV candle data."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    tick_volume: int = 0
    
    class Config:
        arbitrary_types_allowed = True


class TickData(BaseModel):
    """Tick data model."""
    timestamp: datetime
    symbol: str
    bid: float
    ask: float
    last: float
    volume: int = 0
    
    class Config:
        arbitrary_types_allowed = True


class MarketDepth(BaseModel):
    """Market depth (order book) data."""
    timestamp: datetime
    symbol: str
    bids: List[tuple]  # [(price, volume), ...]
    asks: List[tuple]  # [(price, volume), ...]


class SpreadData(BaseModel):
    """Spread information."""
    timestamp: datetime
    symbol: str
    spread: float  # In points
    spread_pips: float  # In pips


class SymbolInfo(BaseModel):
    """Symbol information from MT5."""
    name: str
    description: str
    point: float
    digits: int
    spread: float
    trade_contract_size: float
    trade_tick_value: float
    trade_tick_size: float
    volume_min: float
    volume_max: float
    volume_step: float


class MarketDataBar(BaseModel):
    """Complete market data bar with derived fields."""
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    tick_volume: int
    spread: float
    trades_count: int = 0
    
    # Derived fields
    typical_price: Optional[float] = None
    hl2: Optional[float] = None
    hlc3: Optional[float] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.high and self.low:
            self.hl2 = (self.high + self.low) / 2
        if self.high and self.low and self.close:
            self.hlc3 = (self.high + self.low + self.close) / 3
        if self.open and self.high and self.low and self.close:
            self.typical_price = (self.high + self.low + self.close) / 3


class FeatureVector(BaseModel):
    """Feature vector for ML models."""
    timestamp: datetime
    symbol: str
    features: dict
    
    # Precomputed indicators
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_width: Optional[float] = None
    stoch_k: Optional[float] = None
    stoch_d: Optional[float] = None
    atr: Optional[float] = None
    price_change_pct: Optional[float] = None
    volume_change_pct: Optional[float] = None
    
    # Market context
    regime: Optional[str] = None
    trend_strength: Optional[float] = None
    volatility_level: Optional[str] = None

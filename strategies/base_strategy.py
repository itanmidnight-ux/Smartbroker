"""
Base strategy class that all strategies must inherit from.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any
from datetime import datetime
import pandas as pd
from pydantic import BaseModel

from config.constants import OrderType, MarketRegime


class Signal(BaseModel):
    """Trading signal with metadata."""
    timestamp: datetime
    symbol: str
    strategy: str
    direction: Optional[OrderType] = None
    score: float = 0.0  # 0-100
    confidence: float = 0.0  # 0-1
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[float] = None
    
    # Metadata
    confluences: int = 0
    total_checks: int = 0
    market_regime: Optional[str] = None
    indicators: Dict[str, Any] = {}
    notes: str = ""
    
    class Config:
        arbitrary_types_allowed = True
    
    @property
    def is_valid(self) -> bool:
        """Check if signal is valid for execution."""
        return (
            self.direction is not None and
            self.score > 50 and
            self.entry_price is not None and
            self.confidence > 0.3
        )


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    """
    
    def __init__(self, name: str, params: Optional[Dict] = None):
        self.name = name
        self.params = params or {}
        self.enabled = True
        self.weight = 1.0  # Dynamic weight based on performance
        
    @abstractmethod
    def generate_signal(
        self,
        df: pd.DataFrame,
        current_price: float,
        symbol: str,
        market_regime: Optional[MarketRegime] = None
    ) -> Signal:
        """
        Generate trading signal based on market data.
        
        Args:
            df: DataFrame with OHLCV and indicators
            current_price: Current market price
            symbol: Trading symbol
            market_regime: Current market regime
        
        Returns:
            Signal object
        """
        pass
    
    def calculate_score(
        self,
        confluences: int,
        total_checks: int,
        regime_alignment: bool = True,
        additional_factors: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Calculate signal score based on confluences and factors.
        
        Args:
            confluences: Number of confirming indicators
            total_checks: Total number of checks performed
            regime_alignment: Whether signal aligns with market regime
            additional_factors: Additional scoring factors
        
        Returns:
            Score from 0 to 100
        """
        # Base score from confluence ratio
        base_score = (confluences / max(total_checks, 1)) * 100
        
        # Regime alignment bonus
        regime_bonus = 10 if regime_alignment else -10
        
        # Additional factors
        factor_bonus = 0
        if additional_factors:
            for factor, value in additional_factors.items():
                factor_bonus += value * 5  # Weight each factor
        
        # Calculate final score
        score = base_score + regime_bonus + factor_bonus
        
        # Clamp to 0-100
        score = max(0, min(100, score))
        
        return score
    
    def calculate_stop_loss(
        self,
        direction: OrderType,
        entry_price: float,
        atr: float,
        multiplier: float = 2.0
    ) -> float:
        """
        Calculate stop loss based on ATR.
        """
        sl_distance = atr * multiplier
        
        if direction == OrderType.BUY:
            return entry_price - sl_distance
        else:
            return entry_price + sl_distance
    
    def calculate_take_profit(
        self,
        direction: OrderType,
        entry_price: float,
        stop_loss: float,
        risk_reward_ratio: float = 2.0
    ) -> float:
        """
        Calculate take profit based on risk-reward ratio.
        """
        risk = abs(entry_price - stop_loss)
        reward = risk * risk_reward_ratio
        
        if direction == OrderType.BUY:
            return entry_price + reward
        else:
            return entry_price - reward
    
    def update_weight(self, performance_metrics: Dict[str, float]):
        """
        Update strategy weight based on performance.
        To be overridden by specific strategies.
        """
        pass
    
    def get_params(self) -> Dict:
        """Get current strategy parameters."""
        return self.params.copy()
    
    def set_params(self, params: Dict):
        """Update strategy parameters."""
        self.params.update(params)
    
    def enable(self):
        """Enable the strategy."""
        self.enabled = True
    
    def disable(self):
        """Disable the strategy."""
        self.enabled = False

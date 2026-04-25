"""
Signal Engine - Aggregates signals from multiple strategies.
"""
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import numpy as np

from strategies.base_strategy import Signal, BaseStrategy
from strategies.trend_strategy import TrendFollowingStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.breakout import BreakoutStrategy
from config.constants import OrderType, MarketRegime, DEFAULT_STRATEGY_WEIGHTS, MIN_SIGNAL_SCORE
from utils.logger import get_logger

logger = get_logger(__name__)


class SignalEngine:
    """
    Aggregates signals from multiple strategies and produces consolidated signals.
    """
    
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        
        # Initialize strategies
        self.strategies: Dict[str, BaseStrategy] = {
            'trend_following': TrendFollowingStrategy(),
            'mean_reversion': MeanReversionStrategy(),
            'breakout': BreakoutStrategy(),
        }
        
        # Strategy weights (dynamic)
        self.weights = DEFAULT_STRATEGY_WEIGHTS.copy()
        
        # Minimum score threshold
        self.min_score = MIN_SIGNAL_SCORE
        
        # Signal history
        self.signal_history: List[Signal] = []
    
    def add_strategy(self, name: str, strategy: BaseStrategy):
        """Add a new strategy to the engine."""
        self.strategies[name] = strategy
        logger.info(f"Added strategy: {name}")
    
    def remove_strategy(self, name: str):
        """Remove a strategy from the engine."""
        if name in self.strategies:
            del self.strategies[name]
            logger.info(f"Removed strategy: {name}")
    
    def update_strategy_weight(self, strategy_name: str, weight: float):
        """Update the weight of a specific strategy."""
        if strategy_name in self.weights:
            self.weights[strategy_name] = max(0.1, min(2.0, weight))
    
    def generate_signals(
        self,
        df: pd.DataFrame,
        current_price: float,
        symbol: str,
        market_regime: Optional[MarketRegime] = None
    ) -> List[Signal]:
        """
        Generate signals from all active strategies.
        
        Args:
            df: DataFrame with OHLCV and indicators
            current_price: Current market price
            symbol: Trading symbol
            market_regime: Current market regime
        
        Returns:
            List of signals from all strategies
        """
        signals = []
        
        for name, strategy in self.strategies.items():
            if not strategy.enabled:
                continue
            
            try:
                signal = strategy.generate_signal(df, current_price, symbol, market_regime)
                
                # Apply strategy weight to score
                weighted_score = signal.score * self.weights.get(name, 1.0)
                signal.score = min(100, weighted_score)
                signal.confidence = signal.score / 100
                
                signals.append(signal)
                self.signal_history.append(signal)
                
            except Exception as e:
                logger.error(f"Error generating signal from {name}", error=str(e))
        
        return signals
    
    def get_consolidated_signal(
        self,
        signals: List[Signal],
        min_agreement: int = 2
    ) -> Optional[Signal]:
        """
        Consolidate multiple signals into one based on agreement.
        
        Args:
            signals: List of signals from different strategies
            min_agreement: Minimum number of strategies agreeing
        
        Returns:
            Consolidated signal or None if no agreement
        """
        if not signals:
            return None
        
        # Filter valid signals
        valid_signals = [s for s in signals if s.is_valid and s.score >= self.min_score]
        
        if not valid_signals:
            return None
        
        # Count agreements by direction
        buy_signals = [s for s in valid_signals if s.direction == OrderType.BUY]
        sell_signals = [s for s in valid_signals if s.direction == OrderType.SELL]
        
        # Check for agreement
        if len(buy_signals) >= min_agreement:
            return self._merge_signals(buy_signals, OrderType.BUY)
        elif len(sell_signals) >= min_agreement:
            return self._merge_signals(sell_signals, OrderType.SELL)
        
        # If only one strong signal, still consider it
        if len(valid_signals) == 1 and valid_signals[0].score >= 80:
            return valid_signals[0]
        
        return None
    
    def _merge_signals(self, signals: List[Signal], direction: OrderType) -> Signal:
        """Merge multiple signals into one consolidated signal."""
        if not signals:
            raise ValueError("No signals to merge")
        
        # Calculate weighted average score
        total_weight = sum(self.weights.get(s.strategy, 1.0) for s in signals)
        weighted_score = sum(
            s.score * self.weights.get(s.strategy, 1.0) 
            for s in signals
        ) / total_weight
        
        # Average entry price
        avg_entry = sum(s.entry_price or signals[0].entry_price for s in signals) / len(signals)
        
        # Most conservative stop loss
        if direction == OrderType.BUY:
            stop_loss = min((s.stop_loss or 0) for s in signals if s.stop_loss) if any(s.stop_loss for s in signals) else None
        else:
            stop_loss = max((s.stop_loss or float('inf')) for s in signals if s.stop_loss) if any(s.stop_loss for s in signals) else None
        
        # Average take profit
        tp_values = [s.take_profit for s in signals if s.take_profit]
        take_profit = sum(tp_values) / len(tp_values) if tp_values else None
        
        # Combine confluences
        total_confluences = sum(s.confluences for s in signals)
        total_checks = sum(s.total_checks for s in signals)
        
        # Merge indicators
        merged_indicators = {}
        for signal in signals:
            for key, value in signal.indicators.items():
                if key not in merged_indicators:
                    merged_indicators[key] = []
                if value is not None:
                    merged_indicators[key].append(value)
        
        # Average indicator values
        for key in merged_indicators:
            if merged_indicators[key]:
                merged_indicators[key] = sum(merged_indicators[key]) / len(merged_indicators[key])
        
        # Create consolidated signal
        consolidated = Signal(
            timestamp=datetime.utcnow(),
            symbol=signals[0].symbol,
            strategy='consolidated',
            direction=direction,
            score=weighted_score,
            confidence=weighted_score / 100,
            entry_price=avg_entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confluences=total_confluences,
            total_checks=total_checks,
            market_regime=signals[0].market_regime,
            indicators=merged_indicators,
            notes=f"Consolidated from {len(signals)} strategies: {[s.strategy for s in signals]}"
        )
        
        return consolidated
    
    def update_strategy_weights_from_performance(self, performance_metrics: Dict[str, Dict[str, float]]):
        """
        Update strategy weights based on performance metrics.
        
        Args:
            performance_metrics: Dict of strategy_name -> metrics
        """
        for strategy_name, metrics in performance_metrics.items():
            if strategy_name in self.strategies:
                self.strategies[strategy_name].update_weight(metrics)
                self.weights[strategy_name] = self.strategies[strategy_name].weight
        
        # Normalize weights
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            for key in self.weights:
                self.weights[key] = self.weights[key] / total_weight * 3  # Keep sum around 3
    
    def get_active_strategies(self) -> List[str]:
        """Get list of active strategy names."""
        return [name for name, strat in self.strategies.items() if strat.enabled]
    
    def get_strategy_info(self) -> Dict[str, Dict]:
        """Get information about all strategies."""
        info = {}
        for name, strategy in self.strategies.items():
            info[name] = {
                'enabled': strategy.enabled,
                'weight': self.weights.get(name, 1.0),
                'params': strategy.get_params(),
            }
        return info

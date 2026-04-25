"""
Breakout Strategy.
Trades breakouts from consolidation ranges and key levels.
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Tuple

from strategies.base_strategy import BaseStrategy, Signal
from config.constants import OrderType, MarketRegime


class BreakoutStrategy(BaseStrategy):
    """
    Breakout Strategy.
    
    Detects consolidation patterns and trades breakouts with volume confirmation.
    
    Entry conditions for LONG breakout:
    - Price breaks above resistance level
    - Volume spike (> 1.5x average)
    - ADX increasing (trend strengthening)
    - RSI > 50 but not overbought
    
    Entry conditions for SHORT breakout:
    - Price breaks below support level
    - Volume spike (> 1.5x average)
    - ADX increasing (trend strengthening)
    - RSI < 50 but not oversold
    """
    
    def __init__(self, params: Optional[Dict] = None):
        default_params = {
            'lookback_period': 20,
            'volume_multiplier': 1.5,
            'adx_min': 20,
            'adx_increasing': True,
            'rsi_min_breakout': 50,
            'rsi_max_breakout': 70,
            'atr_sl_multiplier': 1.5,
            'rr_ratio': 2.5,
            'false_breakout_filter': True,
        }
        super().__init__('breakout', {**default_params, **(params or {})})
    
    def generate_signal(
        self,
        df: pd.DataFrame,
        current_price: float,
        symbol: str,
        market_regime: Optional[MarketRegime] = None
    ) -> Signal:
        if len(df) < self.params['lookback_period'] + 10:
            return self._create_empty_signal(symbol)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        confluences = 0
        total_checks = 0
        additional_factors = {}
        
        # Calculate support and resistance
        lookback = self.params['lookback_period']
        recent_highs = df['high'].iloc[-lookback:-1]
        recent_lows = df['low'].iloc[-lookback:-1]
        
        resistance = recent_highs.max()
        support = recent_lows.min()
        range_size = resistance - support
        
        # Get indicators
        volume = latest.get('volume', 0)
        volume_ma = latest.get('volume_ma_10', df['volume'].iloc[-lookback:].mean())
        adx = latest.get('adx', 0)
        prev_adx = prev.get('adx', adx)
        rsi = latest.get('rsi', 50)
        atr = latest.get('atr', current_price * 0.01)
        
        # Check 1: Price breakout
        total_checks += 1
        breakout_above = current_price > resistance
        breakout_below = current_price < support
        
        # Check if it's a fresh breakout (not already broken multiple times)
        prev_close = df['close'].iloc[-2]
        fresh_breakout_up = breakout_above and prev_close <= resistance
        fresh_breakout_down = breakout_below and prev_close >= support
        
        if fresh_breakout_up or fresh_breakout_down:
            confluences += 1
            additional_factors['breakout_strength'] = min(abs(current_price - (resistance if breakout_above else support)) / range_size, 1.0)
        
        # Check 2: Volume confirmation
        total_checks += 1
        volume_ratio = volume / (volume_ma + 1e-10)
        volume_spike = volume_ratio > self.params['volume_multiplier']
        
        if volume_spike:
            confluences += 1
            additional_factors['volume_confirmation'] = min(volume_ratio / self.params['volume_multiplier'], 2.0) * 0.5
        
        # Check 3: ADX confirmation (trend strength)
        total_checks += 1
        adx_ok = adx > self.params['adx_min']
        adx_increasing = adx > prev_adx if self.params['adx_increasing'] else True
        
        if adx_ok and adx_increasing:
            confluences += 1
            additional_factors['adx_momentum'] = min((adx - self.params['adx_min']) / 20, 1.0)
        
        # Check 4: RSI confirmation
        total_checks += 1
        if breakout_above:
            rsi_ok = self.params['rsi_min_breakout'] < rsi < self.params['rsi_max_breakout']
        else:
            rsi_ok = (100 - self.params['rsi_max_breakout']) < rsi < (100 - self.params['rsi_min_breakout'])
        
        if rsi_ok:
            confluences += 1
        
        # Check 5: Range compression before breakout (optional bonus)
        total_checks += 1
        if lookback >= 10:
            # Check if range was compressing (low volatility before breakout)
            prev_range = df['high'].iloc[-lookback:-5].max() - df['low'].iloc[-lookback:-5].min()
            curr_range = range_size
            
            if curr_range < prev_range * 0.8:  # Range compressed by 20%
                confluences += 0.5
                additional_factors['compression'] = 0.5
        else:
            total_checks -= 1
        
        # Determine direction
        direction = None
        
        if fresh_breakout_up and volume_spike and adx_ok:
            direction = OrderType.BUY
        elif fresh_breakout_down and volume_spike and adx_ok:
            direction = OrderType.SELL
        
        # False breakout filter
        if self.params['false_breakout_filter'] and direction:
            # Check if price is extending too far from the breakout level
            if direction == OrderType.BUY:
                extension = (current_price - resistance) / range_size if range_size > 0 else 0
            else:
                extension = (support - current_price) / range_size if range_size > 0 else 0
            
            if extension > 0.5:  # More than 50% of range extended
                # Reduce confidence but don't invalidate
                additional_factors['overextended'] = -0.3
        
        # Calculate score
        regime_alignment = True
        if market_regime:
            # Breakouts work best when transitioning from ranging to trending
            if market_regime == MarketRegime.RANGING:
                regime_alignment = True
                additional_factors['regime_bonus'] = 0.3
            elif market_regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
                regime_alignment = True
            elif market_regime == MarketRegime.HIGH_VOLATILITY:
                # High vol can mean false breakouts
                regime_alignment = False
                additional_factors['volatility_warning'] = -0.2
        
        score = self.calculate_score(
            confluences=int(confluences),
            total_checks=total_checks,
            regime_alignment=regime_alignment,
            additional_factors=additional_factors
        )
        
        # Calculate SL/TP
        stop_loss = None
        take_profit = None
        
        if direction:
            # Stop loss on the other side of the range
            if direction == OrderType.BUY:
                stop_loss = support - atr * 0.5
                # Take profit based on range projection
                take_profit = current_price + (range_size * self.params['rr_ratio'])
            else:
                stop_loss = resistance + atr * 0.5
                take_profit = current_price - (range_size * self.params['rr_ratio'])
            
            # Use ATR-based stop if it's tighter
            atr_stop = self.calculate_stop_loss(
                direction, current_price, atr, self.params['atr_sl_multiplier']
            )
            
            if direction == OrderType.BUY:
                stop_loss = max(stop_loss, atr_stop)
            else:
                stop_loss = min(stop_loss, atr_stop)
        
        # Create signal
        signal = Signal(
            timestamp=datetime.utcnow(),
            symbol=symbol,
            strategy=self.name,
            direction=direction,
            score=score,
            confidence=score / 100,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confluences=int(confluences),
            total_checks=total_checks,
            market_regime=market_regime.value if market_regime else None,
            indicators={
                'resistance': resistance,
                'support': support,
                'range_size': range_size,
                'volume_ratio': volume_ratio,
                'adx': adx,
                'rsi': rsi,
            },
            notes=f"Breakout: {confluences}/{total_checks} confluences, Vol ratio={volume_ratio:.2f}"
        )
        
        return signal
    
    def _create_empty_signal(self, symbol: str) -> Signal:
        """Create empty signal when insufficient data."""
        return Signal(
            timestamp=datetime.utcnow(),
            symbol=symbol,
            strategy=self.name,
            score=0,
            confidence=0,
            confluences=0,
            total_checks=0,
            notes="Insufficient data"
        )
    
    def update_weight(self, performance_metrics: Dict[str, float]):
        """Update strategy weight based on recent performance."""
        winrate = performance_metrics.get('winrate', 0.5)
        profit_factor = performance_metrics.get('profit_factor', 1.0)
        avg_rr = performance_metrics.get('avg_rr', 2.0)
        
        # Breakouts should have lower winrate but higher RR
        if winrate > 0.40 and profit_factor > 1.3:
            self.weight = min(self.weight * 1.1, 2.0)
        elif winrate < 0.35 or profit_factor < 0.9:
            self.weight = max(self.weight * 0.9, 0.5)

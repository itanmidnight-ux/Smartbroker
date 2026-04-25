"""
Mean Reversion Strategy.
Trades against extreme moves, expecting price to revert to mean.
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Dict

from strategies.base_strategy import BaseStrategy, Signal
from config.constants import OrderType, MarketRegime


class MeanReversionStrategy(BaseStrategy):
    """
    Mean Reversion Strategy.
    
    Entry conditions for LONG (oversold):
    - RSI < 30 (oversold)
    - Price below lower Bollinger Band
    - Stochastic %K < 20
    - Price far from mean (> 2 std dev)
    - ADX < 25 (weak trend, ranging market)
    
    Entry conditions for SHORT (overbought):
    - RSI > 70 (overbought)
    - Price above upper Bollinger Band
    - Stochastic %K > 80
    - Price far from mean (> 2 std dev)
    - ADX < 25 (weak trend, ranging market)
    """
    
    def __init__(self, params: Optional[Dict] = None):
        default_params = {
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'stoch_oversold': 20,
            'stoch_overbought': 80,
            'bb_std_dev': 2.0,
            'adx_max': 25,
            'atr_sl_multiplier': 1.5,
            'rr_ratio': 1.5,
            'mean_reversion_target': 'middle',  # 'middle' or 'opposite_band'
        }
        super().__init__('mean_reversion', {**default_params, **(params or {})})
    
    def generate_signal(
        self,
        df: pd.DataFrame,
        current_price: float,
        symbol: str,
        market_regime: Optional[MarketRegime] = None
    ) -> Signal:
        if len(df) < 50:
            return self._create_empty_signal(symbol)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        confluences = 0
        total_checks = 0
        additional_factors = {}
        
        # Get indicators
        rsi = latest.get('rsi', 50)
        stoch_k = latest.get('stoch_k', 50)
        stoch_d = latest.get('stoch_d', 50)
        bb_upper = latest.get('bb_upper')
        bb_middle = latest.get('bb_middle')
        bb_lower = latest.get('bb_lower')
        adx = latest.get('adx', 0)
        atr = latest.get('atr', current_price * 0.01)
        
        # Check 1: RSI extreme
        total_checks += 1
        rsi_oversold = rsi < self.params['rsi_oversold']
        rsi_overbought = rsi > self.params['rsi_overbought']
        
        if rsi_oversold or rsi_overbought:
            confluences += 1
            if rsi_oversold:
                additional_factors['rsi_extreme'] = min((self.params['rsi_oversold'] - rsi) / 30, 1.0)
            else:
                additional_factors['rsi_extreme'] = min((rsi - self.params['rsi_overbought']) / 30, 1.0)
        
        # Check 2: Bollinger Bands position
        total_checks += 1
        bb_breakout = False
        if bb_upper and bb_lower:
            bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)
            
            price_below_bb = current_price < bb_lower
            price_above_bb = current_price > bb_upper
            
            if price_below_bb or price_above_bb:
                confluences += 1
                bb_breakout = True
                
                # Extra points for extreme breakout
                if price_below_bb:
                    bb_distance = (bb_lower - current_price) / (bb_upper - bb_lower)
                else:
                    bb_distance = (current_price - bb_upper) / (bb_upper - bb_lower)
                
                additional_factors['bb_extreme'] = min(bb_distance * 2, 1.0)
        
        # Check 3: Stochastic extreme
        total_checks += 1
        stoch_oversold = stoch_k < self.params['stoch_oversold']
        stoch_overbought = stoch_k > self.params['stoch_overbought']
        
        if stoch_oversold or stoch_overbought:
            confluences += 1
        
        # Check 4: ADX (should be low for mean reversion)
        total_checks += 1
        low_adx = adx < self.params['adx_max']
        
        if low_adx:
            confluences += 1
            additional_factors['low_volatility'] = 1.0
        
        # Check 5: Stochastic crossover (confirmation)
        total_checks += 1
        prev_stoch_k = prev.get('stoch_k', stoch_k)
        
        stoch_cross_up = stoch_k > stoch_d and prev_stoch_k <= prev.get('stoch_d', stoch_d)
        stoch_cross_down = stoch_k < stoch_d and prev_stoch_k >= prev.get('stoch_d', stoch_d)
        
        if stoch_cross_up or stoch_cross_down:
            confluences += 0.5
        
        # Determine direction
        direction = None
        
        # Long setup: oversold conditions
        if rsi_oversold and (not bb_breakout or current_price < bb_lower) and stoch_oversold and low_adx:
            direction = OrderType.BUY
        
        # Short setup: overbought conditions
        elif rsi_overbought and (not bb_breakout or current_price > bb_upper) and stoch_overbought and low_adx:
            direction = OrderType.SELL
        
        # Calculate score
        regime_alignment = True
        if market_regime:
            # Mean reversion works best in ranging markets
            if market_regime not in [MarketRegime.RANGING, MarketRegime.LOW_VOLATILITY]:
                regime_alignment = False
                # Reduce score but don't invalidate
                additional_factors['regime_mismatch'] = -0.5
        
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
            # For mean reversion, use tighter stops
            stop_loss = self.calculate_stop_loss(
                direction, current_price, atr, self.params['atr_sl_multiplier']
            )
            
            # Take profit at mean (middle band) or opposite band
            if bb_middle:
                if direction == OrderType.BUY:
                    if self.params['mean_reversion_target'] == 'middle':
                        take_profit = bb_middle
                    else:
                        take_profit = bb_upper
                else:
                    if self.params['mean_reversion_target'] == 'middle':
                        take_profit = bb_middle
                    else:
                        take_profit = bb_lower
            else:
                take_profit = self.calculate_take_profit(
                    direction, current_price, stop_loss, self.params['rr_ratio']
                )
        
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
                'rsi': rsi,
                'stoch_k': stoch_k,
                'stoch_d': stoch_d,
                'bb_upper': bb_upper,
                'bb_middle': bb_middle,
                'bb_lower': bb_lower,
                'adx': adx,
            },
            notes=f"Mean reversion: {confluences}/{total_checks} confluences, RSI={rsi:.1f}"
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
        
        # Mean reversion typically has higher winrate but lower RR
        if winrate > 0.50 and profit_factor > 1.1:
            self.weight = min(self.weight * 1.1, 2.0)
        elif winrate < 0.40 or profit_factor < 0.9:
            self.weight = max(self.weight * 0.9, 0.5)

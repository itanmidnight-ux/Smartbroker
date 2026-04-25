"""
Trend Following Strategy.
Enters trades in the direction of the established trend.
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Dict

from strategies.base_strategy import BaseStrategy, Signal
from config.constants import OrderType, MarketRegime


class TrendFollowingStrategy(BaseStrategy):
    """
    Trend Following Strategy using multiple indicators for confluence.
    
    Entry conditions for LONG:
    - Price above MA(50) and MA(200)
    - ADX > 25 (strong trend)
    - MACD bullish crossover or positive
    - RSI > 50 but < 70 (not overbought)
    - Ichimoku: Price above cloud
    
    Entry conditions for SHORT:
    - Price below MA(50) and MA(200)
    - ADX > 25 (strong trend)
    - MACD bearish crossover or negative
    - RSI < 50 but > 30 (not oversold)
    - Ichimoku: Price below cloud
    """
    
    def __init__(self, params: Optional[Dict] = None):
        default_params = {
            'ma_fast': 50,
            'ma_slow': 200,
            'adx_threshold': 25,
            'rsi_min': 50,
            'rsi_max': 70,
            'atr_sl_multiplier': 2.0,
            'rr_ratio': 2.0,
        }
        super().__init__('trend_following', {**default_params, **(params or {})})
    
    def generate_signal(
        self,
        df: pd.DataFrame,
        current_price: float,
        symbol: str,
        market_regime: Optional[MarketRegime] = None
    ) -> Signal:
        if len(df) < self.params['ma_slow']:
            return self._create_empty_signal(symbol)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        confluences = 0
        total_checks = 0
        additional_factors = {}
        
        # Calculate moving averages if not present
        if 'ma_50' not in df.columns:
            ma_fast = df['close'].rolling(window=self.params['ma_fast']).mean().iloc[-1]
            ma_slow = df['close'].rolling(window=self.params['ma_slow']).mean().iloc[-1]
        else:
            ma_fast = latest.get('ma_20', latest['close'])  # Fallback
            ma_slow = latest.get('ma_50', latest['close'])
        
        # Check 1: MA Alignment
        total_checks += 1
        ma_bullish = current_price > ma_fast > ma_slow
        ma_bearish = current_price < ma_fast < ma_slow
        
        if ma_bullish or ma_bearish:
            confluences += 1
            additional_factors['ma_alignment'] = 1.0
        
        # Check 2: ADX (trend strength)
        total_checks += 1
        adx = latest.get('adx', 0)
        if adx > self.params['adx_threshold']:
            confluences += 1
            additional_factors['adx_strength'] = min((adx - self.params['adx_threshold']) / 20, 1.0)
        
        # Check 3: MACD
        total_checks += 1
        macd = latest.get('macd', 0)
        macd_signal = latest.get('macd_signal', 0)
        macd_hist = latest.get('macd_hist', 0)
        
        prev_macd_hist = prev.get('macd_hist', 0) if len(df) > 1 else macd_hist
        
        macd_bullish = macd > macd_signal and macd_hist > 0
        macd_bearish = macd < macd_signal and macd_hist < 0
        
        # Check for crossover
        macd_crossover_bullish = macd_hist > 0 and prev_macd_hist <= 0
        macd_crossover_bearish = macd_hist < 0 and prev_macd_hist >= 0
        
        if macd_crossover_bullish or macd_crossover_bearish:
            confluences += 1
            additional_factors['macd_crossover'] = 1.0
        elif macd_bullish or macd_bearish:
            confluences += 0.5
        
        # Check 4: RSI
        total_checks += 1
        rsi = latest.get('rsi', 50)
        
        rsi_bullish = self.params['rsi_min'] < rsi < self.params['rsi_max']
        rsi_bearish = (100 - self.params['rsi_max']) < rsi < (100 - self.params['rsi_min'])
        
        if rsi_bullish or rsi_bearish:
            confluences += 1
        
        # Check 5: Ichimoku (if available)
        total_checks += 1
        senkou_a = latest.get('senkou_span_a')
        senkou_b = latest.get('senkou_span_b')
        
        if senkou_a is not None and senkou_b is not None:
            cloud_top = max(senkou_a, senkou_b)
            cloud_bottom = min(senkou_a, senkou_b)
            
            ichimoku_bullish = current_price > cloud_top
            ichimoku_bearish = current_price < cloud_bottom
            
            if ichimoku_bullish or ichimoku_bearish:
                confluences += 1
                additional_factors['ichimoku'] = 1.0
        else:
            # Skip this check if Ichimoku not available
            total_checks -= 1
        
        # Determine direction
        direction = None
        if ma_bullish and (macd_bullish or macd_crossover_bullish) and rsi_bullish:
            direction = OrderType.BUY
        elif ma_bearish and (macd_bearish or macd_crossover_bearish) and rsi_bearish:
            direction = OrderType.SELL
        
        # Calculate score
        regime_alignment = True
        if market_regime:
            if direction == OrderType.BUY and market_regime in [MarketRegime.TRENDING_DOWN, MarketRegime.RANGING]:
                regime_alignment = False
            elif direction == OrderType.SELL and market_regime in [MarketRegime.TRENDING_UP, MarketRegime.RANGING]:
                regime_alignment = False
        
        score = self.calculate_score(
            confluences=int(confluences),
            total_checks=total_checks,
            regime_alignment=regime_alignment,
            additional_factors=additional_factors
        )
        
        # Calculate SL/TP
        atr = latest.get('atr', current_price * 0.01)
        stop_loss = None
        take_profit = None
        
        if direction:
            stop_loss = self.calculate_stop_loss(direction, current_price, atr, self.params['atr_sl_multiplier'])
            take_profit = self.calculate_take_profit(direction, current_price, stop_loss, self.params['rr_ratio'])
        
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
                'macd': macd,
                'adx': adx,
                'ma_fast': ma_fast,
                'ma_slow': ma_slow,
            },
            notes=f"Trend strategy: {confluences}/{total_checks} confluences"
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
        
        # Increase weight for good performance
        if winrate > 0.55 and profit_factor > 1.2:
            self.weight = min(self.weight * 1.1, 2.0)
        elif winrate < 0.45 or profit_factor < 0.8:
            self.weight = max(self.weight * 0.9, 0.5)

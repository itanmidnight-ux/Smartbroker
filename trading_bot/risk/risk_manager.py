"""
Trading Bot ML - Advanced Risk Management Module v2.0
Sistema de gestión de riesgo profesional basado en XAU_USD_MultiTrader_Pro v7.5
Incluye: Pirámide de lotes, protección de capital, Peak Profit Close, Kill Switch
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from enum import Enum

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Regímenes de mercado detectados por el Supervisor LLM"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    VOLATILE = "volatile"
    TRENDING = "trending"
    RANGING = "ranging"


class RiskManager:
    """
    Gestor de riesgo profesional con todas las características del MQL5 v7.5
    """
    
    def __init__(self, initial_capital: float = 1000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.protected_capital = 0.0
        self.working_capital = initial_capital
        
        # Configuración de riesgo
        self.risk_per_trade_pct = 0.5  # 0.5% por trade
        self.max_daily_loss_pct = 5.0  # 5% máximo diario
        self.critical_drawdown_pct = 10.0  # 10% drawdown crítico
        self.max_consecutive_losses = 3
        self.rr_minimum = 3.0  # Risk/Reward mínimo 3:1
        
        # Estado diario
        self.daily_profit = 0.0
        self.daily_loss = 0.0
        self.consecutive_losses = 0
        self.total_trades_today = 0
        
        # Historial
        self.profit_history = []
        self.loss_history = []
        self.trade_history = []
        
        # Kill Switch
        self.kill_switch_active = False
        self.kill_switch_reason = ""
        
        # Pirámide de lotes (configuración MQL5)
        self.pyramid_enabled = True
        self.pyramid_tiers = [
            {'capital_max': 1000, 'lot': 0.01},
            {'capital_max': 3000, 'lot': 0.02},
            {'capital_max': 6000, 'lot': 0.03},
            {'capital_max': 10000, 'lot': 0.05},
            {'capital_max': float('inf'), 'lot': 0.10}
        ]
        
        # Protección de capital
        self.capital_protection_enabled = True
        self.capital_protection_threshold = 30.0
        self.capital_preservation_pct = 20.0
        
        # Peak Profit Close
        self.peak_profit_enabled = True
        self.peak_profit_retrace_pct = 30.0
        self.peak_records = {}  # ticket -> peak_profit
        
        # Filtros
        self.spread_atr_max_ratio = 0.4
        self.extreme_market_detected = False
        
    def calculate_position_size(self, symbol_price: float, 
                                atr: float,
                                stop_loss_pips: float,
                                account_balance: float) -> float:
        """
        Calcular tamaño de posición usando pirámide de lotes y riesgo por trade
        
        Returns:
            lot_size: Tamaño de lote calculado
        """
        # Determinar lote base según pirámide de capital
        base_lot = self._get_pyramid_lot(account_balance)
        
        # Ajustar por riesgo
        risk_amount = account_balance * (self.risk_per_trade_pct / 100)
        
        # Calcular lote basado en stop loss
        if stop_loss_pips > 0:
            pip_value = symbol_price * 0.0001  # Aproximación para Forex
            calculated_lot = risk_amount / (stop_loss_pips * pip_value)
            
            # Usar el menor entre el calculado y el de la pirámide
            final_lot = min(base_lot, calculated_lot)
        else:
            final_lot = base_lot
        
        # Redondear a 2 decimales
        final_lot = round(final_lot, 2)
        
        logger.info(f"Position size calculated: {final_lot} lots (pyramid: {base_lot}, risk-based: {calculated_lot if stop_loss_pips > 0 else 'N/A'})")
        return final_lot
    
    def _get_pyramid_lot(self, capital: float) -> float:
        """Obtener lote según tier de pirámide de capital"""
        for tier in self.pyramid_tiers:
            if capital <= tier['capital_max']:
                return tier['lot']
        return self.pyramid_tiers[-1]['lot']
    
    def validate_trade(self, 
                      spread: float, 
                      atr: float,
                      confidence_score: float,
                      min_confidence: float) -> Tuple[bool, str]:
        """
        Validar si un trade puede ser ejecutado (sistema de filtros MQL5)
        
        Returns:
            (es_valido, razon)
        """
        # 1. Kill Switch check
        if self.kill_switch_active:
            return False, f"Kill Switch activo: {self.kill_switch_reason}"
        
        # 2. Spread/ATR filter (CRÍTICO - como en MQL5 v7.5)
        if atr > 0:
            spread_atr_ratio = spread / atr
            if spread_atr_ratio > self.spread_atr_max_ratio:
                return False, f"Spread/ATR ratio {spread_atr_ratio:.2f} > {self.spread_atr_max_ratio}"
        
        # 3. Confidence score filter
        if confidence_score < min_confidence:
            return False, f"Confianza {confidence_score:.2f} < mínimo {min_confidence}"
        
        # 4. Daily loss limit
        daily_total = self.daily_profit - self.daily_loss
        if abs(daily_total) > (self.initial_capital * self.max_daily_loss_pct / 100):
            return False, f"Límite de pérdida diaria alcanzado"
        
        # 5. Consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, f"Máximo de pérdidas consecutivas ({self.max_consecutive_losses})"
        
        # 6. Extreme market detection
        if self.extreme_market_detected:
            return False, "Mercado extremo detectado - operaciones pausadas"
        
        return True, "Trade validado correctamente"
    
    def update_daily_stats(self, profit_loss: float):
        """Actualizar estadísticas diarias después de cerrar un trade"""
        if profit_loss > 0:
            self.daily_profit += profit_loss
            self.consecutive_losses = 0
            self.profit_history.append(profit_loss)
        else:
            self.daily_loss += abs(profit_loss)
            self.consecutive_losses += 1
            self.loss_history.append(abs(profit_loss))
        
        self.total_trades_today += 1
        self.trade_history.append({
            'timestamp': datetime.now(),
            'profit_loss': profit_loss
        })
        
        logger.info(f"Daily stats updated: P/L=${profit_loss:.2f}, Consecutive losses: {self.consecutive_losses}")
    
    def reset_daily_stats(self):
        """Resetear estadísticas diarias (nuevo día)"""
        logger.info(f"Resetting daily stats. Previous: Profit=${self.daily_profit:.2f}, Loss=${self.daily_loss:.2f}")
        self.daily_profit = 0.0
        self.daily_loss = 0.0
        self.consecutive_losses = 0
        self.total_trades_today = 0
    
    def activate_kill_switch(self, reason: str):
        """Activar Kill Switch para detener operaciones"""
        self.kill_switch_active = True
        self.kill_switch_reason = reason
        logger.critical(f"🚨 KILL SWITCH ACTIVATED: {reason}")
    
    def deactivate_kill_switch(self):
        """Desactivar Kill Switch"""
        self.kill_switch_active = False
        old_reason = self.kill_switch_reason
        self.kill_switch_reason = ""
        logger.info(f"✅ Kill Switch deactivated. Previous reason: {old_reason}")
    
    def check_capital_protection(self, current_balance: float) -> bool:
        """
        Verificar y activar protección de capital si es necesario
        
        Returns:
            protection_active: Si la protección está activa
        """
        if not self.capital_protection_enabled:
            return False
        
        total_profit = current_balance - self.initial_capital
        
        if total_profit >= self.capital_protection_threshold:
            # Activar protección
            self.protected_capital = total_profit * (self.capital_preservation_pct / 100)
            self.working_capital = current_balance - self.protected_capital
            logger.info(f"💰 Capital protection activated: Protected=${self.protected_capital:.2f}, Working=${self.working_capital:.2f}")
            return True
        
        return False
    
    def track_peak_profit(self, ticket: int, current_profit: float):
        """Rastrear pico de ganancia para Peak Profit Close"""
        if not self.peak_profit_enabled:
            return
        
        if ticket not in self.peak_records:
            self.peak_records[ticket] = current_profit
        else:
            # Actualizar pico si es mayor
            if current_profit > self.peak_records[ticket]:
                self.peak_records[ticket] = current_profit
    
    def should_close_at_peak(self, ticket: int, current_profit: float) -> bool:
        """
        Verificar si se debe cerrar un trade por retroceso desde el pico
        
        Returns:
            should_close: Si se debe cerrar
        """
        if not self.peak_profit_enabled:
            return False
        
        if ticket not in self.peak_records:
            return False
        
        peak = self.peak_records[ticket]
        
        # Solo aplicar si hay ganancias
        if peak <= 0 or current_profit <= 0:
            return False
        
        # Calcular retroceso
        retrace_pct = ((peak - current_profit) / peak) * 100
        
        if retrace_pct >= self.peak_profit_retrace_pct:
            logger.info(f"📉 Peak Profit Close triggered for #{ticket}: Peak=${peak:.2f}, Current=${current_profit:.2f}, Retrace={retrace_pct:.1f}%")
            return True
        
        return False
    
    def adjust_risk_for_market_regime(self, regime: MarketRegime):
        """Ajustar parámetros de riesgo según régimen de mercado"""
        if regime == MarketRegime.VOLATILE:
            # Reducir riesgo en mercados volátiles
            self.risk_per_trade_pct = 0.25  # Mitad del riesgo normal
            self.spread_atr_max_ratio = 0.3  # Filtro más estricto
            logger.warning("⚠️ Volatile market detected - Risk reduced to 0.25%")
            
        elif regime == MarketRegime.TRENDING:
            # Aumentar ligeramente en tendencias claras
            self.risk_per_trade_pct = 0.75
            logger.info("📈 Trending market detected - Risk increased to 0.75%")
            
        elif regime == MarketRegime.RANGING:
            # Riesgo normal en rangos
            self.risk_per_trade_pct = 0.5
            logger.info("➡️ Ranging market detected - Normal risk 0.5%")
    
    def set_extreme_market_flag(self, is_extreme: bool, reason: str = ""):
        """Marcar mercado como extremo"""
        self.extreme_market_detected = is_extreme
        if is_extreme:
            logger.warning(f"🚨 EXTREME MARKET DETECTED: {reason}")
            # Reducir riesgo automáticamente
            self.risk_per_trade_pct = 0.25
        else:
            logger.info("✅ Market conditions normalized")
            self.risk_per_trade_pct = 0.5
    
    def get_statistics(self) -> Dict:
        """Obtener estadísticas completas del gestor de riesgo"""
        total_profit = sum(self.profit_history) if self.profit_history else 0
        total_loss = sum(self.loss_history) if self.loss_history else 0
        
        win_count = len(self.profit_history)
        loss_count = len(self.loss_history)
        total_trades = win_count + loss_count
        
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
        profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')
        
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'protected_capital': self.protected_capital,
            'working_capital': self.working_capital,
            'daily_profit': self.daily_profit,
            'daily_loss': self.daily_loss,
            'consecutive_losses': self.consecutive_losses,
            'kill_switch_active': self.kill_switch_active,
            'extreme_market': self.extreme_market_detected,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_profit': total_profit,
            'total_loss': total_loss,
            'risk_per_trade_pct': self.risk_per_trade_pct
        }


class TradeValidator:
    """
    Sistema de validación de trades multi-nivel inspirado en MQL5 v7.5
    Implementa el sistema "POSIBLE" de validación progresiva
    """
    
    def __init__(self):
        self.validation_factors = []
        self.valid_threshold_m15 = 3  # Mínimo 3/5 factores para M15
        self.valid_threshold_h1 = 2   # Mínimo 2/5 para H1/H4 (más leniente)
        
    def add_validation_factor(self, name: str, is_valid: bool, weight: float = 1.0):
        """Añadir factor de validación"""
        self.validation_factors.append({
            'name': name,
            'valid': is_valid,
            'weight': weight
        })
    
    def validate(self, timeframe: str) -> Tuple[bool, str]:
        """
        Validar trade basado en múltiples factores
        
        Returns:
            (es_valido, resumen)
        """
        if not self.validation_factors:
            return False, "No hay factores de validación"
        
        # Determinar threshold según timeframe
        if timeframe in ['1h', '4h', '8h', '12h']:
            threshold = self.valid_threshold_h1
        else:
            threshold = self.valid_threshold_m15
        
        # Contar factores válidos
        valid_count = sum(1 for f in self.validation_factors if f['valid'])
        total_factors = len(self.validation_factors)
        
        is_valid = valid_count >= threshold
        
        # Crear resumen
        summary = f"{valid_count}/{total_factors} factores válidos (mínimo requerido: {threshold})\n"
        for factor in self.validation_factors:
            status = "✅" if factor['valid'] else "❌"
            summary += f"  {status} {factor['name']}\n"
        
        # Resetear para próxima validación
        self.validation_factors = []
        
        return is_valid, summary
    
    def get_possible_state(self, ticket: int, open_time: datetime, 
                          direction: int) -> Dict:
        """
        Crear estado de trade POSIBLE (sistema MQL5)
        
        Returns:
            possible_state: Diccionario con estado del trade
        """
        return {
            'ticket': ticket,
            'open_time': open_time,
            'last_check_time': datetime.now(),
            'direction': direction,
            'validation_count': 0,
            'is_possible': True,
            'validation_reason': ''
        }


# Funciones utilitarias
def calculate_dynamic_sl_tp(entry_price: float, 
                           atr: float,
                           direction: int,
                           rr_ratio: float = 3.0) -> Tuple[float, float]:
    """
    Calcular Stop Loss y Take Profit dinámicos basados en ATR
    
    Args:
        entry_price: Precio de entrada
        atr: Average True Range actual
        direction: 1 para LONG, -1 para SHORT
        rr_ratio: Risk/Reward ratio deseado
        
    Returns:
        (stop_loss, take_profit)
    """
    sl_distance = atr * 1.5  # SL a 1.5x ATR
    tp_distance = sl_distance * rr_ratio  # TP a 3x el SL
    
    if direction == 1:  # LONG
        stop_loss = entry_price - sl_distance
        take_profit = entry_price + tp_distance
    else:  # SHORT
        stop_loss = entry_price + sl_distance
        take_profit = entry_price - tp_distance
    
    return stop_loss, take_profit


def get_trade_maturity_seconds(timeframe: str) -> int:
    """
    Obtener tiempo mínimo de madurez del trade antes de validar (MQL5 v7.5)
    
    Evita cierres prematuros en TF amplios donde el precio necesita tiempo.
    """
    maturity_map = {
        '5m': 30,
        '15m': 60,    # 1 minuto mínimo
        '30m': 300,   # 5 minutos mínimo
        '1h': 600,    # 10 minutos mínimo
        '2h': 900,
        '4h': 1200,   # 20 minutos mínimo
        '8h': 1800,
        '12h': 2400
    }
    
    return maturity_map.get(timeframe, 60)

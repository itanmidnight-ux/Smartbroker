"""
Trading Bot ML - Core Trading Engine v2.0
Motor principal de trading que integra ML, Risk Management y Data Fetching
Inspirado en XAU_USD_MultiTrader_Pro v7.5 STABLE
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import time
import threading
import json

import pandas as pd
import numpy as np

from trading_bot.data.data_fetcher import DataFetcher, TechnicalIndicators
from trading_bot.ml.ml_engine import MLEngine
from trading_bot.risk.risk_manager import (
    RiskManager, 
    TradeValidator, 
    MarketRegime,
    calculate_dynamic_sl_tp,
    get_trade_maturity_seconds
)
from trading_bot.core.llm_supervisor import LLMSupervisor
from trading_bot.simulation.trading_simulator import TradingSimulator

logger = logging.getLogger(__name__)


class TradingEngine:
    """
    Motor de trading principal que coordina todos los subsistemas
    Implementa arquitectura profesional tipo EA de MetaTrader 5
    """
    
    def __init__(self, symbol: str = "GC=F", initial_capital: float = 1000.0):
        self.symbol = symbol
        self.initial_capital = initial_capital
        
        # Inicializar componentes
        self.data_fetcher = DataFetcher()
        self.ml_engine = MLEngine()
        self.risk_manager = RiskManager(initial_capital)
        self.trade_validator = TradeValidator()
        self.llm_supervisor = LLMSupervisor()
        self.simulator = TradingSimulator(initial_capital)
        
        # Estado del motor
        self.is_running = False
        self.current_timeframe = "15m"
        self.active_trades = {}
        self.pending_trades = []
        
        # Variables de control de velas (como en MQL5 v7.5)
        self.last_candle_close_time = 0
        self.last_trade_close_time = 0
        self.candle_trade_executed = False
        self.next_trade_allowed_time = 0
        self.last_trade_open_candle_time = 0
        
        # Sistema POSIBLE (validación progresiva)
        self.possible_trades = []
        
        # Estadísticas
        self.signals_generated = 0
        self.trades_executed = 0
        self.last_update = None
        
        # Hilos
        self.trading_thread = None
        self.supervisor_thread = None
        
    def start(self, timeframe: str = "15m"):
        """Iniciar el motor de trading"""
        if self.is_running:
            logger.warning("El motor ya está en ejecución")
            return
        
        self.current_timeframe = timeframe
        self.is_running = True
        
        logger.info(f"🚀 Iniciando Trading Engine para {self.symbol} en {timeframe}")
        
        # Iniciar hilo de trading
        self.trading_thread = threading.Thread(target=self._trading_loop, daemon=True)
        self.trading_thread.start()
        
        # Iniciar hilo del supervisor LLM
        self.supervisor_thread = threading.Thread(target=self._supervisor_loop, daemon=True)
        self.supervisor_thread.start()
        
        logger.info("✅ Trading Engine iniciado correctamente")
    
    def stop(self):
        """Detener el motor de trading"""
        self.is_running = False
        logger.info("⏹️ Trading Engine detenido")
    
    def _trading_loop(self):
        """Bucle principal de trading (se ejecuta en hilo separado)"""
        logger.info("🔄 Trading loop iniciado")
        
        while self.is_running:
            try:
                # Control de velocidad (throttling como en MQL5)
                current_time = time.time()
                if current_time == self.last_update:
                    time.sleep(0.1)
                    continue
                
                self.last_update = current_time
                
                # Ejecutar ciclo de trading
                self._execute_trading_cycle()
                
                # Esperar antes del siguiente ciclo
                time.sleep(5)  # Verificar cada 5 segundos
                
            except Exception as e:
                logger.error(f"Error en trading loop: {str(e)}", exc_info=True)
                time.sleep(10)
    
    def _supervisor_loop(self):
        """Bucle del supervisor LLM (se ejecuta en hilo separado)"""
        logger.info("🧠 Supervisor LLM loop iniciado")
        
        while self.is_running:
            try:
                # Ejecutar análisis del supervisor cada 10 minutos
                self._run_supervisor_analysis()
                
                # Esperar 10 minutos
                for _ in range(120):  # 120 * 5s = 600s = 10min
                    if not self.is_running:
                        break
                    time.sleep(5)
                    
            except Exception as e:
                logger.error(f"Error en supervisor loop: {str(e)}", exc_info=True)
                time.sleep(60)
    
    def _execute_trading_cycle(self):
        """Ejecutar un ciclo completo de trading"""
        # 1. Obtener datos actualizados
        df = self.data_fetcher.fetch_data(self.symbol, self.current_timeframe)
        
        if df is None or df.empty:
            logger.warning("No hay datos disponibles")
            return
        
        # 2. Calcular indicadores técnicos
        df = TechnicalIndicators.calculate_all_indicators(df, self.current_timeframe)
        
        if df.empty:
            logger.warning("No se pudieron calcular indicadores")
            return
        
        # 3. Verificar filtros de mercado
        spread_valid, spread_ratio = self.data_fetcher.validate_spread_atr_ratio(df)
        if not spread_valid:
            logger.warning(f"❌ Filtro Spread/ATR fallido: {spread_ratio:.2f}")
            return
        
        # 4. Detectar condiciones extremas
        extreme_state = self.data_fetcher.detect_market_extremes(df)
        self.risk_manager.set_extreme_market_flag(
            extreme_state['extreme'],
            extreme_state['reason']
        )
        
        # 5. Obtener predicción del ML
        prediction = self.ml_engine.predict_signal(df, self.current_timeframe)
        
        if prediction is None:
            logger.warning("No hay predicción del ML")
            return
        
        signal = prediction.get('signal', 'HOLD')
        confidence = prediction.get('confidence', 0.0)
        
        # 6. Validar trade con múltiples factores
        self._add_validation_factors(df, prediction)
        is_valid, validation_summary = self.trade_validator.validate(self.current_timeframe)
        
        if not is_valid:
            logger.debug(f"Trade no válido: {validation_summary}")
            return
        
        # 7. Validar con risk manager
        current_spread = df['spread_pct'].iloc[-1]
        current_atr = df['atr'].iloc[-1]
        min_confidence = self._get_min_confidence_for_mode()
        
        risk_valid, risk_reason = self.risk_manager.validate_trade(
            spread=current_spread,
            atr=current_atr,
            confidence_score=confidence,
            min_confidence=min_confidence
        )
        
        if not risk_valid:
            logger.warning(f"❌ Risk Manager rechazó trade: {risk_reason}")
            return
        
        # 8. Generar señal de trading
        if signal != 'HOLD':
            self.signals_generated += 1
            self._process_signal(signal, confidence, df)
    
    def _add_validation_factors(self, df: pd.DataFrame, prediction: Dict):
        """Añadir factores de validación para el sistema POSIBLE"""
        # Factor 1: Tendencia EMA
        ema_fast = df['ema_20'].iloc[-1]
        ema_slow = df['ema_50'].iloc[-1]
        trend_valid = (ema_fast > ema_slow) if prediction['signal'] == 'BUY' else (ema_fast < ema_slow)
        self.trade_validator.add_validation_factor("EMA_Trend", trend_valid)
        
        # Factor 2: RSI no sobreextendido
        rsi = df['rsi_14'].iloc[-1]
        rsi_valid = True
        if prediction['signal'] == 'BUY':
            rsi_valid = rsi < 70  # No sobrecomprado
        elif prediction['signal'] == 'SELL':
            rsi_valid = rsi > 30  # No sobreventa
        self.trade_validator.add_validation_factor("RSI_Filter", rsi_valid)
        
        # Factor 3: Volumen suficiente
        volume_ratio = df.get('volume_ratio', pd.Series([1.0])).iloc[-1]
        volume_valid = volume_ratio > 0.8
        self.trade_validator.add_validation_factor("Volume", volume_valid)
        
        # Factor 4: Volatilidad adecuada
        atr_pct = df['atr_pct'].iloc[-1]
        vol_valid = 0.001 < atr_pct < 0.05  # Ni muy baja ni muy alta
        self.trade_validator.add_validation_factor("Volatility", vol_valid)
        
        # Factor 5: Confianza ML
        ml_valid = prediction.get('confidence', 0) > 0.6
        self.trade_validator.add_validation_factor("ML_Confidence", ml_valid)
    
    def _get_min_confidence_for_mode(self) -> float:
        """Obtener confianza mínima según modo de operación"""
        # Esto debería venir de la configuración
        mode = "normal"  # safe, normal, aggressive, very_active
        
        confidence_map = {
            'safe': 0.85,
            'normal': 0.75,
            'aggressive': 0.65,
            'very_active': 0.55
        }
        
        return confidence_map.get(mode, 0.75)
    
    def _process_signal(self, signal: str, confidence: float, df: pd.DataFrame):
        """Procesar señal de trading y ejecutar en simulador"""
        current_price = df['Close'].iloc[-1]
        current_atr = df['atr'].iloc[-1]
        
        # Determinar dirección
        direction = 1 if signal == 'BUY' else -1
        
        # Calcular SL y TP dinámicos
        sl, tp = calculate_dynamic_sl_tp(
            entry_price=current_price,
            atr=current_atr,
            direction=direction,
            rr_ratio=3.0
        )
        
        # Calcular tamaño de posición
        position_size = self.risk_manager.calculate_position_size(
            symbol_price=current_price,
            atr=current_atr,
            stop_loss_pips=abs(current_price - sl),
            account_balance=self.risk_manager.current_capital
        )
        
        # Crear ticket único
        ticket = int(time.time() * 1000)
        
        # Ejecutar en simulador
        trade_result = self.simulator.open_position(
            symbol=self.symbol,
            direction=signal,
            entry_price=current_price,
            stop_loss=sl,
            take_profit=tp,
            lot_size=position_size,
            timeframe=self.current_timeframe,
            confidence=confidence
        )
        
        if trade_result:
            self.trades_executed += 1
            self.active_trades[ticket] = {
                'ticket': ticket,
                'symbol': self.symbol,
                'direction': signal,
                'entry_price': current_price,
                'stop_loss': sl,
                'take_profit': tp,
                'lot_size': position_size,
                'open_time': datetime.now(),
                'timeframe': self.current_timeframe,
                'confidence': confidence
            }
            
            # Registrar en log CSV
            self.data_fetcher.log_trade_event(
                event_type="OPEN",
                symbol=self.symbol,
                timeframe=self.current_timeframe,
                price=current_price,
                spread=df['spread_pct'].iloc[-1],
                atr=current_atr,
                signal=signal,
                confidence=confidence,
                action=f"BUY_{position_size}_lots" if signal == 'BUY' else f"SELL_{position_size}_lots",
                notes=f"Ticket #{ticket}"
            )
            
            logger.info(f"🎯 TRADE EJECUTADO: {signal} {self.symbol} @ {current_price:.2f} | SL: {sl:.2f} | TP: {tp:.2f} | Lots: {position_size}")
    
    def _run_supervisor_analysis(self):
        """Ejecutar análisis del supervisor LLM"""
        logger.info("🔍 Ejecutando análisis del supervisor LLM...")
        
        # Obtener datos recientes
        df = self.data_fetcher.fetch_data(self.symbol, self.current_timeframe)
        
        if df is None or df.empty:
            return
        
        # Obtener estadísticas del risk manager
        risk_stats = self.risk_manager.get_statistics()
        
        # Obtener estadísticas del simulador
        sim_stats = self.simulator.get_statistics()
        
        # Ejecutar análisis del supervisor
        analysis = self.llm_supervisor.analyze_market(
            market_data=df,
            current_position=None,  # Podría pasar la posición actual
            risk_stats=risk_stats,
            performance_stats=sim_stats
        )
        
        if analysis:
            # Aplicar recomendaciones del supervisor
            self._apply_supervisor_recommendations(analysis)
    
    def _apply_supervisor_recommendations(self, analysis: Dict):
        """Aplicar recomendaciones del supervisor LLM"""
        regime_str = analysis.get('market_regime', 'neutral')
        
        try:
            regime = MarketRegime(regime_str)
            self.risk_manager.adjust_risk_for_market_regime(regime)
            logger.info(f"📊 Régimen de mercado aplicado: {regime.value}")
        except ValueError:
            logger.warning(f"Régimen de mercado desconocido: {regime_str}")
        
        # Aplicar ajustes de parámetros si los hay
        adjustments = analysis.get('parameter_adjustments', {})
        
        if 'risk_per_trade' in adjustments:
            old_risk = self.risk_manager.risk_per_trade_pct
            self.risk_manager.risk_per_trade_pct = adjustments['risk_per_trade']
            logger.info(f"⚙️ Riesgo ajustado: {old_risk}% → {self.risk_manager.risk_per_trade_pct}%")
        
        if 'min_confidence' in adjustments:
            # Esto debería guardarse en configuración global
            logger.info(f"⚙️ Confianza mínima ajustada a: {adjustments['min_confidence']}")
    
    def update_positions(self):
        """Actualizar posiciones abiertas (verificar SL/TP/Trailing)"""
        for ticket, trade in list(self.active_trades.items()):
            # Obtener precio actual
            current_price = self.data_fetcher.get_latest_price(self.symbol)
            
            if current_price is None:
                continue
            
            # Verificar si se debe cerrar por Peak Profit Close
            unrealized_pnl = self._calculate_unrealized_pnl(trade, current_price)
            
            if self.risk_manager.should_close_at_peak(ticket, unrealized_pnl):
                self._close_position(ticket, current_price, "PEAK_PROFIT")
                continue
            
            # Verificar SL y TP
            if trade['direction'] == 'BUY':
                if current_price <= trade['stop_loss']:
                    self._close_position(ticket, current_price, "STOP_LOSS")
                elif current_price >= trade['take_profit']:
                    self._close_position(ticket, current_price, "TAKE_PROFIT")
            else:  # SELL
                if current_price >= trade['stop_loss']:
                    self._close_position(ticket, current_price, "STOP_LOSS")
                elif current_price <= trade['take_profit']:
                    self._close_position(ticket, current_price, "TAKE_PROFIT")
    
    def _calculate_unrealized_pnl(self, trade: Dict, current_price: float) -> float:
        """Calcular P&L no realizado de un trade"""
        if trade['direction'] == 'BUY':
            pnl = (current_price - trade['entry_price']) * trade['lot_size'] * 100
        else:
            pnl = (trade['entry_price'] - current_price) * trade['lot_size'] * 100
        
        return pnl
    
    def _close_position(self, ticket: int, exit_price: float, reason: str):
        """Cerrar posición"""
        if ticket not in self.active_trades:
            return
        
        trade = self.active_trades[ticket]
        
        # Calcular P&L
        pnl = self._calculate_unrealized_pnl(trade, exit_price)
        
        # Cerrar en simulador
        close_result = self.simulator.close_position(ticket, exit_price)
        
        if close_result:
            # Actualizar risk manager
            self.risk_manager.update_daily_stats(pnl)
            self.risk_manager.track_peak_profit(ticket, pnl)
            
            # Registrar en log
            self.data_fetcher.log_trade_event(
                event_type="CLOSE",
                symbol=self.symbol,
                timeframe=trade['timeframe'],
                price=exit_price,
                spread=0,
                atr=0,
                signal=trade['direction'],
                confidence=trade['confidence'],
                action=f"CLOSE_{reason}",
                profit_loss=pnl,
                notes=f"Ticket #{ticket}"
            )
            
            logger.info(f"💰 POSICIÓN CERRADA: #{ticket} {reason} | P&L: ${pnl:.2f}")
            
            # Eliminar de activos
            del self.active_trades[ticket]
    
    def get_status(self) -> Dict:
        """Obtener estado completo del motor"""
        return {
            'is_running': self.is_running,
            'symbol': self.symbol,
            'timeframe': self.current_timeframe,
            'active_trades': len(self.active_trades),
            'signals_generated': self.signals_generated,
            'trades_executed': self.trades_executed,
            'last_update': self.last_update,
            'risk_stats': self.risk_manager.get_statistics(),
            'simulator_stats': self.simulator.get_statistics(),
            'possible_trades': len(self.possible_trades)
        }


# Singleton global
_engine_instance = None


def get_trading_engine(symbol: str = "GC=F", initial_capital: float = 1000.0) -> TradingEngine:
    """Obtener instancia singleton del motor de trading"""
    global _engine_instance
    
    if _engine_instance is None:
        _engine_instance = TradingEngine(symbol, initial_capital)
    
    return _engine_instance

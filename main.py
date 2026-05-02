"""
Trading Bot ML - Archivo Principal de Ejecución
Integra todos los módulos del sistema
"""

import sys
import os
import logging
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional

# Añadir ruta al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trading_bot.config.settings import (
    SUPPORTED_TIMEFRAMES,
    OPERATION_MODES,
    DEFAULT_SYMBOLS,
    LOG_FILE,
    LOG_FORMAT,
    LOG_LEVEL,
    TIMEFRAME_CONFIG
)
from trading_bot.data.data_fetcher import DataFetcher, TechnicalIndicators
from trading_bot.ml.ml_engine import AdaptiveMLManager
from trading_bot.simulation.trading_simulator import TradingSimulator
from trading_bot.core.llm_supervisor import LLMSupervisor
from trading_bot.core.web_server import WebServer


class TradingBot:
    """Clase principal del Trading Bot"""
    
    def __init__(self):
        # Configuración inicial
        self.running = False
        self.current_timeframe = '1h'
        self.current_mode = 'normal'
        self.tracked_symbols = DEFAULT_SYMBOLS[:5]  # Primeros 5 por defecto
        self.auto_adjust = True
        
        # Inicializar componentes
        self.data_fetcher = DataFetcher()
        self.ml_manager = AdaptiveMLManager()
        self.simulator = TradingSimulator()
        self.supervisor = LLMSupervisor()
        self.web_server = None
        
        # Estado actual
        self.latest_signals = {}
        self.market_data = {}
        self.logs_buffer = []
        
        # Configurar logging
        self._setup_logging()
        
        logger.info("=" * 60)
        logger.info("TRADING BOT ML INICIALIZADO")
        logger.info("=" * 60)
    
    def _setup_logging(self):
        """Configurar sistema de logging"""
        # Logger para archivo
        file_handler = logging.FileHandler(LOG_FILE)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        
        # Logger para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        
        # Configurar logger principal
        global logger
        logger = logging.getLogger('TradingBot')
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # Buffer para logs recientes
        class LogBufferHandler(logging.Handler):
            def __init__(self, bot_instance, max_lines=100):
                super().__init__()
                self.bot = bot_instance
                self.max_lines = max_lines
            
            def emit(self, record):
                log_entry = self.format(record)
                self.bot.logs_buffer.append(log_entry)
                if len(self.bot.logs_buffer) > self.max_lines:
                    self.bot.logs_buffer = self.bot.logs_buffer[-self.max_lines:]
        
        buffer_handler = LogBufferHandler(self)
        buffer_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(buffer_handler)
    
    def initialize(self):
        """Inicializar todos los componentes"""
        logger.info("Inicializando componentes...")
        
        # Inicializar ML Manager para todos los timeframes
        logger.info("Inicializando motores ML...")
        self.ml_manager.initialize_all_timeframes()
        
        # Cargar datos iniciales
        logger.info("Cargando datos iniciales...")
        self._load_initial_data()
        
        # Entrenar modelos si es necesario
        logger.info("Verificando entrenamiento de modelos...")
        self._ensure_models_trained()
        
        # Inicializar servidor web
        logger.info("Inicializando servidor web...")
        self.web_server = WebServer(bot_instance=self)
        
        logger.info("Inicialización completada")
    
    def _load_initial_data(self):
        """Cargar datos iniciales para todos los timeframes"""
        for tf in SUPPORTED_TIMEFRAMES:
            for symbol in self.tracked_symbols:
                try:
                    data = self.data_fetcher.fetch_data(symbol, tf)
                    if data is not None:
                        # Calcular indicadores
                        data_with_indicators = TechnicalIndicators.calculate_all_indicators(data, tf)
                        key = f"{symbol}_{tf}"
                        self.market_data[key] = data_with_indicators
                        logger.debug(f"Datos cargados: {key}")
                except Exception as e:
                    logger.error(f"Error cargando datos {symbol} {tf}: {str(e)}")
    
    def _ensure_models_trained(self):
        """Asegurar que los modelos estén entrenados"""
        for tf in SUPPORTED_TIMEFRAMES:
            engine = self.ml_manager.get_engine(tf)
            
            # Recopilar datos para este timeframe
            tf_data = []
            for symbol in self.tracked_symbols:
                key = f"{symbol}_{tf}"
                if key in self.market_data:
                    tf_data.append(self.market_data[key])
            
            if tf_data:
                # Combinar datos de múltiples símbolos
                combined_data = pd.concat(tf_data, ignore_index=False)
                
                # Verificar si necesita entrenamiento
                if not engine.is_fitted or len(combined_data) > len(engine.feature_names) * 10:
                    logger.info(f"Entrenando modelo para {tf}...")
                    engine.train(combined_data)
    
    def start(self):
        """Iniciar el bot"""
        if self.running:
            logger.warning("El bot ya está en ejecución")
            return
        
        logger.info("Iniciando Trading Bot...")
        self.running = True
        
        # Iniciar hilo de actualización de datos
        data_thread = threading.Thread(target=self._data_update_loop, daemon=True)
        data_thread.start()
        
        # Iniciar hilo de análisis y predicción
        prediction_thread = threading.Thread(target=self._prediction_loop, daemon=True)
        prediction_thread.start()
        
        # Iniciar hilo del supervisor LLM
        if self.auto_adjust:
            supervisor_thread = threading.Thread(target=self._supervisor_loop, daemon=True)
            supervisor_thread.start()
        
        # Iniciar servidor web (bloqueante)
        if self.web_server:
            self.web_server.start()
    
    def stop(self):
        """Detener el bot"""
        logger.info("Deteniendo Trading Bot...")
        self.running = False
        
        if self.web_server:
            self.web_server.stop()
        
        # Guardar modelos
        logger.info("Guardando modelos...")
        for tf in SUPPORTED_TIMEFRAMES:
            engine = self.ml_manager.get_engine(tf)
            if engine:
                engine.save_models()
        
        # Guardar resultados del simulador
        if hasattr(self, 'simulator'):
            self.simulator.save_results()
        
        # Guardar log del supervisor
        if hasattr(self, 'supervisor'):
            self.supervisor.save_analysis_log()
        
        logger.info("Trading Bot detenido correctamente")
    
    def _data_update_loop(self):
        """Bucle de actualización de datos"""
        update_interval = 60  # Segundos
        
        while self.running:
            try:
                # Actualizar datos para el timeframe actual
                for symbol in self.tracked_symbols:
                    data = self.data_fetcher.fetch_data(symbol, self.current_timeframe)
                    if data is not None:
                        data_with_indicators = TechnicalIndicators.calculate_all_indicators(data, self.current_timeframe)
                        key = f"{symbol}_{self.current_timeframe}"
                        self.market_data[key] = data_with_indicators
                
                logger.debug(f"Datos actualizados para {self.current_timeframe}")
                
            except Exception as e:
                logger.error(f"Error en actualización de datos: {str(e)}")
            
            time.sleep(update_interval)
    
    def _prediction_loop(self):
        """Bucle de predicción y generación de señales"""
        prediction_interval = 30  # Segundos
        
        while self.running:
            try:
                # Generar señales para cada símbolo
                for symbol in self.tracked_symbols:
                    key = f"{symbol}_{self.current_timeframe}"
                    
                    if key not in self.market_data:
                        continue
                    
                    df = self.market_data[key]
                    if len(df) < 50:
                        continue
                    
                    # Obtener predicción del ML
                    engine = self.ml_manager.get_engine(self.current_timeframe)
                    if engine and engine.is_fitted:
                        prediction = engine.predict(df)
                        
                        # Aplicar filtros del modo
                        mode_config = OPERATION_MODES[self.current_mode]
                        
                        if prediction['confidence'] >= mode_config['confidence_threshold']:
                            self.latest_signals[symbol] = prediction
                            
                            # Ejecutar en simulador si hay señal clara
                            if prediction['signal'] in ['BUY', 'SELL']:
                                self._execute_signal(symbol, prediction, df)
                        
                        # Actualizar performance del modelo
                        self._update_model_performance(symbol, engine)
                
                logger.debug(f"Señales generadas: {len(self.latest_signals)}")
                
            except Exception as e:
                logger.error(f"Error en predicción: {str(e)}")
            
            time.sleep(prediction_interval)
    
    def _execute_signal(self, symbol: str, prediction: Dict, df):
        """Ejecutar señal en el simulador"""
        try:
            current_price = df['Close'].iloc[-1]
            atr = df['atr'].iloc[-1] if 'atr' in df.columns else current_price * 0.02
            
            direction = 1 if prediction['signal'] == 'BUY' else -1
            
            # Verificar si ya hay posición abierta para este símbolo
            open_positions = self.simulator.get_open_positions()
            for pos in open_positions:
                if pos['symbol'] == symbol:
                    return  # Ya hay posición abierta
            
            # Calcular tamaño de posición
            mode_config = OPERATION_MODES[self.current_mode]
            position_size = (self.simulator.balance * mode_config['max_position_size']) / current_price
            
            # Abrir posición
            self.simulator.open_position(
                symbol=symbol,
                direction=direction,
                entry_price=current_price,
                position_size=position_size,
                atr=atr,
                timeframe=self.current_timeframe,
                mode=self.current_mode
            )
            
            logger.info(f"Señal ejecutada: {symbol} {prediction['signal']} @ {current_price:.4f}")
            
        except Exception as e:
            logger.error(f"Error ejecutando señal: {str(e)}")
    
    def _update_model_performance(self, symbol: str, engine):
        """Actualizar performance del modelo con resultados reales"""
        # Esta función se llamaría cuando una posición se cierra
        # para actualizar las estadísticas del modelo
        pass
    
    def _supervisor_loop(self):
        """Bucle del supervisor LLM"""
        analysis_interval = 300  # 5 minutos
        
        while self.running:
            try:
                # Obtener datos actuales
                key = f"{self.tracked_symbols[0]}_{self.current_timeframe}"
                if key in self.market_data:
                    df = self.market_data[key]
                    
                    # Analizar mercado
                    simulator_stats = self.simulator.get_statistics()
                    analysis = self.supervisor.analyze_market(df, self.current_timeframe, simulator_stats)
                    
                    # Evaluar performance
                    evaluation = self.supervisor.evaluate_performance(simulator_stats)
                    
                    # Hacer ajustes automáticos si es necesario
                    if evaluation.get('action_required') and self.auto_adjust:
                        current_params = OPERATION_MODES[self.current_mode].copy()
                        adjusted_params = self.supervisor.make_adjustments(analysis, current_params)
                        
                        # Aplicar ajustes sugeridos
                        suggested_mode = analysis.get('suggested_mode')
                        if suggested_mode and suggested_mode != self.current_mode:
                            logger.info(f"Ajuste automático: cambiando a modo {suggested_mode}")
                            self.current_mode = suggested_mode
                    
                    logger.info(f"Análisis supervisor completado. Régimen: {self.supervisor.market_regime}")
                
            except Exception as e:
                logger.error(f"Error en supervisor: {str(e)}")
            
            time.sleep(analysis_interval)
    
    def set_timeframe(self, timeframe: str):
        """Cambiar timeframe actual"""
        if timeframe in SUPPORTED_TIMEFRAMES:
            old_tf = self.current_timeframe
            self.current_timeframe = timeframe
            logger.info(f"Timeframe cambiado: {old_tf} -> {timeframe}")
            return True
        logger.error(f"Timeframe no válido: {timeframe}")
        return False
    
    def set_mode(self, mode: str):
        """Cambiar modo de operación"""
        if mode in OPERATION_MODES:
            old_mode = self.current_mode
            self.current_mode = mode
            logger.info(f"Modo cambiado: {old_mode} -> {mode}")
            return True
        logger.error(f"Modo no válido: {mode}")
        return False
    
    def set_symbols(self, symbols: List[str]):
        """Cambiar símbolos monitoreados"""
        self.tracked_symbols = symbols
        logger.info(f"Símbolos actualizados: {symbols}")
    
    def get_chart_data(self, symbol: str, timeframe: str):
        """Obtener datos para gráfico"""
        key = f"{symbol}_{timeframe}"
        if key in self.market_data:
            df = self.market_data[key].tail(100)  # Últimas 100 velas
            return df[['Open', 'High', 'Low', 'Close', 'Volume']]
        return None
    
    def retrain_all_models(self) -> Dict:
        """Forzar reentrenamiento de todos los modelos"""
        results = {}
        
        for tf in SUPPORTED_TIMEFRAMES:
            tf_data = []
            for symbol in self.tracked_symbols:
                key = f"{symbol}_{tf}"
                if key in self.market_data:
                    tf_data.append(self.market_data[key])
            
            if tf_data:
                combined_data = pd.concat(tf_data, ignore_index=False)
                engine = self.ml_manager.get_engine(tf)
                if engine:
                    success = engine.train(combined_data, force=True)
                    results[tf] = success
        
        return results
    
    def retrain_model(self, timeframe: str) -> Dict:
        """Forzar reentrenamiento de un modelo específico"""
        if timeframe not in SUPPORTED_TIMEFRAMES:
            return {'error': 'Timeframe no válido'}
        
        tf_data = []
        for symbol in self.tracked_symbols:
            key = f"{symbol}_{timeframe}"
            if key in self.market_data:
                tf_data.append(self.market_data[key])
        
        if tf_data:
            combined_data = pd.concat(tf_data, ignore_index=False)
            engine = self.ml_manager.get_engine(timeframe)
            if engine:
                success = engine.train(combined_data, force=True)
                return {'timeframe': timeframe, 'success': success}
        
        return {'error': 'Datos no disponibles'}
    
    def get_recent_logs(self, lines: int = 50) -> List[str]:
        """Obtener logs recientes"""
        return self.logs_buffer[-lines:]


# Import pandas aquí para evitar problemas de circular import
import pandas as pd

# Logger global
logger = logging.getLogger('TradingBot')


def main():
    """Función principal de entrada"""
    print("=" * 60)
    print("  TRADING BOT ML - SISTEMA DE PREDICCIÓN AVANZADO")
    print("=" * 60)
    print()
    
    # Crear instancia del bot
    bot = TradingBot()
    
    # Inicializar componentes
    bot.initialize()
    
    # Iniciar bot
    try:
        bot.start()
    except KeyboardInterrupt:
        print("\n\nDeteniendo por solicitud del usuario...")
        bot.stop()
    except Exception as e:
        logger.error(f"Error fatal: {str(e)}")
        bot.stop()
        raise


if __name__ == '__main__':
    main()

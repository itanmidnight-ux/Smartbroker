"""
Trading Bot ML - Servidor Web Flask
API REST y WebSocket para la interfaz gráfica
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Optional

from trading_bot.config.settings import WEB_CONFIG, SUPPORTED_TIMEFRAMES, OPERATION_MODES

logger = logging.getLogger(__name__)


class WebServer:
    """Servidor web Flask con Socket.IO"""
    
    def __init__(self, bot_instance=None):
        self.app = Flask(__name__, 
                        template_folder='../../templates',
                        static_folder='../../static')
        self.app.config['SECRET_KEY'] = WEB_CONFIG['secret_key']
        self.app.config['CORS_ORIGINS'] = ['*']
        
        CORS(self.app)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='eventlet')
        
        self.bot = bot_instance
        self.running = False
        
        # Registrar rutas
        self._register_routes()
        self._register_socket_events()
        
        logger.info("Servidor web inicializado")
    
    def _register_routes(self):
        """Registrar rutas HTTP"""
        
        @self.app.route('/')
        def index():
            return render_template('index.html')
        
        @self.app.route('/api/status')
        def get_status():
            """Obtener estado general del bot"""
            if not self.bot:
                return jsonify({'error': 'Bot no inicializado'})
            
            status = {
                'running': self.bot.running,
                'current_timeframe': self.bot.current_timeframe,
                'current_mode': self.bot.current_mode,
                'symbols': self.bot.tracked_symbols,
                'ml_stats': {},
                'simulator_stats': {},
                'supervisor_status': {}
            }
            
            # Obtener estadísticas de ML por timeframe
            for tf in SUPPORTED_TIMEFRAMES:
                engine = self.bot.ml_manager.get_engine(tf)
                if engine:
                    status['ml_stats'][tf] = engine.get_stats()
            
            # Estadísticas del simulador
            if hasattr(self.bot, 'simulator'):
                status['simulator_stats'] = self.bot.simulator.get_statistics()
            
            # Estado del supervisor
            if hasattr(self.bot, 'supervisor'):
                status['supervisor_status'] = self.bot.supervisor.get_supervisor_status()
            
            return jsonify(status)
        
        @self.app.route('/api/timeframes')
        def get_timeframes():
            """Obtener timeframes soportados"""
            return jsonify({
                'supported': SUPPORTED_TIMEFRAMES,
                'current': self.bot.current_timeframe if self.bot else '1h'
            })
        
        @self.app.route('/api/modes')
        def get_modes():
            """Obtener modos de operación"""
            modes = []
            for key, value in OPERATION_MODES.items():
                modes.append({
                    'id': key,
                    'name': value['name'],
                    'confidence_threshold': value['confidence_threshold'],
                    'max_position_size': value['max_position_size'],
                    'stop_loss_pct': value['stop_loss_pct'],
                    'take_profit_pct': value['take_profit_pct']
                })
            return jsonify(modes)
        
        @self.app.route('/api/signals')
        def get_signals():
            """Obtener señales actuales"""
            if not self.bot:
                return jsonify([])
            
            signals = []
            for symbol in self.bot.tracked_symbols:
                if symbol in self.bot.latest_signals:
                    signal_data = self.bot.latest_signals[symbol].copy()
                    signal_data['symbol'] = symbol
                    signals.append(signal_data)
            
            return jsonify(signals)
        
        @self.app.route('/api/price/<symbol>')
        def get_price(symbol):
            """Obtener precio actual de un símbolo"""
            if not self.bot:
                return jsonify({'error': 'Bot no inicializado'})
            
            price = self.bot.data_fetcher.get_latest_price(symbol)
            if price:
                return jsonify({'symbol': symbol, 'price': price})
            return jsonify({'error': 'Precio no disponible'})
        
        @self.app.route('/api/chart/<symbol>/<timeframe>')
        def get_chart_data(symbol, timeframe):
            """Obtener datos para gráfico"""
            if not self.bot:
                return jsonify([])
            
            data = self.bot.get_chart_data(symbol, timeframe)
            if data is not None:
                return jsonify(data.to_dict('records'))
            return jsonify([])
        
        @self.app.route('/api/trades')
        def get_trades():
            """Obtener historial de trades"""
            if not self.bot or not hasattr(self.bot, 'simulator'):
                return jsonify([])
            
            limit = request.args.get('limit', 20, type=int)
            trades = self.bot.simulator.get_recent_trades(limit)
            return jsonify(trades)
        
        @self.app.route('/api/positions')
        def get_positions():
            """Obtener posiciones abiertas"""
            if not self.bot or not hasattr(self.bot, 'simulator'):
                return jsonify([])
            
            positions = self.bot.simulator.get_open_positions()
            return jsonify(positions)
        
        @self.app.route('/api/equity-curve')
        def get_equity_curve():
            """Obtener curva de equity"""
            if not self.bot or not hasattr(self.bot, 'simulator'):
                return jsonify([])
            
            points = request.args.get('points', 500, type=int)
            curve = self.bot.simulator.get_equity_curve(points)
            return jsonify(curve)
        
        @self.app.route('/api/settings', methods=['GET'])
        def get_settings():
            """Obtener configuración actual"""
            if not self.bot:
                return jsonify({})
            
            settings = {
                'timeframe': self.bot.current_timeframe,
                'mode': self.bot.current_mode,
                'symbols': self.bot.tracked_symbols,
                'auto_adjust': getattr(self.bot, 'auto_adjust', True)
            }
            return jsonify(settings)
        
        @self.app.route('/api/settings', methods=['POST'])
        def update_settings():
            """Actualizar configuración"""
            if not self.bot:
                return jsonify({'error': 'Bot no inicializado'})
            
            data = request.json
            
            if 'timeframe' in data and data['timeframe'] in SUPPORTED_TIMEFRAMES:
                self.bot.set_timeframe(data['timeframe'])
            
            if 'mode' in data and data['mode'] in OPERATION_MODES:
                self.bot.set_mode(data['mode'])
            
            if 'symbols' in data:
                self.bot.set_symbols(data['symbols'])
            
            if 'auto_adjust' in data:
                self.bot.auto_adjust = data['auto_adjust']
            
            return jsonify({'success': True, 'settings': get_settings().get_json()})
        
        @self.app.route('/api/ml/retrain', methods=['POST'])
        def retrain_ml():
            """Forzar reentrenamiento de ML"""
            if not self.bot:
                return jsonify({'error': 'Bot no inicializado'})
            
            timeframe = request.args.get('timeframe', 'all')
            
            if timeframe == 'all':
                results = self.bot.retrain_all_models()
            else:
                results = self.bot.retrain_model(timeframe)
            
            return jsonify(results)
        
        @self.app.route('/api/simulator/reset', methods=['POST'])
        def reset_simulator():
            """Reiniciar simulador"""
            if not self.bot or not hasattr(self.bot, 'simulator'):
                return jsonify({'error': 'Simulador no disponible'})
            
            self.bot.simulator.reset()
            return jsonify({'success': True})
        
        @self.app.route('/api/logs')
        def get_logs():
            """Obtener logs recientes"""
            if not self.bot:
                return jsonify([])
            
            lines = request.args.get('lines', 50, type=int)
            logs = self.bot.get_recent_logs(lines)
            return jsonify(logs)
    
    def _register_socket_events(self):
        """Registrar eventos de Socket.IO"""
        
        @self.socketio.on('connect')
        def handle_connect():
            logger.info("Cliente conectado")
            emit('connected', {'message': 'Conectado al servidor'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            logger.info("Cliente desconectado")
        
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            channel = data.get('channel')
            logger.info(f"Cliente suscrito a {channel}")
        
        @self.socketio.on('request_update')
        def handle_request_update():
            """Enviar actualización inmediata"""
            if self.bot:
                self._emit_realtime_data()
    
    def _emit_realtime_data(self):
        """Emitir datos en tiempo real a todos los clientes"""
        if not self.bot:
            return
        
        try:
            # Enviar señales actualizadas
            signals = []
            for symbol, signal in self.bot.latest_signals.items():
                signal_copy = signal.copy()
                signal_copy['symbol'] = symbol
                signals.append(signal_copy)
            
            self.socketio.emit('signals_update', {'signals': signals})
            
            # Enviar estadísticas del simulador
            if hasattr(self.bot, 'simulator'):
                stats = self.bot.simulator.get_statistics()
                self.socketio.emit('simulator_stats', stats)
            
            # Enviar estado del supervisor
            if hasattr(self.bot, 'supervisor'):
                supervisor_status = self.bot.supervisor.get_supervisor_status()
                self.socketio.emit('supervisor_update', supervisor_status)
            
            # Enviar precios actualizados
            prices = {}
            for symbol in self.bot.tracked_symbols:
                price = self.bot.data_fetcher.get_latest_price(symbol)
                if price:
                    prices[symbol] = price
            
            if prices:
                self.socketio.emit('prices_update', {'prices': prices})
            
        except Exception as e:
            logger.error(f"Error emitiendo datos: {str(e)}")
    
    def start_background_emitter(self):
        """Iniciar emisor en segundo plano"""
        def emit_loop():
            while self.running:
                self._emit_realtime_data()
                time.sleep(2)  # Actualizar cada 2 segundos
        
        thread = threading.Thread(target=emit_loop, daemon=True)
        thread.start()
        logger.info("Emisor en segundo plano iniciado")
    
    def start(self, host=None, port=None):
        """Iniciar servidor web"""
        host = host or WEB_CONFIG['host']
        port = port or WEB_CONFIG['port']
        
        self.running = True
        self.start_background_emitter()
        
        logger.info(f"Iniciando servidor web en {host}:{port}")
        
        try:
            self.socketio.run(self.app, host=host, port=port, debug=False, use_reloader=False)
        except Exception as e:
            logger.error(f"Error iniciando servidor: {str(e)}")
            self.running = False
    
    def stop(self):
        """Detener servidor web"""
        self.running = False
        logger.info("Servidor web detenido")

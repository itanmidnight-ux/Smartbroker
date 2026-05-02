"""
Trading Bot ML - Configuración Central
Configuraciones específicas para cada timeframe y modo de operación
"""

import os
from datetime import timedelta

# Timeframes soportados
SUPPORTED_TIMEFRAMES = ['5m', '15m', '1h', '4h']

# Mapeo de timeframes a minutos
TIMEFRAME_MINUTES = {
    '5m': 5,
    '15m': 15,
    '1h': 60,
    '4h': 240
}

# Mapeo de timeframes a períodos de Yahoo Finance
TIMEFRAME_YF_PERIOD = {
    '5m': '1d',
    '15m': '5d',
    '1h': '1mo',
    '4h': '3mo'
}

# Mapeo de timeframes a intervalos de Yahoo Finance
TIMEFRAME_YF_INTERVAL = {
    '5m': '5m',
    '15m': '15m',
    '1h': '1h',
    '4h': '1h'  # Usamos 1h y luego hacemos resample
}

# Configuración por timeframe
TIMEFRAME_CONFIG = {
    '5m': {
        'lookback_period': 100,
        'prediction_horizon': 5,
        'min_volume': 1000000,
        'volatility_threshold': 0.02,
        'rsi_oversold': 25,
        'rsi_overbought': 75,
        'macd_fast': 8,
        'macd_slow': 17,
        'macd_signal': 9,
        'bb_std': 2.0,
        'atr_multiplier_sl': 1.5,
        'atr_multiplier_tp': 3.0,
        'retrain_frequency': 50,  # Retraining cada 50 velas
        'data_points_min': 500
    },
    '15m': {
        'lookback_period': 150,
        'prediction_horizon': 10,
        'min_volume': 500000,
        'volatility_threshold': 0.015,
        'rsi_oversold': 28,
        'rsi_overbought': 72,
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9,
        'bb_std': 2.0,
        'atr_multiplier_sl': 1.8,
        'atr_multiplier_tp': 3.5,
        'retrain_frequency': 30,
        'data_points_min': 600
    },
    '1h': {
        'lookback_period': 200,
        'prediction_horizon': 20,
        'min_volume': 200000,
        'volatility_threshold': 0.01,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9,
        'bb_std': 2.0,
        'atr_multiplier_sl': 2.0,
        'atr_multiplier_tp': 4.0,
        'retrain_frequency': 20,
        'data_points_min': 800
    },
    '4h': {
        'lookback_period': 300,
        'prediction_horizon': 40,
        'min_volume': 100000,
        'volatility_threshold': 0.008,
        'rsi_oversold': 32,
        'rsi_overbought': 68,
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9,
        'bb_std': 2.0,
        'atr_multiplier_sl': 2.5,
        'atr_multiplier_tp': 5.0,
        'retrain_frequency': 10,
        'data_points_min': 1000
    }
}

# Modos de operación
OPERATION_MODES = {
    'safe': {
        'name': 'Segura 100%',
        'confidence_threshold': 0.85,
        'max_position_size': 0.02,
        'stop_loss_pct': 0.01,
        'take_profit_pct': 0.03,
        'max_trades_per_day': 3,
        'risk_reward_ratio': 3.0,
        'use_strict_filters': True,
        'min_signal_strength': 0.9
    },
    'normal': {
        'name': 'Normal',
        'confidence_threshold': 0.75,
        'max_position_size': 0.05,
        'stop_loss_pct': 0.015,
        'take_profit_pct': 0.035,
        'max_trades_per_day': 5,
        'risk_reward_ratio': 2.5,
        'use_strict_filters': True,
        'min_signal_strength': 0.75
    },
    'aggressive': {
        'name': 'Agresiva',
        'confidence_threshold': 0.65,
        'max_position_size': 0.1,
        'stop_loss_pct': 0.02,
        'take_profit_pct': 0.05,
        'max_trades_per_day': 8,
        'risk_reward_ratio': 2.0,
        'use_strict_filters': False,
        'min_signal_strength': 0.6
    },
    'very_active': {
        'name': 'Muy Activa',
        'confidence_threshold': 0.55,
        'max_position_size': 0.15,
        'stop_loss_pct': 0.025,
        'take_profit_pct': 0.06,
        'max_trades_per_day': 15,
        'risk_reward_ratio': 1.8,
        'use_strict_filters': False,
        'min_signal_strength': 0.5
    }
}

# Configuración del servidor web
WEB_CONFIG = {
    'host': '0.0.0.0',
    'port': 9000,
    'debug': False,
    'secret_key': os.urandom(24).hex()
}

# Configuración de Machine Learning
ML_CONFIG = {
    'test_size': 0.2,
    'validation_size': 0.1,
    'n_estimators_rf': 200,
    'n_estimators_gb': 150,
    'max_depth': 15,
    'learning_rate': 0.05,
    'lstm_units': [64, 32],
    'dropout_rate': 0.2,
    'batch_size': 32,
    'epochs': 50,
    'early_stopping_patience': 10,
    'target_win_rate': 0.80,
    'retrain_on_win_rate_drop': 0.75,
    'feature_importance_threshold': 0.01
}

# Configuración del Supervisor LLM
LLM_SUPERVISOR_CONFIG = {
    'analysis_interval': 600,  # 10 minutos en segundos
    'min_trades_for_analysis': 10,
    'win_rate_threshold_low': 0.75,
    'win_rate_threshold_high': 0.85,
    'max_drawdown_threshold': 0.15,
    'adjustment_cooldown': 1800,  # 30 minutos entre ajustes
    'market_regime_check_interval': 300  # 5 minutos
}

# Configuración del Simulador
SIMULATOR_CONFIG = {
    'initial_balance': 10000,
    'commission_pct': 0.001,
    'slippage_pct': 0.0005,
    'enable_real_time': True,
    'update_interval': 60,  # Segundos
    'max_open_positions': 3,
    'log_all_trades': True
}

# Símbolos por defecto
DEFAULT_SYMBOLS = [
    'BTC-USD',
    'ETH-USD',
    'EURUSD=X',
    'GBPUSD=X',
    'USDJPY=X',
    'GC=F',  # Oro
    'CL=F',  # Petróleo
    'ES=F',  # S&P 500
    'NQ=F',  # NASDAQ
    'AAPL',
    'GOOGL',
    'MSFT',
    'TSLA',
    'AMZN'
]

# Rutas del sistema
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'trading_bot', 'models')
LOGS_DIR = os.path.join(BASE_DIR, 'trading_bot', 'logs')
DATA_CACHE_DIR = os.path.join(BASE_DIR, 'trading_bot', 'data_cache')

# Asegurar que los directorios existan
for directory in [MODELS_DIR, LOGS_DIR, DATA_CACHE_DIR]:
    os.makedirs(directory, exist_ok=True)

# Logging configuration
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'
LOG_FILE = os.path.join(LOGS_DIR, 'trading_bot.log')

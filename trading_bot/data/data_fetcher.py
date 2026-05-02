"""
Trading Bot ML - Data Fetcher Module v2.0
Obtención de datos del mercado en tiempo real con Yahoo Finance
Mejorado con sistemas de validación tipo MQL5 Pro v7.5
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import time
import os
import csv
from pathlib import Path

from trading_bot.config.settings import (
    TIMEFRAME_YF_PERIOD, 
    TIMEFRAME_YF_INTERVAL,
    TIMEFRAME_CONFIG,
    DATA_CACHE_DIR
)

logger = logging.getLogger(__name__)


class DataFetcher:
    """Clase para obtener y procesar datos del mercado con validaciones avanzadas"""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 60  # Segundos
        self.spread_history = []
        self.volatility_history = []
        self.last_tick_time = 0
        self.log_file_handle = None
        self.initialize_log_file()
        
    def initialize_log_file(self):
        """Inicializar archivo de logging estilo MQL5"""
        try:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            date_str = datetime.now().strftime("%Y%m%d")
            self.log_file = log_dir / f"{date_str}_trading_bot.csv"
            
            # Escribir cabecera si es nuevo
            if not self.log_file.exists():
                with open(self.log_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        'timestamp', 'event_type', 'symbol', 'timeframe', 
                        'price', 'spread', 'atr', 'signal', 'confidence',
                        'action', 'profit_loss', 'notes'
                    ])
            
            logger.info(f"Log file initialized: {self.log_file}")
        except Exception as e:
            logger.error(f"Error initializing log file: {str(e)}")
    
    def log_trade_event(self, event_type: str, symbol: str, timeframe: str,
                       price: float, spread: float, atr: float,
                       signal: str = "", confidence: float = 0.0,
                       action: str = "", profit_loss: float = 0.0,
                       notes: str = ""):
        """Registrar evento en log CSV"""
        try:
            with open(self.log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().isoformat(),
                    event_type,
                    symbol,
                    timeframe,
                    price,
                    spread,
                    atr,
                    signal,
                    confidence,
                    action,
                    profit_loss,
                    notes
                ])
        except Exception as e:
            logger.error(f"Error writing to log file: {str(e)}")
    
    def fetch_data(self, symbol: str, timeframe: str, 
                   lookback: Optional[int] = None) -> Optional[pd.DataFrame]:
        """
        Obtener datos históricos de un símbolo con validaciones
        
        Args:
            symbol: Símbolo del activo (ej. BTC-USD, EURUSD=X)
            timeframe: Timeframe ('5m', '15m', '1h', '4h')
            lookback: Número de velas a obtener
            
        Returns:
            DataFrame con datos OHLCV
        """
        if timeframe not in TIMEFRAME_YF_PERIOD:
            logger.error(f"Timeframe no soportado: {timeframe}")
            return None
            
        try:
            ticker = yf.Ticker(symbol)
            period = TIMEFRAME_YF_PERIOD[timeframe]
            interval = TIMEFRAME_YF_INTERVAL[timeframe]
            
            # Obtener datos
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                logger.warning(f"No hay datos para {symbol} en {timeframe}")
                return None
            
            # Calcular spread estimado (High - Low como proxy)
            df['spread'] = df['High'] - df['Low']
            df['spread_pct'] = df['spread'] / df['Close']
            
            # Para 4h, hacer resample de datos 1h
            if timeframe == '4h':
                df = self._resample_to_4h(df)
                
            # Limitar si se especificó lookback
            if lookback:
                df = df.tail(lookback)
                
            # Cache
            cache_key = f"{symbol}_{timeframe}"
            self.cache[cache_key] = {
                'data': df,
                'timestamp': time.time()
            }
            
            # Actualizar historiales
            if not df.empty:
                latest_spread = df['spread_pct'].iloc[-1]
                self.spread_history.append(latest_spread)
                if len(self.spread_history) > 100:
                    self.spread_history.pop(0)
            
            logger.info(f"Datos obtenidos: {symbol} {timeframe} - {len(df)} velas, Spread: {df['spread_pct'].iloc[-1]*100:.4f}%")
            return df
            
        except Exception as e:
            logger.error(f"Error al obtener datos de {symbol}: {str(e)}")
            return None
    
    def _resample_to_4h(self, df: pd.DataFrame) -> pd.DataFrame:
        """Resamplear datos de 1h a 4h"""
        ohlc_dict = {
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }
        
        df_4h = df.resample('4h').apply(ohlc_dict)
        df_4h = df_4h.dropna()
        
        # Recalcular spread para 4h
        df_4h['spread'] = df_4h['High'] - df_4h['Low']
        df_4h['spread_pct'] = df_4h['spread'] / df_4h['Close']
        
        return df_4h
    
    def get_cached_data(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Obtener datos del cache si están disponibles"""
        cache_key = f"{symbol}_{timeframe}"
        
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached['timestamp'] < self.cache_duration:
                return cached['data']
                
        return None
    
    def validate_spread_atr_ratio(self, df: pd.DataFrame, max_ratio: float = 0.4) -> Tuple[bool, float]:
        """
        Validar que el spread no sea mayor al 40% del ATR (como en MQL5 v7.5)
        
        Returns:
            (es_valido, ratio_actual)
        """
        if df is None or df.empty or 'atr' not in df.columns:
            return False, 0.0
        
        latest_spread = df['spread'].iloc[-1]
        latest_atr = df['atr'].iloc[-1]
        
        if latest_atr == 0:
            return False, 999.0
        
        ratio = latest_spread / latest_atr
        is_valid = ratio <= max_ratio
        
        if not is_valid:
            logger.warning(f"⚠️ FILTER: Spread/ATR ratio = {ratio:.2f} (max: {max_ratio}). NO OPERAR.")
        
        return is_valid, ratio
    
    def get_current_spread(self, symbol: str) -> float:
        """Obtener spread actual estimado"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d', interval='1m')
            if not data.empty:
                spread = (data['High'].iloc[-1] - data['Low'].iloc[-1]) / data['Close'].iloc[-1]
                return spread
        except Exception as e:
            logger.error(f"Error al obtener spread de {symbol}: {str(e)}")
        return 0.0
    
    def fetch_multiple_symbols(self, symbols: List[str], 
                               timeframe: str) -> Dict[str, pd.DataFrame]:
        """Obtener datos para múltiples símbolos"""
        results = {}
        
        for symbol in symbols:
            data = self.fetch_data(symbol, timeframe)
            if data is not None:
                results[symbol] = data
                
        return results
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Obtener el último precio de un símbolo"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d', interval='1m')
            if not data.empty:
                return data['Close'].iloc[-1]
        except Exception as e:
            logger.error(f"Error al obtener precio de {symbol}: {str(e)}")
        return None
    
    def detect_market_extremes(self, df: pd.DataFrame, lookback: int = 20) -> Dict:
        """Detectar condiciones extremas de mercado (volatilidad anormal)"""
        if df is None or df.empty:
            return {'extreme': False, 'reason': 'no_data'}
        
        # Volatilidad actual vs histórica
        current_vol = df['Close'].pct_change().rolling(10).std().iloc[-1]
        historical_vol = df['Close'].pct_change().rolling(50).std().mean()
        
        vol_ratio = current_vol / historical_vol if historical_vol > 0 else 0
        
        # Spread extremo
        avg_spread = np.mean(self.spread_history[-20:]) if self.spread_history else 0
        current_spread = self.spread_history[-1] if self.spread_history else 0
        spread_ratio = current_spread / avg_spread if avg_spread > 0 else 0
        
        extreme = vol_ratio > 3.0 or spread_ratio > 2.5
        
        reason = []
        if vol_ratio > 3.0:
            reason.append(f"volatilidad_extrema ({vol_ratio:.2f}x)")
        if spread_ratio > 2.5:
            reason.append(f"spread_extremo ({spread_ratio:.2f}x)")
        
        return {
            'extreme': extreme,
            'reason': ', '.join(reason) if reason else 'normal',
            'vol_ratio': vol_ratio,
            'spread_ratio': spread_ratio
        }


class TechnicalIndicators:
    """Calculadora de indicadores técnicos avanzados"""
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Calcular todos los indicadores técnicos necesarios
        
        Args:
            df: DataFrame con datos OHLCV
            timeframe: Timeframe actual
            
        Returns:
            DataFrame con indicadores añadidos
        """
        if df is None or df.empty:
            return df
            
        df = df.copy()
        config = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG['1h'])
        
        # Indicadores básicos
        df = TechnicalIndicators.add_sma(df, [7, 14, 20, 50, 100, 200])
        df = TechnicalIndicators.add_ema(df, [7, 14, 20, 50, 100])
        df = TechnicalIndicators.add_rsi(df, [7, 14, 21])
        df = TechnicalIndicators.add_macd(df, 
                                          config['macd_fast'], 
                                          config['macd_slow'], 
                                          config['macd_signal'])
        df = TechnicalIndicators.add_bollinger_bands(df, config['bb_std'])
        df = TechnicalIndicators.add_atr(df, 14)
        df = TechnicalIndicators.add_stochastic(df, 14, 3)
        df = TechnicalIndicators.add_adx(df, 14)
        df = TechnicalIndicators.add_cci(df, 20)
        df = TechnicalIndicators.add_williams_r(df, 14)
        df = TechnicalIndicators.add_mfi(df, 14)
        df = TechnicalIndicators.add_obv(df)
        df = TechnicalIndicators.add_vwap(df)
        
        # Indicadores personalizados avanzados
        df = TechnicalIndicators.add_custom_momentum_indicator(df)
        df = TechnicalIndicators.add_volatility_ratio(df)
        df = TechnicalIndicators.add_volume_profile(df)
        df = TechnicalIndicators.add_price_action_patterns(df)
        df = TechnicalIndicators.add_market_strength_index(df)
        
        # Eliminar NaN
        df = df.dropna()
        
        return df
    
    @staticmethod
    def add_sma(df: pd.DataFrame, periods: List[int]) -> pd.DataFrame:
        """Añadir Simple Moving Averages"""
        for period in periods:
            df[f'sma_{period}'] = df['Close'].rolling(window=period).mean()
        return df
    
    @staticmethod
    def add_ema(df: pd.DataFrame, periods: List[int]) -> pd.DataFrame:
        """Añadir Exponential Moving Averages"""
        for period in periods:
            df[f'ema_{period}'] = df['Close'].ewm(span=period, adjust=False).mean()
        return df
    
    @staticmethod
    def add_rsi(df: pd.DataFrame, periods: List[int]) -> pd.DataFrame:
        """Añadir Relative Strength Index"""
        for period in periods:
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
        return df
    
    @staticmethod
    def add_macd(df: pd.DataFrame, fast: int, slow: int, signal: int) -> pd.DataFrame:
        """Añadir MACD"""
        ema_fast = df['Close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['Close'].ewm(span=slow, adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        return df
    
    @staticmethod
    def add_bollinger_bands(df: pd.DataFrame, std_dev: float) -> pd.DataFrame:
        """Añadir Bandas de Bollinger"""
        df['bb_middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (std_dev * bb_std)
        df['bb_lower'] = df['bb_middle'] - (std_dev * bb_std)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_percent'] = (df['Close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        return df
    
    @staticmethod
    def add_atr(df: pd.DataFrame, period: int) -> pd.DataFrame:
        """Añadir Average True Range"""
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(period).mean()
        df['atr_pct'] = df['atr'] / df['Close']
        return df
    
    @staticmethod
    def add_stochastic(df: pd.DataFrame, k_period: int, d_period: int) -> pd.DataFrame:
        """Añadir Stochastic Oscillator"""
        low_min = df['Low'].rolling(window=k_period).min()
        high_max = df['High'].rolling(window=k_period).max()
        df['stoch_k'] = 100 * (df['Close'] - low_min) / (high_max - low_min)
        df['stoch_d'] = df['stoch_k'].rolling(window=d_period).mean()
        return df
    
    @staticmethod
    def add_adx(df: pd.DataFrame, period: int) -> pd.DataFrame:
        """Añadir Average Directional Index"""
        plus_dm = df['High'].diff()
        minus_dm = -df['Low'].diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        tr = ranges.max(axis=1)
        
        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
        
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        df['adx'] = dx.rolling(period).mean()
        df['plus_di'] = plus_di
        df['minus_di'] = minus_di
        return df
    
    @staticmethod
    def add_cci(df: pd.DataFrame, period: int) -> pd.DataFrame:
        """Añadir Commodity Channel Index"""
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        sma_tp = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
        df['cci'] = (tp - sma_tp) / (0.015 * mad)
        return df
    
    @staticmethod
    def add_williams_r(df: pd.DataFrame, period: int) -> pd.DataFrame:
        """Añadir Williams %R"""
        highest_high = df['High'].rolling(window=period).max()
        lowest_low = df['Low'].rolling(window=period).min()
        df['williams_r'] = -100 * (highest_high - df['Close']) / (highest_high - lowest_low)
        return df
    
    @staticmethod
    def add_mfi(df: pd.DataFrame, period: int) -> pd.DataFrame:
        """Añadir Money Flow Index"""
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        money_flow = typical_price * df['Volume']
        
        delta = typical_price.diff()
        positive_flow = money_flow.where(delta > 0, 0)
        negative_flow = money_flow.where(delta < 0, 0)
        
        positive_mf = positive_flow.rolling(window=period).sum()
        negative_mf = negative_flow.rolling(window=period).sum()
        
        mfi = 100 - (100 / (1 + positive_mf / negative_mf))
        df['mfi'] = mfi
        return df
    
    @staticmethod
    def add_obv(df: pd.DataFrame) -> pd.DataFrame:
        """Añadir On-Balance Volume"""
        df['obv'] = np.where(df['Close'] > df['Close'].shift(),
                             df['Volume'],
                             np.where(df['Close'] < df['Close'].shift(),
                                     -df['Volume'], 0)).cumsum()
        return df
    
    @staticmethod
    def add_vwap(df: pd.DataFrame) -> pd.DataFrame:
        """Añadir Volume Weighted Average Price"""
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        df['vwap'] = (tp * df['Volume']).cumsum() / df['Volume'].cumsum()
        return df
    
    @staticmethod
    def add_custom_momentum_indicator(df: pd.DataFrame) -> pd.DataFrame:
        """
        Indicador personalizado de momentum combinando RSI, MACD y velocidad de precio
        """
        # Normalizar RSI
        rsi_norm = (df['rsi_14'] - 50) / 50
        
        # Normalizar MACD
        macd_norm = df['macd'] / df['Close'].rolling(20).std()
        
        # Velocidad de precio
        price_velocity = df['Close'].pct_change(periods=5)
        
        # Combinar
        df['custom_momentum'] = (
            0.4 * rsi_norm + 
            0.4 * macd_norm + 
            0.2 * price_velocity
        )
        
        return df
    
    @staticmethod
    def add_volatility_ratio(df: pd.DataFrame) -> pd.DataFrame:
        """Ratio de volatilidad actual vs histórica"""
        current_vol = df['Close'].rolling(10).std()
        historical_vol = df['Close'].rolling(50).std()
        df['volatility_ratio'] = current_vol / historical_vol
        return df
    
    @staticmethod
    def add_volume_profile(df: pd.DataFrame) -> pd.DataFrame:
        """Perfil de volumen relativo"""
        avg_volume = df['Volume'].rolling(20).mean()
        df['volume_ratio'] = df['Volume'] / avg_volume
        df['volume_spike'] = (df['volume_ratio'] > 2).astype(int)
        return df
    
    @staticmethod
    def add_price_action_patterns(df: pd.DataFrame) -> pd.DataFrame:
        """Detección de patrones de acción de precio"""
        # Doji
        body_size = np.abs(df['Close'] - df['Open'])
        candle_range = df['High'] - df['Low']
        df['is_doji'] = (body_size < candle_range * 0.1).astype(int)
        
        # Martillo / Hombre colgado
        lower_shadow = np.minimum(df['Open'], df['Close']) - df['Low']
        upper_shadow = df['High'] - np.maximum(df['Open'], df['Close'])
        df['is_hammer'] = ((lower_shadow > 2 * body_size) & 
                          (upper_shadow < body_size * 0.5)).astype(int)
        
        # Tendencia actual
        df['price_trend'] = np.where(df['Close'] > df['Close'].shift(5), 1,
                                    np.where(df['Close'] < df['Close'].shift(5), -1, 0))
        
        return df
    
    @staticmethod
    def add_market_strength_index(df: pd.DataFrame) -> pd.DataFrame:
        """Índice de fuerza del mercado personalizado"""
        # Fuerza de tendencia
        trend_strength = np.abs(df['Close'] - df['Close'].shift(10)) / df['Close'].shift(10)
        
        # Fuerza de volumen
        volume_strength = df['volume_ratio'] * np.abs(df['Close'].pct_change())
        
        # Consolidar
        df['market_strength'] = (
            0.5 * trend_strength * 100 +
            0.3 * volume_strength * 100 +
            0.2 * df['adx'] / 100
        )
        
        return df


# Funciones utilitarias
def save_data_to_cache(df: pd.DataFrame, symbol: str, timeframe: str):
    """Guardar datos en cache local"""
    filename = f"{symbol.replace('-', '_')}_{timeframe}.csv"
    filepath = os.path.join(DATA_CACHE_DIR, filename)
    df.to_csv(filepath)
    logger.debug(f"Datos guardados en cache: {filepath}")


def load_data_from_cache(symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
    """Cargar datos desde cache local"""
    filename = f"{symbol.replace('-', '_')}_{timeframe}.csv"
    filepath = os.path.join(DATA_CACHE_DIR, filename)
    
    if os.path.exists(filepath):
        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        logger.debug(f"Datos cargados desde cache: {filepath}")
        return df
    
    return None

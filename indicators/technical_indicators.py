"""
Technical indicators implementation.
All indicators work with pandas DataFrames.
"""
import numpy as np
import pandas as pd
from typing import Tuple, Optional


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).
    
    Args:
        prices: Price series (typically close prices)
        period: RSI period
    
    Returns:
        RSI series (0-100)
    """
    delta = prices.diff()
    
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_macd(
    prices: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD indicator.
    
    Args:
        prices: Price series
        fast_period: Fast EMA period
        slow_period: Slow EMA period
        signal_period: Signal line period
    
    Returns:
        Tuple of (MACD line, Signal line, Histogram)
    """
    ema_fast = prices.ewm(span=fast_period, adjust=False).mean()
    ema_slow = prices.ewm(span=slow_period, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(
    prices: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands.
    
    Args:
        prices: Price series
        period: Moving average period
        std_dev: Standard deviation multiplier
    
    Returns:
        Tuple of (Upper band, Middle band, Lower band)
    """
    middle = prices.rolling(window=period, min_periods=period).mean()
    std = prices.rolling(window=period, min_periods=period).std()
    
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    
    return upper, middle, lower


def calculate_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3
) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate Stochastic Oscillator.
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        k_period: %K period
        d_period: %D period (smoothing)
    
    Returns:
        Tuple of (%K, %D)
    """
    lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
    highest_high = high.rolling(window=k_period, min_periods=k_period).max()
    
    k = 100 * ((close - lowest_low) / (highest_high - lowest_low + 1e-10))
    d = k.rolling(window=d_period, min_periods=d_period).mean()
    
    return k, d


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    Calculate Average True Range (ATR).
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        period: ATR period
    
    Returns:
        ATR series
    """
    prev_close = close.shift(1)
    
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(window=period, min_periods=period).mean()
    
    return atr


def calculate_ichimoku(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_span_b_period: int = 52,
    displacement: int = 26
) -> dict:
    """
    Calculate Ichimoku Cloud components.
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        tenkan_period: Tenkan-sen period
        kijun_period: Kijun-sen period
        senkou_span_b_period: Senkou Span B period
        displacement: Displacement (chikou span shift)
    
    Returns:
        Dictionary with all Ichimoku components
    """
    # Tenkan-sen (Conversion Line)
    tenkan_sen = (
        high.rolling(window=tenkan_period, min_periods=tenkan_period).max() +
        low.rolling(window=tenkan_period, min_periods=tenkan_period).min()
    ) / 2
    
    # Kijun-sen (Base Line)
    kijun_sen = (
        high.rolling(window=kijun_period, min_periods=kijun_period).max() +
        low.rolling(window=kijun_period, min_periods=kijun_period).min()
    ) / 2
    
    # Senkou Span A (Leading Span A)
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(displacement)
    
    # Senkou Span B (Leading Span B)
    senkou_span_b = (
        high.rolling(window=senkou_span_b_period, min_periods=senkou_span_b_period).max() +
        low.rolling(window=senkou_span_b_period, min_periods=senkou_span_b_period).min()
    ) / 2
    senkou_span_b = senkou_span_b.shift(displacement)
    
    # Chikou Span (Lagging Span)
    chikou_span = close.shift(-displacement)
    
    return {
        'tenkan_sen': tenkan_sen,
        'kijun_sen': kijun_sen,
        'senkou_span_a': senkou_span_a,
        'senkou_span_b': senkou_span_b,
        'chikou_span': chikou_span
    }


def calculate_adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    Calculate Average Directional Index (ADX).
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        period: ADX period
    
    Returns:
        ADX series
    """
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)
    
    # True Range
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=period).mean()
    
    # Directional Movement
    plus_dm = high - prev_high
    minus_dm = prev_low - low
    
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    # Smoothed DM
    plus_di = 100 * (plus_dm.rolling(window=period, min_periods=period).mean() / (atr + 1e-10))
    minus_di = 100 * (minus_dm.rolling(window=period, min_periods=period).mean() / (atr + 1e-10))
    
    # DX and ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
    adx = dx.rolling(window=period, min_periods=period).mean()
    
    return adx


def calculate_vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series
) -> pd.Series:
    """
    Calculate Volume Weighted Average Price (VWAP).
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        volume: Volume series
    
    Returns:
        VWAP series
    """
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).cumsum() / volume.cumsum()
    
    return vwap


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all technical indicators on a DataFrame.
    
    Args:
        df: DataFrame with columns: open, high, low, close, volume
    
    Returns:
        DataFrame with all indicators added
    """
    df = df.copy()
    
    # RSI
    df['rsi'] = calculate_rsi(df['close'])
    
    # MACD
    macd, signal, hist = calculate_macd(df['close'])
    df['macd'] = macd
    df['macd_signal'] = signal
    df['macd_hist'] = hist
    
    # Bollinger Bands
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(df['close'])
    df['bb_upper'] = bb_upper
    df['bb_middle'] = bb_middle
    df['bb_lower'] = bb_lower
    df['bb_width'] = (bb_upper - bb_lower) / bb_middle
    
    # Stochastic
    stoch_k, stoch_d = calculate_stochastic(df['high'], df['low'], df['close'])
    df['stoch_k'] = stoch_k
    df['stoch_d'] = stoch_d
    
    # ATR
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'])
    
    # Ichimoku
    ichimoku = calculate_ichimoku(df['high'], df['low'], df['close'])
    df['tenkan_sen'] = ichimoku['tenkan_sen']
    df['kijun_sen'] = ichimoku['kijun_sen']
    df['senkou_span_a'] = ichimoku['senkou_span_a']
    df['senkou_span_b'] = ichimoku['senkou_span_b']
    
    # ADX
    df['adx'] = calculate_adx(df['high'], df['low'], df['close'])
    
    # VWAP
    df['vwap'] = calculate_vwap(df['high'], df['low'], df['close'], df['volume'])
    
    # Price changes
    df['price_change_pct'] = df['close'].pct_change() * 100
    df['volume_change_pct'] = df['volume'].pct_change() * 100
    
    return df

"""
Helper utilities for the trading system.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Optional, Tuple, List
from config.constants import OrderType, TradeDirection


def get_utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def timestamp_to_datetime(timestamp: float) -> datetime:
    """Convert Unix timestamp to datetime."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def datetime_to_timestamp(dt: datetime) -> float:
    """Convert datetime to Unix timestamp."""
    return dt.timestamp()


def calculate_pips(symbol: str, price: float) -> float:
    """
    Calculate pip value based on symbol.
    For most pairs: 0.0001 = 1 pip
    For JPY pairs: 0.01 = 1 pip
    """
    if "JPY" in symbol:
        return price * 100
    else:
        return price * 10000


def pips_to_price(symbol: str, pips: float) -> float:
    """
    Convert pips to price difference.
    """
    if "JPY" in symbol:
        return pips / 100
    else:
        return pips / 10000


def calculate_position_size(
    balance: float,
    risk_pct: float,
    stop_loss_pips: float,
    symbol: str,
    tick_value: float = 10.0
) -> float:
    """
    Calculate position size based on risk parameters.
    
    Args:
        balance: Account balance
        risk_pct: Risk percentage (e.g., 1.0 for 1%)
        stop_loss_pips: Stop loss in pips
        symbol: Trading symbol
        tick_value: Value per tick (approximate)
    
    Returns:
        Lot size
    """
    risk_amount = balance * (risk_pct / 100)
    sl_in_ticks = stop_loss_pips * 10  # Approximate
    
    if sl_in_ticks <= 0:
        return 0.01
    
    lot_size = risk_amount / (sl_in_ticks * tick_value)
    
    # Round to 2 decimal places and ensure minimum
    lot_size = max(0.01, round(lot_size, 2))
    
    return lot_size


def calculate_profit_loss(
    direction: TradeDirection,
    entry_price: float,
    exit_price: float,
    lots: float,
    symbol: str
) -> float:
    """
    Calculate profit or loss for a trade.
    """
    if direction == TradeDirection.LONG:
        price_diff = exit_price - entry_price
    else:
        price_diff = entry_price - exit_price
    
    # Approximate pip value calculation
    if "JPY" in symbol:
        pip_value = 0.01
    else:
        pip_value = 0.0001
    
    pips = price_diff / pip_value
    tick_value = 10.0  # Approximate for standard lot
    
    profit = pips * lots * tick_value
    
    return profit


def resample_ohlcv(
    df: pd.DataFrame,
    timeframe: str,
    include_volume: bool = True
) -> pd.DataFrame:
    """
    Resample OHLCV data to a different timeframe.
    
    Args:
        df: DataFrame with columns: timestamp, open, high, low, close, volume
        timeframe: Target timeframe (e.g., '5T' for 5 minutes)
        include_volume: Whether to include volume
    
    Returns:
        Resampled DataFrame
    """
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    
    agg_dict = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
    }
    
    if include_volume and 'volume' in df.columns:
        agg_dict['volume'] = 'sum'
    
    resampled = df.resample(timeframe).agg(agg_dict)
    resampled = resampled.dropna()
    
    return resampled.reset_index()


def detect_market_structure(
    highs: np.ndarray,
    lows: np.ndarray,
    lookback: int = 20
) -> Tuple[str, Optional[float], Optional[float]]:
    """
    Detect market structure (HH/HL or LH/LL).
    
    Returns:
        Structure type, last swing high, last swing low
    """
    if len(highs) < lookback or len(lows) < lookback:
        return "UNKNOWN", None, None
    
    recent_highs = highs[-lookback:]
    recent_lows = lows[-lookback:]
    
    # Find peaks and troughs
    from scipy.signal import argrelextrema
    
    order = min(5, len(recent_highs) // 3)
    
    if order < 1:
        return "UNKNOWN", None, None
    
    peak_indices = argrelextrema(recent_highs, np.less, order=order)[0]
    trough_indices = argrelextrema(recent_lows, np.greater, order=order)[0]
    
    if len(peak_indices) < 2 or len(trough_indices) < 2:
        return "CONSOLIDATING", None, None
    
    # Analyze trend
    last_peak = recent_highs[peak_indices[-1]]
    prev_peak = recent_highs[peak_indices[-2]]
    last_trough = recent_lows[trough_indices[-1]]
    prev_trough = recent_lows[trough_indices[-2]]
    
    if last_peak > prev_peak and last_trough > prev_trough:
        return "UPTREND", last_peak, last_trough
    elif last_peak < prev_peak and last_trough < prev_trough:
        return "DOWNTREND", last_peak, last_trough
    else:
        return "RANGING", last_peak, last_trough


def normalize_features(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """
    Normalize features using z-score normalization.
    """
    df = df.copy()
    for col in columns:
        if col in df.columns:
            mean = df[col].rolling(window=100, min_periods=20).mean()
            std = df[col].rolling(window=100, min_periods=20).std()
            df[col + '_norm'] = (df[col] - mean) / (std + 1e-8)
    
    return df


def add_noise(price: float, noise_pct: float = 0.0001) -> float:
    """
    Add realistic noise to price data for simulation.
    """
    noise = np.random.normal(0, price * noise_pct)
    return price + noise

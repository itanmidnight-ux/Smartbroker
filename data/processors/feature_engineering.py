"""
Feature engineering for ML models.
Processes market data into features for prediction.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from indicators.technical_indicators import calculate_all_indicators
from utils.helpers import detect_market_structure
from config.constants import MarketRegime


class FeatureEngineer:
    """
    Feature engineering pipeline for trading ML models.
    """
    
    def __init__(self):
        self.feature_columns = [
            'rsi',
            'macd',
            'macd_signal',
            'macd_hist',
            'bb_upper',
            'bb_middle',
            'bb_lower',
            'bb_width',
            'stoch_k',
            'stoch_d',
            'atr',
            'adx',
            'price_change_pct',
            'volume_change_pct',
            'tenkan_sen',
            'kijun_sen',
            'senkou_span_a',
            'senkou_span_b',
        ]
        
        self.target_columns = [
            'future_return_5',
            'future_return_10',
            'future_return_20',
        ]
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create all features from raw OHLCV data.
        
        Args:
            df: DataFrame with columns: open, high, low, close, volume
        
        Returns:
            DataFrame with all features
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # Calculate all technical indicators
        df = calculate_all_indicators(df)
        
        # Add market structure features
        df = self._add_market_structure_features(df)
        
        # Add volatility features
        df = self._add_volatility_features(df)
        
        # Add momentum features
        df = self._add_momentum_features(df)
        
        # Add volume features
        df = self._add_volume_features(df)
        
        # Add price position features
        df = self._add_price_position_features(df)
        
        # Create target variables (for supervised learning)
        df = self._create_targets(df)
        
        # Normalize rolling features
        df = self._normalize_features(df)
        
        return df
    
    def _add_market_structure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add market structure detection features."""
        df = df.copy()
        
        # Higher highs and lower lows detection
        df['hh'] = (df['high'] == df['high'].rolling(window=20, min_periods=20).max()).astype(int)
        df['ll'] = (df['low'] == df['low'].rolling(window=20, min_periods=20).min()).astype(int)
        
        # Distance from recent high/low
        df['dist_from_high_20'] = (df['high'].rolling(window=20, min_periods=20).max() - df['close']) / df['close'] * 100
        df['dist_from_low_20'] = (df['close'] - df['low'].rolling(window=20, min_periods=20).min()) / df['close'] * 100
        
        # Trend structure
        rolling_high = df['high'].rolling(window=10, min_periods=10).max()
        rolling_low = df['low'].rolling(window=10, min_periods=10).min()
        
        df['trend_structure'] = np.where(
            (rolling_high > rolling_high.shift(1)) & (rolling_low > rolling_low.shift(1)),
            1,  # Uptrend
            np.where(
                (rolling_high < rolling_high.shift(1)) & (rolling_low < rolling_low.shift(1)),
                -1,  # Downtrend
                0  # Ranging
            )
        )
        
        return df
    
    def _add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volatility-related features."""
        df = df.copy()
        
        # Historical volatility (rolling std of returns)
        df['returns'] = df['close'].pct_change()
        df['volatility_10'] = df['returns'].rolling(window=10, min_periods=10).std() * np.sqrt(252) * 100
        df['volatility_20'] = df['returns'].rolling(window=20, min_periods=20).std() * np.sqrt(252) * 100
        
        # Volatility regime
        vol_mean = df['volatility_20'].rolling(window=50, min_periods=50).mean()
        vol_std = df['volatility_20'].rolling(window=50, min_periods=50).std()
        
        df['volatility_zscore'] = (df['volatility_20'] - vol_mean) / (vol_std + 1e-10)
        df['volatility_regime'] = np.where(
            df['volatility_zscore'] > 1,
            'HIGH',
            np.where(df['volatility_zscore'] < -1, 'LOW', 'NORMAL')
        )
        
        # ATR ratio
        df['atr_ratio'] = df['atr'] / df['close'] * 100
        
        return df
    
    def _add_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add momentum features."""
        df = df.copy()
        
        # Rate of change
        df['roc_5'] = df['close'].pct_change(periods=5) * 100
        df['roc_10'] = df['close'].pct_change(periods=10) * 100
        df['roc_20'] = df['close'].pct_change(periods=20) * 100
        
        # Momentum score
        df['momentum_score'] = (
            0.3 * df['rsi'] +
            0.3 * df['stoch_k'] +
            0.2 * (df['macd'] / (df['close'] * 0.01)) +
            0.2 * df['roc_10']
        ) / 100
        
        # Acceleration
        df['momentum_accel'] = df['momentum_score'].diff()
        
        return df
    
    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based features."""
        df = df.copy()
        
        # Volume moving averages
        df['volume_ma_10'] = df['volume'].rolling(window=10, min_periods=10).mean()
        df['volume_ma_20'] = df['volume'].rolling(window=20, min_periods=20).mean()
        
        # Volume ratio
        df['volume_ratio'] = df['volume'] / (df['volume_ma_10'] + 1e-10)
        
        # Volume spike detection
        vol_std = df['volume'].rolling(window=20, min_periods=20).std()
        df['volume_spike'] = (df['volume'] > df['volume_ma_10'] + 2 * vol_std).astype(int)
        
        # On-balance volume (simplified)
        df['obv'] = (np.sign(df['close'].diff()) * df['volume']).cumsum()
        df['obv_ma'] = df['obv'].rolling(window=10, min_periods=10).mean()
        
        return df
    
    def _add_price_position_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add price position relative to bands/levels."""
        df = df.copy()
        
        # Position within Bollinger Bands
        bb_range = df['bb_upper'] - df['bb_lower']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (bb_range + 1e-10)
        
        # Position within recent range
        range_high = df['high'].rolling(window=20, min_periods=20).max()
        range_low = df['low'].rolling(window=20, min_periods=20).min()
        range_size = range_high - range_low
        df['range_position'] = (df['close'] - range_low) / (range_size + 1e-10)
        
        # Distance from moving averages
        df['ma_20'] = df['close'].rolling(window=20, min_periods=20).mean()
        df['ma_50'] = df['close'].rolling(window=50, min_periods=50).mean()
        df['ma_200'] = df['close'].rolling(window=200, min_periods=200).mean()
        
        df['dist_from_ma20'] = (df['close'] - df['ma_20']) / df['ma_20'] * 100
        df['dist_from_ma50'] = (df['close'] - df['ma_50']) / df['ma_50'] * 100
        
        # MA alignment
        df['ma_alignment'] = np.where(
            (df['ma_20'] > df['ma_50']) & (df['ma_50'] > df['ma_200']),
            1,  # Bullish alignment
            np.where(
                (df['ma_20'] < df['ma_50']) & (df['ma_50'] < df['ma_200']),
                -1,  # Bearish alignment
                0  # Mixed
            )
        )
        
        return df
    
    def _create_targets(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create target variables for supervised learning."""
        df = df.copy()
        
        # Future returns at different horizons
        df['future_return_5'] = df['close'].shift(-5) / df['close'] - 1
        df['future_return_10'] = df['close'].shift(-10) / df['close'] - 1
        df['future_return_20'] = df['close'].shift(-20) / df['close'] - 1
        
        # Direction classification
        df['direction_5'] = (df['future_return_5'] > 0).astype(int)
        df['direction_10'] = (df['future_return_10'] > 0).astype(int)
        
        # Strong move classification
        threshold = 0.005  # 0.5% move
        df['strong_move_5'] = (abs(df['future_return_5']) > threshold).astype(int)
        
        return df
    
    def _normalize_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize features using rolling z-score."""
        df = df.copy()
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            if col not in ['hh', 'll', 'trend_structure', 'volume_spike', 
                          'direction_5', 'direction_10', 'strong_move_5',
                          'ma_alignment', 'volatility_regime']:
                
                # Rolling normalization
                rolling_mean = df[col].rolling(window=100, min_periods=20).mean()
                rolling_std = df[col].rolling(window=100, min_periods=20).std()
                
                df[f'{col}_norm'] = (df[col] - rolling_mean) / (rolling_std + 1e-10)
        
        return df
    
    def get_feature_matrix(
        self,
        df: pd.DataFrame,
        include_normalized: bool = True
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Get feature matrix ready for ML model.
        
        Args:
            df: DataFrame with all features
            include_normalized: Whether to include normalized features
        
        Returns:
            Tuple of (feature DataFrame, feature column names)
        """
        df = df.copy()
        
        # Select base features
        available_features = [col for col in self.feature_columns if col in df.columns]
        
        if include_normalized:
            # Also include normalized versions
            norm_features = [f'{col}_norm' for col in available_features if f'{col}_norm' in df.columns]
            all_features = available_features + norm_features
        else:
            all_features = available_features
        
        # Drop rows with NaN values
        df_clean = df[all_features].dropna()
        
        return df_clean, all_features
    
    def classify_regime(self, df: pd.DataFrame) -> pd.Series:
        """
        Classify market regime based on features.
        
        Returns:
            Series with regime labels
        """
        df = df.copy()
        
        # Use ADX for trend strength
        adx_threshold = 25
        
        # Determine regime
        conditions = [
            (df['adx'] > adx_threshold) & (df['trend_structure'] == 1),
            (df['adx'] > adx_threshold) & (df['trend_structure'] == -1),
            (df['adx'] <= adx_threshold),
            (df['volatility_zscore'] > 1),
            (df['volatility_zscore'] < -1),
        ]
        
        choices = [
            MarketRegime.TRENDING_UP.value,
            MarketRegime.TRENDING_DOWN.value,
            MarketRegime.RANGING.value,
            MarketRegime.HIGH_VOLATILITY.value,
            MarketRegime.LOW_VOLATILITY.value,
        ]
        
        regime = np.select(conditions, choices, default=MarketRegime.RANGING.value)
        
        return pd.Series(regime, index=df.index)


# Global feature engineer instance
feature_engineer = FeatureEngineer()

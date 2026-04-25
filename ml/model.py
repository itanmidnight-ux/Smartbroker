"""
Machine Learning Model for market regime classification and prediction.
Uses LightGBM as the primary model.
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import joblib
from pathlib import Path

from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import lightgbm as lgb

from config.constants import MarketRegime, FEATURE_COLUMNS
from utils.logger import get_logger

logger = get_logger(__name__)


class MarketRegimeClassifier:
    """
    Market regime classifier using LightGBM.
    Classifies market into: TRENDING_UP, TRENDING_DOWN, RANGING, HIGH_VOLATILITY, LOW_VOLATILITY
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.model: Optional[lgb.LGBMClassifier] = None
        self.scaler = StandardScaler()
        self.model_path = model_path or "models/regime_classifier.pkl"
        self.is_fitted = False
        self.feature_columns = FEATURE_COLUMNS.copy()
        
        # Class mapping
        self.class_mapping = {
            'TRENDING_UP': 0,
            'TRENDING_DOWN': 1,
            'RANGING': 2,
            'HIGH_VOLATILITY': 3,
            'LOW_VOLATILITY': 4,
        }
        self.reverse_class_mapping = {v: k for k, v in self.class_mapping.items()}
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for the model."""
        df = df.copy()
        
        # Select only available feature columns
        available_cols = [col for col in self.feature_columns if col in df.columns]
        
        if not available_cols:
            raise ValueError("No feature columns found in DataFrame")
        
        return df[available_cols]
    
    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        validation_split: float = 0.2,
        use_time_series_split: bool = True
    ) -> Dict:
        """
        Train the regime classifier.
        
        Args:
            X: Feature DataFrame
            y: Target series (regime labels)
            validation_split: Fraction of data for validation
            use_time_series_split: Use time series cross-validation
        
        Returns:
            Training metrics
        """
        logger.info("Training regime classifier", samples=len(X))
        
        # Prepare data
        X_clean = X.dropna()
        y_clean = y.loc[X_clean.index].dropna()
        
        # Align indices
        common_idx = X_clean.index.intersection(y_clean.index)
        X_clean = X_clean.loc[common_idx]
        y_clean = y_clean.loc[common_idx]
        
        if len(X_clean) < 100:
            raise ValueError("Insufficient training data")
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X_clean)
        
        # Split data
        if use_time_series_split:
            split_idx = int(len(X_scaled) * (1 - validation_split))
            X_train, X_val = X_scaled[:split_idx], X_scaled[split_idx:]
            y_train, y_val = y_clean.iloc[:split_idx], y_clean.iloc[split_idx:]
        else:
            X_train, X_val, y_train, y_val = train_test_split(
                X_scaled, y_clean, test_size=validation_split, shuffle=False
            )
        
        # Initialize model
        self.model = lgb.LGBMClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            num_leaves=31,
            class_weight='balanced',
            random_state=42,
            verbose=-1,
        )
        
        # Train
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)]
        )
        
        self.is_fitted = True
        
        # Evaluate
        y_pred = self.model.predict(X_val)
        accuracy = accuracy_score(y_val, y_pred)
        
        logger.info(f"Model trained. Validation accuracy: {accuracy:.4f}")
        
        return {
            'accuracy': accuracy,
            'train_samples': len(X_train),
            'val_samples': len(X_val),
            'n_features': X_train.shape[1],
        }
    
    def predict(self, X: pd.DataFrame) -> pd.Series:
        """
        Predict market regime.
        
        Args:
            X: Feature DataFrame
        
        Returns:
            Series of predicted regime labels
        """
        if not self.is_fitted or self.model is None:
            # Return default regime if not fitted
            logger.warning("Model not fitted, returning default regime")
            return pd.Series(['RANGING'] * len(X), index=X.index)
        
        X_clean = X.dropna()
        X_scaled = self.scaler.transform(X_clean)
        
        predictions = self.model.predict(X_scaled)
        
        # Map back to labels
        labels = [self.reverse_class_mapping[p] for p in predictions]
        
        return pd.Series(labels, index=X_clean.index)
    
    def predict_proba(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Get prediction probabilities for each regime.
        
        Args:
            X: Feature DataFrame
        
        Returns:
            DataFrame with probabilities for each regime
        """
        if not self.is_fitted or self.model is None:
            return pd.DataFrame()
        
        X_clean = X.dropna()
        X_scaled = self.scaler.transform(X_clean)
        
        probas = self.model.predict_proba(X_scaled)
        
        columns = [self.reverse_class_mapping[i] for i in range(probas.shape[1])]
        
        return pd.DataFrame(probas, columns=columns, index=X_clean.index)
    
    def get_feature_importance(self) -> pd.DataFrame:
        """Get feature importance from the model."""
        if not self.is_fitted or self.model is None:
            return pd.DataFrame()
        
        importance = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': self.model.feature_importances_
        })
        
        return importance.sort_values('importance', ascending=False)
    
    def save(self, path: Optional[str] = None):
        """Save model to disk."""
        if not self.is_fitted:
            logger.warning("Cannot save unfitted model")
            return
        
        save_path = path or self.model_path
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'feature_columns': self.feature_columns,
            'is_fitted': self.is_fitted,
        }, save_path)
        
        logger.info(f"Model saved to {save_path}")
    
    def load(self, path: Optional[str] = None) -> bool:
        """Load model from disk."""
        load_path = path or self.model_path
        
        if not Path(load_path).exists():
            logger.warning(f"Model file not found: {load_path}")
            return False
        
        try:
            data = joblib.load(load_path)
            self.model = data['model']
            self.scaler = data['scaler']
            self.feature_columns = data['feature_columns']
            self.is_fitted = data['is_fitted']
            
            logger.info(f"Model loaded from {load_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False


class AdaptiveParameterTuner:
    """
    Dynamically adjusts strategy parameters based on market conditions.
    """
    
    def __init__(self):
        self.param_history: Dict[str, List[Dict]] = {}
        self.performance_by_params: Dict[str, Dict] = {}
    
    def record_params_performance(
        self,
        strategy_name: str,
        params: Dict,
        performance: Dict[str, float]
    ):
        """Record performance for a set of parameters."""
        if strategy_name not in self.param_history:
            self.param_history[strategy_name] = []
            self.performance_by_params[strategy_name] = {}
        
        # Create param key
        param_key = str(sorted(params.items()))
        
        self.param_history[strategy_name].append({
            'params': params,
            'performance': performance,
            'timestamp': datetime.utcnow(),
        })
        
        # Update best performance for these params
        if param_key not in self.performance_by_params[strategy_name]:
            self.performance_by_params[strategy_name][param_key] = {
                'params': params,
                'total_profit': 0,
                'trades': 0,
                'wins': 0,
            }
        
        stats = self.performance_by_params[strategy_name][param_key]
        stats['total_profit'] += performance.get('profit', 0)
        stats['trades'] += 1
        if performance.get('profit', 0) > 0:
            stats['wins'] += 1
    
    def get_optimal_params(
        self,
        strategy_name: str,
        min_trades: int = 10
    ) -> Optional[Dict]:
        """Get best performing parameters for a strategy."""
        if strategy_name not in self.performance_by_params:
            return None
        
        perf_data = self.performance_by_params[strategy_name]
        
        # Filter by minimum trades
        valid_params = [
            (key, data) for key, data in perf_data.items()
            if data['trades'] >= min_trades
        ]
        
        if not valid_params:
            return None
        
        # Find best by profit factor
        best = max(
            valid_params,
            key=lambda x: x[1]['total_profit'] / max(x[1]['trades'], 1)
        )
        
        return best[1]['params']

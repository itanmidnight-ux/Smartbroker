"""
Trading Bot ML - Motor de Machine Learning Avanzado
Ensemble de modelos con auto-entrenamiento y adaptación continua
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import StandardScaler
import joblib
import logging
from typing import Dict, List, Optional, Tuple
import os
import time
from datetime import datetime

from trading_bot.config.settings import (
    ML_CONFIG,
    MODELS_DIR,
    LOGS_DIR,
    SUPPORTED_TIMEFRAMES
)

logger = logging.getLogger(__name__)


class MLEngine:
    """Motor de Machine Learning para predicción de señales de trading"""
    
    def __init__(self, timeframe: str = '1h'):
        self.timeframe = timeframe
        self.models = {}
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.feature_names = []
        self.performance_history = []
        self.last_retrain = None
        self.win_rate = 0.0
        self.total_predictions = 0
        self.correct_predictions = 0
        
        # Configurar modelos
        self._initialize_models()
        
    def _initialize_models(self):
        """Inicializar todos los modelos del ensemble"""
        config = ML_CONFIG
        
        # Random Forest
        self.models['rf'] = RandomForestClassifier(
            n_estimators=config['n_estimators_rf'],
            max_depth=config['max_depth'],
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )
        
        # Gradient Boosting
        self.models['gb'] = GradientBoostingClassifier(
            n_estimators=config['n_estimators_gb'],
            max_depth=config['max_depth'],
            learning_rate=config['learning_rate'],
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42
        )
        
        # MLP Neural Network
        self.models['mlp'] = MLPClassifier(
            hidden_layer_sizes=(128, 64, 32),
            activation='relu',
            solver='adam',
            alpha=0.001,
            batch_size=config['batch_size'],
            learning_rate='adaptive',
            learning_rate_init=0.001,
            max_iter=config['epochs'],
            early_stopping=True,
            validation_fraction=0.1,
            random_state=42
        )
        
        logger.info(f"Modelos inicializados para timeframe {self.timeframe}")
    
    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
        """
        Preparar features para el modelo
        
        Args:
            df: DataFrame con indicadores técnicos
            
        Returns:
            Tuple con array de features y nombres de features
        """
        # Seleccionar columnas de features (todas excepto OHLCV básico)
        exclude_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        # Filtrar columnas con NaN
        df_clean = df[feature_cols].dropna(axis=1)
        feature_cols = df_clean.columns.tolist()
        
        self.feature_names = feature_cols
        
        return df_clean.values, feature_cols
    
    def create_target(self, df: pd.DataFrame, horizon: int = 5) -> np.ndarray:
        """
        Crear variable objetivo: 1 si el precio sube en el horizonte, 0 si baja
        
        Args:
            df: DataFrame con precios
            horizon: Número de velas hacia adelante para predecir
            
        Returns:
            Array con targets (0 o 1)
        """
        future_close = df['Close'].shift(-horizon)
        target = (future_close > df['Close']).astype(int)
        return target[:-horizon]  # Eliminar últimos valores sin target
    
    def train(self, df: pd.DataFrame, force: bool = False) -> bool:
        """
        Entrenar todos los modelos
        
        Args:
            df: DataFrame con datos y indicadores
            force: Forzar reentrenamiento
            
        Returns:
            True si el entrenamiento fue exitoso
        """
        try:
            logger.info(f"Iniciando entrenamiento para {self.timeframe}...")
            
            if len(df) < 500:
                logger.warning(f"Datos insuficientes: {len(df)} < 500")
                return False
            
            # Preparar features
            X, feature_names = self.prepare_features(df)
            
            if len(feature_names) < 10:
                logger.warning(f"Muy pocas features: {len(feature_names)}")
                return False
            
            # Crear target
            config = ML_CONFIG
            horizon = 5  # Predecir 5 velas adelante
            y = self.create_target(df, horizon)
            
            # Ajustar longitudes
            min_len = min(len(X), len(y))
            X = X[:min_len]
            y = y[:min_len]
            
            # Split train/test
            test_size = config['test_size']
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42, stratify=y
            )
            
            # Escalar features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Entrenar cada modelo
            model_scores = {}
            
            for name, model in self.models.items():
                logger.info(f"Entrenando {name}...")
                
                try:
                    model.fit(X_train_scaled, y_train)
                    
                    # Evaluar
                    y_pred = model.predict(X_test_scaled)
                    accuracy = accuracy_score(y_test, y_pred)
                    precision = precision_score(y_test, y_pred, zero_division=0)
                    f1 = f1_score(y_test, y_pred)
                    
                    # Cross-validation
                    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)
                    
                    model_scores[name] = {
                        'accuracy': accuracy,
                        'precision': precision,
                        'f1': f1,
                        'cv_mean': cv_scores.mean(),
                        'cv_std': cv_scores.std()
                    }
                    
                    logger.info(f"{name}: Accuracy={accuracy:.4f}, Precision={precision:.4f}, F1={f1:.4f}")
                    
                except Exception as e:
                    logger.error(f"Error entrenando {name}: {str(e)}")
                    continue
            
            if not model_scores:
                logger.error("Ningún modelo pudo ser entrenado")
                return False
            
            # Guardar información del entrenamiento
            self.is_fitted = True
            self.last_retrain = datetime.now()
            self.training_scores = model_scores
            
            # Calcular score promedio ponderado
            weights = {'rf': 0.4, 'gb': 0.35, 'mlp': 0.25}
            weighted_accuracy = sum(
                model_scores.get(name, {}).get('accuracy', 0) * weight 
                for name, weight in weights.items()
            )
            
            self.overall_accuracy = weighted_accuracy
            logger.info(f"Accuracy promedio ponderado: {weighted_accuracy:.4f}")
            
            # Guardar modelos
            self.save_models()
            
            logger.info(f"Entrenamiento completado para {self.timeframe}")
            return True
            
        except Exception as e:
            logger.error(f"Error en entrenamiento: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def predict(self, df: pd.DataFrame) -> Dict:
        """
        Hacer predicción con ensemble de modelos
        
        Args:
            df: DataFrame con la última vela y sus indicadores
            
        Returns:
            Diccionario con predicción y confianza
        """
        if not self.is_fitted:
            return {
                'signal': 'HOLD',
                'confidence': 0.0,
                'direction': 0,
                'error': 'Modelo no entrenado'
            }
        
        try:
            # Preparar features
            X, _ = self.prepare_features(df.tail(1))
            
            if X.shape[1] != len(self.feature_names):
                # Reajustar columnas
                X = X[:, :len(self.feature_names)]
            
            X_scaled = self.scaler.transform(X)
            
            # Predicciones individuales
            predictions = {}
            probabilities = {}
            
            for name, model in self.models.items():
                try:
                    pred = model.predict(X_scaled)[0]
                    prob = model.predict_proba(X_scaled)[0]
                    predictions[name] = pred
                    probabilities[name] = prob[1] if len(prob) > 1 else prob[0]
                except Exception as e:
                    logger.warning(f"Error en predicción {name}: {str(e)}")
                    predictions[name] = 0
                    probabilities[name] = 0.5
            
            # Ensemble voting ponderado
            weights = {'rf': 0.4, 'gb': 0.35, 'mlp': 0.25}
            
            weighted_prob = sum(
                probabilities.get(name, 0.5) * weight 
                for name, weight in weights.items()
            )
            
            weighted_pred = 1 if weighted_prob > 0.5 else 0
            
            # Determinar señal
            if weighted_prob > 0.65:
                signal = 'BUY'
                direction = 1
            elif weighted_prob < 0.35:
                signal = 'SELL'
                direction = -1
            else:
                signal = 'HOLD'
                direction = 0
            
            # Confianza
            confidence = max(weighted_prob, 1 - weighted_prob)
            
            result = {
                'signal': signal,
                'confidence': float(confidence),
                'direction': direction,
                'probability': float(weighted_prob),
                'individual_predictions': predictions,
                'individual_probabilities': probabilities,
                'timestamp': datetime.now().isoformat()
            }
            
            self.total_predictions += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error en predicción: {str(e)}")
            return {
                'signal': 'HOLD',
                'confidence': 0.0,
                'direction': 0,
                'error': str(e)
            }
    
    def update_performance(self, actual_result: int, predicted_direction: int):
        """
        Actualizar estadísticas de performance
        
        Args:
            actual_result: Resultado real (1=up, 0=down)
            predicted_direction: Dirección predicha (1, 0, -1)
        """
        if predicted_direction == 0:  # HOLD
            return
        
        expected = 1 if predicted_direction == 1 else 0
        is_correct = (actual_result == expected)
        
        if is_correct:
            self.correct_predictions += 1
        
        self.win_rate = self.correct_predictions / max(1, self.total_predictions)
        
        self.performance_history.append({
            'timestamp': datetime.now(),
            'predicted': predicted_direction,
            'actual': actual_result,
            'correct': is_correct
        })
        
        # Mantener solo últimas 1000 predicciones
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]
    
    def needs_retraining(self) -> bool:
        """Verificar si el modelo necesita reentrenamiento"""
        if not self.is_fitted or self.last_retrain is None:
            return True
        
        # Si win rate baja del threshold
        if self.win_rate < ML_CONFIG['retrain_on_win_rate_drop']:
            logger.info(f"Win rate bajo ({self.win_rate:.2f}), reentrenando...")
            return True
        
        # Si pasó mucho tiempo desde último retrain
        hours_since_retrain = (datetime.now() - self.last_retrain).total_seconds() / 3600
        if hours_since_retrain > 24:  # Cada 24 horas
            return True
        
        return False
    
    def save_models(self):
        """Guardar modelos en disco"""
        try:
            model_dir = os.path.join(MODELS_DIR, self.timeframe)
            os.makedirs(model_dir, exist_ok=True)
            
            # Guardar cada modelo
            for name, model in self.models.items():
                filepath = os.path.join(model_dir, f'{name}_model.pkl')
                joblib.dump(model, filepath)
            
            # Guardar scaler
            scaler_path = os.path.join(model_dir, 'scaler.pkl')
            joblib.dump(self.scaler, scaler_path)
            
            # Guardar metadata
            metadata = {
                'timeframe': self.timeframe,
                'is_fitted': self.is_fitted,
                'feature_names': self.feature_names,
                'win_rate': self.win_rate,
                'total_predictions': self.total_predictions,
                'last_retrain': self.last_retrain.isoformat() if self.last_retrain else None,
                'training_scores': self.training_scores if hasattr(self, 'training_scores') else {}
            }
            metadata_path = os.path.join(model_dir, 'metadata.json')
            import json
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            logger.info(f"Modelos guardados en {model_dir}")
            
        except Exception as e:
            logger.error(f"Error guardando modelos: {str(e)}")
    
    def load_models(self) -> bool:
        """Cargar modelos desde disco"""
        try:
            model_dir = os.path.join(MODELS_DIR, self.timeframe)
            
            if not os.path.exists(model_dir):
                logger.info(f"No hay modelos guardados para {self.timeframe}")
                return False
            
            # Cargar scaler
            scaler_path = os.path.join(model_dir, 'scaler.pkl')
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
            
            # Cargar modelos
            loaded_count = 0
            for name in self.models.keys():
                filepath = os.path.join(model_dir, f'{name}_model.pkl')
                if os.path.exists(filepath):
                    self.models[name] = joblib.load(filepath)
                    loaded_count += 1
            
            if loaded_count > 0:
                self.is_fitted = True
                logger.info(f"Modelos cargados: {loaded_count}/{len(self.models)}")
                
                # Cargar metadata
                metadata_path = os.path.join(model_dir, 'metadata.json')
                if os.path.exists(metadata_path):
                    import json
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                        self.win_rate = metadata.get('win_rate', 0)
                        self.total_predictions = metadata.get('total_predictions', 0)
                        self.feature_names = metadata.get('feature_names', [])
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error cargando modelos: {str(e)}")
            return False
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Obtener importancia de features"""
        if not self.is_fitted:
            return {}
        
        try:
            # Usar Random Forest para importancia
            rf_model = self.models.get('rf')
            if rf_model is None:
                return {}
            
            importances = rf_model.feature_importances_
            
            importance_dict = dict(zip(self.feature_names, importances))
            
            # Ordenar por importancia
            sorted_importance = dict(
                sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
            )
            
            return sorted_importance
            
        except Exception as e:
            logger.error(f"Error obteniendo importancia: {str(e)}")
            return {}
    
    def get_stats(self) -> Dict:
        """Obtener estadísticas del modelo"""
        return {
            'timeframe': self.timeframe,
            'is_fitted': self.is_fitted,
            'win_rate': self.win_rate,
            'total_predictions': self.total_predictions,
            'correct_predictions': self.correct_predictions,
            'last_retrain': self.last_retrain.isoformat() if self.last_retrain else None,
            'training_scores': getattr(self, 'training_scores', {}),
            'overall_accuracy': getattr(self, 'overall_accuracy', 0),
            'feature_count': len(self.feature_names)
        }


class AdaptiveMLManager:
    """Gestor de ML adaptativo para múltiples timeframes"""
    
    def __init__(self):
        self.ml_engines = {}
        self.initialized = False
        
    def initialize_all_timeframes(self):
        """Inicializar motores ML para todos los timeframes soportados"""
        for tf in SUPPORTED_TIMEFRAMES:
            if tf not in self.ml_engines:
                self.ml_engines[tf] = MLEngine(timeframe=tf)
                # Intentar cargar modelos existentes
                self.ml_engines[tf].load_models()
        
        self.initialized = True
        logger.info(f"ML Manager inicializado para {len(self.ml_engines)} timeframes")
    
    def get_engine(self, timeframe: str) -> Optional[MLEngine]:
        """Obtener engine para un timeframe específico"""
        if timeframe not in self.ml_engines:
            logger.error(f"Timeframe no soportado: {timeframe}")
            return None
        return self.ml_engines[timeframe]
    
    def train_all(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, bool]:
        """Entrenar todos los engines con sus respectivos datos"""
        results = {}
        
        for tf, df in data_dict.items():
            if tf in self.ml_engines:
                success = self.ml_engines[tf].train(df)
                results[tf] = success
        
        return results
    
    def predict_all(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
        """Hacer predicciones para todos los timeframes"""
        results = {}
        
        for tf, df in data_dict.items():
            if tf in self.ml_engines:
                results[tf] = self.ml_engines[tf].predict(df)
        
        return results
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Obtener estadísticas de todos los engines"""
        stats = {}
        for tf, engine in self.ml_engines.items():
            stats[tf] = engine.get_stats()
        return stats
    
    def check_retraining_needed(self) -> List[str]:
        """Verificar qué engines necesitan reentrenamiento"""
        needs_retrain = []
        for tf, engine in self.ml_engines.items():
            if engine.needs_retraining():
                needs_retrain.append(tf)
        return needs_retrain

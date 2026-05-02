"""
Trading Bot ML - Supervisor LLM (Large Language Model)
Sistema de supervisión inteligente que analiza el mercado y ajusta parámetros automáticamente
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import os
import numpy as np
import pandas as pd

from trading_bot.config.settings import (
    LLM_SUPERVISOR_CONFIG,
    OPERATION_MODES,
    TIMEFRAME_CONFIG,
    LOGS_DIR
)

logger = logging.getLogger(__name__)


class MarketRegime:
    """Clase para detectar el régimen actual del mercado"""
    
    BULLISH = 'BULLISH'
    BEARISH = 'BEARISH'
    NEUTRAL = 'NEUTRAL'
    VOLATILE = 'VOLATILE'
    TRENDING_UP = 'TRENDING_UP'
    TRENDING_DOWN = 'TRENDING_DOWN'
    
    @staticmethod
    def detect(df: pd.DataFrame) -> str:
        """
        Detectar régimen actual del mercado
        
        Args:
            df: DataFrame con datos OHLCV e indicadores
            
        Returns:
            String con el régimen detectado
        """
        if len(df) < 50:
            return MarketRegime.NEUTRAL
        
        # Calcular métricas
        sma_20 = df['Close'].rolling(20).mean().iloc[-1]
        sma_50 = df['Close'].rolling(50).mean().iloc[-1]
        sma_200 = df['Close'].rolling(200).mean().iloc[-1]
        
        current_price = df['Close'].iloc[-1]
        
        # Volatilidad
        volatility = df['Close'].pct_change().std() * np.sqrt(252)
        
        # Tendencia
        price_above_sma20 = current_price > sma_20
        price_above_sma50 = current_price > sma_50
        price_above_sma200 = current_price > sma_200
        
        sma20_above_sma50 = sma_20 > sma_50
        sma50_above_sma200 = sma_50 > sma_200
        
        # ADX para fuerza de tendencia
        adx = df.get('adx', pd.Series([20])).iloc[-1]
        
        # Determinar régimen
        if volatility > 0.4:  # Alta volatilidad
            return MarketRegime.VOLATILE
        
        if price_above_sma20 and price_above_sma50 and price_above_sma200:
            if sma20_above_sma50 and sma50_above_sma200:
                if adx > 25:
                    return MarketRegime.TRENDING_UP
                return MarketRegime.BULLISH
        
        if not price_above_sma20 and not price_above_sma50 and not price_above_sma200:
            if not sma20_above_sma50 and not sma50_above_sma200:
                if adx > 25:
                    return MarketRegime.TRENDING_DOWN
                return MarketRegime.BEARISH
        
        return MarketRegime.NEUTRAL


class LLMSupervisor:
    """
    Supervisor tipo LLM que analiza datos y toma decisiones
    Simula un modelo de lenguaje para análisis de mercado
    """
    
    def __init__(self):
        self.config = LLM_SUPERVISOR_CONFIG
        self.last_analysis = None
        self.last_adjustment = None
        self.analysis_history = []
        self.adjustments_made = []
        self.current_mode = 'normal'
        self.market_regime = MarketRegime.NEUTRAL
        self.performance_metrics = {}
        self.recommendations = []
        
        logger.info("LLM Supervisor inicializado")
    
    def analyze_market(self, df: pd.DataFrame, timeframe: str,
                       simulator_stats: Dict = None) -> Dict:
        """
        Analizar el mercado y generar conclusiones
        
        Args:
            df: DataFrame con datos del mercado
            timeframe: Timeframe actual
            simulator_stats: Estadísticas del simulador
            
        Returns:
            Diccionario con análisis y recomendaciones
        """
        logger.info(f"Analizando mercado para {timeframe}...")
        
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'timeframe': timeframe,
            'market_regime': None,
            'trend_strength': 0,
            'volatility_level': 'NORMAL',
            'momentum': 0,
            'volume_analysis': 'NORMAL',
            'risk_level': 'MEDIUM',
            'recommendations': [],
            'suggested_mode': self.current_mode,
            'confidence': 0.0
        }
        
        if len(df) < 50:
            analysis['error'] = 'Datos insuficientes'
            return analysis
        
        # Detectar régimen de mercado
        self.market_regime = MarketRegime.detect(df)
        analysis['market_regime'] = self.market_regime
        
        # Calcular fuerza de tendencia
        sma_20 = df['Close'].rolling(20).mean()
        sma_50 = df['Close'].rolling(50).mean()
        trend_strength = abs(sma_20.iloc[-1] - sma_50.iloc[-1]) / sma_50.iloc[-1] * 100
        analysis['trend_strength'] = trend_strength
        
        # Nivel de volatilidad
        volatility = df['Close'].pct_change().std()
        if volatility > 0.03:
            analysis['volatility_level'] = 'HIGH'
            analysis['risk_level'] = 'HIGH'
        elif volatility < 0.01:
            analysis['volatility_level'] = 'LOW'
            analysis['risk_level'] = 'LOW'
        
        # Momentum
        momentum = (df['Close'].iloc[-1] - df['Close'].iloc[-10]) / df['Close'].iloc[-10] * 100
        analysis['momentum'] = momentum
        
        # Análisis de volumen
        avg_volume = df['Volume'].rolling(20).mean()
        current_volume = df['Volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume.iloc[-1] if avg_volume.iloc[-1] > 0 else 1
        
        if volume_ratio > 2:
            analysis['volume_analysis'] = 'HIGH'
        elif volume_ratio < 0.5:
            analysis['volume_analysis'] = 'LOW'
        
        # Generar recomendaciones basadas en análisis
        recommendations = self._generate_recommendations(analysis, simulator_stats)
        analysis['recommendations'] = recommendations
        
        # Sugerir modo de operación
        suggested_mode = self._suggest_mode(analysis, simulator_stats)
        analysis['suggested_mode'] = suggested_mode
        
        # Calcular confianza
        confidence = self._calculate_confidence(analysis)
        analysis['confidence'] = confidence
        
        # Guardar histórico
        self.last_analysis = analysis
        self.analysis_history.append(analysis)
        
        # Mantener solo últimos 100 análisis
        if len(self.analysis_history) > 100:
            self.analysis_history = self.analysis_history[-100:]
        
        logger.info(f"Análisis completado. Régimen: {self.market_regime}, Confianza: {confidence:.2f}")
        
        return analysis
    
    def _generate_recommendations(self, analysis: Dict, 
                                   simulator_stats: Dict = None) -> List[str]:
        """Generar recomendaciones basadas en el análisis"""
        recommendations = []
        
        regime = analysis['market_regime']
        volatility = analysis['volatility_level']
        momentum = analysis['momentum']
        
        # Recomendaciones por régimen
        if regime == MarketRegime.TRENDING_UP:
            recommendations.append("Tendencia alcista fuerte identificada. Considerar posiciones LONG.")
            recommendations.append("Usar trailing stop para maximizar ganancias.")
        elif regime == MarketRegime.TRENDING_DOWN:
            recommendations.append("Tendencia bajista fuerte identificada. Considerar posiciones SHORT o esperar.")
            recommendations.append("Evitar compras hasta confirmación de reversión.")
        elif regime == MarketRegime.VOLATILE:
            recommendations.append("Alta volatilidad detectada. Reducir tamaño de posición.")
            recommendations.append("Ampliar stops para evitar salidas prematuras.")
        elif regime == MarketRegime.NEUTRAL:
            recommendations.append("Mercado lateral. Estrategias de rango pueden funcionar.")
            recommendations.append("Esperar ruptura clara antes de entrar.")
        
        # Recomendaciones por volatilidad
        if volatility == 'HIGH':
            recommendations.append("Volatilidad alta. Usar modo SEGURO recomendado.")
        elif volatility == 'LOW':
            recommendations.append("Volatilidad baja. Oportunidades limitadas.")
        
        # Recomendaciones por momentum
        if momentum > 5:
            recommendations.append("Momentum muy positivo. Posible sobrecompra.")
        elif momentum < -5:
            recommendations.append("Momentum muy negativo. Posible sobreventa.")
        
        # Basadas en performance del simulador
        if simulator_stats:
            win_rate = simulator_stats.get('win_rate', 0)
            if win_rate < 70:
                recommendations.append("Win rate bajo. Considerar ajustar parámetros o cambiar a modo SEGURO.")
            elif win_rate > 85:
                recommendations.append("Excelente performance. Mantener estrategia actual.")
            
            max_dd = simulator_stats.get('max_drawdown', 0)
            if max_dd > 15:
                recommendations.append("Drawdown alto. Reducir riesgo inmediatamente.")
        
        return recommendations
    
    def _suggest_mode(self, analysis: Dict, 
                      simulator_stats: Dict = None) -> str:
        """Sugerir modo de operación óptimo"""
        regime = analysis['market_regime']
        volatility = analysis['volatility_level']
        confidence = analysis['confidence']
        
        # Empezar con modo normal
        suggested = 'normal'
        
        # Ajustar por volatilidad
        if volatility == 'HIGH':
            suggested = 'safe'
        
        # Ajustar por régimen
        if regime == MarketRegime.VOLATILE:
            suggested = 'safe'
        elif regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            if volatility != 'HIGH':
                suggested = 'aggressive'
        
        # Ajustar por performance
        if simulator_stats:
            win_rate = simulator_stats.get('win_rate', 0)
            max_dd = simulator_stats.get('max_drawdown', 0)
            
            if win_rate < 65 or max_dd > 20:
                suggested = 'safe'
            elif win_rate > 80 and max_dd < 10:
                if suggested != 'safe':  # No subir si ya es safe por otras razones
                    suggested = 'aggressive'
        
        return suggested
    
    def _calculate_confidence(self, analysis: Dict) -> float:
        """Calcular nivel de confianza del análisis"""
        confidence = 0.5  # Base
        
        # Aumentar confianza con tendencia clara
        if analysis['trend_strength'] > 2:
            confidence += 0.2
        
        # Aumentar con volumen confirmado
        if analysis['volume_analysis'] == 'HIGH':
            confidence += 0.1
        
        # Disminuir con volatilidad extrema
        if analysis['volatility_level'] == 'HIGH':
            confidence -= 0.15
        
        # Aumentar si hay momentum claro
        if abs(analysis['momentum']) > 3:
            confidence += 0.1
        
        return min(max(confidence, 0.0), 1.0)
    
    def make_adjustments(self, analysis: Dict, 
                         current_params: Dict) -> Dict:
        """
        Hacer ajustes automáticos a los parámetros
        
        Args:
            analysis: Análisis actual del mercado
            current_params: Parámetros actuales
            
        Returns:
            Diccionario con parámetros ajustados
        """
        now = datetime.now()
        
        # Verificar cooldown
        if self.last_adjustment:
            time_since_last = (now - self.last_adjustment).total_seconds()
            if time_since_last < self.config['adjustment_cooldown']:
                logger.info(f"Ajuste en cooldown. Faltan {self.config['adjustment_cooldown'] - time_since_last:.0f}s")
                return current_params
        
        adjusted_params = current_params.copy()
        adjustments = []
        
        regime = analysis['market_regime']
        volatility = analysis['volatility_level']
        
        # Ajustar stops según volatilidad
        if volatility == 'HIGH':
            if 'stop_loss_pct' in adjusted_params:
                adjusted_params['stop_loss_pct'] *= 1.5
                adjustments.append("SL aumentado por alta volatilidad")
            if 'take_profit_pct' in adjusted_params:
                adjusted_params['take_profit_pct'] *= 1.3
                adjustments.append("TP aumentado por alta volatilidad")
        elif volatility == 'LOW':
            if 'stop_loss_pct' in adjusted_params:
                adjusted_params['stop_loss_pct'] *= 0.8
                adjustments.append("SL reducido por baja volatilidad")
        
        # Ajustar por régimen
        if regime == MarketRegime.VOLATILE:
            if 'confidence_threshold' in adjusted_params:
                adjusted_params['confidence_threshold'] = min(0.9, 
                    adjusted_params.get('confidence_threshold', 0.7) + 0.1)
                adjustments.append("Umbral de confianza aumentado")
        
        if regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            if 'max_position_size' in adjusted_params:
                adjusted_params['max_position_size'] *= 1.2
                adjustments.append("Tamaño de posición aumentado por tendencia clara")
        
        # Guardar ajustes
        if adjustments:
            self.last_adjustment = now
            adjustment_record = {
                'timestamp': now.isoformat(),
                'adjustments': adjustments,
                'regime': regime,
                'params_before': current_params,
                'params_after': adjusted_params
            }
            self.adjustments_made.append(adjustment_record)
            
            logger.info(f"Ajustes realizados: {adjustments}")
        
        return adjusted_params
    
    def evaluate_performance(self, simulator_stats: Dict) -> Dict:
        """
        Evaluar performance y generar correcciones
        
        Args:
            simulator_stats: Estadísticas del simulador
            
        Returns:
            Diccionario con evaluación y correcciones
        """
        evaluation = {
            'timestamp': datetime.now().isoformat(),
            'overall_score': 0,
            'strengths': [],
            'weaknesses': [],
            'corrections': [],
            'action_required': False
        }
        
        win_rate = simulator_stats.get('win_rate', 0)
        profit_factor = simulator_stats.get('profit_factor', 0)
        max_dd = simulator_stats.get('max_drawdown', 0)
        sharpe = simulator_stats.get('sharpe_ratio', 0)
        total_trades = simulator_stats.get('total_trades', 0)
        
        # Evaluar win rate
        if win_rate >= 80:
            evaluation['strengths'].append(f"Excelente win rate: {win_rate:.1f}%")
            evaluation['overall_score'] += 30
        elif win_rate >= 70:
            evaluation['strengths'].append(f"Buen win rate: {win_rate:.1f}%")
            evaluation['overall_score'] += 20
        elif win_rate >= 60:
            evaluation['weaknesses'].append(f"Win rate mejorable: {win_rate:.1f}%")
            evaluation['overall_score'] += 10
            evaluation['corrections'].append("Considerar filtrar señales de baja confianza")
        else:
            evaluation['weaknesses'].append(f"Win rate bajo: {win_rate:.1f}%")
            evaluation['corrections'].append("Cambiar a modo SEGURO inmediatamente")
            evaluation['action_required'] = True
        
        # Evaluar drawdown
        if max_dd <= 10:
            evaluation['strengths'].append(f"Drawdown controlado: {max_dd:.1f}%")
            evaluation['overall_score'] += 30
        elif max_dd <= 15:
            evaluation['strengths'].append(f"Drawdown aceptable: {max_dd:.1f}%")
            evaluation['overall_score'] += 20
        elif max_dd <= 20:
            evaluation['weaknesses'].append(f"Drawdown elevado: {max_dd:.1f}%")
            evaluation['overall_score'] += 10
            evaluation['corrections'].append("Reducir tamaño de posición")
        else:
            evaluation['weaknesses'].append(f"Drawdown peligroso: {max_dd:.1f}%")
            evaluation['corrections'].append("Detener operaciones y revisar estrategia")
            evaluation['action_required'] = True
        
        # Evaluar profit factor
        if profit_factor >= 2.0:
            evaluation['strengths'].append(f"Profit factor excelente: {profit_factor:.2f}")
            evaluation['overall_score'] += 25
        elif profit_factor >= 1.5:
            evaluation['strengths'].append(f"Profit factor bueno: {profit_factor:.2f}")
            evaluation['overall_score'] += 15
        elif profit_factor >= 1.0:
            evaluation['weaknesses'].append(f"Profit factor mejorable: {profit_factor:.2f}")
            evaluation['overall_score'] += 5
        else:
            evaluation['weaknesses'].append(f"Profit factor negativo: {profit_factor:.2f}")
            evaluation['corrections'].append("Revisar relación riesgo/beneficio")
        
        # Evaluar Sharpe ratio
        if sharpe >= 2.0:
            evaluation['strengths'].append(f"Sharpe ratio excelente: {sharpe:.2f}")
            evaluation['overall_score'] += 15
        elif sharpe >= 1.0:
            evaluation['strengths'].append(f"Sharpe ratio aceptable: {sharpe:.2f}")
            evaluation['overall_score'] += 10
        
        # Normalizar score a 100
        evaluation['overall_score'] = min(100, evaluation['overall_score'])
        
        # Guardar evaluación
        self.performance_metrics = evaluation
        
        logger.info(f"Evaluación completada. Score: {evaluation['overall_score']}/100")
        
        return evaluation
    
    def get_supervisor_status(self) -> Dict:
        """Obtener estado completo del supervisor"""
        return {
            'current_mode': self.current_mode,
            'market_regime': self.market_regime,
            'last_analysis': self.last_analysis,
            'last_adjustment': self.last_adjustment.isoformat() if self.last_adjustment else None,
            'total_analyses': len(self.analysis_history),
            'total_adjustments': len(self.adjustments_made),
            'performance_metrics': self.performance_metrics,
            'recent_recommendations': self.analysis_history[-1]['recommendations'] if self.analysis_history else []
        }
    
    def save_analysis_log(self):
        """Guardar log de análisis"""
        log_file = os.path.join(LOGS_DIR, 'llm_supervisor_log.json')
        
        log_data = {
            'analysis_history': self.analysis_history[-50:],  # Últimos 50
            'adjustments_made': self.adjustments_made[-20:],  # Últimos 20
            'performance_metrics': self.performance_metrics
        }
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2, default=str)
        
        logger.info(f"Log guardado en {log_file}")

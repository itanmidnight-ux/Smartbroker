# Plan de Implementación - Smartbroker

## Resumen Ejecutivo

Este documento detalla el plan para completar la implementación del sistema de trading algorítmico Smartbroker, basado en la arquitectura definida y el estado actual del proyecto.

---

## Estado Actual (Diciembre 2024)

### ✅ Completado (Fase 1-3 Parcial)

1. **Infraestructura Base**
   - [x] Conexión resiliente a MT5
   - [x] Carga de perfiles de broker
   - [x] Sistema de configuración (.env)
   - [x] Scripts de instalación Windows

2. **Data Feed**
   - [x] MT5 Data Feed funcional
   - [x] Soporte multi-símbolo (XAUUSD, XAUEUR)
   - [x] Obtención de OHLCV
   - [x] Detección de régimen de mercado

3. **Machine Learning**
   - [x] Pipeline de entrenamiento con walk-forward
   - [x] Calibración probabilística (sigmoid)
   - [x] Clasificación de regímenes (trending/ranging/high_volatility)
   - [x] Modelo por régimen
   - [x] Validación con green_flag
   - [x] Registry de modelos versionados

4. **Señales**
   - [x] Sistema básico de scoring
   - [x] Procesador de señales
   - [x] Almacenamiento en SQLite
   - [x] Análisis de confluencia

5. **API**
   - [x] FastAPI configurado
   - [x] Endpoints de validación
   - [x] Endpoints de entrenamiento ML
   - [x] Endpoints de predicción
   - [x] Control de estrategia (on/off)

6. **Dashboard**
   - [x] Dashboard web operativo
   - [x] Visualización de velas
   - [x] Historial de señales
   - [x] Indicador 5min

7. **Agente Adaptativo**
   - [x] AdaptiveBanditAgent implementado
   - [x] Estado pre-entrenado
   - [x] Feedback básico

8. **Risk Management**
   - [x] Kill switch básico
   - [x] Límites de riesgo
   - [x] Control de modo real (live_armed)

---

## 🔴 Pendientes Críticos

### Fase 2 - Completar Inteligencia Básica

#### 2.1 Estrategias de Trading (PRIORIDAD ALTA)
- [ ] **Trend Following Strategy**
  - Entrada por cruce de medias
  - Filtro de tendencia con ADX
  - SL/TP dinámicos con ATR
  
- [ ] **Mean Reversion Strategy**
  - Bandas de Bollinger
  - RSI extremos
  - Vuelta a la media
  
- [ ] **Breakout Strategy**
  - Ruptura de rangos
  - Volumen de confirmación
  - False breakout detection
  
- [ ] **Scalping Strategy**
  - Entradas rápidas M1/M5
  - Objetivo pequeño (5-10 pips)
  - Stop ajustado

**Archivos a crear:**
```
python/src/strategy/
├── trend_following.py
├── mean_reversion.py
├── breakout.py
├── scalping.py
└── base_strategy.py (interface común)
```

#### 2.2 Sistema de Scoring Mejorado
- [ ] Score 0-100 con pesos dinámicos
- [ ] Contexto de mercado integrado
- [ ] Confluencias múltiples (mínimo 3/5)
- [ ] Nivel de confianza (%)
- [ ] Historical performance por setup

**Mejoras necesarias:**
```python
class SignalScore:
    score: int  # 0-100
    confidence: float  # 0-1
    context: str  # trending/ranging/volatile
    confluences: List[str]  # ["RSI", "MACD", "BB", ...]
    regime_fit: str  # mejor régimen para esta señal
    historical_winrate: float  # winrate histórico similar setup
```

#### 2.3 Backtesting Robusto
- [ ] Motor de backtesting vectorizado
- [ ] Soporte multi-timeframe
- [ ] Métricas completas (Sharpe, Sortino, Calmar)
- [ ] Curva de equity
- [ ] Drawdown analysis
- [ ] Walk-forward optimization

**Archivo:** `python/src/backtest/engine.py`

---

### Fase 3 - Completar ML Real

#### 3.1 Feature Engineering Avanzado
- [ ] Features de estructura de mercado
  - Highs/Lows significativos
  - Order blocks (conceptos SMC)
  - Fair value gaps
  
- [ ] Features de volumen
  - Volume profile
  - VWAP
  - Acumulación/distribución
  
- [ ] Features de volatilidad
  - ATR múltiple timeframes
  - Volatilidad relativa
  - Rangos históricos

**Archivo:** `python/src/ml/feature_engineer.py`

#### 3.2 Simulación Mejorada
- [ ] **Slippage Dinámico**
  ```python
  slippage = base_slippage * (volatility_factor) * (liquidity_factor)
  ```
  
- [ ] **Spread Variable**
  - Spread real por hora del día
  - Spread en noticias económicas
  - Spread por broker
  
- [ ] **Latencia Simulada**
  - Delay de ejecución (50-500ms)
  - Probabilidad de rechazo
  - Reintentos
  
- [ ] **Ejecución Parcial (Fills)**
  - Fill ratio según liquidez
  - Partial fills
  - Slippage en fills parciales

**Archivo:** `python/src/simulator/execution_engine.py`

#### 3.3 LightGBM Integration
- [ ] Migrar de LogisticRegression a LightGBM
- [ ] Hyperparameter tuning automático
- [ ] Feature importance tracking
- [ ] Early stopping

```python
import lightgbm as lgb

params = {
    'objective': 'binary',
    'metric': 'auc',
    'boosting_type': 'gbdt',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.9,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'verbose': -1
}
```

---

### Fase 4 - Multi-Agente

#### 4.1 Ranking Dinámico de Estrategias
- [ ] Performance tracking por estrategia
- [ ] Rolling winrate (últimos 50-100 trades)
- [ ] Profit factor por estrategia
- [ ] Asignación de peso según performance
- [ ] Eliminación temporal de estrategias underperforming

**Archivo:** `python/src/strategy/ranker.py`

```python
class StrategyRanker:
    def __init__(self):
        self.performance = {}  # strategy_id -> metrics
        
    def update_performance(self, strategy_id: str, trade_result: dict):
        # Actualizar métricas
        pass
        
    def get_weights(self) -> Dict[str, float]:
        # Retornar pesos normalizados
        pass
        
    def get_active_strategies(self) -> List[str]:
        # Estrategias activas (no underperforming)
        pass
```

#### 4.2 Asignación Adaptativa de Capital
- [ ] Risk parity entre estrategias
- [ ] Kelly criterion modificado
- [ ] Máxima exposición por activo
- [ ] Correlación entre estrategias

**Archivo:** `python/src/risk/capital_allocator.py`

#### 4.3 Sistema Multi-Estrategia
- [ ] Ejecución simultánea de 4 estrategias
- [ ] Señales combinadas con voting
- [ ] Gestión de conflictos (compra vs venta)
- [ ] Exposure netting

**Archivo:** `python/src/strategy/multi_strategy_manager.py`

---

### Fase 5 - Auto-Optimización Total

#### 5.1 Reentrenamiento Automático
- [ ] Schedule de reentrenamiento (diario/semanal)
- [ ] Trigger por drift detection
- [ ] Validación automática antes de deploy
- [ ] Rollback si performance empeora

**Archivo:** `python/src/ml/auto_retrain.py`

```python
class AutoRetrainer:
    def __init__(self):
        self.last_train_date = None
        self.performance_threshold = 0.45  # minimum accuracy
        
    def should_retrain(self) -> bool:
        # Verificar tiempo desde último train
        # Verificar drift
        # Verificar performance reciente
        pass
        
    def retrain_if_needed(self, symbol: str, data: pd.DataFrame):
        if self.should_retrain():
            result = train_and_register(symbol, data)
            if not result['green_flag']:
                self.rollback()
```

#### 5.2 Memoria de Patrones
- [ ] Database de setups históricos
- [ ] Clustering de patrones similares
- [ ] Búsqueda por similitud (cosine similarity)
- [ ] Performance de patrones similares

**Archivo:** `python/src/ml/pattern_memory.py`

```python
class PatternMemory:
    def __init__(self):
        self.patterns = []  # list of pattern embeddings
        self.results = []   # results after each pattern
        
    def store_pattern(self, features: np.array, result: dict):
        # Guardar patrón y resultado
        pass
        
    def find_similar(self, current_features: np.array, top_k: int = 10):
        # Buscar patrones similares
        # Retornar winrate histórico
        pass
```

#### 5.3 Feedback Loop Completo
- [ ] Tracking post-trade automático
- [ ] Actualización de pesos basada en resultado
- [ ] Ajuste de parámetros en caliente
- [ ] Aprendizaje por refuerzo básico

**Archivo:** `python/src/agent/reinforcement_learner.py`

#### 5.4 Anti-Overfitting Avanzado
- [ ] Inyección de ruido en backtesting
  ```python
  noisy_close = close * (1 + np.random.normal(0, 0.0001, len(close)))
  ```
- [ ] Penalización a curvas "perfectas"
  - Si Sharpe > 3 → penalizar
  - Si winrate > 70% → sospechoso
- [ ] Out-of-sample testing estricto
- [ ] Purged K-Fold Cross Validation

---

## Infraestructura Pendiente

### Bases de Datos

#### Redis (Tiempo Real)
- [ ] Instalar Redis
- [ ] Caché de precios
- [ ] Estado actual del mercado
- [ ] Señales en tiempo real

```python
# python/src/storage/redis_store.py
import redis

class RedisStore:
    def __init__(self):
        self.client = redis.Redis(host='localhost', port=6379, db=0)
        
    def set_price(self, symbol: str, price: float):
        self.client.set(f"price:{symbol}", price)
        
    def get_price(self, symbol: str) -> float:
        return float(self.client.get(f"price:{symbol}"))
```

#### PostgreSQL (Histórico)
- [ ] Instalar PostgreSQL
- [ ] Schema de trades
- [ ] Schema de señales
- [ ] Schema de métricas
- [ ] TimescaleDB extension (opcional)

```sql
-- Tabla de trades
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20),
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    action VARCHAR(10),
    entry_price FLOAT,
    exit_price FLOAT,
    pnl FLOAT,
    strategy_id VARCHAR(50),
    regime VARCHAR(20)
);

-- Tabla de señales
CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    symbol VARCHAR(20),
    score INTEGER,
    confidence FLOAT,
    action VARCHAR(10),
    regime VARCHAR(20)
);
```

### Monitoreo

#### Grafana Dashboard
- [ ] Instalar Grafana
- [ ] DataSource PostgreSQL
- [ ] Dashboards:
  - P&L en tiempo real
  - Drawdown
  - Winrate rolling
  - Exposición por activo
  - Performance por estrategia
  - Régimen de mercado actual

#### Alertas
- [ ] Alerta de drawdown máximo
- [ ] Alerta de pérdida diaria
- [ ] Alerta de error en conexión MT5
- [ ] Alerta de drift detectado

---

## API Endpoints Pendientes

### Nuevos Endpoints Requeridos

```python
# Estado completo del bot
GET /status
{
    "running": true,
    "mode": "paper",
    "active_strategies": ["trend_following", "mean_reversion"],
    "current_regime": "trending",
    "balance": 10000.0,
    "equity": 10250.0,
    "drawdown": 0.025,
    "positions": [...]
}

# Métricas detalladas
GET /metrics
{
    "winrate": 0.52,
    "profit_factor": 1.65,
    "sharpe_ratio": 1.2,
    "max_drawdown": 0.08,
    "total_trades": 245,
    "avg_trade_duration": "2h 15m",
    "expectancy": 15.50
}

# Control avanzado
POST /control
{
    "action": "set_mode",  # paper|live|stop
    "aggressiveness": 0.5,  # 0-1
    "max_positions": 3,
    "enabled_strategies": ["trend_following"]
}

# Backtesting
POST /backtest
{
    "symbol": "XAUUSD",
    "strategy": "trend_following",
    "start_date": "2024-01-01",
    "end_date": "2024-12-01",
    "initial_capital": 10000
}

# Performance por estrategia
GET /performance/strategies
[
    {
        "strategy_id": "trend_following",
        "winrate": 0.55,
        "profit_factor": 1.8,
        "total_trades": 89,
        "pnl": 1250.0
    },
    ...
]
```

---

## Cronograma Estimado

### Semana 1-2: Estrategias Básicas
- Implementar 2 estrategias (trend following + mean reversion)
- Mejorar sistema de scoring
- Documentar estrategias

### Semana 3-4: Backtesting y Simulación
- Motor de backtesting
- Slippage y spread variable
- Métricas de performance

### Semana 5-6: ML Avanzado
- Migrar a LightGBM
- Feature engineering avanzado
- Pattern memory básico

### Semana 7-8: Multi-Estrategia
- Ranking dinámico
- Asignación de capital
- Ejecución simultánea

### Semana 9-10: Auto-Optimización
- Reentrenamiento automático
- Feedback loop
- Anti-overfitting

### Semana 11-12: Infraestructura
- Redis + PostgreSQL
- Grafana dashboards
- Alertas y monitoreo

---

## Testing y Validación

### Tests Unitarios
```bash
# Ejecutar tests
cd python
pytest tests/
```

**Cobertura objetivo:** > 80%

### Tests de Integración
- [ ] Conexión MT5 mock
- [ ] Simulador con datos históricos
- [ ] Pipeline ML completo
- [ ] API endpoints

### Validación en Paper Trading
- [ ] Mínimo 100 trades en paper
- [ ] Múltiples regímenes de mercado
- [ ] Validar métricas vs backtest
- [ ] Stress test en volatilidad alta

---

## Criterios de Éxito

### Para ir a Producción (Live Trading)

1. **Performance:**
   - Winrate > 45%
   - Profit Factor > 1.5
   - Max Drawdown < 15%
   - Sharpe Ratio > 1.0

2. **Estabilidad:**
   - 1000+ trades en paper sin crashes
   - Uptime > 99%
   - Recovery automático de errores

3. **Validación:**
   - Backtest walk-forward positivo
   - Paper trading consistente con backtest
   - Múltiples regímenes probados

4. **Seguridad:**
   - Kill switch funcional
   - Límites de riesgo respetados
   - Modo real bloqueado por defecto

---

## Riesgos y Mitigación

### Riesgo: Overfitting
**Mitigación:**
- Walk-forward validation
- Out-of-sample testing
- Penalización a curvas perfectas
- Ruido en simulación

### Riesgo: Underperformance en Live
**Mitigación:**
- Empezar con tamaño mínimo
- Escalar gradualmente
- Monitoreo constante
- Stop loss agresivo inicial

### Riesgo: Fallos Técnicos
**Mitigación:**
- Conexión resiliente
- Reintentos automáticos
- Alertas tempranas
- Plan de rollback

### Riesgo: Cambios de Régimen Bruscos
**Mitigación:**
- Detección rápida de régimen
- Reducción de exposición en incertidumbre
- Estrategias diversificadas
- Kill switch por volatilidad

---

## Próximos Pasos Inmediatos

### Esta Semana:
1. [ ] Implementar TrendFollowingStrategy
2. [ ] Mejorar SignalScore con contexto
3. [ ] Crear documentación de estrategias

### Próxima Semana:
1. [ ] Implementar MeanReversionStrategy
2. [ ] Backtesting engine básico
3. [ ] Tests unitarios de estrategias

### Este Mes:
1. [ ] 4 estrategias funcionando
2. [ ] Sistema de ranking básico
3. [ ] Simulación con slippage

---

## Recursos Necesarios

### Humanos:
- 1 desarrollador Python (tiempo completo)
- 1 quant/trader (part-time para validación)

### Infraestructura:
- Servidor Windows (para MT5) o VPS
- Cuenta MT5 demo/real
- Redis server
- PostgreSQL server
- Grafana (opcional pero recomendado)

### Costos Estimados:
- VPS Windows: $50-100/mes
- Datos adicionales (opcional): $0-200/mes
- Herramientas monitoring: $0-50/mes

---

## Conclusión

El sistema Smartbroker tiene una base sólida (Fases 1-3 parcialmente completas). Los próximos 3 meses deben enfocarse en:

1. **Completar estrategias** (Fase 2)
2. **Mejorar ML y simulación** (Fase 3)
3. **Implementar multi-agente** (Fase 4)
4. **Auto-optimización** (Fase 5)

Con ejecución disciplinada y validación rigurosa, el sistema puede estar listo para trading real con capital pequeño en 3-4 meses.

**Recordatorio:** Nunca saltar validación en paper trading. Mejor 1 mes extra de testing que pérdidas evitables.

---

**Documento vivo - Última actualización: Diciembre 2024**
**Próxima revisión: Fin de cada sprint (2 semanas)**

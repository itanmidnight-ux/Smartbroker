# Arquitectura del Sistema de Trading - Smartbroker

## 1. VISIÓN GLOBAL DEL SISTEMA

El bot no es uno solo. Es un sistema compuesto por:

```
[DATA FEED] → [ENGINE DE MERCADO] → [SIMULADOR] → [IA + DECISIÓN] → [EVALUADOR] → [AUTO-OPTIMIZACIÓN]
                                      ↑__________________________________________↓
```

**👉 Todo gira en un loop continuo de aprendizaje en tiempo real**

---

## 2. TODAS LAS INTEGRACIONES NECESARIAS

### 2.1 Integración de datos de mercado (CRÍTICO)

**Fuentes soportadas:**
- MetaTrader 5 (Python API)
- Binance (WebSocket + REST)
- Opcional: AlphaVantage / Polygon (histórico)

**Características requeridas:**
- Streaming en tiempo real (ticks o 1s)
- Velas: M1, M5, M15 (mínimo)
- Datos adicionales:
  - Spread
  - Volumen real o tick volume
  - Profundidad de mercado (si disponible)

**Implementación actual:**
- `python/src/broker/mt5_connector.py` - Conexión resiliente a MT5
- `python/src/data/market_data.py` - Gestión de datos OHLCV
- Soporte multi-símbolo: XAUUSD, XAUEUR

---

### 2.2 Integración de Machine Learning

**Librerías:**
- LightGBM (rápido y preciso)
- PyTorch (si luego escalas a deep learning)
- Scikit-learn (clustering, preprocessing)

**Funciones ML implementadas:**
- Clasificación de mercado:
  - tendencia
  - rango
  - volatilidad alta/baja
- Ajuste dinámico:
  - parámetros de indicadores
  - SL/TP
  - Ranking de estrategias

**Archivos clave:**
- `python/src/ml/model_trainer.py` - Entrenamiento con walk-forward
- `python/src/ml/regime_classifier.py` - Clasificador de régimen
- `python/src/ml/calibrated_model.py` - Calibración probabilística

---

### 2.3 Motor de simulación (Paper Trading REALISTA)

**Debe integrarse con:**
- Datos reales (live feed)
- Motor de ejecución simulado

**Simulación avanzada:**
- Slippage dinámico
- Spread variable
- Latencia simulada
- Ejecución parcial (fills)

**Gestión:**
- Balance virtual
- Equity
- Drawdown
- Historial completo de trades

**Estado actual:**
- Simulador básico implementado
- Pendiente: slippage dinámico y fills parciales

---

### 2.4 Motor de ejecución lógica (estrategias)

**Indicadores disponibles:**
- RSI
- MACD
- Bollinger Bands
- Stochastic
- Ichimoku (filtro)
- ATR (riesgo)
- Estructura de mercado (OBLIGATORIO)

**Sistema:**
- Confluencia de señales
- Score en vez de señal binaria

**Implementación:**
- `python/src/strategy/` - Estrategias base
- `python/src/signals/` - Sistema de scoring

---

### 2.5 Motor de auto-adaptación

**Integraciones:**
- ML feedback loop
- Base de datos de resultados
- Motor de optimización

**Funciones:**
- Reentrenamiento automático
- Ajuste de pesos
- Eliminación de estrategias malas

**Estado:** En desarrollo (Fase 5)

---

### 2.6 Base de datos

**3 tipos necesarios:**

1. **Tiempo real** - Redis
   - Datos de ticks
   - Estado actual del mercado
   - Señales en tiempo real

2. **Histórica** - PostgreSQL o TimescaleDB
   - Histórico de precios
   - Trades ejecutados
   - Métricas de rendimiento

3. **ML / features** - Parquet / archivos optimizados
   - Features para entrenamiento
   - Modelos versionados
   - Patrones históricos

**Implementación actual:**
- Archivos parquet en `python/src/data/`
- Pendiente: Redis y PostgreSQL

---

### 2.7 Sistema de monitoreo

**Requerimientos:**
- Logs estructurados
- Métricas:
  - winrate
  - drawdown
  - profit factor

**Dashboard (opcional):**
- Grafana
- Dashboard web propio (implementado)

**Actual:**
- Dashboard operativo en `python/src/dashboard/`
- Logs en `logs/`
- Endpoints de métricas en API

---

### 2.8 API interna

**Framework:** FastAPI

**Endpoints actuales:**
- `/system/validate` - Validación del sistema
- `/signal/indicator5m` - Señal próximos 5 minutos
- `/strategy/toggle` - Control on/off
- `/signals/analyze` - Análisis de señales
- `/ml/validate/data` - Validación datos ML
- `/ml/validate/model` - Validación modelo

**Endpoints pendientes:**
- `/status` - Estado completo del bot
- `/metrics` - Métricas detalladas
- `/control` - Control avanzado (modo agresivo, etc.)

---

## 3. CARACTERÍSTICAS OBLIGATORIAS DEL BOT

### 3.1 Sistema de señales con scoring

**Nada de BUY/SELL simples.**

Cada señal debe tener:
- ✅ Score (0–100)
- ✅ Confianza
- ✅ Contexto de mercado

**Ejemplo:**
```
BUY → Score: 82
Contexto: tendencia alcista
Confluencias: 4/5
```

**Estado:** Implementado en fase básica

---

### 3.2 Multi-estrategia simultánea

**El bot debe correr:**
- Trend following
- Mean reversion
- Breakout
- Scalping

**Y hacer:**
- Evaluación continua
- Asignación dinámica de "peso"

**Estado:** Pendiente (Fase 4)

---

### 3.3 Aprendizaje continuo (CORE)

**Después de cada trade:**
- Resultado
- Drawdown
- Duración
- Condiciones

**Y ajustar:**
- pesos de indicadores
- reglas de entrada
- agresividad

**Estado:** Pipeline ML funcional, pendiente feedback loop automático

---

### 3.4 Simulación como si fuera real

**El bot DEBE creer que está operando dinero real:**
- capital virtual
- riesgo realista
- gestión completa

**👉 Esto es lo que permite aprendizaje sin perder dinero**

**Estado:** Implementado

---

### 3.5 Gestión de riesgo adaptativa

**Debe aprender:**
- cuándo dejar de operar
- cuándo reducir tamaño
- cuándo aumentar agresividad

**Incluye:**
- Kill switch
- Max DD dinámico
- Reducción en rachas malas

**Estado:** Básico implementado, pendiente adaptativo

---

### 3.6 Memoria de patrones

**Guardar:**
- setups exitosos
- setups fallidos

**Aplicar:**
- clustering
- similitud de patrones

**Estado:** Pendiente (Fase 5)

---

### 3.7 Anti-overfitting (CRÍTICO)

**Si no implementas esto, todo falla.**

**Debe incluir:**
- ✅ validación fuera de muestra (walk-forward implementado)
- ruido en simulación (pendiente)
- penalización a estrategias "perfectas" (pendiente)

---

### 3.8 Detección de régimen de mercado

**El bot debe saber:**
- trending
- ranging
- alta volatilidad

**Y cambiar comportamiento automáticamente.**

**Estado:** ✅ Implementado en Fase 3

---

## 4. FLUJO COMPLETO DEL SISTEMA

**Paso a paso real:**

1. Recibe datos en tiempo real (MT5/Binance)
2. Construye features:
   - indicadores
   - contexto
   - estructura de mercado
3. ML clasifica mercado (trending/ranging/volatilidad)
4. Estrategias generan señales (multi-strategy)
5. Sistema calcula score (0-100) con confluencias
6. Simulador ejecuta trade (paper trading)
7. Se guarda resultado (DB + logs)
8. Motor de aprendizaje ajusta parámetros
9. Repite loop (continuo)

---

## 5. FASES DE IMPLEMENTACIÓN (REALISTA)

### 🟢 Fase 1 – Base sólida (COMPLETADA)
- [x] Data feed MT5
- [x] Indicadores básicos
- [x] Simulador simple
- [x] Conexión resiliente

### 🟡 Fase 2 – Inteligencia básica (EN PROGRESO)
- [x] Sistema de scoring
- [ ] 1 estrategia optimizada
- [ ] Backtesting robusto

### 🟠 Fase 3 – ML real (EN PROGRESO)
- [x] Clasificador de mercado
- [x] Ajuste dinámico
- [x] Calibración probabilística
- [ ] Feature engineering avanzado

### 🔵 Fase 4 – Multi-agente (PENDIENTE)
- [ ] Varias estrategias
- [ ] Ranking dinámico
- [ ] Asignación adaptativa

### 🔴 Fase 5 – Auto-optimización total (PENDIENTE)
- [ ] Reentrenamiento automático
- [ ] Eliminación de estrategias malas
- [ ] Memoria de patrones
- [ ] Loop completo de aprendizaje

---

## 6. REALIDAD (IMPORTANTE)

**Te lo digo sin adornos:**

❌ No vas a lograr winrate "perfecto"
❌ Más ML ≠ más ganancias
❌ Complejidad mal gestionada = pérdidas

**Pero:**

✅ Este enfoque SÍ puede crear ventaja real
✅ El simulador + feedback loop es lo más potente que puedes hacer
✅ Estás en camino de algo tipo "mini hedge fund"

---

## 7. PRÓXIMOS PASOS INMEDIATOS

### Semana 1-2:
1. Completar sistema de backtesting
2. Optimizar 1 estrategia base
3. Mejorar simulación (slippage, fills)

### Semana 3-4:
1. Implementar 2 estrategias adicionales
2. Sistema de ranking dinámico
3. Dashboard de métricas avanzado

### Mes 2:
1. Feedback loop automático
2. Memoria de patrones
3. Reentrenamiento programado

### Mes 3:
1. Sistema multi-agente completo
2. Auto-optimización
3. Validación exhaustiva

---

## 8. MÉTRICAS DE ÉXITO

**Objetivos realistas:**
- Winrate: 45-55% (con profit factor > 1.5)
- Max Drawdown: < 15%
- Sharpe Ratio: > 1.0
- Profit Factor: > 1.5
- Expectancy: positiva

**Monitoreo continuo:**
- Daily P&L
- Winrate rolling (últimos 100 trades)
- Drawdown actual vs histórico
- Exposición por activo
- Efectividad por régimen de mercado

---

## 9. GESTIÓN DE RIESGO DETALLADA

### Position Sizing:
```python
tamaño_posicion = (capital * riesgo_por_trade) / (entrada - stop_loss)
```

### Límites:
- Máximo 2-3% por trade
- Máximo 5-10% exposición total
- Máximo 3 posiciones simultáneas

### Kill Switch:
- Stop diario: -5%
- Stop semanal: -10%
- Stop mensual: -15%

### Reducción progresiva:
- Tras 3 pérdidas consecutivas: reducir 50%
- Tras 5 pérdidas consecutivas: detener trading

---

## 10. ARQUITECTURA TÉCNICA

### Componentes principales:

```
┌─────────────────────────────────────────┐
│          DATA LAYER                     │
│  ┌─────────────┐  ┌──────────────────┐ │
│  │  MT5 Feed   │  │  Binance Feed    │ │
│  └─────────────┘  └──────────────────┘ │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│        PROCESSING LAYER                 │
│  ┌─────────────┐  ┌──────────────────┐ │
│  │ Indicators  │  │ Feature Engine   │ │
│  └─────────────┘  └──────────────────┘ │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│         INTELLIGENCE LAYER              │
│  ┌─────────────┐  ┌──────────────────┐ │
│  │ Regime ML   │  │ Strategy Scores  │ │
│  └─────────────┘  └──────────────────┘ │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│        EXECUTION LAYER                  │
│  ┌─────────────┐  ┌──────────────────┐ │
│  │ Simulator   │  │ Risk Manager     │ │
│  └─────────────┘  └──────────────────┘ │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│        LEARNING LAYER                   │
│  ┌─────────────┐  ┌──────────────────┐ │
│  │ Performance │  │ Model Updater    │ │
│  │   Tracker   │  │                  │ │
│  └─────────────┘  └──────────────────┘ │
└─────────────────────────────────────────┘
```

---

## 11. STACK TECNOLÓGICO

### Core:
- Python 3.10+
- MetaTrader 5 (MT5)
- FastAPI
- Redis (pendiente)
- PostgreSQL (pendiente)

### ML/Data:
- scikit-learn
- LightGBM
- PyTorch (opcional)
- pandas, numpy
- pyarrow (parquet)

### Infraestructura:
- Docker (recomendado)
- Grafana (monitoreo)
- Git (versionado)

### Windows-specific:
- PowerShell scripts
- .env management
- MT5 Terminal integration

---

**Documento vivo - Última actualización: 2024**

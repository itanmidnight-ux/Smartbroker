# Arquitectura propuesta: EA de MetaTrader 5 + sistema avanzado en Python (Windows)

## 1) Objetivo del sistema
Diseñar una plataforma híbrida donde:
- **MQL5 (EA en MT5)** ejecuta operaciones en tiempo real con alta fiabilidad.
- **Python** entrena y sirve modelos de Machine Learning.
- Un **motor de adaptación automática** ajusta parámetros por régimen de mercado.
- Un **orquestador de riesgo** protege capital y limita exposición.

> En Windows, MT5 es el ejecutor principal y Python actúa como capa de inteligencia.

---

## 2) Stack tecnológico recomendado (compatible con Windows)

### Núcleo de trading
- **MetaTrader 5 + MQL5**: ejecución de órdenes, gestión de posiciones, controles de riesgo de baja latencia.
- **Python 3.11+**: pipeline de datos, entrenamiento, inferencia, analítica avanzada.

### Machine Learning
- **pandas, numpy, scipy**: ingeniería de features.
- **scikit-learn**: modelos clásicos (XGBoost-like alternatives, RF, Logistic, calibration).
- **LightGBM/XGBoost**: tabular de alta performance.
- **PyTorch** (opcional): modelos secuenciales (LSTM/Transformer para series temporales).
- **mlflow**: tracking de experimentos y versionado de modelos.

### Infraestructura local (Windows)
- **FastAPI**: microservicio local para inferencia.
- **SQLite / PostgreSQL** (inicial/pro): persistencia de señales, trades y métricas.
- **Redis** (opcional): cache de features y señales de baja latencia.
- **Docker Desktop en Windows** (opcional en fase 2) para empaquetado de servicios Python.

### Calidad y MLOps
- **pytest**: pruebas unitarias e integración.
- **ruff + black + mypy**: estilo, lint y tipado.
- **pre-commit**: calidad automática.
- **GitHub Actions** (o runner local Windows): CI para tests y validaciones.

---

## 3) Estructura de carpetas recomendada

```text
Smartbroker/
├─ README.md
├─ docs/
│  ├─ arquitectura_general.md
│  ├─ roadmap_fases.md
│  └─ estructura_proyecto_mt5_ml_windows.md
├─ mt5/
│  ├─ Experts/
│  │  └─ SmartBrokerEA.mq5
│  ├─ Include/
│  │  ├─ risk_manager.mqh
│  │  ├─ signal_router.mqh
│  │  ├─ execution_engine.mqh
│  │  └─ telemetry.mqh
│  ├─ Scripts/
│  └─ config/
│     ├─ symbols.json
│     └─ risk_profiles.json
├─ python/
│  ├─ pyproject.toml
│  ├─ requirements.txt
│  ├─ src/
│  │  ├─ data/
│  │  │  ├─ ingest_mt5.py
│  │  │  ├─ feature_store.py
│  │  │  └─ market_regime.py
│  │  ├─ ml/
│  │  │  ├─ train.py
│  │  │  ├─ predict.py
│  │  │  ├─ model_registry.py
│  │  │  └─ drift_detection.py
│  │  ├─ strategy/
│  │  │  ├─ signal_generator.py
│  │  │  ├─ position_sizer.py
│  │  │  └─ portfolio_allocator.py
│  │  ├─ risk/
│  │  │  ├─ risk_limits.py
│  │  │  └─ kill_switch.py
│  │  ├─ services/
│  │  │  ├─ api.py
│  │  │  └─ scheduler.py
│  │  └─ monitoring/
│  │     ├─ metrics.py
│  │     └─ alerts.py
│  ├─ tests/
│  │  ├─ test_features.py
│  │  ├─ test_models.py
│  │  └─ test_risk.py
│  └─ models/
│     ├─ latest/
│     └─ archive/
├─ infra/
│  ├─ powershell/
│  │  ├─ setup_windows.ps1
│  │  ├─ run_api.ps1
│  │  └─ run_training.ps1
│  └─ docker/
│     └─ docker-compose.yml
├─ data/
│  ├─ raw/
│  ├─ processed/
│  └─ backtests/
└─ logs/
   ├─ mt5/
   └─ python/
```

---

## 4) Diseño por módulos (responsabilidades)

### A. Módulo EA (MQL5)
- Captura ticks/velas y estado de cuenta.
- Consume señal externa (archivo local, socket o HTTP local).
- Ejecuta órdenes con validación de spread/slippage.
- Aplica límites de riesgo (por operación, diario, drawdown global).

**Archivos clave**
- `mt5/Experts/SmartBrokerEA.mq5`
- `mt5/Include/risk_manager.mqh`
- `mt5/Include/execution_engine.mqh`

### B. Módulo de inteligencia (Python)
- Construcción de features multi-timeframe (M1 a D1).
- Entrenamiento de modelos por símbolo y régimen.
- Servicio de inferencia online de señales y confianza.

**Archivos clave**
- `python/src/ml/train.py`
- `python/src/ml/predict.py`
- `python/src/services/api.py`

### C. Motor de adaptación automática
- Clasifica régimen: tendencia, rango, alta volatilidad, evento.
- Ajusta pesos de estrategias y riesgo automáticamente.
- Detecta drift de datos/modelo y dispara reentrenamiento.

**Archivos clave**
- `python/src/data/market_regime.py`
- `python/src/ml/drift_detection.py`
- `python/src/strategy/portfolio_allocator.py`

### D. Observabilidad y control
- Métricas en tiempo real: win rate, expectancy, max DD, latencia.
- Alertas y kill-switch ante anomalías.
- Auditoría de señales y decisiones del modelo.

**Archivos clave**
- `python/src/monitoring/metrics.py`
- `python/src/risk/kill_switch.py`
- `mt5/Include/telemetry.mqh`

---

## 5) Protocolo de comunicación MT5 ↔ Python (Windows)

Opciones recomendadas en orden:
1. **HTTP local (FastAPI en `localhost`)**: simple y mantenible.
2. **Archivo/cola local**: muy robusto, menor complejidad inicial.
3. **Sockets ZeroMQ**: útil para ultra-baja latencia (fase avanzada).

**Contrato mínimo de señal**
- input: símbolo, timeframe, timestamp, features base, estado de posiciones.
- output: acción (`buy/sell/hold`), probabilidad, SL, TP, tamaño sugerido, expiración de señal.

---

## 6) Timeframes y lógica multi-estrategia

Para cubrir “todos los frames” sin sobreajuste:
- **Scalping**: M1/M5 (filtro estricto de spread y slippage).
- **Intradía**: M15/H1 (señales principales).
- **Swing**: H4/D1 (sesgo macro/régimen).

Recomendación:
- Un modelo por horizonte o un ensemble jerárquico.
- Ponderación dinámica por desempeño reciente y régimen.

---

## 7) Seguridad de capital y robustez

- Hard limits:
  - pérdida diaria máxima,
  - drawdown máximo,
  - límite de operaciones simultáneas,
  - límite de correlación entre símbolos.
- Kill-switch automático por:
  - latencia anómala,
  - rechazo consecutivo de órdenes,
  - spread fuera de rango,
  - degradación de modelo (drift).

---

## 8) Hoja de ruta en fases

### Fase 0 (base)
- Refactor del EA actual a arquitectura modular.
- Canal estable MT5 ↔ Python (HTTP local).
- Backtesting reproducible + métricas estándar.

### Fase 1 (ML inicial)
- Features robustas multi-timeframe.
- Modelo baseline tabular + calibración.
- Gestión de riesgo dinámica por volatilidad.

### Fase 2 (adaptación automática)
- Detector de régimen + selector de estrategia.
- Drift detection + reentrenamiento programado.
- Dashboard de monitoreo.

### Fase 3 (ultra avanzado)
- Ensemble híbrido (tabular + secuencial).
- Optimización bayesiana de hiperparámetros.
- Motor de portafolio multi-símbolo con control de correlación.

---

## 9) Archivos mínimos para arrancar (MVP en Windows)

1. `mt5/Experts/SmartBrokerEA.mq5`
2. `mt5/Include/risk_manager.mqh`
3. `python/src/services/api.py`
4. `python/src/ml/predict.py`
5. `python/src/data/feature_store.py`
6. `python/src/risk/risk_limits.py`
7. `infra/powershell/setup_windows.ps1`
8. `infra/powershell/run_api.ps1`
9. `python/requirements.txt`
10. `docs/arquitectura_general.md`

Con este set ya puedes ejecutar un flujo real: EA pide señal → Python responde → EA ejecuta con gestión de riesgo.

---

## 10) Recomendaciones prácticas para Windows

- Instalar MT5 y fijar una sola ruta de terminal para evitar confusión entre instancias.
- Crear un entorno virtual Python por proyecto (`.venv`).
- Usar PowerShell scripts para arranque uniforme.
- Configurar logging rotativo para no saturar disco.
- Mantener versión fija de modelos en producción (no sobrescribir sin validación A/B).

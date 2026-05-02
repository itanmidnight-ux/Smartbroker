# Trading Bot ML v2.0 - Sistema Avanzado de Predicción

## 🚀 Características Principales

### Machine Learning Avanzado
- **Ensemble Models**: Random Forest, Gradient Boosting, MLP Classifier
- **Deep Learning**: LSTM (cuando TensorFlow está disponible)
- **Feature Engineering**: +50 indicadores técnicos
- **Auto-Aprendizaje**: Mejora continua basada en resultados
- **Objetivo**: >80% win rate

### Supervisor LLM Inteligente
- Análisis continuo del mercado
- Ajustes automáticos de parámetros
- Detección de régimen de mercado (BULLISH, BEARISH, NEUTRAL, VOLATILE)
- Correcciones automáticas al sistema de ML

### Simulación Local Funcional
- Datos de mercado real (yfinance)
- Backtesting completo
- Gestión de posiciones (SL/TP automático)
- Estadísticas detalladas
- Curva de equity en tiempo real

### Interfaz Web Avanzada
- Dashboard interactivo
- Gráficos en tiempo real (Plotly)
- Predicciones visibles
- Configuración de timeframes y modos
- Puerto: 9000

## 📁 Estructura del Proyecto

```
/workspace/
├── main.py                      # Punto de entrada principal
├── requirements.txt             # Dependencias de Python
├── install.sh                   # Script de instalación
├── run.sh                       # Script de ejecución
├── trading_bot/
│   ├── config/
│   │   └── settings.py          # Configuración central
│   ├── data/
│   │   └── data_fetcher.py      # Obtención de datos
│   ├── ml/
│   │   └── ml_engine.py         # Motor de ML
│   ├── simulation/
│   │   └── trading_simulator.py # Simulador de trading
│   └── core/
│       ├── llm_supervisor.py    # Supervisor LLM
│       └── web_server.py        # Servidor Flask
├── templates/
│   └── index.html               # Interfaz web
└── static/
    ├── css/style.css            # Estilos avanzados
    └── js/app.js                # JavaScript frontend
```

## 🔧 Timeframes Soportados

Únicamente estos timeframes están disponibles:
- **5m** - 5 minutos
- **15m** - 15 minutos (default)
- **30m** - 30 minutos
- **1h** - 1 hora
- **2h** - 2 horas
- **4h** - 4 horas
- **8h** - 8 horas
- **12h** - 12 horas

## ⚙️ Modos de Operación

| Modo | Threshold | Riesgo | Máx Posiciones | Descripción |
|------|-----------|--------|----------------|-------------|
| 🛡️ Segura 100% | 85% | 10% | 1 | Máxima seguridad |
| ⚖️ Normal | 70% | 30% | 2 | Equilibrio |
| 🚀 Agresiva | 60% | 50% | 3 | Mayor exposición |
| ⚡ Muy Activa | 50% | 70% | 5 | Máxima actividad |

## 📊 Instalación

### Método Automático (Recomendado)

```bash
cd /workspace
chmod +x install.sh
./install.sh
```

### Método Manual

```bash
cd /workspace
pip3 install -r requirements.txt
```

## ▶️ Ejecución

```bash
cd /workspace
chmod +x run.sh
./run.sh
```

O directamente:

```bash
python3 main.py
```

## 🌐 Acceso a la Interfaz

Una vez iniciado el bot:

```
http://localhost:9000
```

## 📈 API Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/status` | GET | Estado del bot |
| `/api/settings` | GET | Configuración actual |
| `/api/settings/update` | POST | Actualizar configuración |
| `/api/market-data` | GET | Datos de un símbolo |
| `/api/all-market-data` | GET | Todos los símbolos |
| `/api/prediction` | GET | Predicción ML |
| `/api/simulation-stats` | GET | Estadísticas simulación |
| `/api/equity-curve` | GET | Curva de equity |
| `/api/ml-performance` | GET | Performance del ML |
| `/api/supervisor-status` | GET | Estado del supervisor |
| `/api/trade-history` | GET | Historial de trades |
| `/api/chart-data` | GET | Datos para gráficos |

## 🎯 Símbolos Soportados

- **BTCUSD** - Bitcoin
- **ETHUSD** - Ethereum
- **EURUSD** - Euro/Dólar
- **GBPUSD** - Libra/Dólar
- **USDJPY** - Dólar/Yen
- **XAUUSD** - Oro
- **SPX500** - S&P 500
- **NAS100** - NASDAQ 100

## 🔍 Indicadores Técnicos Implementados

### Tendencia
- SMA (5, 10, 20, 50, 100, 200)
- EMA (5, 10, 20, 50, 100, 200)
- MACD
- ADX/ATR

### Momentum
- RSI (7, 14, 21)
- Stochastic Oscillator
- Williams %R
- ROC (5, 10, 20)

### Volatilidad
- Bollinger Bands
- Volatilidad Histórica
- ATR Normalizado

### Volumen
- Volume SMA
- OBV (On Balance Volume)
- VWAP

### Patrones de Velas
- Doji
- Hammer/Hanging Man
- Engulfing (Bullish/Bearish)

### Estadísticos
- Skewness/Kurtosis
- Percentiles
- Z-Score

## 🤖 Sistema de Auto-Mejora

El supervisor LLM realiza análisis cada 10 minutos:

1. **Analiza** el win rate actual vs objetivo (80%)
2. **Detecta** el régimen de mercado
3. **Evalúa** el drawdown
4. **Genera** recomendaciones
5. **Aplica** ajustes automáticamente:
   - Cambia threshold de confianza
   - Ajusta niveles de riesgo
   - Trigger retraining del modelo
   - Cambia modo de operación (crítico)

## 📝 Logs

Los logs se guardan en:
```
/workspace/logs/main.log
/workspace/logs/bot_startup.log
```

## ⚠️ Consideraciones Importantes

1. **Datos en Vivo**: El sistema usa yfinance para datos reales. Sin conexión, genera datos simulados.

2. **TensorFlow**: Opcional. Si no está disponible, usa solo modelos clásicos (scikit-learn).

3. **Simulación**: Las operaciones son simuladas. No ejecuta trades reales.

4. **Recursos**: El entrenamiento inicial puede tomar varios minutos.

5. **Persistencia**: Los modelos se guardan en `/workspace/models/`.

## 🎯 Objetivo del Sistema

Alcanzar y mantener un **win rate >80%** mediante:
- Selección precisa de entradas (alto threshold de confianza)
- Gestión de riesgo adaptativa
- Mejora continua del modelo
- Ajustes automáticos del supervisor

## 📞 Soporte

Para problemas o preguntas, revisar los logs en `/workspace/logs/`.

---

**Versión**: 2.0.0  
**Puerto**: 9000  
**Python Requerido**: 3.8+

# Smartbroker

Sistema híbrido para trading algorítmico avanzado con **MetaTrader 5 (EA/MQL5)** y **Python (ML + adaptación automática)**, compatible con Windows.

## Inicio rápido (Windows)
1. Copiar variables:
   - `copy .env.example .env`
2. Instalar y configurar todo automáticamente:
   - `./install.ps1`
3. Ejecutar API local:
   - `./run.ps1`
4. Ejecutar dashboard:
   - `./infra/windows/run_dashboard.ps1`

### Instalación y configuración automática
`install.ps1` ahora ejecuta:
- instalación de dependencias,
- bootstrap de agente + modelos base,
- self-test de sistema.

## Símbolos base
- `XAUUSD`
- `XAUEUR`

Configurar en `.env`:
- `SYMBOLS=XAUUSD,XAUEUR`
- `BROKER_PROFILE=metaquotes_demo` o `BROKER_PROFILE=weltrade_real`
- `ALLOW_LIVE_TRADING=true` (solo si quieres modo real armado por defecto)

## Mejoras aplicadas (primeras 3)
1. Walk-forward temporal en entrenamiento.
2. Calibración probabilística (sigmoid) en modelos.
3. Selección automática de modelo por régimen (`trending`, `ranging`, `high_volatility`).

## Funcionalidad implementada (fase actual)
- Conexión robusta con reintentos a MT5 (`ResilientMT5Connector`).
- Obtención de snapshot de mercado y OHLCV desde MT5 para múltiples símbolos.
- Botón principal Run/Stop Strategy (simulación por defecto / real bajo control).
- Indicador de señal para próximos 5 minutos.
- Gráfico principal de velas japonesas + historial de señales.
- Sistema de señales con ingesta, análisis y feedback.
- Agente adaptativo online con estado preentrenado versionado en el repositorio.
- Pipeline ML funcional con entrenamiento, inferencia y validación por `green_flag`.
- Control de seguridad para modo real (`live_armed`).

## Endpoints clave de validación
- `GET /system/validate`
- `GET /signal/indicator5m`
- `POST /strategy/toggle`
- `GET /signals/analyze`
- `GET /ml/validate/data`
- `GET /ml/validate/model`

## Documentación
- Arquitectura general: `docs/estructura_proyecto_mt5_ml_windows.md`
- Conexión brokers MT5: `docs/conexion_brokers_mt5.md`
- Referencias conexión MT5: `docs/referencias_conexion_mt5.md`
- Dashboard operativo: `docs/dashboard_operativo.md`
- Señales + agente: `docs/adaptive_agent_signals.md`
- Referencias ML: `docs/referencias_ml_trading.md`
- Plan inmediato de ejecución: `docs/plan_ejecucion_fase_0_1.md`

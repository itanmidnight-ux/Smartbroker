# Dashboard operativo (Streamlit)

## Objetivo
Visualizar y operar el bot con controles de ejecución real/simulada y validación continua.

## Vista principal
- Botón **∆ Run Strategy** / **■ Stop Strategy**.
- Si está desactivado (por defecto): modo simulación con datos reales.
- Si está activado: modo estrategia activa (real bajo `live_armed`).
- Indicador de señal próximos 5 minutos.
- Gráfico principal de velas japonesas con señales históricas superpuestas.

## Pestañas actuales
- **Conexión**: estado de API, broker activo, validación de sistema.
- **Señales**: pre-trade check, plan de ejecución, ingesta y análisis.
- **Agente**: validación de agente y feedback online.
- **Órdenes/Posiciones**: trades recientes (simulados/reales según modo).
- **Riesgo**: métricas runtime y estado de seguridad.
- **Machine Learning**: entrenamiento y predicción 5m.

## Ejecución
1. API: `./run.ps1`
2. Dashboard: `./infra/windows/run_dashboard.ps1`

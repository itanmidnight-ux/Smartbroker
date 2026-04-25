# Sistema de señales + agente adaptativo

## Objetivo
Agregar recepción, tratado/análisis de señales y adaptación automática con un agente liviano entrenable online.

## Componentes
- `signals/store.py`: persistencia SQLite de señales y rewards.
- `signals/processor.py`: análisis agregado de acciones/regímenes/reward.
- `agent/adaptive_agent.py`: agente contextual tipo bandit con estado preentrenado en `python/models/adaptive_agent_state.json`.

## Endpoints de validación (green flags)
- `POST /signal` (ingesta + decisión final del agente)
- `GET /signals/recent`
- `GET /signals/analyze`
- `POST /signals/feedback` (aprendizaje online)
- `GET /agent/validate`

Todos devuelven `green_flag` para validación funcional rápida.

## Entrenamiento rápido
El repositorio ya incluye un estado preentrenado (`adaptive_agent_state.json`) para evitar entrenamiento largo en instalación inicial. El aprendizaje posterior se hace online con `/signals/feedback`.

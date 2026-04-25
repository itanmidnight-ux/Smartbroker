# Referencias técnicas de Machine Learning aplicadas

Fuentes públicas y primarias usadas para diseñar este pipeline ML y agente adaptativo:

1. `TimeSeriesSplit` (validación temporal):
   - https://sklearn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
2. `Pipeline` (preprocesado + modelo):
   - https://sklearn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html
3. `LogisticRegression`:
   - https://sklearn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html
4. Contextual bandits (visión general):
   - https://en.wikipedia.org/wiki/Multi-armed_bandit
5. Integración Python MetaTrader5 (`copy_rates_from*`):
   - https://www.mql5.com/en/docs/python_metatrader5

## Decisiones implementadas
- Split temporal para evitar leakage en series de tiempo.
- Pipeline con `StandardScaler + LogisticRegression` para baseline estable.
- Registro de modelo `latest` por símbolo.
- Endpoints de validación con `green_flag` para data y modelo.
- Agente adaptativo online con feedback de reward (`/signals/feedback`).

# Referencias técnicas usadas para diseñar la conexión MT5

Se usaron fuentes oficiales de MetaQuotes/MQL5 para estructurar la conexión robusta:

1. Python Integration (MetaTrader5 package):
   - https://www.mql5.com/en/docs/python_metatrader5
2. initialize:
   - https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py
3. login:
   - https://www.mql5.com/en/docs/python_metatrader5/mt5login_py
4. copy_rates_from_pos (OHLCV):
   - https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesfrompos_py
5. symbol_info_tick:
   - https://www.mql5.com/en/docs/python_metatrader5/mt5symbolinfotick_py

## Criterios aplicados
- Reintentos con backoff progresivo.
- Separación de perfiles por broker y entorno (demo/live).
- Tolerancia a fallos y reporte explícito de errores para dashboard.

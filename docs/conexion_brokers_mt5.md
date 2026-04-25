# Conexión de brokers en MT5: Weltrade (real) y MetaQuotes-Demo (pruebas)

## Principio operativo
- `metaquotes_demo`: entorno de pruebas/paper.
- `weltrade_real`: entorno productivo real.

El motor Python usa `BROKER_PROFILE` para seleccionar el perfil correcto de conexión.

## Flujo recomendado
1. Validar estrategia en `metaquotes_demo`.
2. Ejecutar pruebas de estabilidad y riesgo.
3. Promover a `weltrade_real` con límites de riesgo más estrictos.

## Variables de entorno críticas
- `BROKER_PROFILE` (`metaquotes_demo` o `weltrade_real`)
- `MT5_TERMINAL_PATH`
- `MT5_LOGIN`
- `MT5_PASSWORD`
- `MT5_SERVER`

## Reglas de seguridad
- Nunca hardcodear credenciales.
- Kill-switch activo por drawdown y pérdida diaria.
- No habilitar operación real si la validación en demo no está aprobada.

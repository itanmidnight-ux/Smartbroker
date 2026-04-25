import os
import requests
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

API_BASE = os.getenv("DASHBOARD_API_BASE", "http://127.0.0.1:8000")

st.set_page_config(page_title="SmartBroker Dashboard", layout="wide")
st.title("SmartBroker Dashboard")
st.caption("Monitoreo: conexión, mercado, señales, agente adaptativo, órdenes, riesgo y ML")


def _get_json(path: str, params: dict | None = None) -> dict:
    return requests.get(f"{API_BASE}{path}", params=params, timeout=12).json()


def _post_json(path: str, payload: dict) -> dict:
    response = requests.post(f"{API_BASE}{path}", json=payload, timeout=20)
    if response.status_code >= 400:
        return {"error": response.text, "green_flag": False}
    return response.json()


def _candles_with_signals(symbol: str) -> go.Figure:
    market = _get_json("/market/ohlcv", params={"symbol": symbol, "bars": 300, "source": "auto"})
    overlay = _get_json("/signals/overlay", params={"symbol": symbol, "limit": 200})

    df = pd.DataFrame(market.get("rows", []))
    if df.empty:
        return go.Figure()

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df["time"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="OHLC",
            )
        ]
    )

    points = overlay.get("points", [])
    if points:
        sdf = pd.DataFrame(points)
        sdf = sdf[sdf["action"].isin(["buy", "sell"])]
        if not sdf.empty:
            marker_map = sdf["action"].map({"buy": "triangle-up", "sell": "triangle-down"})
            color_map = sdf["action"].map({"buy": "green", "sell": "red"})
            fig.add_trace(
                go.Scatter(
                    x=sdf["time"],
                    y=[df["close"].iloc[-1]] * len(sdf),
                    mode="markers",
                    marker=dict(symbol=marker_map, color=color_map, size=10),
                    text=sdf["action"],
                    name="Signals",
                )
            )

    fig.update_layout(height=520, xaxis_rangeslider_visible=False, title=f"{symbol} Candles + Signal History")
    return fig


# Controls principales (RUN/STOP)
health = _get_json("/health")
strategy_enabled = bool(health.get("strategy_enabled", False))
sim_mode = bool(health.get("simulation_mode", True))

c_run, c_status, c_indicator = st.columns([1.3, 1.2, 1.2])
with c_run:
    if not strategy_enabled:
        if st.button("∆ Run Strategy", type="primary"):
            result = _post_json("/strategy/toggle", {"enabled": True})
            st.success(result)
    else:
        if st.button("■ Stop Strategy"):
            result = _post_json("/strategy/toggle", {"enabled": False})
            st.warning(result)
with c_status:
    st.metric("Modo", "SIMULACIÓN" if sim_mode else "REAL")
    st.metric("Estrategia", "ACTIVA" if strategy_enabled else "DETENIDA")
with c_indicator:
    ind = _get_json("/signal/indicator5m", params={"symbol": "XAUUSD", "source": "auto"})
    st.metric("Indicador 5m", ind.get("indicator_5m", "N/A"))
    st.caption(f"prob_up: {round(ind.get('prob_up', 0.0), 4)}")

# Gráfico principal
symbol_main = st.selectbox("Símbolo principal", ["XAUUSD", "XAUEUR"], index=0)
fig = _candles_with_signals(symbol_main)
st.plotly_chart(fig, use_container_width=True)

tab_connection, tab_signal, tab_agent, tab_orders, tab_risk, tab_ml = st.tabs([
    "Conexión",
    "Señales",
    "Agente",
    "Órdenes/Posiciones",
    "Riesgo",
    "Machine Learning",
])

with tab_connection:
    st.subheader("Estado de conexión")
    runtime = _get_json("/runtime/status")
    st.json({"health": health, "runtime": runtime})
    if st.button("Validar sistema completo"):
        st.json(_get_json("/system/validate"))

with tab_signal:
    st.subheader("Ingesta y tratado de señales")
    symbol = st.selectbox("Símbolo señal", ["XAUUSD", "XAUEUR"], index=0)
    volatility = st.number_input("Volatilidad", min_value=0.0, value=0.01, step=0.001, format="%.4f")
    trend_strength = st.number_input("Fuerza tendencia", min_value=0.0, max_value=1.0, value=0.65, step=0.05)
    trend = st.selectbox("Trend flag", [0, 1], index=1)
    spread = st.number_input("Spread actual (points)", min_value=0.0, value=35.0, step=1.0)

    if st.button("Pre-trade check"):
        st.json(_post_json("/risk/pretrade-check", {"symbol": symbol, "spread_points": spread, "max_spread_points": 60.0, "probability": 0.62}))

    if st.button("Generar plan de ejecución"):
        st.json(_post_json("/execution/plan", {"symbol": symbol, "action": "buy" if trend == 1 else "sell", "probability": 0.62, "spread_points": spread, "max_spread_points": 60.0, "balance": 10000.0, "risk_pct": 0.5, "stop_loss_points": 250.0, "take_profit_points": 500.0, "point_value": 1.0}))

    if st.button("Procesar señal"):
        st.json(_post_json("/signal", {"symbol": symbol, "volatility": volatility, "trend_strength": trend_strength, "trend": trend, "source": "dashboard"}))

    if st.button("Ver señales recientes"):
        st.json(_get_json("/signals/recent", params={"limit": 50}))

    if st.button("Analizar señales"):
        st.json(_get_json("/signals/analyze", params={"limit": 200}))

with tab_agent:
    st.subheader("Agente adaptativo")
    st.json(_get_json("/agent/validate"))

    signal_id = st.number_input("Signal ID", min_value=1, value=1, step=1)
    regime = st.selectbox("Regime", ["trending", "ranging", "high_volatility", "unknown"], index=0)
    action = st.selectbox("Action", ["buy", "sell", "hold"], index=0)
    reward = st.number_input("Reward", value=0.01, step=0.01, format="%.4f")
    if st.button("Enviar feedback"):
        st.json(_post_json("/signals/feedback", {"signal_id": int(signal_id), "regime": regime, "action": action, "reward": reward}))

with tab_orders:
    st.subheader("Órdenes/Posiciones + Sim trades")
    st.json(_get_json("/trades/recent", params={"limit": 50}))

with tab_risk:
    st.subheader("Controles de riesgo")
    runtime = _get_json("/runtime/status")
    st.metric("Régimen", runtime.get("last_regime", "unknown"))
    st.metric("Última acción", runtime.get("last_signal_action", "hold"))
    st.metric("Probabilidad", runtime.get("last_signal_probability", 0.0))
    st.metric("Conectado", str(runtime.get("connected", False)))
    st.metric("Live Armed", str(runtime.get("live_armed", False)))

with tab_ml:
    st.subheader("Pipeline de Machine Learning")
    symbol = st.selectbox("Símbolo ML", ["XAUUSD", "XAUEUR"], index=0)
    bars = st.slider("Barras para entrenamiento", min_value=200, max_value=2000, value=800, step=100)
    source = st.selectbox("Fuente de datos", ["auto", "mt5", "synthetic"], index=0)

    if st.button("Entrenar Modelo"):
        st.json(_post_json("/ml/train", {"symbol": symbol, "bars": bars, "source": source}))
    if st.button("Predecir 5m"):
        st.json(_get_json("/signal/indicator5m", params={"symbol": symbol, "source": source}))

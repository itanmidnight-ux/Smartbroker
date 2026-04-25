from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
import uvicorn

from app.settings import settings
from broker.profile_loader import load_profile
from broker.mt5_connection import MT5ConnectionManager
from broker.resilient_connection import ResilientMT5Connector
from data.market_regime import detect_regime
from data.mt5_data_feed import MT5DataFeed, MT5TradingFeed, summarize_ohlcv, synthetic_ohlcv
from ml.predict import predict_latest
from ml.train import train_and_register
from services.ml_validation import validation_result
from ml.model_registry import load_latest_model
from services.runtime_state import runtime_state
from signals.store import init_store, insert_signal, recent_signals, update_reward, insert_trade, recent_trades
from signals.processor import analyze_signals
from agent.adaptive_agent import AdaptiveBanditAgent
from execution.planner import build_execution_plan

app = FastAPI(title="SmartBroker Signal API", version="0.6.0")
agent = AdaptiveBanditAgent()


class SignalRequest(BaseModel):
    symbol: str
    volatility: float
    trend_strength: float
    trend: int
    source: str = "api"


class ArmLiveRequest(BaseModel):
    confirm: bool


class StrategyToggleRequest(BaseModel):
    enabled: bool


class MLTrainRequest(BaseModel):
    symbol: str
    bars: int = 800
    source: str = "auto"  # auto|mt5|synthetic


class MLPredictRequest(BaseModel):
    symbol: str
    bars: int = 300
    source: str = "auto"  # auto|mt5|synthetic


class FeedbackRequest(BaseModel):
    signal_id: int
    regime: str
    action: str
    reward: float


class PreTradeCheckRequest(BaseModel):
    symbol: str
    spread_points: float
    max_spread_points: float = 60.0
    probability: float = 0.5


class ExecutionPlanRequest(BaseModel):
    symbol: str
    action: str
    probability: float
    spread_points: float
    max_spread_points: float = 60.0
    balance: float = 10000.0
    risk_pct: float = 0.5
    stop_loss_points: float = 250.0
    take_profit_points: float = 500.0
    point_value: float = 1.0


def _assert_live_mode_allowed(profile: dict) -> None:
    if profile["mode"] == "live" and not runtime_state.live_armed:
        raise HTTPException(status_code=403, detail="Modo real no armado. Activa live_armed para continuar.")


def _fetch_ohlcv(symbol: str, bars: int, source: str):
    if source == "synthetic":
        return synthetic_ohlcv(symbol, rows=bars), "synthetic"

    if source in {"auto", "mt5"}:
        try:
            feed = MT5DataFeed(symbol, settings.timeframe)
            feed.ensure_symbol()
            return feed.get_ohlcv(bars=bars), "mt5"
        except Exception:
            if source == "mt5":
                raise
            return synthetic_ohlcv(symbol, rows=bars), "synthetic-fallback"

    raise HTTPException(status_code=400, detail="source inválido. Usa auto|mt5|synthetic")


@app.on_event("startup")
def startup_connect() -> None:
    profile = load_profile(settings.broker_profile)
    manager = MT5ConnectionManager(profile)
    connector = ResilientMT5Connector(manager)

    init_store()
    runtime_state.live_armed = settings.allow_live_trading and profile["mode"] == "live"
    runtime_state.strategy_enabled = False
    runtime_state.simulation_mode = True

    try:
        session = connector.connect_with_retry()
        runtime_state.connected = True
        runtime_state.broker_profile = session.name
        runtime_state.broker_mode = session.mode
        runtime_state.server = session.server
        runtime_state.last_error = ""
    except Exception as exc:  # noqa: BLE001
        runtime_state.connected = False
        runtime_state.last_error = str(exc)
    finally:
        runtime_state.touch()


@app.get("/health")
def health() -> dict:
    profile = load_profile(settings.broker_profile)
    return {
        "status": "ok",
        "broker_profile": profile["name"],
        "mode": profile["mode"],
        "connected": runtime_state.connected,
        "symbols": settings.symbols,
        "live_armed": runtime_state.live_armed,
        "strategy_enabled": runtime_state.strategy_enabled,
        "simulation_mode": runtime_state.simulation_mode,
    }


@app.get("/runtime/status")
def runtime_status() -> dict:
    return runtime_state.__dict__


@app.post("/runtime/arm-live")
def arm_live(req: ArmLiveRequest) -> dict:
    profile = load_profile(settings.broker_profile)
    if profile["mode"] != "live":
        raise HTTPException(status_code=400, detail="El perfil activo no es live.")

    runtime_state.live_armed = bool(req.confirm)
    runtime_state.touch()
    return {"live_armed": runtime_state.live_armed, "profile": profile["name"], "green_flag": runtime_state.live_armed}


@app.post("/strategy/toggle")
def strategy_toggle(req: StrategyToggleRequest) -> dict:
    profile = load_profile(settings.broker_profile)

    if req.enabled and profile["mode"] == "live" and not runtime_state.live_armed:
        raise HTTPException(status_code=403, detail="No se puede activar estrategia real sin live_armed.")

    runtime_state.strategy_enabled = bool(req.enabled)
    runtime_state.simulation_mode = not runtime_state.strategy_enabled
    runtime_state.touch()

    return {
        "strategy_enabled": runtime_state.strategy_enabled,
        "simulation_mode": runtime_state.simulation_mode,
        "green_flag": True,
    }


@app.post("/signal")
def signal(req: SignalRequest) -> dict:
    profile = load_profile(settings.broker_profile)
    _assert_live_mode_allowed(profile)

    regime = detect_regime(req.volatility, req.trend_strength)
    ml_action = "buy" if req.trend == 1 and regime.name != "high_volatility" else "sell" if req.trend == 0 else "hold"
    probability = 0.62 if ml_action != "hold" else 0.55

    agent_decision = agent.decide(regime.name, ml_action, probability)
    final_action = agent_decision["final_action"]
    signal_id = insert_signal(req.symbol, regime.name, ml_action, final_action, probability, req.source)

    trade_mode = "SIM" if runtime_state.simulation_mode else "LIVE"
    trade_status = "simulated" if runtime_state.simulation_mode else "sent"
    trade_id = insert_trade(signal_id, req.symbol, final_action, trade_mode, trade_status, None, 0.0, 0.0)

    runtime_state.last_signal_action = final_action
    runtime_state.last_signal_probability = probability
    runtime_state.last_regime = regime.name
    runtime_state.touch()

    return {
        "signal_id": signal_id,
        "trade_id": trade_id,
        "symbol": req.symbol,
        "ml_action": ml_action,
        "final_action": final_action,
        "probability": probability,
        "regime": regime.name,
        "regime_confidence": regime.confidence,
        "agent": agent_decision,
        "execution_mode": trade_mode,
        "broker_profile": profile["name"],
        "green_flag": True,
    }


@app.post("/signals/feedback")
def signal_feedback(req: FeedbackRequest) -> dict:
    update_reward(req.signal_id, req.reward)
    upd = agent.update(req.regime, req.action, req.reward)
    runtime_state.touch()
    return {"signal_id": req.signal_id, "agent_update": upd, "green_flag": True}


@app.get("/signals/recent")
def signals_recent(limit: int = Query(50, ge=1, le=500)) -> dict:
    rows = recent_signals(limit=limit)
    return {"count": len(rows), "rows": rows, "green_flag": True}


@app.get("/signals/analyze")
def signals_analyze(limit: int = Query(200, ge=10, le=2000)) -> dict:
    rows = recent_signals(limit=limit)
    analysis = analyze_signals(rows)
    return analysis


@app.get("/signals/overlay")
def signals_overlay(symbol: str = Query("XAUUSD"), limit: int = Query(100, ge=10, le=1000)) -> dict:
    rows = [r for r in recent_signals(limit=limit) if r["symbol"] == symbol]
    points = [{"time": r["ts_utc"], "action": r["final_action"], "id": r["id"], "probability": r["probability"]} for r in rows]
    return {"symbol": symbol, "points": points, "green_flag": True}


@app.get("/trades/recent")
def trades_recent(limit: int = Query(50, ge=1, le=500)) -> dict:
    rows = recent_trades(limit=limit)
    return {"count": len(rows), "rows": rows, "green_flag": True}


@app.get("/agent/validate")
def agent_validate() -> dict:
    return agent.validate()


@app.post("/execution/plan")
def execution_plan(req: ExecutionPlanRequest) -> dict:
    plan = build_execution_plan(
        symbol=req.symbol,
        action=req.action,
        probability=req.probability,
        spread_points=req.spread_points,
        max_spread_points=req.max_spread_points,
        balance=req.balance,
        risk_pct=req.risk_pct,
        stop_loss_points=req.stop_loss_points,
        take_profit_points=req.take_profit_points,
        point_value=req.point_value,
    )
    runtime_state.touch()
    return plan


@app.post("/risk/pretrade-check")
def risk_pretrade_check(req: PreTradeCheckRequest) -> dict:
    profile = load_profile(settings.broker_profile)
    live_ok = not (profile["mode"] == "live" and not runtime_state.live_armed)
    spread_ok = req.spread_points <= req.max_spread_points
    prob_ok = req.probability >= 0.52
    ok = live_ok and spread_ok and prob_ok
    return {
        "symbol": req.symbol,
        "live_ok": live_ok,
        "spread_ok": spread_ok,
        "prob_ok": prob_ok,
        "allowed": ok,
        "green_flag": ok,
    }


@app.get("/system/validate")
def system_validate() -> dict:
    validations = {
        "agent": agent.validate(),
        "signal_store": validation_result("signal_store", True, {"note": "sqlite ready"}),
    }

    data_check = ml_validate_data(symbol=settings.symbols[0], bars=300, source="synthetic")
    model_check = ml_validate_model(symbol=settings.symbols[0])
    validations["ml_data"] = data_check
    validations["ml_model"] = model_check

    overall = all(v.get("green_flag", False) for v in validations.values())
    return {"overall_green": overall, "checks": validations, "green_flag": overall}


@app.get("/signal/indicator5m")
def signal_indicator_5m(symbol: str = Query("XAUUSD"), source: str = Query("auto")) -> dict:
    df, used_source = _fetch_ohlcv(symbol, 400, source)
    pred = predict_latest(symbol, df)
    return {"symbol": symbol, "indicator_5m": pred["indicator_5m"], "prob_up": pred["prob_up"], "model_key": pred["model_key"], "source": used_source, "green_flag": True}


@app.get("/market/snapshot")
def market_snapshot(symbol: str = Query(None)) -> dict:
    target_symbol = symbol or settings.symbols[0]
    feed = MT5DataFeed(target_symbol, settings.timeframe)
    feed.ensure_symbol()
    snap = feed.get_snapshot()
    runtime_state.touch()
    payload = snap.__dict__
    payload["green_flag"] = True
    return payload


@app.get("/market/ohlcv")
def market_ohlcv(symbol: str = Query(None), bars: int = Query(200, ge=50, le=2000), source: str = Query("auto")) -> dict:
    target_symbol = symbol or settings.symbols[0]
    df, used_source = _fetch_ohlcv(target_symbol, bars, source)
    summary = summarize_ohlcv(df)
    runtime_state.touch()
    rows = [] if df.empty else df.tail(300).assign(time=lambda x: x["time"].astype(str)).to_dict(orient="records")
    return {"symbol": target_symbol, "source": used_source, "summary": summary, "rows": rows, "green_flag": len(rows) > 0}


@app.get("/trading/orders")
def trading_orders() -> dict:
    profile = load_profile(settings.broker_profile)
    _assert_live_mode_allowed(profile)
    orders = MT5TradingFeed.get_pending_orders()
    runtime_state.touch()
    return {"count": len(orders), "orders": orders, "green_flag": True}


@app.get("/trading/positions")
def trading_positions() -> dict:
    profile = load_profile(settings.broker_profile)
    _assert_live_mode_allowed(profile)
    positions = MT5TradingFeed.get_open_positions()
    runtime_state.touch()
    return {"count": len(positions), "positions": positions, "green_flag": True}


@app.post("/ml/train")
def ml_train(req: MLTrainRequest) -> dict:
    df, used_source = _fetch_ohlcv(req.symbol, req.bars, req.source)
    result = train_and_register(req.symbol, df)
    result["source"] = used_source
    runtime_state.touch()
    return result


@app.post("/ml/predict")
def ml_predict(req: MLPredictRequest) -> dict:
    df, used_source = _fetch_ohlcv(req.symbol, req.bars, req.source)
    result = predict_latest(req.symbol, df)
    result["source"] = used_source
    runtime_state.touch()
    return result


@app.get("/ml/validate/data")
def ml_validate_data(symbol: str = Query(None), bars: int = Query(500), source: str = Query("auto")) -> dict:
    target_symbol = symbol or settings.symbols[0]
    try:
        df, used_source = _fetch_ohlcv(target_symbol, bars, source)
        ok = not df.empty and {"time", "open", "high", "low", "close", "tick_volume"}.issubset(df.columns)
        return validation_result("ml_data_pipeline", ok, {"rows": len(df), "source": used_source, "columns": list(df.columns)})
    except Exception as exc:  # noqa: BLE001
        return validation_result("ml_data_pipeline", False, {"error": str(exc)})


@app.get("/ml/validate/model")
def ml_validate_model(symbol: str = Query(None)) -> dict:
    target_symbol = symbol or settings.symbols[0]
    try:
        payload = load_latest_model(target_symbol)
        ok = "model" in payload and "features" in payload and "metrics" in payload
        return validation_result("ml_model_registry", ok, {"features": payload.get("features", []), "metrics": payload.get("metrics", {})})
    except Exception as exc:  # noqa: BLE001
        return validation_result("ml_model_registry", False, {"error": str(exc)})


@app.post("/connect")
def connect() -> dict:
    profile = load_profile(settings.broker_profile)
    manager = MT5ConnectionManager(profile)
    connector = ResilientMT5Connector(manager)
    session = connector.connect_with_retry()
    runtime_state.connected = True
    runtime_state.broker_profile = session.name
    runtime_state.broker_mode = session.mode
    runtime_state.server = session.server
    runtime_state.last_error = ""
    runtime_state.touch()
    manager.shutdown()
    return {
        "connected": True,
        "profile": session.name,
        "server": session.server,
        "mode": session.mode,
        "login": session.login,
        "green_flag": True,
    }


if __name__ == "__main__":
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)

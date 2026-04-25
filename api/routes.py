"""
FastAPI routes for the trading system API.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime

from database.models import get_db, TradeModel, SignalModel, PerformanceMetricModel
from simulation.paper_broker import PaperBroker
from risk.risk_manager import RiskManager
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/status")
async def get_status():
    """Get overall system status."""
    return {
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }


@router.get("/signals")
async def get_signals(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get recent trading signals."""
    try:
        signals = db.query(SignalModel).order_by(
            SignalModel.timestamp.desc()
        ).limit(limit).all()
        
        return {
            "signals": [s.to_dict() if hasattr(s, 'to_dict') else {
                'id': s.id,
                'timestamp': s.timestamp.isoformat() if s.timestamp else None,
                'symbol': s.symbol,
                'strategy': s.strategy,
                'direction': s.direction,
                'score': s.score,
                'confidence': s.confidence,
                'executed': s.executed,
            } for s in signals],
            "count": len(signals),
        }
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        return {"signals": [], "count": 0}


@router.get("/trades")
async def get_trades(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get trades with optional status filter."""
    try:
        query = db.query(TradeModel)
        
        if status:
            query = query.filter(TradeModel.status == status.upper())
        
        trades = query.order_by(TradeModel.timestamp.desc()).limit(limit).all()
        
        return {
            "trades": [t.to_dict() if hasattr(t, 'to_dict') else {
                'trade_id': t.trade_id,
                'symbol': t.symbol,
                'direction': t.direction,
                'entry_price': t.entry_price,
                'exit_price': t.exit_price,
                'profit_loss': t.profit_loss,
                'status': t.status,
                'timestamp': t.timestamp.isoformat() if t.timestamp else None,
            } for t in trades],
            "count": len(trades),
        }
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_performance(db: Session = Depends(get_db)):
    """Get performance metrics."""
    try:
        # Get latest performance metric
        latest = db.query(PerformanceMetricModel).order_by(
            PerformanceMetricModel.timestamp.desc()
        ).first()
        
        if not latest:
            return {
                "metrics": {},
                "message": "No performance data yet"
            }
        
        return {
            "metrics": {
                'balance': latest.balance,
                'equity': latest.equity,
                'total_return': latest.total_return,
                'winrate': latest.winrate,
                'profit_factor': latest.profit_factor,
                'max_drawdown': latest.max_drawdown,
                'current_drawdown': latest.current_drawdown,
                'total_trades': latest.total_trades,
            },
            "timestamp": latest.timestamp.isoformat() if latest.timestamp else None,
        }
    except Exception as e:
        logger.error(f"Error getting performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk-status")
async def get_risk_status():
    """Get current risk management status."""
    from main import risk_manager
    
    return risk_manager.get_risk_status()


@router.post("/control/reset-kill-switch")
async def reset_kill_switch():
    """Reset the kill switch manually."""
    from main import risk_manager
    
    risk_manager.reset_kill_switch()
    
    return {
        "status": "success",
        "message": "Kill switch reset",
    }


@router.get("/strategies")
async def get_strategies():
    """Get information about active strategies."""
    from main import signal_engine
    
    return {
        "strategies": signal_engine.get_strategy_info(),
        "active": signal_engine.get_active_strategies(),
    }


@router.post("/control/update-strategy-weight")
async def update_strategy_weight(
    strategy_name: str,
    weight: float
):
    """Update the weight of a specific strategy."""
    from main import signal_engine
    
    if strategy_name not in signal_engine.strategies:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy '{strategy_name}' not found"
        )
    
    signal_engine.update_strategy_weight(strategy_name, weight)
    
    return {
        "status": "success",
        "strategy": strategy_name,
        "new_weight": weight,
    }


@router.get("/market-regime")
async def get_market_regime():
    """Get current market regime classification."""
    from main import ml_classifier, current_regime
    
    if ml_classifier is None or not ml_classifier.is_fitted:
        return {
            "regime": current_regime,
            "model_status": "not_fitted",
        }
    
    return {
        "regime": current_regime,
        "model_status": "fitted",
    }


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }

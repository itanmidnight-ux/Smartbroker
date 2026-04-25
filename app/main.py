"""
Main application entry point.
Orchestrates all components of the trading system.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict
import pandas as pd

from fastapi import FastAPI
from contextlib import asynccontextmanager

from config.settings import settings
from config.constants import Timeframe, MarketRegime
from data.feeds.mt5_feed import MT5Feed, mt5_feed
from data.processors.feature_engineering import FeatureEngineer, feature_engineer
from engine.signal_engine import SignalEngine
from simulation.paper_broker import PaperBroker
from risk.risk_manager import RiskManager
from ml.model import MarketRegimeClassifier, AdaptiveParameterTuner
from database.models import init_db, get_db, save_signal, save_trade, save_performance_metric
from api.routes import router
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


# Global instances
signal_engine: Optional[SignalEngine] = None
paper_broker: Optional[PaperBroker] = None
risk_manager: Optional[RiskManager] = None
ml_classifier: Optional[MarketRegimeClassifier] = None
param_tuner: Optional[AdaptiveParameterTuner] = None
feature_engineer_instance: Optional[FeatureEngineer] = None

current_regime: str = "RANGING"
is_running = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global signal_engine, paper_broker, risk_manager, ml_classifier, param_tuner, feature_engineer_instance
    
    # Startup
    logger.info("Starting SmartBroker Trading System")
    
    # Initialize components
    setup_logging()
    init_db()
    
    signal_engine = SignalEngine()
    paper_broker = PaperBroker()
    risk_manager = RiskManager()
    ml_classifier = MarketRegimeClassifier()
    param_tuner = AdaptiveParameterTuner()
    feature_engineer_instance = FeatureEngineer()
    
    # Try to load existing model
    ml_classifier.load()
    
    # Connect to MT5 (optional - will work in simulation mode if not available)
    await mt5_feed.connect()
    
    logger.info("System initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down system")
    mt5_feed.disconnect()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Autonomous Trading Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "status": "running" if is_running else "stopped",
        "version": "1.0.0",
    }


async def process_market_data(
    symbol: str = None,
    timeframe: Timeframe = Timeframe.M5
):
    """
    Main processing loop for market data.
    """
    global current_regime, is_running
    
    symbol = symbol or settings.default_symbol
    is_running = True
    
    logger.info(f"Starting market data processing for {symbol}")
    
    while is_running:
        try:
            # Get historical data
            df = await mt5_feed.get_historical_ohlcv(symbol, timeframe, bars=200)
            
            if df.empty:
                logger.warning("No data received, waiting...")
                await asyncio.sleep(5)
                continue
            
            # Get current prices
            tick = await mt5_feed.get_latest_tick(symbol)
            if not tick:
                await asyncio.sleep(1)
                continue
            
            current_price = tick.last
            current_bid = tick.bid
            current_ask = tick.ask
            
            # Process features
            df_features = feature_engineer_instance.create_features(df)
            
            if len(df_features) < 50:
                await asyncio.sleep(5)
                continue
            
            # Classify market regime
            if ml_classifier.is_fitted:
                regime_pred = ml_classifier.predict(df_features.iloc[-1:])
                current_regime = regime_pred.iloc[0] if len(regime_pred) > 0 else "RANGING"
            else:
                # Use rule-based regime detection
                adx = df_features['adx'].iloc[-1] if 'adx' in df_features else 0
                if adx > 25:
                    trend_structure = df_features.get('trend_structure', pd.Series([0])).iloc[-1]
                    current_regime = "TRENDING_UP" if trend_structure > 0 else "TRENDING_DOWN"
                else:
                    current_regime = "RANGING"
            
            # Generate signals
            signals = signal_engine.generate_signals(
                df_features,
                current_price,
                symbol,
                MarketRegime(current_regime) if current_regime in [e.value for e in MarketRegime] else None
            )
            
            # Get consolidated signal
            consolidated_signal = signal_engine.get_consolidated_signal(signals)
            
            # Check if we should trade
            if consolidated_signal and consolidated_signal.is_valid:
                can_trade, reason = risk_manager.can_open_trade(
                    len(paper_broker.open_trades),
                    consolidated_signal.score
                )
                
                if can_trade:
                    # Execute trade
                    trade = paper_broker.execute_signal(
                        consolidated_signal,
                        current_bid,
                        current_ask
                    )
                    
                    if trade:
                        # Save to database
                        try:
                            db = next(get_db())
                            save_signal(db, {
                                'symbol': symbol,
                                'strategy': consolidated_signal.strategy,
                                'direction': consolidated_signal.direction.value if consolidated_signal.direction else None,
                                'score': consolidated_signal.score,
                                'confidence': consolidated_signal.confidence,
                                'entry_price': consolidated_signal.entry_price,
                                'stop_loss': consolidated_signal.stop_loss,
                                'take_profit': consolidated_signal.take_profit,
                                'confluences': consolidated_signal.confluences,
                                'total_checks': consolidated_signal.total_checks,
                                'market_regime': current_regime,
                                'indicators': consolidated_signal.indicators,
                                'executed': True,
                                'trade_id': trade.trade_id,
                            })
                            db.close()
                        except Exception as e:
                            logger.error(f"Error saving signal: {e}")
            
            # Update open trades
            paper_broker.update_trades(current_bid, current_ask, symbol)
            
            # Check kill switch
            if risk_manager.check_kill_switch(paper_broker.equity):
                logger.warning("Trading halted by risk manager")
            
            # Save performance metrics periodically
            if len(paper_broker.closed_trades) % 10 == 0:
                try:
                    db = next(get_db())
                    metrics = paper_broker.get_performance_metrics()
                    save_performance_metric(db, {
                        'balance': metrics['balance'],
                        'equity': metrics['equity'],
                        'total_return': metrics['total_return'],
                        'total_trades': metrics['total_trades'],
                        'winning_trades': metrics['winning_trades'],
                        'losing_trades': metrics['losing_trades'],
                        'winrate': metrics['winrate'],
                        'profit_factor': metrics['profit_factor'],
                        'current_drawdown': metrics['current_drawdown'],
                        'max_drawdown': metrics['max_drawdown'],
                    })
                    db.close()
                except Exception as e:
                    logger.error(f"Error saving metrics: {e}")
            
            await asyncio.sleep(1)  # Wait before next iteration
            
        except Exception as e:
            logger.error(f"Error in processing loop: {e}", exc_info=True)
            await asyncio.sleep(5)


@app.post("/start")
async def start_trading(symbol: Optional[str] = None):
    """Start the trading loop."""
    global is_running
    
    if is_running:
        return {"status": "already_running"}
    
    symbol = symbol or settings.default_symbol
    
    asyncio.create_task(process_market_data(symbol))
    
    return {
        "status": "started",
        "symbol": symbol,
    }


@app.post("/stop")
async def stop_trading():
    """Stop the trading loop."""
    global is_running
    is_running = False
    
    return {"status": "stopped"}


@app.get("/info")
async def get_system_info():
    """Get comprehensive system information."""
    from main import paper_broker, risk_manager, signal_engine, current_regime
    
    info = {
        "trading_active": is_running,
        "current_regime": current_regime,
        "broker": paper_broker.get_performance_metrics() if paper_broker else {},
        "risk": risk_manager.get_risk_status() if risk_manager else {},
        "strategies": signal_engine.get_strategy_info() if signal_engine else {},
    }
    
    return info


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )

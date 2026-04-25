"""
Database models and connection handling.
Uses SQLAlchemy with SQLite fallback.
"""
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone
from typing import Optional
import json

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# Create engine
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

# Session factory
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Base class
Base = declarative_base()


class TradeModel(Base):
    """SQLAlchemy model for trades."""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(String, unique=True, index=True)
    symbol = Column(String, index=True)
    direction = Column(String)  # LONG or SHORT
    strategy = Column(String, index=True)
    
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    lots = Column(Float)
    
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    
    profit_loss = Column(Float, default=0.0)
    profit_loss_pips = Column(Float, default=0.0)
    
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    exit_timestamp = Column(DateTime, nullable=True)
    
    status = Column(String, default="OPEN")  # OPEN, CLOSED
    exit_reason = Column(String, nullable=True)  # STOP_LOSS, TAKE_PROFIT, MANUAL
    
    max_drawdown = Column(Float, default=0.0)
    max_profit = Column(Float, default=0.0)
    
    metadata_json = Column(JSON, nullable=True)
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'trade_id': self.trade_id,
            'symbol': self.symbol,
            'direction': self.direction,
            'strategy': self.strategy,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'lots': self.lots,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'profit_loss': self.profit_loss,
            'profit_loss_pips': self.profit_loss_pips,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'exit_timestamp': self.exit_timestamp.isoformat() if self.exit_timestamp else None,
            'status': self.status,
            'exit_reason': self.exit_reason,
            'max_drawdown': self.max_drawdown,
            'max_profit': self.max_profit,
        }


class SignalModel(Base):
    """SQLAlchemy model for signals."""
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    symbol = Column(String, index=True)
    strategy = Column(String, index=True)
    
    direction = Column(String, nullable=True)
    score = Column(Float)
    confidence = Column(Float)
    
    entry_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    
    confluences = Column(Integer, default=0)
    total_checks = Column(Integer, default=0)
    
    market_regime = Column(String, nullable=True)
    indicators = Column(JSON, nullable=True)
    
    executed = Column(Boolean, default=False)
    trade_id = Column(String, nullable=True)
    
    notes = Column(String, nullable=True)


class PerformanceMetricModel(Base):
    """SQLAlchemy model for performance metrics."""
    __tablename__ = "performance_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    balance = Column(Float)
    equity = Column(Float)
    total_return = Column(Float)
    
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    winrate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    
    current_drawdown = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    
    daily_pnl = Column(Float, default=0.0)
    
    metrics_json = Column(JSON, nullable=True)


class ModelMetricsModel(Base):
    """SQLAlchemy model for ML model metrics."""
    __tablename__ = "model_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    model_name = Column(String, index=True)
    model_type = Column(String)  # regime_classifier, predictor, etc.
    
    accuracy = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    
    training_samples = Column(Integer, default=0)
    features = Column(JSON, nullable=True)
    
    model_path = Column(String, nullable=True)


def init_db():
    """Initialize database tables."""
    logger.info("Initializing database")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Helper functions
def save_trade(db, trade_data: dict) -> TradeModel:
    """Save a trade to the database."""
    trade = TradeModel(**trade_data)
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


def save_signal(db, signal_data: dict) -> SignalModel:
    """Save a signal to the database."""
    signal = SignalModel(**signal_data)
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


def save_performance_metric(db, metrics: dict) -> PerformanceMetricModel:
    """Save performance metrics to the database."""
    metric = PerformanceMetricModel(**metrics)
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric


def get_recent_trades(db, limit: int = 100) -> list:
    """Get recent trades from database."""
    return db.query(TradeModel).order_by(TradeModel.timestamp.desc()).limit(limit).all()


def get_recent_signals(db, limit: int = 100) -> list:
    """Get recent signals from database."""
    return db.query(SignalModel).order_by(SignalModel.timestamp.desc()).limit(limit).all()

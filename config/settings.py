"""
Configuration settings for the trading system.
Uses pydantic-settings for environment-based configuration.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "SmartBroker Trading System"
    debug: bool = False
    log_level: str = "INFO"
    
    # MetaTrader 5
    mt5_login: Optional[int] = None
    mt5_password: Optional[str] = None
    mt5_server: str = "MetaQuotes-Demo"
    mt5_path: Optional[str] = None
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./trading.db"
    redis_url: str = "redis://localhost:6379/0"
    use_redis: bool = False
    
    # Trading
    initial_balance: float = 10000.0
    default_symbol: str = "EURUSD"
    default_lot_size: float = 0.01
    max_drawdown_pct: float = 5.0
    kill_switch: bool = False
    
    # Simulation
    simulate_slippage: bool = True
    slippage_pips: float = 1.0
    simulate_latency_ms: int = 50
    spread_multiplier: float = 1.0
    
    # ML
    ml_retrain_frequency: int = 100  # Retrain every N trades
    ml_confidence_threshold: float = 0.6
    regime_lookback_period: int = 100
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Risk
    max_position_size: float = 0.1
    risk_per_trade_pct: float = 1.0
    max_open_trades: int = 5
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()

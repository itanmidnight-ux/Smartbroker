from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv
import os

from utils.symbols import parse_symbols

load_dotenv()

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseModel):
    broker_profile: str = os.getenv("BROKER_PROFILE", "metaquotes_demo")
    symbols: list[str] = parse_symbols(os.getenv("SYMBOLS", "XAUUSD,XAUEUR"))
    timeframe: str = os.getenv("TIMEFRAME", "M15")
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    max_daily_loss_pct: float = float(os.getenv("RISK_MAX_DAILY_LOSS_PCT", "2.0"))
    max_drawdown_pct: float = float(os.getenv("RISK_MAX_DRAWDOWN_PCT", "8.0"))
    allow_live_trading: bool = os.getenv("ALLOW_LIVE_TRADING", "false").lower() in {"1", "true", "yes"}


settings = Settings()

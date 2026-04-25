from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json
import joblib


ROOT = Path(__file__).resolve().parents[3]
MODELS_DIR = ROOT / "python" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)



def _safe_symbol(symbol: str) -> str:
    return symbol.replace("/", "_").replace(" ", "_").upper()


def save_model(symbol: str, payload: dict) -> dict:
    symbol_name = _safe_symbol(symbol)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    model_file = MODELS_DIR / f"{symbol_name}_{ts}.joblib"
    latest_file = MODELS_DIR / f"{symbol_name}_latest.joblib"
    meta_file = MODELS_DIR / f"{symbol_name}_{ts}.json"

    joblib.dump(payload, model_file)
    joblib.dump(payload, latest_file)

    meta = {
        "symbol": symbol_name,
        "created_utc": ts,
        "model_file": str(model_file),
        "latest_file": str(latest_file),
        "metrics": payload.get("metrics", {}),
        "features": payload.get("features", []),
    }
    meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def load_latest_model(symbol: str) -> dict:
    symbol_name = _safe_symbol(symbol)
    latest_file = MODELS_DIR / f"{symbol_name}_latest.joblib"
    if not latest_file.exists():
        raise FileNotFoundError(f"No existe modelo latest para {symbol_name}")
    return joblib.load(latest_file)

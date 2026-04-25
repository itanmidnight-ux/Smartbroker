from pathlib import Path
import json


def load_profile(profile_name: str) -> dict:
    root = Path(__file__).resolve().parents[3]
    profile_map = {
        "metaquotes_demo": root / "config" / "brokers" / "metaquotes.demo.json",
        "weltrade_real": root / "config" / "brokers" / "weltrade.real.json",
    }
    if profile_name not in profile_map:
        raise ValueError(f"Perfil no soportado: {profile_name}")

    profile_path = profile_map[profile_name]
    return json.loads(profile_path.read_text(encoding="utf-8"))

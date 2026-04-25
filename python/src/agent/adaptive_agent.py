from __future__ import annotations

from pathlib import Path
import json
import random

ROOT = Path(__file__).resolve().parents[3]
STATE_PATH = ROOT / "python" / "models" / "adaptive_agent_state.json"
ACTIONS = ["buy", "sell", "hold"]


class AdaptiveBanditAgent:
    def __init__(self, epsilon: float = 0.10) -> None:
        self.epsilon = epsilon
        self.state = self._load_state()

    def _default_state(self) -> dict:
        def fresh() -> dict:
            return {"q": {a: 0.0 for a in ACTIONS}, "n": {a: 0 for a in ACTIONS}}

        return {
            "version": 1,
            "regimes": {
                "trending": fresh(),
                "ranging": fresh(),
                "high_volatility": fresh(),
                "unknown": fresh(),
            },
        }

    def _load_state(self) -> dict:
        if not STATE_PATH.exists():
            state = self._default_state()
            self._save_state(state)
            return state
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))

    def _save_state(self, state: dict | None = None) -> None:
        payload = state if state is not None else self.state
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def decide(self, regime: str, ml_action: str, probability: float) -> dict:
        regime_key = regime if regime in self.state["regimes"] else "unknown"
        values = self.state["regimes"][regime_key]["q"]

        if random.random() < self.epsilon:
            final_action = random.choice(ACTIONS)
            policy = "explore"
        else:
            best = max(values, key=values.get)
            final_action = ml_action if probability >= 0.60 else best
            policy = "exploit"

        return {
            "regime": regime_key,
            "ml_action": ml_action,
            "final_action": final_action,
            "policy_mode": policy,
            "q_values": values,
            "green_flag": True,
        }

    def update(self, regime: str, action: str, reward: float) -> dict:
        regime_key = regime if regime in self.state["regimes"] else "unknown"
        bucket = self.state["regimes"][regime_key]

        n = bucket["n"].get(action, 0) + 1
        q = bucket["q"].get(action, 0.0)
        bucket["n"][action] = n
        bucket["q"][action] = q + (reward - q) / n

        self._save_state()
        return {
            "regime": regime_key,
            "action": action,
            "reward": reward,
            "new_q": bucket["q"][action],
            "samples": n,
            "green_flag": True,
        }

    def validate(self) -> dict:
        ok = bool(self.state.get("regimes"))
        return {"ok": ok, "green_flag": ok, "state_path": str(STATE_PATH)}

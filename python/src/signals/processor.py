from __future__ import annotations

from collections import Counter


def analyze_signals(rows: list[dict]) -> dict:
    if not rows:
        return {"count": 0, "green_flag": False}

    actions = Counter(r["final_action"] for r in rows)
    regimes = Counter(r["regime"] for r in rows)

    rewards = [r["reward"] for r in rows if r.get("reward") is not None]
    avg_reward = sum(rewards) / len(rewards) if rewards else 0.0

    return {
        "count": len(rows),
        "actions": dict(actions),
        "regimes": dict(regimes),
        "avg_reward": avg_reward,
        "green_flag": True,
    }

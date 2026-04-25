from __future__ import annotations


def validation_result(name: str, ok: bool, details: dict | None = None) -> dict:
    return {
        "name": name,
        "ok": ok,
        "green_flag": ok,
        "details": details or {},
    }

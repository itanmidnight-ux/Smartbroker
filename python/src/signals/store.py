from __future__ import annotations

import sqlite3
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "signals.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_store() -> None:
    with _conn() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_utc TEXT NOT NULL,
                symbol TEXT NOT NULL,
                regime TEXT NOT NULL,
                ml_action TEXT NOT NULL,
                final_action TEXT NOT NULL,
                probability REAL NOT NULL,
                source TEXT NOT NULL,
                reward REAL
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_utc TEXT NOT NULL,
                signal_id INTEGER,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                entry_price REAL,
                quantity REAL,
                pnl REAL,
                FOREIGN KEY(signal_id) REFERENCES signals(id)
            )
            """
        )


def insert_signal(symbol: str, regime: str, ml_action: str, final_action: str, probability: float, source: str) -> int:
    init_store()
    ts = datetime.now(timezone.utc).isoformat()
    with _conn() as con:
        cur = con.execute(
            """
            INSERT INTO signals (ts_utc, symbol, regime, ml_action, final_action, probability, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ts, symbol, regime, ml_action, final_action, probability, source),
        )
        return int(cur.lastrowid)


def insert_trade(signal_id: int, symbol: str, side: str, mode: str, status: str, entry_price: float | None, quantity: float, pnl: float = 0.0) -> int:
    init_store()
    ts = datetime.now(timezone.utc).isoformat()
    with _conn() as con:
        cur = con.execute(
            """
            INSERT INTO trades (ts_utc, signal_id, symbol, side, mode, status, entry_price, quantity, pnl)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ts, signal_id, symbol, side, mode, status, entry_price, quantity, pnl),
        )
        return int(cur.lastrowid)


def recent_trades(limit: int = 50) -> list[dict]:
    init_store()
    with _conn() as con:
        cur = con.execute(
            """
            SELECT id, ts_utc, signal_id, symbol, side, mode, status, entry_price, quantity, pnl
            FROM trades
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    return [dict(zip(cols, row)) for row in rows]


def update_reward(signal_id: int, reward: float) -> None:
    init_store()
    with _conn() as con:
        con.execute("UPDATE signals SET reward = ? WHERE id = ?", (reward, signal_id))


def recent_signals(limit: int = 50) -> list[dict]:
    init_store()
    with _conn() as con:
        cur = con.execute(
            """
            SELECT id, ts_utc, symbol, regime, ml_action, final_action, probability, source, reward
            FROM signals
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    return [dict(zip(cols, row)) for row in rows]

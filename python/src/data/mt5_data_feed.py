from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd

try:
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover
    mt5 = None

TIMEFRAME_MAP = {
    "M1": getattr(mt5, "TIMEFRAME_M1", None),
    "M5": getattr(mt5, "TIMEFRAME_M5", None),
    "M15": getattr(mt5, "TIMEFRAME_M15", None),
    "M30": getattr(mt5, "TIMEFRAME_M30", None),
    "H1": getattr(mt5, "TIMEFRAME_H1", None),
    "H4": getattr(mt5, "TIMEFRAME_H4", None),
    "D1": getattr(mt5, "TIMEFRAME_D1", None),
}


@dataclass
class MarketSnapshot:
    symbol: str
    bid: float
    ask: float
    spread_points: float
    timestamp_utc: str


class MT5DataFeed:
    def __init__(self, symbol: str, timeframe: str = "M15") -> None:
        self.symbol = symbol
        self.timeframe = timeframe

    def ensure_symbol(self) -> bool:
        if mt5 is None:
            raise RuntimeError("MetaTrader5 package no instalado.")
        return bool(mt5.symbol_select(self.symbol, True))

    def get_snapshot(self) -> MarketSnapshot:
        if mt5 is None:
            raise RuntimeError("MetaTrader5 package no instalado.")

        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            raise RuntimeError(f"No se pudo obtener tick para {self.symbol}: {mt5.last_error()}")

        symbol_info = mt5.symbol_info(self.symbol)
        point = symbol_info.point if symbol_info else 0.00001
        spread_points = (tick.ask - tick.bid) / point if point else 0.0

        return MarketSnapshot(
            symbol=self.symbol,
            bid=float(tick.bid),
            ask=float(tick.ask),
            spread_points=float(spread_points),
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
        )

    def get_ohlcv(self, bars: int = 500) -> pd.DataFrame:
        if mt5 is None:
            raise RuntimeError("MetaTrader5 package no instalado.")

        tf = TIMEFRAME_MAP.get(self.timeframe)
        if tf is None:
            raise ValueError(f"Timeframe no soportado: {self.timeframe}")

        rates = mt5.copy_rates_from_pos(self.symbol, tf, 0, bars)
        if rates is None:
            raise RuntimeError(f"No se pudo obtener OHLCV: {mt5.last_error()}")

        df = pd.DataFrame(rates)
        if df.empty:
            return df

        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        return df


class MT5TradingFeed:
    @staticmethod
    def get_open_positions() -> list[dict[str, Any]]:
        if mt5 is None:
            raise RuntimeError("MetaTrader5 package no instalado.")
        positions = mt5.positions_get()
        if positions is None:
            return []
        return [p._asdict() for p in positions]

    @staticmethod
    def get_pending_orders() -> list[dict[str, Any]]:
        if mt5 is None:
            raise RuntimeError("MetaTrader5 package no instalado.")
        orders = mt5.orders_get()
        if orders is None:
            return []
        return [o._asdict() for o in orders]


def summarize_ohlcv(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"bars": 0}

    latest = df.iloc[-1]
    return {
        "bars": int(len(df)),
        "latest_time": latest["time"].isoformat(),
        "latest_close": float(latest["close"]),
        "latest_volume": float(latest["tick_volume"]),
    }


def synthetic_ohlcv(symbol: str, rows: int = 500) -> pd.DataFrame:
    rng = pd.date_range(end=pd.Timestamp.utcnow(), periods=rows, freq="5min", tz="UTC")
    base = pd.Series(range(rows), dtype=float)
    close = 1900 + (base * 0.05) + (base % 7 - 3) * 0.2
    open_ = close.shift(1).fillna(close.iloc[0])
    high = pd.concat([open_, close], axis=1).max(axis=1) + 0.5
    low = pd.concat([open_, close], axis=1).min(axis=1) - 0.5
    tick_volume = 100 + (base % 20) * 5
    return pd.DataFrame({
        "time": rng,
        "open": open_.values,
        "high": high.values,
        "low": low.values,
        "close": close.values,
        "tick_volume": tick_volume.values,
        "symbol": symbol,
    })

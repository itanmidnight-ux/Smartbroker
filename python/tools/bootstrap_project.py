from __future__ import annotations

from signals.store import init_store
from agent.adaptive_agent import AdaptiveBanditAgent
from data.mt5_data_feed import synthetic_ohlcv
from ml.train import train_and_register

SYMBOLS = ["XAUUSD", "XAUEUR"]


def main() -> None:
    init_store()
    agent = AdaptiveBanditAgent()
    print(f"[bootstrap] agent_state_ok={agent.validate()['green_flag']}")

    for symbol in SYMBOLS:
        ohlcv = synthetic_ohlcv(symbol, rows=900)
        result = train_and_register(symbol, ohlcv)
        print(f"[bootstrap] model={symbol} green_flag={result['green_flag']} rows={result['train_rows']}")

    print("[bootstrap] completed")


if __name__ == "__main__":
    main()

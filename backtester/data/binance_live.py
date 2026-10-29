"""Live crypto bars streamed from the Binance WebSocket API (experimental).

This handler shows how the same ``DataHandler`` interface can be fed by a
push-based stream instead of a historical replay. It is not wired into the
backtest loop yet. Requires the ``live`` extra (``pip install -e ".[live]"``).
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from queue import Queue

import numpy as np

from backtester.data.base import Bar, DataHandler
from backtester.events import MarketEvent

logger = logging.getLogger(__name__)


class BinanceLiveDataHandler(DataHandler):
    """Publishes a ``MarketEvent`` for every closed kline received."""

    def __init__(self, events: Queue, symbol_list: list[str], interval: str = "1m"):
        self.events = events
        self.symbol_list = [s.lower() for s in symbol_list]
        self.interval = interval
        self.continue_backtest = True
        self.latest_symbol_data: dict[str, list[Bar]] = defaultdict(list)

    async def _stream(self, manager, symbol: str) -> None:
        async with manager.kline_socket(symbol, interval=self.interval) as stream:
            while self.continue_backtest:
                msg = await stream.recv()
                if msg.get("e") != "kline" or not msg["k"]["x"]:  # keep closed klines only
                    continue
                k = msg["k"]
                timestamp = datetime.fromtimestamp(k["t"] / 1000, tz=timezone.utc)
                bar = {
                    "open": float(k["o"]),
                    "high": float(k["h"]),
                    "low": float(k["l"]),
                    "close": float(k["c"]),
                    "volume": float(k["v"]),
                    "adj_close": float(k["c"]),
                }
                self.latest_symbol_data[symbol].append((timestamp, bar))
                self.events.put(MarketEvent())
                logger.info("%s bar received at %s", symbol, timestamp)

    async def run(self) -> None:
        from binance import AsyncClient, BinanceSocketManager

        client = await AsyncClient.create()
        try:
            manager = BinanceSocketManager(client)
            await asyncio.gather(*(self._stream(manager, s) for s in self.symbol_list))
        finally:
            await client.close_connection()

    def get_latest_bar(self, symbol: str) -> Bar:
        return self.latest_symbol_data[symbol][-1]

    def get_latest_bars(self, symbol: str, n: int = 1) -> list[Bar]:
        return self.latest_symbol_data[symbol][-n:]

    def get_latest_bar_datetime(self, symbol: str):
        return self.get_latest_bar(symbol)[0]

    def get_latest_bar_value(self, symbol: str, val_type: str) -> float:
        return float(self.get_latest_bar(symbol)[1][val_type])

    def get_latest_bars_values(self, symbol: str, val_type: str, n: int = 1) -> np.ndarray:
        return np.array([bar[1][val_type] for bar in self.get_latest_bars(symbol, n)])

    def update_bars(self) -> None:
        """Nothing to do: bars are pushed by the WebSocket stream."""

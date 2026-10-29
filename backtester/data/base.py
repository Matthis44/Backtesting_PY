"""Common interface and historical replay logic for data handlers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from queue import Queue

import numpy as np
import pandas as pd

from backtester.events import MarketEvent

#: Columns every bar must provide, in this order.
BAR_COLUMNS = ["open", "high", "low", "close", "volume", "adj_close"]

Bar = tuple[pd.Timestamp, pd.Series]


class DataHandler(ABC):
    """Interface shared by historical and live data handlers.

    Strategies and portfolios only see the bars already "published", which
    prevents look-ahead bias during a backtest.
    """

    symbol_list: list[str]
    continue_backtest: bool

    @abstractmethod
    def get_latest_bar(self, symbol: str) -> Bar: ...

    @abstractmethod
    def get_latest_bars(self, symbol: str, n: int = 1) -> list[Bar]: ...

    @abstractmethod
    def get_latest_bar_datetime(self, symbol: str) -> pd.Timestamp: ...

    @abstractmethod
    def get_latest_bar_value(self, symbol: str, val_type: str) -> float: ...

    @abstractmethod
    def get_latest_bars_values(self, symbol: str, val_type: str, n: int = 1) -> np.ndarray: ...

    @abstractmethod
    def update_bars(self) -> None: ...


class HistoricDataHandler(DataHandler):
    """Replays historical OHLCV bars one at a time.

    Subclasses only implement :meth:`load_data`, which returns one DataFrame
    per symbol indexed by datetime with the columns in :data:`BAR_COLUMNS`.
    All symbols are aligned on the union of their dates and gaps are
    forward-filled, so every symbol has a bar on every timestamp.
    """

    def __init__(self, events: Queue, symbol_list: list[str]):
        self.events = events
        self.symbol_list = list(symbol_list)
        self.continue_backtest = True
        self.latest_symbol_data: dict[str, list[Bar]] = {s: [] for s in self.symbol_list}
        self._iterators: dict[str, Iterator[Bar]] = self._prepare(self.load_data())

    @abstractmethod
    def load_data(self) -> dict[str, pd.DataFrame]:
        """Return the raw bars for each symbol in ``symbol_list``."""

    def _prepare(self, frames: dict[str, pd.DataFrame]) -> dict[str, Iterator[Bar]]:
        missing = [s for s in self.symbol_list if s not in frames or frames[s].empty]
        if missing:
            raise ValueError(f"No data found for: {', '.join(missing)}")

        combined_index = None
        for symbol in self.symbol_list:
            frame = frames[symbol]
            absent = set(BAR_COLUMNS) - set(frame.columns)
            if absent:
                raise ValueError(f"{symbol}: missing columns {sorted(absent)}")
            frames[symbol] = frame[BAR_COLUMNS].sort_index()
            index = frames[symbol].index
            combined_index = index if combined_index is None else combined_index.union(index)

        return {symbol: frames[symbol].reindex(combined_index).ffill().iterrows() for symbol in self.symbol_list}

    def update_bars(self) -> None:
        """Publish the next bar of every symbol and emit a ``MarketEvent``."""
        for symbol in self.symbol_list:
            try:
                bar = next(self._iterators[symbol])
            except StopIteration:
                self.continue_backtest = False
                return
            self.latest_symbol_data[symbol].append(bar)
        self.events.put(MarketEvent())

    def get_latest_bar(self, symbol: str) -> Bar:
        bars = self._bars(symbol)
        if not bars:
            raise IndexError(f"No bar published yet for {symbol}")
        return bars[-1]

    def get_latest_bars(self, symbol: str, n: int = 1) -> list[Bar]:
        return self._bars(symbol)[-n:]

    def get_latest_bar_datetime(self, symbol: str) -> pd.Timestamp:
        return self.get_latest_bar(symbol)[0]

    def get_latest_bar_value(self, symbol: str, val_type: str) -> float:
        return float(self.get_latest_bar(symbol)[1][val_type])

    def get_latest_bars_values(self, symbol: str, val_type: str, n: int = 1) -> np.ndarray:
        return np.array([bar[1][val_type] for bar in self.get_latest_bars(symbol, n)])

    def _bars(self, symbol: str) -> list[Bar]:
        try:
            return self.latest_symbol_data[symbol]
        except KeyError:
            raise KeyError(f"Unknown symbol: {symbol}") from None

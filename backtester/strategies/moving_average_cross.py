"""Long-only moving average crossover."""

from __future__ import annotations

import logging
from queue import Queue

from backtester.data.base import DataHandler
from backtester.events import MarketEvent, SignalEvent
from backtester.strategies.base import Strategy

logger = logging.getLogger(__name__)


class MovingAverageCrossStrategy(Strategy):
    """Go long when the short SMA crosses above the long SMA, exit when it crosses below.

    Signals are computed on adjusted close prices so that splits and dividends
    do not create false crossovers.
    """

    strategy_id = "MACross"

    def __init__(
        self,
        data_handler: DataHandler,
        events: Queue,
        short_window: int = 40,
        long_window: int = 100,
    ):
        if not 0 < short_window < long_window:
            raise ValueError("Expected 0 < short_window < long_window")
        super().__init__(data_handler, events)
        self.short_window = short_window
        self.long_window = long_window
        self.invested = {symbol: False for symbol in self.symbol_list}

    def calculate_signals(self, event: MarketEvent) -> None:
        if event.type != "MARKET":
            return

        for symbol in self.symbol_list:
            prices = self.data_handler.get_latest_bars_values(symbol, "adj_close", n=self.long_window)
            if len(prices) < self.long_window:
                continue  # warm-up period

            short_sma = prices[-self.short_window :].mean()
            long_sma = prices.mean()
            dt = self.data_handler.get_latest_bar_datetime(symbol)

            if short_sma > long_sma and not self.invested[symbol]:
                self._emit(symbol, dt, "LONG")
                self.invested[symbol] = True
            elif short_sma < long_sma and self.invested[symbol]:
                self._emit(symbol, dt, "EXIT")
                self.invested[symbol] = False

    def _emit(self, symbol: str, dt, signal_type: str) -> None:
        logger.debug("%s %s %s (SMA%d vs SMA%d)", dt, signal_type, symbol, self.short_window, self.long_window)
        self.events.put(SignalEvent(self.strategy_id, symbol, dt, signal_type))

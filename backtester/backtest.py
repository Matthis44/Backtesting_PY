"""Event loop tying the components together."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from queue import Empty, Queue

import pandas as pd

from backtester.data.base import DataHandler
from backtester.execution import SimulatedExecutionHandler
from backtester.portfolio import Portfolio
from backtester.strategies.base import Strategy

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    equity_curve: pd.DataFrame
    stats: dict[str, float]
    signals: int
    orders: int
    fills: int


class Backtest:
    """Runs a strategy on historical data, bar by bar.

    For every bar: the data handler publishes it (``MARKET``), the strategy
    may emit a ``SIGNAL``, the portfolio turns it into an ``ORDER``, and the
    execution handler sends back a ``FILL``. Processing each bar's events
    before publishing the next one prevents look-ahead bias.

    Example::

        events = Queue()
        data = HistoricCSVDataHandler(events, ["AAPL"], "data/")
        bt = Backtest(data, MovingAverageCrossStrategy, events=events,
                      strategy_params={"short_window": 20, "long_window": 50})
        result = bt.run()
    """

    def __init__(
        self,
        data_handler: DataHandler,
        strategy_cls: type[Strategy],
        events: Queue,
        initial_capital: float = 100_000.0,
        start_date: pd.Timestamp | None = None,
        strategy_params: dict | None = None,
        lot_size: int = 100,
        heartbeat: float = 0.0,
    ):
        self.events = events
        self.data_handler = data_handler
        self.heartbeat = heartbeat
        self.strategy = strategy_cls(data_handler, events, **(strategy_params or {}))
        self.portfolio = Portfolio(
            data_handler,
            events,
            start_date if start_date is not None else pd.Timestamp.min,
            initial_capital,
            lot_size,
        )
        self.execution_handler = SimulatedExecutionHandler(events, data_handler)
        self.signals = self.orders = self.fills = 0

    def _dispatch(self, event) -> None:
        if event.type == "MARKET":
            self.strategy.calculate_signals(event)
            self.portfolio.update_timeindex()
        elif event.type == "SIGNAL":
            self.signals += 1
            self.portfolio.update_signal(event)
        elif event.type == "ORDER":
            self.orders += 1
            self.execution_handler.execute_order(event)
        elif event.type == "FILL":
            self.fills += 1
            self.portfolio.update_fill(event)

    def run(self) -> BacktestResult:
        logger.info("Starting backtest on %s", ", ".join(self.data_handler.symbol_list))
        while True:
            self.data_handler.update_bars()
            if not self.data_handler.continue_backtest:
                break
            while True:
                try:
                    event = self.events.get(block=False)
                except Empty:
                    break
                self._dispatch(event)
            if self.heartbeat:
                time.sleep(self.heartbeat)

        curve = self.portfolio.create_equity_curve()
        result = BacktestResult(curve, self.portfolio.summary_stats(), self.signals, self.orders, self.fills)
        logger.info("Backtest finished: %d signals, %d orders, %d fills", self.signals, self.orders, self.fills)
        return result

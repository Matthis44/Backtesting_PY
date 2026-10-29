"""Order execution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from queue import Queue

from backtester.data.base import DataHandler
from backtester.events import FillEvent, OrderEvent


class ExecutionHandler(ABC):
    """Turns ``OrderEvent``s into ``FillEvent``s (simulated or through a broker API)."""

    @abstractmethod
    def execute_order(self, event: OrderEvent) -> None: ...


class SimulatedExecutionHandler(ExecutionHandler):
    """Fills every order immediately and entirely at the latest price.

    Simplifying assumptions: no slippage, no latency, no partial fills.
    """

    def __init__(self, events: Queue, data_handler: DataHandler):
        self.events = events
        self.data_handler = data_handler

    def execute_order(self, event: OrderEvent) -> None:
        if event.type != "ORDER":
            return
        price = self.data_handler.get_latest_bar_value(event.symbol, "adj_close")
        self.events.put(
            FillEvent(
                timeindex=self.data_handler.get_latest_bar_datetime(event.symbol),
                symbol=event.symbol,
                exchange="SIMULATED",
                quantity=event.quantity,
                direction=event.direction,
                fill_cost=price * event.quantity,
            )
        )

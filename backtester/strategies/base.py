"""Base class for strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from queue import Queue

from backtester.data.base import DataHandler
from backtester.events import MarketEvent


class Strategy(ABC):
    """Turns market data into ``SignalEvent``s put on the event queue."""

    def __init__(self, data_handler: DataHandler, events: Queue):
        self.data_handler = data_handler
        self.events = events
        self.symbol_list = data_handler.symbol_list

    @abstractmethod
    def calculate_signals(self, event: MarketEvent) -> None:
        """React to a new bar, possibly emitting signals."""

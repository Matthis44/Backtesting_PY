"""Events exchanged between the components of the backtester.

The engine is driven by a single queue: the data handler emits a
``MarketEvent`` for every new bar, the strategy answers with ``SignalEvent``s,
the portfolio turns signals into ``OrderEvent``s and the execution handler
fills them with ``FillEvent``s.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


class Event:
    """Base class for every event; ``type`` is used to dispatch it."""

    type: str


@dataclass
class MarketEvent(Event):
    """A new bar is available for every symbol."""

    type: str = field(default="MARKET", init=False)


@dataclass
class SignalEvent(Event):
    """Trading signal emitted by a strategy."""

    strategy_id: str
    symbol: str
    datetime: datetime
    signal_type: str  # "LONG", "SHORT" or "EXIT"
    strength: float = 1.0
    type: str = field(default="SIGNAL", init=False)


@dataclass
class OrderEvent(Event):
    """Order sent by the portfolio to the execution handler."""

    symbol: str
    order_type: str  # "MKT" or "LMT"
    quantity: int
    direction: str  # "BUY" or "SELL"
    type: str = field(default="ORDER", init=False)


class CommissionModel(ABC):
    """Computes the commission charged for a fill."""

    @abstractmethod
    def calculate(self, quantity: int) -> float: ...


class IBCommissionModel(CommissionModel):
    """Interactive Brokers style fixed-rate commission for US equities."""

    def calculate(self, quantity: int) -> float:
        rate = 0.013 if quantity <= 500 else 0.008
        return max(1.3, rate * quantity)


@dataclass
class FillEvent(Event):
    """An order has been executed."""

    timeindex: datetime
    symbol: str
    exchange: str
    quantity: int
    direction: str  # "BUY" or "SELL"
    fill_cost: float | None = None
    commission: float | None = None
    commission_model: CommissionModel | None = field(default=None, repr=False)
    type: str = field(default="FILL", init=False)

    def __post_init__(self) -> None:
        if self.commission is None:
            model = self.commission_model or IBCommissionModel()
            self.commission = model.calculate(self.quantity)

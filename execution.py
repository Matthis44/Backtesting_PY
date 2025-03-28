# execution.py
from abc import ABC, abstractmethod
import datetime
from event import FillEvent


class ExecutionHandler(ABC):
    """
    Abstract base class for executing orders.

    This can be subclassed into:
    - SimulatedExecutionHandler (for backtesting)
    - LiveBrokerExecutionHandler (for real trading via API)

    Methods:
    - execute_order(event): receives OrderEvent, produces FillEvent
    """

    @abstractmethod
    def execute_order(self, event):
        """
        Executes an order, producing a FillEvent.

        Parameters:
        - event: OrderEvent to be executed
        """
        raise NotImplementedError("Should implement execute_order()")


class SimulatedExecutionHandler(ExecutionHandler):
    """
    A naive simulated execution handler:
    - Instantly fills all orders at market price
    - No slippage, no latency, no partial fills
    """

    def __init__(self, events):
        """
        Parameters:
        - events: queue.Queue object for sending FillEvents
        """
        self.events = events

    def execute_order(self, event):
        """
        Converts OrderEvent to FillEvent immediately (at "market").

        Parameters:
        - event: OrderEvent
        """
        if event.type == 'ORDER':
            fill_event = FillEvent(
                timeindex=datetime.datetime.utcnow(),
                symbol=event.symbol,
                exchange='SIMULATED',  # or 'ARCA', 'NYSE', etc.
                quantity=event.quantity,
                direction=event.direction,
                fill_cost=None  # Portfolio will handle pricing
            )
            self.events.put(fill_event)

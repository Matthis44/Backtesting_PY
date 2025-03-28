# strategy.py
from abc import ABC, abstractmethod
import datetime
import numpy as np
import pandas as pd
from event import SignalEvent


class Strategy(ABC):
    """
    Strategy is an abstract base class that provides an interface for
    all trading strategy implementations.

    Its job is to generate SignalEvent objects based on market data updates.
    """

    @abstractmethod
    def calculate_signals(self):
        """
        Logic to calculate signals.
        Should produce SignalEvents and inject them into the event queue.
        """
        raise NotImplementedError("Should implement calculate_signals()")

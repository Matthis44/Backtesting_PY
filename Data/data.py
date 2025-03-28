# data.py
from abc import ABC, abstractmethod
import os
import pandas as pd
import numpy as np
from event import MarketEvent


class DataHandler(ABC):
    """
    Abstract base class providing an interface for all data handlers
    (both historic and live).
    """

    @abstractmethod
    def get_latest_bar(self, symbol):
        raise NotImplementedError("Should implement get_latest_bar()")

    @abstractmethod
    def get_latest_bars(self, symbol, N=1):
        raise NotImplementedError("Should implement get_latest_bars()")

    @abstractmethod
    def get_latest_bar_datetime(self, symbol):
        raise NotImplementedError("Should implement get_latest_bar_datetime()")

    @abstractmethod
    def get_latest_bar_value(self, symbol, val_type):
        raise NotImplementedError("Should implement get_latest_bar_value()")

    @abstractmethod
    def get_latest_bars_values(self, symbol, val_type, N=1):
        raise NotImplementedError("Should implement get_latest_bars_values()")

    @abstractmethod
    def update_bars(self):
        raise NotImplementedError("Should implement update_bars()")



"""Trading strategies."""

from backtester.strategies.base import Strategy
from backtester.strategies.moving_average_cross import MovingAverageCrossStrategy

__all__ = ["Strategy", "MovingAverageCrossStrategy"]

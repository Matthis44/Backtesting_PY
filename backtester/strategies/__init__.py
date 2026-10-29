"""Trading strategies."""

from backtester.strategies.base import Strategy
from backtester.strategies.mean_reversion import MeanReversionStrategy
from backtester.strategies.moving_average_cross import MovingAverageCrossStrategy
from backtester.strategies.pairs_trading import PairsTradingStrategy

__all__ = ["Strategy", "MeanReversionStrategy", "MovingAverageCrossStrategy", "PairsTradingStrategy"]

"""Statistical arbitrage on a pair of cointegrated assets."""

from __future__ import annotations

import logging
from queue import Queue

import numpy as np

from backtester.cointegration import ols
from backtester.data.base import DataHandler
from backtester.events import MarketEvent, SignalEvent
from backtester.strategies.base import Strategy

logger = logging.getLogger(__name__)


class PairsTradingStrategy(Strategy):
    """Trade the spread ``y - beta * x`` when it moves away from its mean.

    On every bar the hedge ratio ``beta`` is re-estimated by OLS over the last
    ``lookback`` bars (only past data, so no look-ahead), and the spread is
    standardised into a z-score:

    - ``z > entry_z``: the spread is rich, sell ``y`` and buy ``beta`` units of ``x``;
    - ``z < -entry_z``: the spread is cheap, buy ``y`` and sell ``beta`` units of ``x``;
    - ``|z| < exit_z``: close both legs.

    The hedge ratio is passed to the portfolio as the signal ``strength`` so the ``x``
    leg is sized at ``beta`` times the ``y`` leg. Use :mod:`backtester.cointegration`
    to check that the pair is cointegrated before trading it.
    """

    strategy_id = "Pairs"

    def __init__(
        self,
        data_handler: DataHandler,
        events: Queue,
        pair: tuple[str, str] | None = None,
        lookback: int = 60,
        entry_z: float = 2.0,
        exit_z: float = 0.5,
    ):
        if lookback < 3:
            raise ValueError("lookback must be at least 3")
        if not 0 <= exit_z < entry_z:
            raise ValueError("Expected 0 <= exit_z < entry_z")
        super().__init__(data_handler, events)
        self.y, self.x = pair or tuple(self.symbol_list[:2])
        if self.y == self.x or {self.y, self.x} - set(self.symbol_list):
            raise ValueError("pair must be two different symbols of the data handler")
        self.lookback = lookback
        self.entry_z = entry_z
        self.exit_z = exit_z
        self.position = 0  # +1 long spread, -1 short spread, 0 flat

    def spread_zscore(self) -> tuple[float, float] | None:
        """Hedge ratio and z-score of the latest spread, or ``None`` during warm-up."""
        y = self.data_handler.get_latest_bars_values(self.y, "adj_close", n=self.lookback)
        x = self.data_handler.get_latest_bars_values(self.x, "adj_close", n=self.lookback)
        if len(y) < self.lookback or np.ptp(x) == 0:
            return None
        _, beta, _ = ols(y, x)
        spread = y - beta * x
        std = spread.std(ddof=1)
        if beta <= 0 or std == 0:
            return None
        return beta, float((spread[-1] - spread.mean()) / std)

    def calculate_signals(self, event: MarketEvent) -> None:
        if event.type != "MARKET":
            return
        estimate = self.spread_zscore()
        if estimate is None:
            return
        beta, z = estimate
        dt = self.data_handler.get_latest_bar_datetime(self.y)

        if self.position == 0 and z > self.entry_z:
            self._emit(dt, ("SHORT", "LONG"), beta, z)
            self.position = -1
        elif self.position == 0 and z < -self.entry_z:
            self._emit(dt, ("LONG", "SHORT"), beta, z)
            self.position = 1
        elif self.position != 0 and abs(z) < self.exit_z:
            self._emit(dt, ("EXIT", "EXIT"), beta, z)
            self.position = 0

    def _emit(self, dt, signals: tuple[str, str], beta: float, z: float) -> None:
        logger.debug("%s %s %s / %s %s (beta=%.3f, z=%.2f)", dt, signals[0], self.y, signals[1], self.x, beta, z)
        self.events.put(SignalEvent(self.strategy_id, self.y, dt, signals[0]))
        self.events.put(SignalEvent(self.strategy_id, self.x, dt, signals[1], strength=beta))

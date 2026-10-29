"""Single-asset mean reversion on the z-score of the price."""

from __future__ import annotations

import logging
from queue import Queue

from backtester.data.base import DataHandler
from backtester.events import MarketEvent, SignalEvent
from backtester.strategies.base import Strategy

logger = logging.getLogger(__name__)


class MeanReversionStrategy(Strategy):
    """Fade large deviations from a rolling mean (Bollinger-band style).

    ``z = (price - rolling mean) / rolling std`` over ``lookback`` bars.
    Go long when ``z < -entry_z``, short when ``z > entry_z`` (if ``allow_short``),
    and exit once ``|z| < exit_z``.
    """

    strategy_id = "MeanReversion"

    def __init__(
        self,
        data_handler: DataHandler,
        events: Queue,
        lookback: int = 20,
        entry_z: float = 2.0,
        exit_z: float = 0.5,
        allow_short: bool = True,
    ):
        if lookback < 2:
            raise ValueError("lookback must be at least 2")
        if not 0 <= exit_z < entry_z:
            raise ValueError("Expected 0 <= exit_z < entry_z")
        super().__init__(data_handler, events)
        self.lookback = lookback
        self.entry_z = entry_z
        self.exit_z = exit_z
        self.allow_short = allow_short
        self.position = {symbol: 0 for symbol in self.symbol_list}  # +1 long, -1 short, 0 flat

    def calculate_signals(self, event: MarketEvent) -> None:
        if event.type != "MARKET":
            return

        for symbol in self.symbol_list:
            prices = self.data_handler.get_latest_bars_values(symbol, "adj_close", n=self.lookback)
            if len(prices) < self.lookback:
                continue  # warm-up period
            std = prices.std(ddof=1)
            if std == 0:
                continue
            z = (prices[-1] - prices.mean()) / std
            dt = self.data_handler.get_latest_bar_datetime(symbol)
            position = self.position[symbol]

            if position == 0 and z < -self.entry_z:
                self._emit(symbol, dt, "LONG", z)
                self.position[symbol] = 1
            elif position == 0 and z > self.entry_z and self.allow_short:
                self._emit(symbol, dt, "SHORT", z)
                self.position[symbol] = -1
            elif position != 0 and abs(z) < self.exit_z:
                self._emit(symbol, dt, "EXIT", z)
                self.position[symbol] = 0

    def _emit(self, symbol: str, dt, signal_type: str, z: float) -> None:
        logger.debug("%s %s %s (z=%.2f)", dt, signal_type, symbol, z)
        self.events.put(SignalEvent(self.strategy_id, symbol, dt, signal_type))

"""Positions, holdings and order sizing."""

from __future__ import annotations

from queue import Queue

import pandas as pd

from backtester.data.base import DataHandler
from backtester.events import FillEvent, OrderEvent, SignalEvent
from backtester.performance import summary_stats


class Portfolio:
    """Tracks positions and mark-to-market holdings, and sizes orders.

    Orders use a fixed lot size; this keeps the engine simple and makes it
    easy to plug in a risk-based sizing rule later.
    """

    def __init__(
        self,
        data_handler: DataHandler,
        events: Queue,
        start_date: pd.Timestamp,
        initial_capital: float = 100_000.0,
        lot_size: int = 100,
    ):
        self.data_handler = data_handler
        self.events = events
        self.symbol_list = data_handler.symbol_list
        self.start_date = start_date
        self.initial_capital = initial_capital
        self.lot_size = lot_size

        self.current_positions = {s: 0 for s in self.symbol_list}
        self.all_positions = [{**self.current_positions, "datetime": start_date}]

        self.current_holdings = self._empty_holdings()
        self.all_holdings = [{**self.current_holdings, "datetime": start_date}]
        self.equity_curve: pd.DataFrame | None = None

    def _empty_holdings(self) -> dict:
        holdings = {s: 0.0 for s in self.symbol_list}
        holdings.update(cash=self.initial_capital, commission=0.0, total=self.initial_capital)
        return holdings

    # --- market data ---------------------------------------------------------

    def update_timeindex(self) -> None:
        """Mark positions to market with the latest bar and record a snapshot."""
        latest_dt = self.data_handler.get_latest_bar_datetime(self.symbol_list[0])
        self.all_positions.append({**self.current_positions, "datetime": latest_dt})

        holdings = {
            "datetime": latest_dt,
            "cash": self.current_holdings["cash"],
            "commission": self.current_holdings["commission"],
            "total": self.current_holdings["cash"],
        }
        for s in self.symbol_list:
            market_value = self.current_positions[s] * self.data_handler.get_latest_bar_value(s, "adj_close")
            holdings[s] = market_value
            holdings["total"] += market_value
        self.all_holdings.append(holdings)

    # --- fills ---------------------------------------------------------------

    def update_fill(self, fill: FillEvent) -> None:
        sign = 1 if fill.direction == "BUY" else -1
        self.current_positions[fill.symbol] += sign * fill.quantity

        cost = sign * fill.fill_cost
        self.current_holdings[fill.symbol] += cost
        self.current_holdings["commission"] += fill.commission
        self.current_holdings["cash"] -= cost + fill.commission
        self.current_holdings["total"] -= cost + fill.commission

    # --- signals -------------------------------------------------------------

    def generate_order(self, signal: SignalEvent) -> OrderEvent | None:
        """Translate a signal into a market order given the current position."""
        quantity = self.current_positions[signal.symbol]
        if signal.signal_type == "LONG" and quantity == 0:
            return OrderEvent(signal.symbol, "MKT", self.lot_size, "BUY")
        if signal.signal_type == "SHORT" and quantity == 0:
            return OrderEvent(signal.symbol, "MKT", self.lot_size, "SELL")
        if signal.signal_type == "EXIT" and quantity != 0:
            return OrderEvent(signal.symbol, "MKT", abs(quantity), "SELL" if quantity > 0 else "BUY")
        return None

    def update_signal(self, signal: SignalEvent) -> None:
        order = self.generate_order(signal)
        if order is not None:
            self.events.put(order)

    # --- results -------------------------------------------------------------

    def create_equity_curve(self) -> pd.DataFrame:
        curve = pd.DataFrame(self.all_holdings).set_index("datetime")
        curve["returns"] = curve["total"].pct_change().fillna(0.0)
        curve["equity_curve"] = (1.0 + curve["returns"]).cumprod()
        self.equity_curve = curve
        return curve

    def summary_stats(self, periods: int = 252) -> dict[str, float]:
        curve = self.equity_curve if self.equity_curve is not None else self.create_equity_curve()
        return summary_stats(curve, periods)

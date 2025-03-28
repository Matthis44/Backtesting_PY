# portfolio.py
import datetime
from math import floor
from collections import defaultdict
import numpy as np
import pandas as pd

from event import FillEvent, OrderEvent
from performance import create_sharpe_ratio, create_drawdowns


class Portfolio:
    """
    Manages positions, holdings, and order generation in response to signals and fills.
    """

    def __init__(self, bars, events, start_date, initial_capital=100000.0):
        self.bars = bars
        self.events = events
        self.symbol_list = bars.symbol_list
        self.start_date = start_date
        self.initial_capital = initial_capital

        self.all_positions = self.construct_all_positions()
        self.current_positions = {s: 0 for s in self.symbol_list}

        self.all_holdings = self.construct_all_holdings()
        self.current_holdings = self.construct_current_holdings()

    def construct_all_positions(self):
        pos = {s: 0 for s in self.symbol_list}
        pos['datetime'] = self.start_date
        return [pos]

    def construct_all_holdings(self):
        hold = {s: 0.0 for s in self.symbol_list}
        hold['datetime'] = self.start_date
        hold['cash'] = self.initial_capital
        hold['commission'] = 0.0
        hold['total'] = self.initial_capital
        return [hold]

    def construct_current_holdings(self):
        hold = {s: 0.0 for s in self.symbol_list}
        hold['cash'] = self.initial_capital
        hold['commission'] = 0.0
        hold['total'] = self.initial_capital
        return hold

    def update_timeindex(self, event):
        """
        Called on a MarketEvent to update positions and holdings with latest bar.
        """
        latest_dt = self.bars.get_latest_bar_datetime(self.symbol_list[0])

        # Update positions
        pos = {s: self.current_positions[s] for s in self.symbol_list}
        pos['datetime'] = latest_dt
        self.all_positions.append(pos)

        # Update holdings
        hold = {s: 0.0 for s in self.symbol_list}
        hold['datetime'] = latest_dt
        hold['cash'] = self.current_holdings['cash']
        hold['commission'] = self.current_holdings['commission']
        hold['total'] = self.current_holdings['cash']

        for s in self.symbol_list:
            market_value = self.current_positions[s] * self.bars.get_latest_bar_value(s, "adj_close")
            hold[s] = market_value
            hold['total'] += market_value

        self.all_holdings.append(hold)

    def update_positions_from_fill(self, fill):
        direction = 1 if fill.direction == 'BUY' else -1
        self.current_positions[fill.symbol] += direction * fill.quantity

    def update_holdings_from_fill(self, fill):
        direction = 1 if fill.direction == 'BUY' else -1
        fill_price = self.bars.get_latest_bar_value(fill.symbol, "adj_close")
        cost = direction * fill_price * fill.quantity

        self.current_holdings[fill.symbol] += cost
        self.current_holdings['commission'] += fill.commission
        self.current_holdings['cash'] -= (cost + fill.commission)
        self.current_holdings['total'] -= (cost + fill.commission)

    def update_fill(self, event):
        if event.type == 'FILL':
            self.update_positions_from_fill(event)
            self.update_holdings_from_fill(event)

    def generate_naive_order(self, signal):
        symbol = signal.symbol
        direction = signal.signal_type
        current_qty = self.current_positions[symbol]
        order_type = 'MKT'
        quantity = 100  # fixed lot size

        if direction == 'LONG' and current_qty == 0:
            return OrderEvent(symbol, order_type, quantity, 'BUY')
        elif direction == 'SHORT' and current_qty == 0:
            return OrderEvent(symbol, order_type, quantity, 'SELL')
        elif direction == 'EXIT':
            if current_qty > 0:
                return OrderEvent(symbol, order_type, abs(current_qty), 'SELL')
            elif current_qty < 0:
                return OrderEvent(symbol, order_type, abs(current_qty), 'BUY')
        return None

    def update_signal(self, event):
        if event.type == 'SIGNAL':
            order = self.generate_naive_order(event)
            if order is not None:
                self.events.put(order)

    def create_equity_curve_dataframe(self):
        """
        Generate equity curve and returns series from holdings.
        """
        curve = pd.DataFrame(self.all_holdings)
        curve.set_index('datetime', inplace=True)
        curve['returns'] = curve['total'].pct_change().fillna(0.0)
        curve['equity_curve'] = (1.0 + curve['returns']).cumprod()
        self.equity_curve = curve

    def output_summary_stats(self):
        """
        Returns a list of portfolio performance statistics.
        """
        total_return = self.equity_curve['equity_curve'].iloc[-1]
        returns = self.equity_curve['returns']
        pnl = self.equity_curve['equity_curve']

        
        
        drawdown, max_dd, dd_duration = create_drawdowns(pnl)
        self.equity_curve['drawdown'] = drawdown
        sharpe = create_sharpe_ratio(returns)

        stats = [
            ("Total Return", f"{(total_return - 1.0) * 100.0:.2f}%"),
            ("Sharpe Ratio", f"{sharpe:.2f}"),
            ("Max Drawdown", f"{max_dd * 100.0:.2f}%"),
            ("Drawdown Duration", f"{dd_duration} bars"),
        ]

        self.equity_curve.to_csv("equity.csv")
        return stats

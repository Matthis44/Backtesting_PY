# backtest.py
import time
import pprint
from queue import Queue

class Backtest:

    """
    The Backtest class orchestrates the entire event-driven backtest:
    - Loads data
    - Runs the event loop (market → signal → order → fill)
    - Tracks and reports performance
    """
    def __init__(
        self,
        symbol_list,
        initial_capital,
        heartbeat,
        start_date,
        data_handler,
        execution_handler,
        portfolio,
        strategy,
        data_source_type="csv",
        data_source_config=None
    ):
        """
        Parameters:
        - data_source_type: "csv" or "mysql"
        - data_source_config: dict of params for the data handler
        """
        self.symbol_list = symbol_list
        self.initial_capital = initial_capital
        self.heartbeat = heartbeat
        self.start_date = start_date
        self.data_handler_cls = data_handler
        self.execution_handler_cls = execution_handler
        self.portfolio_cls = portfolio
        self.strategy_cls = strategy
        self.events = Queue()

        self.data_source_type = data_source_type
        self.data_source_config = data_source_config or {}

        self.signals = 0
        self.orders = 0
        self.fills = 0

        self._generate_trading_instances()


    def _generate_trading_instances(self):
        print("Creating DataHandler, Strategy, Portfolio and ExecutionHandler")

        if self.data_source_type == "csv":
            self.data_handler = self.data_handler_cls(
                self.events,
                self.data_source_config["csv_dir"],
                self.symbol_list
            )
        elif self.data_source_type == "mysql":
            self.data_handler = self.data_handler_cls(
                self.events,
                self.symbol_list,
                **self.data_source_config
            )

        else:
            raise ValueError("Unsupported data source type: %s" % self.data_source_type)

        self.strategy = self.strategy_cls(self.data_handler, self.events)
        self.portfolio = self.portfolio_cls(
            self.data_handler, self.events, self.start_date, self.initial_capital
        )
        self.execution_handler = self.execution_handler_cls(self.events)


    def _run_backtest(self):
        """
        Main event loop: processes the event queue and simulates trading.
        """
        print("Starting backtest...")

        while True:
            # Market heartbeat
            if self.data_handler.continue_backtest:
                self.data_handler.update_bars()
            else:
                break

            # Process events in the queue
            while not self.events.empty():
                event = self.events.get()

                if event is None:
                    continue

                if event.type == 'MARKET':
                    self.strategy.calculate_signals(event)
                    self.portfolio.update_timeindex(event)

                elif event.type == 'SIGNAL':
                    self.signals += 1
                    self.portfolio.update_signal(event)

                elif event.type == 'ORDER':
                    self.orders += 1
                    self.execution_handler.execute_order(event)

                elif event.type == 'FILL':
                    self.fills += 1
                    self.portfolio.update_fill(event)

            time.sleep(self.heartbeat)

    def _output_performance(self):
        """
        Generates and prints performance statistics.
        """
        self.portfolio.create_equity_curve_dataframe()
        print("Final portfolio statistics:\n")

        stats = self.portfolio.output_summary_stats()
        pprint.pprint(stats)

        print("\nEquity curve (last 10 rows):")
        print(self.portfolio.equity_curve.tail(10))

        print(f"\nTotal signals: {self.signals}")
        print(f"Total orders:  {self.orders}")
        print(f"Total fills:   {self.fills}")

    def simulate_trading(self):
        """
        Orchestrates the backtest: run and report results.
        """
        self._run_backtest()
        self._output_performance()

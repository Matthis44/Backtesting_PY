import pandas as pd
import numpy as np
import os
from data import DataHandler
from event import MarketEvent

class HistoricCSVDataHandler(DataHandler):
    """
    Reads CSV files for each requested symbol and provides an interface
    that mimics live data streaming.
    """

    def __init__(self, events, csv_dir, symbol_list):
        self.events = events
        self.csv_dir = csv_dir
        self.symbol_list = symbol_list

        self.symbol_data = {}
        self.latest_symbol_data = {}
        self.continue_backtest = True

        self._open_convert_csv_files()

    def _open_convert_csv_files(self):
        """
        Reads CSVs and converts them into iterators of (datetime, Series) tuples.
        """
        comb_index = None

        for symbol in self.symbol_list:
            path = os.path.join(self.csv_dir, f"{symbol}.csv")
            self.symbol_data[symbol] = pd.read_csv(
                path,
                header=0,
                index_col=0,
                parse_dates=True,
                names=['datetime', 'open', 'high', 'low', 'close', 'volume', 'adj_close']
            ).sort_index()

            if comb_index is None:
                comb_index = self.symbol_data[symbol].index
            else:
                comb_index = comb_index.union(self.symbol_data[symbol].index)

            self.latest_symbol_data[symbol] = []

        for symbol in self.symbol_list:
            self.symbol_data[symbol] = self.symbol_data[symbol] \
                .reindex(index=comb_index, method='pad') \
                .iterrows()

    def _get_new_bar(self, symbol):
        """
        Generator that yields the next bar from the symbol's data.
        """
        for bar in self.symbol_data[symbol]:
            yield bar

    def get_latest_bar(self, symbol):
        try:
            return self.latest_symbol_data[symbol][-1]
        except KeyError:
            raise KeyError(f"Symbol {symbol} not found in historical data.")
        except IndexError:
            raise IndexError(f"No data for symbol {symbol} yet.")

    def get_latest_bars(self, symbol, N=1):
        try:
            return self.latest_symbol_data[symbol][-N:]
        except KeyError:
            raise KeyError(f"Symbol {symbol} not found in historical data.")

    def get_latest_bar_datetime(self, symbol):
        try:
            return self.get_latest_bar(symbol)[0]
        except Exception as e:
            raise RuntimeError(f"Could not get datetime for {symbol}: {str(e)}")

    def get_latest_bar_value(self, symbol, val_type):
        try:
            return self.get_latest_bar(symbol)[1][val_type]
        except Exception as e:
            raise RuntimeError(f"Could not get value '{val_type}' for {symbol}: {str(e)}")

    def get_latest_bars_values(self, symbol, val_type, N=1):
        try:
            bars = self.get_latest_bars(symbol, N)
            return np.array([bar[1][val_type] for bar in bars])
        except Exception as e:
            raise RuntimeError(f"Could not get last {N} values '{val_type}' for {symbol}: {str(e)}")

    def update_bars(self):
        """
        Advances the data by one "tick" for each symbol, generating a MarketEvent.
        """
        for symbol in self.symbol_list:
            try:
                bar = next(self._get_new_bar(symbol))
            except StopIteration:
                self.continue_backtest = False
            else:
                if bar is not None:
                    self.latest_symbol_data[symbol].append(bar)

        self.events.put(MarketEvent())

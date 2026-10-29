"""Historical bars read from one CSV file per symbol."""

from __future__ import annotations

from pathlib import Path
from queue import Queue

import pandas as pd

from backtester.data.base import BAR_COLUMNS, HistoricDataHandler


class HistoricCSVDataHandler(HistoricDataHandler):
    """Reads ``<csv_dir>/<SYMBOL>.csv`` files.

    Expected format: a header row, then ``datetime`` followed by the columns
    ``open, high, low, close, volume, adj_close`` (the format written by
    ``scripts/download_prices.py``).
    """

    def __init__(self, events: Queue, symbol_list: list[str], csv_dir: str | Path):
        self.csv_dir = Path(csv_dir)
        super().__init__(events, symbol_list)

    def load_data(self) -> dict[str, pd.DataFrame]:
        frames = {}
        for symbol in self.symbol_list:
            path = self.csv_dir / f"{symbol}.csv"
            if not path.exists():
                raise FileNotFoundError(f"{path} not found")
            frames[symbol] = pd.read_csv(
                path,
                header=0,
                index_col=0,
                parse_dates=True,
                names=["datetime", *BAR_COLUMNS],
            )
        return frames

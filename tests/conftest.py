from queue import Queue

import numpy as np
import pandas as pd
import pytest

from backtester.data.base import BAR_COLUMNS, HistoricDataHandler


class InMemoryDataHandler(HistoricDataHandler):
    """Replays DataFrames given directly, to test the engine without files."""

    def __init__(self, events, frames: dict[str, pd.DataFrame]):
        self._frames = frames
        super().__init__(events, list(frames))

    def load_data(self):
        return {s: df.copy() for s, df in self._frames.items()}


def make_bars(closes, start="2024-01-01") -> pd.DataFrame:
    closes = np.asarray(closes, dtype=float)
    index = pd.bdate_range(start, periods=len(closes), name="datetime")
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes * 1.01,
            "low": closes * 0.99,
            "close": closes,
            "volume": 1_000,
            "adj_close": closes,
        },
        index=index,
    )[BAR_COLUMNS]


@pytest.fixture
def events():
    return Queue()


@pytest.fixture
def handler_factory(events):
    def factory(**closes_by_symbol):
        frames = {s: make_bars(c) for s, c in closes_by_symbol.items()}
        return InMemoryDataHandler(events, frames)

    return factory

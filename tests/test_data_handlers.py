from queue import Queue

import pandas as pd
import pytest

from backtester.data import HistoricCSVDataHandler
from tests.conftest import InMemoryDataHandler, make_bars


def test_bars_are_published_one_at_a_time(handler_factory, events):
    handler = handler_factory(AAA=[10, 11, 12])

    handler.update_bars()
    assert handler.get_latest_bar_value("AAA", "close") == 10
    assert events.get().type == "MARKET"

    handler.update_bars()
    assert list(handler.get_latest_bars_values("AAA", "close", n=5)) == [10, 11]


def test_backtest_stops_when_data_is_exhausted(handler_factory):
    handler = handler_factory(AAA=[10])
    handler.update_bars()
    assert handler.continue_backtest
    handler.update_bars()
    assert not handler.continue_backtest


def test_symbols_are_aligned_and_forward_filled(events):
    a = make_bars([10, 11, 12])
    b = make_bars([20, 21, 22]).drop(a.index[1])  # B has no bar on day 2
    handler = InMemoryDataHandler(events, {"A": a, "B": b})

    handler.update_bars()
    handler.update_bars()
    assert handler.get_latest_bar_datetime("A") == handler.get_latest_bar_datetime("B")
    assert handler.get_latest_bar_value("B", "close") == 20  # carried forward


def test_missing_columns_are_rejected(events):
    bars = make_bars([1, 2]).drop(columns="adj_close")
    with pytest.raises(ValueError, match="adj_close"):
        InMemoryDataHandler(events, {"A": bars})


def test_csv_handler_reads_files(tmp_path):
    make_bars([1, 2, 3]).to_csv(tmp_path / "XYZ.csv")
    handler = HistoricCSVDataHandler(Queue(), ["XYZ"], tmp_path)
    handler.update_bars()
    assert isinstance(handler.get_latest_bar_datetime("XYZ"), pd.Timestamp)
    assert handler.get_latest_bar_value("XYZ", "adj_close") == 1


def test_csv_handler_reports_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        HistoricCSVDataHandler(Queue(), ["NOPE"], tmp_path)

import numpy as np
import pandas as pd

from scripts.prices import normalise, to_yahoo_ticker, validate
from tests.conftest import make_bars


def test_yahoo_ticker_format():
    assert to_yahoo_ticker("BRK.B") == "BRK-B"
    assert to_yahoo_ticker("AAPL") == "AAPL"


def test_normalise_maps_vendor_columns():
    raw = pd.DataFrame(
        {"Open": [1.0], "High": [2.0], "Low": [0.5], "Close": [1.5], "Adj Close": [1.4], "Volume": [10]},
        index=pd.DatetimeIndex(["2024-01-02 00:00"], tz="America/New_York"),
    )
    df = normalise(raw)
    assert list(df.columns) == ["open", "high", "low", "close", "volume", "adj_close"]
    assert df.index.tz is None


def test_validate_drops_corrupt_rows():
    df = make_bars([10, 11, 12, 13, 14])
    df.iloc[1, df.columns.get_loc("close")] = np.nan  # missing value
    df.iloc[2, df.columns.get_loc("low")] = 99  # low above close
    df.iloc[3, df.columns.get_loc("adj_close")] = -1  # negative price

    clean = validate(df, "TEST")
    assert list(clean["open"]) == [10, 14]

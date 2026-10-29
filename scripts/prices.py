"""Download, normalise and validate daily prices from Yahoo Finance."""

from __future__ import annotations

import logging

import pandas as pd

from backtester.data.base import BAR_COLUMNS

logger = logging.getLogger(__name__)

YAHOO_COLUMNS = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume",
    "Adj Close": "adj_close",
}


def to_yahoo_ticker(ticker: str) -> str:
    """Yahoo uses '-' for share classes (BRK.B -> BRK-B)."""
    return ticker.replace(".", "-")


def normalise(raw: pd.DataFrame) -> pd.DataFrame:
    """Map Yahoo columns to ``BAR_COLUMNS`` and index by a naive date."""
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):  # recent yfinance versions add a ticker level
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=YAHOO_COLUMNS)
    missing = set(BAR_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns from vendor: {sorted(missing)}")
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df.index.name = "datetime"
    return df[BAR_COLUMNS]


def validate(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Drop rows that would corrupt a backtest and log what was removed.

    Rules: no missing values, strictly positive prices, ``low <= open, close <= high``,
    non-negative volume, unique and sorted dates.
    """
    checks = {
        "missing values": df.isna().any(axis=1),
        "non-positive price": (df[["open", "high", "low", "close", "adj_close"]] <= 0).any(axis=1),
        "inconsistent OHLC": (df["low"] > df[["open", "close"]].min(axis=1))
        | (df["high"] < df[["open", "close"]].max(axis=1)),
        "negative volume": df["volume"] < 0,
        "duplicate date": df.index.duplicated(keep="last"),
    }
    bad = pd.Series(False, index=df.index)
    for reason, mask in checks.items():
        mask = pd.Series(mask, index=df.index)
        if mask.any():
            logger.warning("%s: %d rows dropped (%s)", ticker, int(mask.sum()), reason)
        bad |= mask
    return df.loc[~bad].sort_index()


def download_daily_prices(ticker: str, start: str = "2000-01-01", end: str | None = None) -> pd.DataFrame:
    """Download, normalise and validate daily bars for one ticker."""
    import yfinance as yf

    raw = yf.download(to_yahoo_ticker(ticker), start=start, end=end, progress=False, auto_adjust=False)
    if raw.empty:
        raise ValueError(f"No data returned for {ticker}")
    return validate(normalise(raw), ticker)

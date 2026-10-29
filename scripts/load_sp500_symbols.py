"""Load the current S&P 500 constituents into the ``symbol`` table.

The list is scraped from Wikipedia. Reruns update names and sectors instead
of creating duplicates.

    python -m scripts.load_sp500_symbols
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd
import requests

from backtester.config import DatabaseConfig

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
logger = logging.getLogger(__name__)


def fetch_sp500_constituents() -> pd.DataFrame:
    """Return a DataFrame with ``ticker``, ``name`` and ``sector`` columns."""
    html = requests.get(WIKI_URL, headers={"User-Agent": "securities-master/1.0"}, timeout=30).text
    table = pd.read_html(html, attrs={"id": "constituents"})[0]
    df = table.rename(columns={"Symbol": "ticker", "Security": "name", "GICS Sector": "sector"})
    df = df[["ticker", "name", "sector"]].dropna(subset=["ticker"])
    df["ticker"] = df["ticker"].str.strip()
    if df["ticker"].duplicated().any():
        raise ValueError("Duplicate tickers in the scraped list")
    return df


def upsert_symbols(df: pd.DataFrame, config: DatabaseConfig) -> int:
    import mysql.connector

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rows = [(t, "stock", n, s, "USD", now, now) for t, n, s in df.itertuples(index=False)]
    sql = """
        INSERT INTO symbol (ticker, instrument, name, sector, currency, created_date, last_updated_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE name = VALUES(name), sector = VALUES(sector),
                                last_updated_date = VALUES(last_updated_date)
    """
    con = mysql.connector.connect(**config.connector_kwargs())
    try:
        with con.cursor() as cur:
            cur.executemany(sql, rows)
        con.commit()
    finally:
        con.close()
    return len(rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    symbols = fetch_sp500_constituents()
    count = upsert_symbols(symbols, DatabaseConfig.from_env())
    logger.info("%d symbols loaded", count)


if __name__ == "__main__":
    main()

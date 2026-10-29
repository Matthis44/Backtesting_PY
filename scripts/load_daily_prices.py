"""Load daily prices for every symbol of the ``symbol`` table into ``daily_price``.

Rows are upserted on (vendor, symbol, date), so the script can be rerun to
refresh recent prices or to pick up vendor corrections.

    python -m scripts.load_daily_prices --start 2015-01-01
    python -m scripts.load_daily_prices --tickers AAPL MSFT
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone

import pandas as pd

from backtester.config import DatabaseConfig
from scripts.prices import download_daily_prices

logger = logging.getLogger(__name__)

UPSERT_SQL = """
    INSERT INTO daily_price (data_vendor_id, symbol_id, price_date, created_date, last_updated_date,
                             open_price, high_price, low_price, close_price, volume, adj_close_price)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE open_price = VALUES(open_price), high_price = VALUES(high_price),
        low_price = VALUES(low_price), close_price = VALUES(close_price), volume = VALUES(volume),
        adj_close_price = VALUES(adj_close_price), last_updated_date = VALUES(last_updated_date)
"""


def to_rows(df: pd.DataFrame, vendor_id: int, symbol_id: int) -> list[tuple]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return [
        (
            vendor_id,
            symbol_id,
            date.date(),
            now,
            now,
            float(r.open),
            float(r.high),
            float(r.low),
            float(r.close),
            int(r.volume),
            float(r.adj_close),
        )
        for date, r in df.iterrows()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", default="2000-01-01")
    parser.add_argument("--tickers", nargs="*", help="restrict to these tickers")
    parser.add_argument("--vendor", default="Yahoo Finance")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    import mysql.connector

    con = mysql.connector.connect(**DatabaseConfig.from_env().connector_kwargs())
    try:
        with con.cursor() as cur:
            cur.execute("SELECT id FROM data_vendor WHERE name = %s", (args.vendor,))
            (vendor_id,) = cur.fetchone()
            cur.execute("SELECT id, ticker FROM symbol ORDER BY ticker")
            symbols = [(i, t) for i, t in cur.fetchall() if not args.tickers or t in args.tickers]

        failed = []
        for n, (symbol_id, ticker) in enumerate(symbols, start=1):
            try:
                prices = download_daily_prices(ticker, start=args.start)
            except Exception as exc:  # one bad ticker must not stop the whole load
                logger.error("(%d/%d) %s failed: %s", n, len(symbols), ticker, exc)
                failed.append(ticker)
                continue
            with con.cursor() as cur:
                cur.executemany(UPSERT_SQL, to_rows(prices, vendor_id, symbol_id))
            con.commit()
            logger.info("(%d/%d) %s: %d rows", n, len(symbols), ticker, len(prices))
    finally:
        con.close()

    if failed:
        logger.warning("%d tickers failed: %s", len(failed), ", ".join(failed))


if __name__ == "__main__":
    main()

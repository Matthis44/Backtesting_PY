"""Historical bars read from a MySQL securities master database.

The schema is defined in ``scripts/sql/schema.sql`` and populated by the
scripts in ``scripts/``. Requires the ``mysql`` extra
(``pip install -e ".[mysql]"``).
"""

from __future__ import annotations

from queue import Queue

import pandas as pd

from backtester.config import DatabaseConfig
from backtester.data.base import HistoricDataHandler

PRICES_QUERY = """
    SELECT dp.price_date      AS datetime,
           dp.open_price      AS open,
           dp.high_price      AS high,
           dp.low_price       AS low,
           dp.close_price     AS close,
           dp.volume          AS volume,
           dp.adj_close_price AS adj_close
    FROM daily_price dp
    JOIN symbol s ON dp.symbol_id = s.id
    WHERE s.ticker = :symbol
    ORDER BY dp.price_date
"""


class MySQLDataHandler(HistoricDataHandler):
    """Loads daily OHLCV bars for each symbol from the ``daily_price`` table."""

    def __init__(
        self,
        events: Queue,
        symbol_list: list[str],
        db_config: DatabaseConfig | None = None,
        start_date: str | None = None,
    ):
        self.db_config = db_config or DatabaseConfig.from_env()
        self.start_date = pd.Timestamp(start_date) if start_date else None
        super().__init__(events, symbol_list)

    def load_data(self) -> dict[str, pd.DataFrame]:
        from sqlalchemy import create_engine, text

        engine = create_engine(self.db_config.sqlalchemy_url)
        frames = {}
        with engine.connect() as conn:
            for symbol in self.symbol_list:
                df = pd.read_sql(
                    text(PRICES_QUERY), conn, params={"symbol": symbol}, parse_dates=["datetime"]
                ).set_index("datetime")
                if self.start_date is not None:
                    df = df.loc[df.index >= self.start_date]
                frames[symbol] = df
        return frames

"""Download daily prices to CSV files, for backtests without a database.

python -m scripts.download_prices AAPL MSFT --start 2015-01-01 --out data/
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from scripts.prices import download_daily_prices

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tickers", nargs="+")
    parser.add_argument("--start", default="2000-01-01")
    parser.add_argument("--out", type=Path, default=Path("data"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    args.out.mkdir(parents=True, exist_ok=True)
    for ticker in args.tickers:
        prices = download_daily_prices(ticker, start=args.start)
        path = args.out / f"{ticker}.csv"
        prices.to_csv(path)
        logger.info("%s: %d rows -> %s", ticker, len(prices), path)


if __name__ == "__main__":
    main()

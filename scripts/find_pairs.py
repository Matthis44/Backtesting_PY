"""Screen a universe for cointegrated pairs (Engle–Granger).

From CSV files (one per ticker, as written by ``download_prices.py``):

    python -m scripts.find_pairs --csv-dir data/sample

From the MySQL securities master, restricted to one GICS sector so that pairs
share an economic link (testing every pair of the S&P 500 would mostly find
false positives):

    python -m scripts.find_pairs --source mysql --sector Utilities --start 2018-01-01

Candidates should then be checked out of sample before being traded.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from backtester.cointegration import find_cointegrated_pairs

PRICES_BY_SECTOR = """
    SELECT s.ticker, dp.price_date, dp.adj_close_price
    FROM daily_price dp
    JOIN symbol s ON dp.symbol_id = s.id
    WHERE s.sector = :sector AND dp.price_date >= :start
"""


def load_csv(csv_dir: Path) -> pd.DataFrame:
    paths = sorted(csv_dir.glob("*.csv"))
    series = {path.stem: pd.read_csv(path, index_col=0, parse_dates=True)["adj_close"] for path in paths}
    if len(series) < 2:
        raise SystemExit(f"Need at least two CSV files in {csv_dir}")
    return pd.DataFrame(series)


def load_mysql(sector: str, start: str) -> pd.DataFrame:
    from sqlalchemy import create_engine, text

    from backtester.config import DatabaseConfig

    engine = create_engine(DatabaseConfig.from_env().sqlalchemy_url)
    with engine.connect() as conn:
        rows = pd.read_sql(text(PRICES_BY_SECTOR), conn, params={"sector": sector, "start": start})
    return rows.pivot(index="price_date", columns="ticker", values="adj_close_price")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", choices=["csv", "mysql"], default="csv")
    parser.add_argument("--csv-dir", type=Path, default=Path("data/sample"))
    parser.add_argument("--sector", help="GICS sector (MySQL source)")
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--min-coverage", type=float, default=0.95, help="drop tickers with less history than this")
    parser.add_argument("--level", choices=["1%", "5%", "10%"], default="5%")
    args = parser.parse_args()

    if args.source == "mysql":
        if not args.sector:
            parser.error("--sector is required with --source mysql")
        prices = load_mysql(args.sector, args.start)
    else:
        prices = load_csv(args.csv_dir)

    prices = prices.loc[:, prices.notna().mean() >= args.min_coverage].ffill().dropna()
    pairs = find_cointegrated_pairs(prices, level=args.level)
    print(f"{prices.shape[1]} tickers, {len(prices)} days, {len(pairs)} cointegrated pairs at {args.level}\n")
    if not pairs.empty:
        print(pairs.round({"hedge_ratio": 3, "adf_stat": 2, "half_life": 1}).to_string(index=False))


if __name__ == "__main__":
    main()

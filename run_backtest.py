"""Run a moving average crossover backtest from the command line.

Examples:
    python run_backtest.py                                    # bundled synthetic sample
    python run_backtest.py --source csv --csv-dir data AAPL MSFT
    python run_backtest.py --source mysql AAPL --start 2010-01-01
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from queue import Queue

import pandas as pd

from backtester import Backtest
from backtester.data import HistoricCSVDataHandler
from backtester.strategies import MovingAverageCrossStrategy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("symbols", nargs="*", default=["SYNTH"])
    parser.add_argument("--source", choices=["csv", "mysql"], default="csv")
    parser.add_argument("--csv-dir", type=Path, default=Path("data/sample"))
    parser.add_argument("--start", help="first date (MySQL source)")
    parser.add_argument("--capital", type=float, default=100_000.0)
    parser.add_argument("--short", type=int, default=40, help="short SMA window")
    parser.add_argument("--long", type=int, default=100, help="long SMA window")
    parser.add_argument("--output", type=Path, default=Path("results/equity_curve.csv"))
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")

    events: Queue = Queue()
    if args.source == "mysql":
        from backtester.data.mysql_handler import MySQLDataHandler

        data = MySQLDataHandler(events, args.symbols, start_date=args.start)
    else:
        data = HistoricCSVDataHandler(events, args.symbols, args.csv_dir)

    result = Backtest(
        data,
        MovingAverageCrossStrategy,
        events=events,
        initial_capital=args.capital,
        start_date=pd.Timestamp(args.start) if args.start else None,
        strategy_params={"short_window": args.short, "long_window": args.long},
    ).run()

    stats = result.stats
    print(f"\nTotal return     {stats['total_return']:>9.2%}")
    print(f"Sharpe ratio     {stats['sharpe_ratio']:>9.2f}")
    print(f"Max drawdown     {stats['max_drawdown']:>9.2%}")
    print(f"Longest drawdown {stats['max_drawdown_duration']:>6d} bars")
    print(f"Trades           {result.fills:>9d}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.equity_curve.iloc[1:].to_csv(args.output)
    print(f"\nEquity curve saved to {args.output}")


if __name__ == "__main__":
    main()

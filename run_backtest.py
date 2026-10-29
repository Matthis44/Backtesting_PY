"""Run a backtest from the command line.

Examples:
    python run_backtest.py                                    # moving average crossover, synthetic sample
    python run_backtest.py --strategy mean_reversion          # z-score mean reversion
    python run_backtest.py --strategy pairs                   # pairs trading on the cointegrated sample pair
    python run_backtest.py --source csv --csv-dir data AAPL MSFT
    python run_backtest.py --source mysql --strategy pairs KO PEP --start 2015-01-01
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from queue import Queue

import pandas as pd

from backtester import Backtest
from backtester.data import HistoricCSVDataHandler
from backtester.strategies import MeanReversionStrategy, MovingAverageCrossStrategy, PairsTradingStrategy

DEFAULT_SYMBOLS = {"ma_cross": ["SYNTH"], "mean_reversion": ["SYNTH"], "pairs": ["PAIR_Y", "PAIR_X"]}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("symbols", nargs="*", help="for pairs: Y then X (default: the synthetic sample)")
    parser.add_argument("--strategy", choices=sorted(DEFAULT_SYMBOLS), default="ma_cross")
    parser.add_argument("--source", choices=["csv", "mysql"], default="csv")
    parser.add_argument("--csv-dir", type=Path, default=Path("data/sample"))
    parser.add_argument("--start", help="first date (MySQL source)")
    parser.add_argument("--capital", type=float, default=100_000.0)
    parser.add_argument("--short", type=int, default=40, help="short SMA window")
    parser.add_argument("--long", type=int, default=100, help="long SMA window")
    parser.add_argument("--lookback", type=int, help="z-score window (default 20 for mean_reversion, 60 for pairs)")
    parser.add_argument("--entry-z", type=float, default=2.0, help="z-score that opens a position")
    parser.add_argument("--exit-z", type=float, default=0.5, help="z-score that closes it")
    parser.add_argument("--output", type=Path, default=Path("results/equity_curve.csv"))
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.symbols = args.symbols or DEFAULT_SYMBOLS[args.strategy]
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")

    events: Queue = Queue()
    if args.source == "mysql":
        from backtester.data.mysql_handler import MySQLDataHandler

        data = MySQLDataHandler(events, args.symbols, start_date=args.start)
    else:
        data = HistoricCSVDataHandler(events, args.symbols, args.csv_dir)

    if args.strategy == "ma_cross":
        strategy_cls, params = MovingAverageCrossStrategy, {"short_window": args.short, "long_window": args.long}
    else:
        strategy_cls = MeanReversionStrategy if args.strategy == "mean_reversion" else PairsTradingStrategy
        lookback = args.lookback or (20 if args.strategy == "mean_reversion" else 60)
        params = {"lookback": lookback, "entry_z": args.entry_z, "exit_z": args.exit_z}

    result = Backtest(
        data,
        strategy_cls,
        events=events,
        initial_capital=args.capital,
        start_date=pd.Timestamp(args.start) if args.start else None,
        strategy_params=params,
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

# Event-driven backtester & securities master

[![tests](https://github.com/Matthis44/backtesting-py/actions/workflows/tests.yml/badge.svg)](https://github.com/Matthis44/backtesting-py/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A Python backtesting engine for equity strategies (trend following, mean reversion and
cointegration-based pairs trading), fed by a small **securities master**:
a MySQL database of reference data (S&P 500 constituents, data vendors) and validated
daily prices, loaded by idempotent scripts.

The engine is **event-driven**: bars are replayed one at a time and every component
reacts to events on a single queue, the same way it would in live trading. This makes
look-ahead bias structurally impossible and lets the same strategy code run on
historical or live data.

![Example backtest](docs/example_backtest.png)

## Highlights

- **Data pipeline**: S&P 500 constituents scraped from Wikipedia, daily OHLCV and
  adjusted prices from Yahoo Finance, normalised and validated before loading.
- **Data quality checks**: rows with missing values, non-positive prices, inconsistent
  OHLC (`low > close`, `high < open`…), negative volume or duplicate dates are dropped
  and logged per ticker.
- **Idempotent loads**: unique keys on `(vendor, symbol, date)` and upserts, so a reload
  refreshes prices instead of duplicating them.
- **Strategies**: moving average crossover, z-score mean reversion (long and short), and
  pairs trading on a rolling hedge ratio, with both legs sized by the hedge ratio.
- **Cointegration from scratch**: Engle–Granger test (OLS + augmented Dickey–Fuller on
  the residuals), unit-root pre-check, half-life of mean reversion and a pair screener by
  GICS sector; the test statistic matches `statsmodels` to 1e-8 in the test suite.
- **Pluggable components**: data handlers (CSV, MySQL, live Binance stream), strategies
  and execution share abstract interfaces.
- **Multi-asset alignment**: symbols are aligned on a common calendar and gaps are
  forward-filled.
- **Performance analytics**: annualised Sharpe ratio, drawdown relative to the
  high-water mark, longest drawdown duration.
- **Tested**: 31 unit and end-to-end tests (P&L checked by hand), linting, CI on
  Python 3.10 to 3.13.

## Architecture

```
            ┌──────────────┐  MARKET   ┌──────────┐  SIGNAL   ┌───────────┐
 prices ──▶ │ DataHandler  │ ────────▶ │ Strategy │ ────────▶ │ Portfolio │
            │ CSV / MySQL  │           └──────────┘           │ positions │
            └──────────────┘                                  │ holdings  │
                   ▲                                          └───────────┘
                   │ latest bars        ┌───────────────────┐   │ ORDER  ▲ FILL
                   └─────────────────── │ ExecutionHandler  │ ◀─┘        │
                                        │ (simulated fills) │ ───────────┘
                                        └───────────────────┘
```

For every bar the data handler publishes it, then all resulting events are processed
before the next bar is released.

| Module | Role |
|---|---|
| `backtester/data/` | `HistoricDataHandler` (replay, alignment), CSV and MySQL loaders, experimental Binance WebSocket handler |
| `backtester/strategies/` | `Strategy` interface, moving average crossover, mean reversion, pairs trading |
| `backtester/cointegration.py` | Engle–Granger test, ADF statistic, half-life, pair screening |
| `backtester/portfolio.py` | positions, mark-to-market holdings, order sizing, equity curve |
| `backtester/execution.py` | simulated execution with Interactive Brokers style commissions |
| `backtester/performance.py` | Sharpe ratio and drawdown statistics |
| `scripts/` | securities master: schema, symbol and price loaders, CSV export, pair screener, sample data |

## Quick start

```bash
git clone https://github.com/Matthis44/backtesting-py.git
cd backtesting-py
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

python run_backtest.py                      # moving average crossover on the synthetic sample
python run_backtest.py --short 20 --long 50
python run_backtest.py --strategy mean_reversion --lookback 20 --entry-z 2
python run_backtest.py --strategy pairs     # pairs trading on the cointegrated sample pair
python -m scripts.find_pairs                # cointegration screen of data/sample/
pytest
```

The samples in `data/sample/` are reproducible synthetic series, so the project runs
offline: `SYNTH` is a geometric Brownian motion, and `PAIR_X` / `PAIR_Y` a cointegrated
pair (`Y = 10 + 1.5 X + spread`, the spread being an Ornstein–Uhlenbeck process). They are
**not** market data.

## Mean reversion and pairs trading

**Mean reversion** fades large moves of a single asset: with `z` the distance of the price
from its rolling mean in rolling standard deviations, it buys when `z < -2`, sells short
when `z > 2` and closes once `|z| < 0.5`.

**Pairs trading** applies the same idea to the spread `Y - beta X` of two assets that are
**cointegrated**, i.e. whose prices wander but never drift apart for long. On every bar the
hedge ratio `beta` is re-estimated by OLS on the last 60 bars (past data only), the spread
is turned into a z-score, and the strategy sells `Y` / buys `beta` units of `X` when the
spread is rich, the reverse when it is cheap.

Finding the pairs is the hard part. `backtester.cointegration` implements the
**Engle–Granger** test: regress `Y` on `X`, then run an augmented Dickey–Fuller test on the
residuals. Two details matter in practice:

- series that are already stationary are excluded first, since they pass the test with
  almost any partner;
- testing every pair of a universe multiplies false positives (about 5% of unrelated pairs
  pass at the 5% level, which the test suite checks), so the screener works within one
  GICS sector and candidates should be confirmed out of sample.

```bash
python -m scripts.find_pairs --source mysql --sector Utilities --start 2018-01-01
python run_backtest.py --source mysql --strategy pairs <Y> <X> --start 2021-01-01
```

### With real prices (CSV)

```bash
pip install -e ".[data]"
python -m scripts.download_prices AAPL MSFT --start 2015-01-01 --out data/
python run_backtest.py --csv-dir data AAPL MSFT
```

### With the MySQL securities master

```bash
pip install -e ".[data,mysql]"
cp .env.example .env                        # then set your MySQL credentials
mysql -u root -p < scripts/sql/schema.sql   # tables + Yahoo vendor
python -m scripts.load_sp500_symbols        # ~500 symbols
python -m scripts.load_daily_prices --start 2010-01-01
python run_backtest.py --source mysql AAPL --start 2015-01-01
```

## Database schema

| Table | Content | Key constraints |
|---|---|---|
| `data_vendor` | price sources | unique name |
| `symbol` | ticker, instrument type, name, GICS sector, currency | unique ticker |
| `daily_price` | OHLC, adjusted close, volume per vendor, symbol and date | unique `(vendor, symbol, date)`, index on `(symbol, date)` |

## Simplifying assumptions

These are deliberate and documented so results are read correctly:

- orders are filled immediately at the adjusted close of the signal bar, with no slippage
  or partial fills;
- position size is a fixed lot (100 shares by default), scaled by the hedge ratio for the
  second leg of a pair; short sales carry no borrow cost;
- the S&P 500 list is today's composition, so a backtest over past years carries
  **survivorship bias**.

## Possible extensions

Point-in-time index membership to remove survivorship bias, a slippage and market impact
model, volatility-based position sizing, a Kalman filter for a time-varying hedge ratio,
Johansen test for baskets of more than two assets, intraday bars, Parquet storage.

## License

MIT

"""Generate the synthetic samples in ``data/sample/`` so the project runs offline.

- ``SYNTH.csv``: a geometric Brownian motion;
- ``PAIR_X.csv`` and ``PAIR_Y.csv``: a cointegrated pair, ``Y = 10 + 1.5 X + spread``
  where the spread is a mean-reverting Ornstein–Uhlenbeck process.

Every generator is seeded, so the files are reproducible. They are NOT market
data: use ``download_prices.py`` for real prices.

    python -m scripts.make_sample_data
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def synthetic_prices(
    n_days: int = 2520, s0: float = 100.0, mu: float = 0.07, sigma: float = 0.2, seed: int = 7
) -> pd.DataFrame:
    """Daily OHLCV bars following a geometric Brownian motion (about 10 years by default)."""
    rng = np.random.default_rng(seed)
    dt = 1 / 252
    log_returns = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * rng.standard_normal(n_days)
    close = s0 * np.exp(np.cumsum(log_returns))
    open_ = np.concatenate([[s0], close[:-1]]) * (1 + 0.002 * rng.standard_normal(n_days))
    spread = np.abs(0.01 * rng.standard_normal(n_days))
    high = np.maximum(open_, close) * (1 + spread)
    low = np.minimum(open_, close) * (1 - spread)
    volume = rng.integers(1_000_000, 5_000_000, n_days)

    index = pd.bdate_range("2014-01-02", periods=n_days, name="datetime")
    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume, "adj_close": close},
        index=index,
    )
    return df.round(4)


def to_bars(close: np.ndarray, rng: np.random.Generator, s0: float) -> pd.DataFrame:
    """Daily OHLCV bars around a close series."""
    n_days = len(close)
    open_ = np.concatenate([[s0], close[:-1]]) * (1 + 0.002 * rng.standard_normal(n_days))
    spread = np.abs(0.01 * rng.standard_normal(n_days))
    high = np.maximum(open_, close) * (1 + spread)
    low = np.minimum(open_, close) * (1 - spread)
    volume = rng.integers(1_000_000, 5_000_000, n_days)
    index = pd.bdate_range("2014-01-02", periods=n_days, name="datetime")
    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume, "adj_close": close},
        index=index,
    )
    return df.round(4)


def cointegrated_pair(
    n_days: int = 2520, beta: float = 1.5, theta: float = 0.05, spread_vol: float = 0.5, seed: int = 6
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Bars for ``X`` (a GBM) and ``Y = 10 + beta * X + OU spread`` (half-life ln2 / theta bars)."""
    rng = np.random.default_rng(seed)
    x = synthetic_prices(n_days=n_days, s0=50.0, mu=0.0, sigma=0.2, seed=seed)["close"].to_numpy()
    spread = np.zeros(n_days)
    for t in range(1, n_days):
        spread[t] = (1 - theta) * spread[t - 1] + spread_vol * rng.standard_normal()
    y = 10 + beta * x + spread
    return to_bars(x, rng, x[0]), to_bars(y, rng, y[0])


def main() -> None:
    out = Path("data/sample")
    out.mkdir(parents=True, exist_ok=True)
    synthetic_prices().to_csv(out / "SYNTH.csv")
    pair_x, pair_y = cointegrated_pair()
    pair_x.to_csv(out / "PAIR_X.csv")
    pair_y.to_csv(out / "PAIR_Y.csv")
    print(f"Wrote SYNTH.csv, PAIR_X.csv and PAIR_Y.csv to {out}")


if __name__ == "__main__":
    main()

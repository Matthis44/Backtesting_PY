"""Generate the synthetic sample in ``data/sample/`` so the project runs offline.

Prices follow a geometric Brownian motion with a seeded generator, so the
file is reproducible. It is NOT market data: use ``download_prices.py`` for
real prices.

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


def main() -> None:
    out = Path("data/sample")
    out.mkdir(parents=True, exist_ok=True)
    synthetic_prices().to_csv(out / "SYNTH.csv")
    print(f"Wrote {out / 'SYNTH.csv'}")


if __name__ == "__main__":
    main()

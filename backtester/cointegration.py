"""Cointegration tools for pairs trading, written with NumPy only.

The Engle–Granger two-step test:

1. regress ``y`` on ``x`` by OLS, ``y = alpha + beta * x + e``;
2. run an augmented Dickey–Fuller regression on the residuals ``e`` (no constant,
   since the residuals already have zero mean). A t-statistic below the
   critical value rejects the unit root: the spread mean-reverts and the pair is
   cointegrated.

The t-statistic matches ``statsmodels.tsa.stattools.coint`` with a fixed number
of lags (checked in the tests). Critical values are MacKinnon's asymptotic values
for two variables with a constant; they are slightly too lenient on short samples.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
import pandas as pd

#: MacKinnon (2010) asymptotic critical values, Engle–Granger test, 2 variables, constant.
EG_CRITICAL_VALUES = {"1%": -3.89644, "5%": -3.33613, "10%": -3.04445}
#: MacKinnon (2010) asymptotic critical values, ADF unit-root test with a constant.
ADF_CRITICAL_VALUES = {"1%": -3.43035, "5%": -2.86154, "10%": -2.56677}


@dataclass(frozen=True)
class CointegrationResult:
    alpha: float
    hedge_ratio: float
    adf_stat: float
    critical_values: dict[str, float]
    half_life: float
    n_obs: int

    def is_cointegrated(self, level: str = "5%") -> bool:
        return self.adf_stat < self.critical_values[level]


def ols(y: np.ndarray, x: np.ndarray) -> tuple[float, float, np.ndarray]:
    """Intercept, slope and residuals of ``y = alpha + beta * x``."""
    y, x = np.asarray(y, dtype=float), np.asarray(x, dtype=float)
    design = np.column_stack([np.ones_like(x), x])
    (alpha, beta), *_ = np.linalg.lstsq(design, y, rcond=None)
    return float(alpha), float(beta), y - alpha - beta * x


def adf_stat(series: np.ndarray, lags: int = 1, constant: bool = False) -> float:
    """t-statistic of ``gamma`` in ``d(s_t) = [c +] gamma * s_{t-1} + sum_i phi_i * d(s_{t-i}) + u_t``."""
    s = np.asarray(series, dtype=float)
    ds = np.diff(s)
    n = len(ds) - lags
    if n <= lags + 2:
        raise ValueError("Series too short for the requested number of lags")

    columns = [s[lags:-1]]  # s_{t-1}
    columns += [ds[lags - i : len(ds) - i] for i in range(1, lags + 1)]  # lagged differences
    if constant:
        columns.append(np.ones(n))
    design = np.column_stack(columns)
    target = ds[lags:]

    coef, *_ = np.linalg.lstsq(design, target, rcond=None)
    resid = target - design @ coef
    sigma2 = resid @ resid / (n - design.shape[1])
    cov = sigma2 * np.linalg.inv(design.T @ design)
    return float(coef[0] / np.sqrt(cov[0, 0]))


def has_unit_root(series: np.ndarray | pd.Series, lags: int = 1, level: str = "5%") -> bool:
    """ADF test with a constant: ``True`` when the unit root is not rejected (the series is I(1)).

    Cointegration only makes sense between non-stationary series: a series that is
    already stationary passes the Engle–Granger test with almost any partner.
    """
    return adf_stat(np.asarray(series, dtype=float), lags=lags, constant=True) >= ADF_CRITICAL_VALUES[level]


def half_life(spread: np.ndarray) -> float:
    """Half-life of mean reversion, in bars, from an AR(1) fit of the spread.

    Returns ``inf`` when the spread does not mean-revert.
    """
    s = np.asarray(spread, dtype=float)
    _, lam, _ = ols(np.diff(s), s[:-1])
    return float(-np.log(2) / lam) if lam < 0 else float("inf")


def engle_granger(y: np.ndarray | pd.Series, x: np.ndarray | pd.Series, lags: int = 1) -> CointegrationResult:
    """Engle–Granger cointegration test of ``y`` on ``x``."""
    y, x = np.asarray(y, dtype=float), np.asarray(x, dtype=float)
    if y.shape != x.shape:
        raise ValueError("y and x must have the same length")
    if np.isnan(y).any() or np.isnan(x).any():
        raise ValueError("Missing values: align and clean the series first")

    alpha, beta, resid = ols(y, x)
    return CointegrationResult(
        alpha=alpha,
        hedge_ratio=beta,
        adf_stat=adf_stat(resid, lags=lags),
        critical_values=dict(EG_CRITICAL_VALUES),
        half_life=half_life(resid),
        n_obs=len(y),
    )


def find_cointegrated_pairs(prices: pd.DataFrame, lags: int = 1, level: str = "5%") -> pd.DataFrame:
    """Test every pair of columns of ``prices`` and return the cointegrated ones.

    Series that are already stationary are excluded first (see :func:`has_unit_root`).
    Both orderings are tested (the Engle–Granger test is not symmetric) and the one
    with the lower statistic is kept. Results are sorted from the strongest pair.

    Testing many pairs multiplies false positives (about 5% of unrelated pairs pass at
    the 5% level), so a candidate should be confirmed out of sample before trading it.
    """
    prices = prices.dropna()
    candidates_cols = [c for c in prices.columns if has_unit_root(prices[c], lags, level)]
    rows = []
    for a, b in combinations(candidates_cols, 2):
        tests = [(a, b, engle_granger(prices[a], prices[b], lags)), (b, a, engle_granger(prices[b], prices[a], lags))]
        y, x, res = min(tests, key=lambda c: c[2].adf_stat)
        if res.is_cointegrated(level):
            rows.append(
                {"y": y, "x": x, "hedge_ratio": res.hedge_ratio, "adf_stat": res.adf_stat, "half_life": res.half_life}
            )
    columns = ["y", "x", "hedge_ratio", "adf_stat", "half_life"]
    return pd.DataFrame(rows, columns=columns).sort_values("adf_stat").reset_index(drop=True)

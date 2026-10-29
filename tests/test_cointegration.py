import numpy as np
import pandas as pd
import pytest

from backtester.cointegration import adf_stat, engle_granger, find_cointegrated_pairs, half_life, has_unit_root, ols


def random_walk(n, seed):
    return 100 + np.cumsum(np.random.default_rng(seed).standard_normal(n))


def ou_process(n, theta, seed, sigma=1.0):
    rng = np.random.default_rng(seed)
    s = np.zeros(n)
    for t in range(1, n):
        s[t] = (1 - theta) * s[t - 1] + sigma * rng.standard_normal()
    return s


def test_ols_recovers_exact_line():
    x = np.arange(10.0)
    alpha, beta, resid = ols(3 + 2 * x, x)
    assert (alpha, beta) == pytest.approx((3, 2))
    assert np.allclose(resid, 0)


def test_cointegrated_pair_is_detected():
    x = random_walk(1500, seed=1)
    y = 5 + 1.5 * x + ou_process(1500, theta=0.1, seed=2)
    result = engle_granger(y, x)
    assert result.is_cointegrated("1%")
    assert result.hedge_ratio == pytest.approx(1.5, abs=0.05)


def test_independent_random_walks_are_not_cointegrated():
    rejections = sum(
        engle_granger(random_walk(1000, seed=s), random_walk(1000, seed=s + 500)).is_cointegrated() for s in range(100)
    )
    assert rejections <= 12  # about 5% expected at the 5% level


def test_half_life_matches_ou_parameter():
    theta = 0.05
    assert half_life(ou_process(20_000, theta, seed=3)) == pytest.approx(np.log(2) / theta, rel=0.15)
    assert half_life(100 * 1.01 ** np.arange(100)) == float("inf")  # explosive, no mean reversion


def test_unit_root_check():
    assert has_unit_root(random_walk(1000, seed=4))
    assert not has_unit_root(ou_process(1000, theta=0.2, seed=5))


def test_screen_keeps_only_the_linked_pair():
    x = random_walk(1500, seed=6)
    prices = pd.DataFrame(
        {
            "X": x,
            "Y": 5 + 1.5 * x + ou_process(1500, theta=0.1, seed=7),
            "Z": random_walk(1500, seed=8),
            "STATIONARY": 50 + ou_process(1500, theta=0.3, seed=9),  # would pass with anything
        }
    )
    pairs = find_cointegrated_pairs(prices)
    assert len(pairs) == 1
    assert set(pairs.loc[0, ["y", "x"]]) == {"X", "Y"}


@pytest.mark.filterwarnings("ignore::FutureWarning")
def test_matches_statsmodels():
    stattools = pytest.importorskip("statsmodels.tsa.stattools")
    x = random_walk(800, seed=10)
    y = 2 + 0.8 * x + ou_process(800, theta=0.05, seed=11)
    for lags in (0, 1, 3):
        expected, _, _ = stattools.coint(y, x, trend="c", maxlag=lags, autolag=None)
        assert engle_granger(y, x, lags=lags).adf_stat == pytest.approx(expected, rel=1e-8)
        s = random_walk(500, seed=lags)
        assert adf_stat(s, lags=lags, constant=True) == pytest.approx(
            stattools.adfuller(s, maxlag=lags, autolag=None, regression="c")[0], rel=1e-8
        )

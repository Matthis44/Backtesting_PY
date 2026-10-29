import math

import numpy as np
import pandas as pd
import pytest

from backtester.performance import drawdowns, sharpe_ratio


def test_sharpe_matches_definition():
    returns = pd.Series([0.01, -0.005, 0.002, 0.007, -0.001])
    expected = np.sqrt(252) * returns.mean() / returns.std(ddof=1)
    assert sharpe_ratio(returns) == pytest.approx(expected)


def test_sharpe_is_nan_without_volatility():
    assert math.isnan(sharpe_ratio(pd.Series([0.01, 0.01, 0.01])))


def test_drawdown_is_relative_to_peak():
    equity = pd.Series([1.0, 1.2, 0.9, 1.0, 1.3, 1.1])
    drawdown, max_dd, duration = drawdowns(equity)

    assert max_dd == pytest.approx(0.25)  # 1.2 -> 0.9
    assert drawdown.iloc[-1] == pytest.approx(1 - 1.1 / 1.3)
    assert duration == 2  # two bars below the 1.2 peak


def test_no_drawdown_on_rising_curve():
    _, max_dd, duration = drawdowns(pd.Series([1.0, 1.1, 1.2]))
    assert max_dd == 0
    assert duration == 0

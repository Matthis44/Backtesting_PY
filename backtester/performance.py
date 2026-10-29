"""Performance statistics computed on an equity curve."""

from __future__ import annotations

import numpy as np
import pandas as pd


def sharpe_ratio(returns: pd.Series, periods: int = 252, risk_free_rate: float = 0.0) -> float:
    """Annualised Sharpe ratio of a series of periodic returns.

    ``periods`` is the number of periods per year (252 for daily bars).
    ``risk_free_rate`` is annual. Returns ``nan`` when volatility is zero.
    """
    excess = returns - risk_free_rate / periods
    std = excess.std(ddof=1)
    if not np.isfinite(std) or std == 0:
        return float("nan")
    return float(np.sqrt(periods) * excess.mean() / std)


def drawdowns(equity_curve: pd.Series) -> tuple[pd.Series, float, int]:
    """Drawdown series, maximum drawdown and longest drawdown duration.

    The drawdown is expressed as a fraction of the running peak
    (``0.25`` means 25% below the high-water mark); the duration is counted
    in bars.
    """
    high_water_mark = equity_curve.cummax()
    drawdown = 1.0 - equity_curve / high_water_mark

    underwater = drawdown > 0
    # Each return to the high-water mark starts a new group; count bars within it.
    groups = (~underwater).cumsum()
    duration = underwater.groupby(groups).cumsum()

    return drawdown, float(drawdown.max()), int(duration.max())


def summary_stats(equity: pd.DataFrame, periods: int = 252) -> dict[str, float]:
    """Key statistics for a curve with ``returns`` and ``equity_curve`` columns."""
    _, max_dd, dd_duration = drawdowns(equity["equity_curve"])
    return {
        "total_return": float(equity["equity_curve"].iloc[-1] - 1.0),
        "sharpe_ratio": sharpe_ratio(equity["returns"], periods),
        "max_drawdown": max_dd,
        "max_drawdown_duration": dd_duration,
    }

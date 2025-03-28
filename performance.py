# performance.py
import numpy as np
import pandas as pd


def create_sharpe_ratio(returns, periods=252):
    """
    Calculate the annualised Sharpe ratio of a return series.
    Assumes a risk-free rate of 0.

    Parameters:
    - returns : pd.Series
        Series of periodic returns (e.g., daily, minute)
    - periods : int
        Number of periods per year (252 for daily, 252*6.5 for hourly, etc.)

    Returns:
    - sharpe_ratio : float
    """
    excess_returns = returns - 0.0
    return np.sqrt(periods) * np.mean(excess_returns) / np.std(excess_returns)


def create_drawdowns(equity_curve):
    """
    Calculate drawdowns and drawdown durations.

    Parameters:
    - equity_curve : pd.Series
        Cumulative returns or portfolio value over time.

    Returns:
    - drawdown : pd.Series
        Series of drawdown values at each time index.
    - max_drawdown : float
        Maximum drawdown value.
    - max_duration : int
        Longest duration of a drawdown.
    """
    # High Water Mark (running max of the equity curve)
    hwm = [0]
    drawdown = pd.Series(index=equity_curve.index, dtype=float)
    duration = pd.Series(index=equity_curve.index, dtype=int)

    for t in range(1, len(equity_curve)):
        hwm.append(max(hwm[t - 1], equity_curve.iloc[t]))
        drawdown.iloc[t] = hwm[t] - equity_curve.iloc[t]
        duration.iloc[t] = 0 if drawdown.iloc[t] == 0 else duration.iloc[t - 1] + 1

    return drawdown, drawdown.max(), duration.max()

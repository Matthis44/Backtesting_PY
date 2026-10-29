import numpy as np
import pytest

from backtester import Backtest
from backtester.events import SignalEvent
from backtester.portfolio import Portfolio
from backtester.strategies import MeanReversionStrategy, PairsTradingStrategy


def run_signals(handler, strategy, events):
    """Replay every bar and return the signals as (symbol, type, strength) tuples."""
    signals = []
    while True:
        handler.update_bars()
        if not handler.continue_backtest:
            return signals
        while not events.empty():
            event = events.get()
            if isinstance(event, SignalEvent):
                signals.append((event.symbol, event.signal_type, round(event.strength, 3)))
            else:
                strategy.calculate_signals(event)


def test_mean_reversion_buys_the_dip_and_exits(handler_factory, events):
    prices = [10, 10.2, 9.8, 10.1, 9.9] * 2 + [8, 8.5, 10, 10]
    handler = handler_factory(AAA=prices)
    strategy = MeanReversionStrategy(handler, events, lookback=10, entry_z=1.5, exit_z=0.5)
    assert run_signals(handler, strategy, events) == [("AAA", "LONG", 1.0), ("AAA", "EXIT", 1.0)]


def test_mean_reversion_shorts_spikes_unless_long_only(handler_factory, events):
    prices = [10, 10.2, 9.8, 10.1, 9.9] * 2 + [12, 11.5, 10, 10]
    handler = handler_factory(AAA=prices)
    signals = run_signals(handler, MeanReversionStrategy(handler, events, 10, 1.5), events)
    assert signals == [("AAA", "SHORT", 1.0), ("AAA", "EXIT", 1.0)]

    handler = handler_factory(AAA=prices)
    assert run_signals(handler, MeanReversionStrategy(handler, events, 10, 1.5, allow_short=False), events) == []


def test_pairs_trades_both_legs_with_hedge_ratio(handler_factory, events):
    x = np.linspace(50, 60, 40)
    noise = np.tile([0.1, -0.1], 20)
    y = 2 * x + noise
    y[30] += 3  # the spread widens: sell Y, buy X
    handler = handler_factory(Y=y, X=x)
    strategy = PairsTradingStrategy(handler, events, lookback=20, entry_z=2.0, exit_z=0.5)
    signals = run_signals(handler, strategy, events)

    # The X leg is sized by the estimated hedge ratio (about 2)
    assert signals[:2] == [("Y", "SHORT", 1.0), ("X", "LONG", pytest.approx(2.0, abs=0.25))]
    assert [s[1] for s in signals[2:4]] == ["EXIT", "EXIT"]


def test_pairs_rejects_unknown_symbols(handler_factory, events):
    with pytest.raises(ValueError):
        PairsTradingStrategy(handler_factory(Y=[1, 2, 3], X=[1, 2, 3]), events, pair=("Y", "Z"))


def test_signal_strength_scales_the_order(handler_factory, events):
    handler = handler_factory(AAA=[10, 11])
    handler.update_bars()
    portfolio = Portfolio(handler, events, start_date=None, lot_size=100)
    order = portfolio.generate_order(SignalEvent("test", "AAA", None, "LONG", strength=1.5))
    assert order.quantity == 150


def test_pairs_end_to_end_profits_on_a_cointegrated_pair(handler_factory, events):
    rng = np.random.default_rng(0)
    x = 50 + np.cumsum(rng.standard_normal(600))
    spread = np.zeros(600)
    for t in range(1, 600):
        spread[t] = 0.9 * spread[t - 1] + rng.standard_normal()
    handler = handler_factory(Y=10 + 1.5 * x + spread, X=x)
    result = Backtest(handler, PairsTradingStrategy, events=events, strategy_params={"lookback": 60}).run()
    assert result.fills > 0
    assert result.stats["total_return"] > 0

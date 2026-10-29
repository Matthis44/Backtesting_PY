import pytest

from backtester import Backtest
from backtester.events import FillEvent, IBCommissionModel, SignalEvent
from backtester.strategies import MovingAverageCrossStrategy


def drain(queue):
    items = []
    while not queue.empty():
        items.append(queue.get())
    return items


def test_crossover_emits_long_then_exit(handler_factory, events):
    prices = [10] * 5 + [11, 12, 13, 14] + [13, 11, 9, 7, 5]
    handler = handler_factory(AAA=prices)
    strategy = MovingAverageCrossStrategy(handler, events, short_window=2, long_window=4)

    signals = []
    while True:
        handler.update_bars()
        if not handler.continue_backtest:
            break
        for event in drain(events):
            strategy.calculate_signals(event)
        signals += [e.signal_type for e in drain(events) if isinstance(e, SignalEvent)]

    assert signals == ["LONG", "EXIT"]


def test_invalid_windows_are_rejected(handler_factory, events):
    with pytest.raises(ValueError):
        MovingAverageCrossStrategy(handler_factory(AAA=[1, 2]), events, short_window=5, long_window=3)


def test_commission_model():
    model = IBCommissionModel()
    assert model.calculate(10) == 1.3  # minimum ticket
    assert model.calculate(500) == pytest.approx(6.5)
    assert model.calculate(1000) == pytest.approx(8.0)


def test_fill_uses_default_commission():
    fill = FillEvent(None, "AAA", "SIMULATED", 100, "BUY", fill_cost=1000.0)
    assert fill.commission == 1.3


def test_end_to_end_profit_and_loss(handler_factory, events):
    # Price rises from 10 to 20 then falls back: the strategy buys on the way up
    # and sells on the way down, so P&L is easy to check by hand.
    prices = [10] * 4 + list(range(11, 21)) + list(range(19, 9, -1))
    handler = handler_factory(AAA=prices)
    result = Backtest(
        handler,
        MovingAverageCrossStrategy,
        events=events,
        initial_capital=10_000,
        strategy_params={"short_window": 2, "long_window": 4},
        lot_size=10,
    ).run()

    assert (result.signals, result.orders, result.fills) == (2, 2, 2)

    holdings = result.equity_curve
    commissions = holdings["commission"].iloc[-1]
    assert commissions == pytest.approx(2 * 1.3)

    # Buy at 11 (bar 4: SMA2=10.5 > SMA4=10.25), sell at 18 (bar 15: SMA2=18.5 < SMA4=19).
    buy_price, sell_price = 11, 18
    assert holdings["total"].iloc[-1] == pytest.approx(10_000 + 10 * (sell_price - buy_price) - commissions)
    assert result.stats["max_drawdown"] >= 0

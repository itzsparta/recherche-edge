from orderflow_bot.features.aggregator import BarAggregator

from .conftest import make_trade


def test_bar_closes_on_window_boundary():
    agg = BarAggregator(bar_ms=60_000, bin_size=1.0)
    assert agg.on_trade(make_trade(0, 100.0, 2.0)) is None
    assert agg.on_trade(make_trade(10_000, 101.5, 1.0, sell=True)) is None
    bar = agg.on_trade(make_trade(60_000, 102.0, 1.0))   # nouvelle fenetre
    assert bar is not None
    assert (bar.open, bar.high, bar.low, bar.close) == (100.0, 101.5, 100.0, 101.5)
    assert bar.volume == 3.0
    assert bar.delta == 2.0 - 1.0
    assert bar.ask_vol == {100: 2.0}
    assert bar.bid_vol == {102: 1.0}    # 101.5 -> bin 102 (round)


def test_flush_returns_partial_bar():
    agg = BarAggregator(bar_ms=60_000, bin_size=1.0)
    agg.on_trade(make_trade(5_000, 100.0))
    bar = agg.flush()
    assert bar is not None and bar.close == 100.0
    assert agg.flush() is None

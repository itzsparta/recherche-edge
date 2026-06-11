from orderflow_bot.features.imbalance import stacked_imbalances
from orderflow_bot.models import FootprintBar


def _bar(ask: dict[int, float], bid: dict[int, float]) -> FootprintBar:
    return FootprintBar(open_ts=0, close_ts=60_000, open=100.0, high=101.0,
                        low=99.0, close=100.0, volume=1.0, delta=0.0,
                        ask_vol=ask, bid_vol=bid)


def test_stacked_buy_imbalances():
    # diagonale : ask(b) vs bid(b-1) ; ratio 3 atteint sur 100,101,102
    bar = _bar(ask={100: 30, 101: 24, 102: 18}, bid={99: 5, 100: 8, 101: 6})
    st = stacked_imbalances(bar, ratio=3.0, min_stack=3)
    assert st["buy"] == [100, 101, 102]
    assert st["sell"] == []


def test_no_stack_below_min():
    bar = _bar(ask={100: 30, 101: 24}, bid={99: 5, 100: 8})
    st = stacked_imbalances(bar, ratio=3.0, min_stack=3)
    assert st["buy"] == []


def test_zero_denominator_counts_as_imbalance():
    bar = _bar(ask={100: 5, 101: 5, 102: 5}, bid={})
    st = stacked_imbalances(bar, ratio=3.0, min_stack=3)
    assert st["buy"] == [100, 101, 102]

from orderflow_bot.models import FootprintBar
from orderflow_bot.strategy.level_rejection import level_rejection_triggers
from orderflow_bot.strategy.zones import Zone


def _bar(o, h, l, c, ts=1000) -> FootprintBar:
    return FootprintBar(open_ts=ts - 1, close_ts=ts, open=o, high=h, low=l, close=c,
                        volume=0.0, delta=0.0, ask_vol={}, bid_vol={})


def test_long_rejection_picks_nearest_support():
    z1 = Zone(96.0, 97.0, 0, "lvn", 105.0)
    z2 = Zone(98.5, 99.0, 1, "val", 105.0)        # support le plus proche sous la cloture
    bar = _bar(o=100.0, h=100.2, l=96.5, c=99.5)  # tape les deux, cloture au-dessus
    trigs = level_rejection_triggers(bar, [z1, z2])
    assert [t.price for t in trigs] == [99.0]     # z2.hi (le plus proche)
    assert trigs[0].side == 1
    assert trigs[0].kind == "level_rejection"
    assert trigs[0].ts == bar.close_ts


def test_short_rejection_emits_trigger():
    z = Zone(103.0, 104.0, -1, "vah", 100.0)
    bar = _bar(o=102.0, h=103.5, l=101.8, c=102.5)  # high tape [103,104], cloture < 103
    trigs = level_rejection_triggers(bar, [z])
    assert len(trigs) == 1
    assert trigs[0].side == -1 and trigs[0].price == 103.0


def test_no_trigger_when_close_inside_zone():
    z = Zone(99.0, 100.0, 1, "val", 105.0)
    bar = _bar(o=99.5, h=99.9, l=99.1, c=99.5)     # reste dans la zone
    assert level_rejection_triggers(bar, [z]) == []


def test_no_trigger_when_bar_misses_zone():
    z = Zone(90.0, 91.0, 1, "val", 95.0)
    bar = _bar(o=100.0, h=101.0, l=99.5, c=100.5)  # n'atteint jamais la zone
    assert level_rejection_triggers(bar, [z]) == []

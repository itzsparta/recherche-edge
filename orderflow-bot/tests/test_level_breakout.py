from orderflow_bot.models import FootprintBar
from orderflow_bot.strategy.level_breakout import level_breakout_triggers
from orderflow_bot.strategy.zones import Zone


def _bar(o, h, l, c, ts=1000) -> FootprintBar:
    return FootprintBar(open_ts=ts - 1, close_ts=ts, open=o, high=h, low=l, close=c,
                        volume=0.0, delta=0.0, ask_vol={}, bid_vol={})


def test_long_breakout_picks_nearest_edge():
    z1 = Zone(96.0, 97.0, 0, "lvn", 100.0)
    z2 = Zone(98.5, 99.0, -1, "vah", 100.0)        # bord casse le plus proche sous la cloture
    bar = _bar(o=95.0, h=100.0, l=95.0, c=100.0)   # corps ouvre sous les deux, cloture au-dessus
    trigs = level_breakout_triggers(bar, [z1, z2])
    assert [t.price for t in trigs] == [99.0]      # z2.hi (le plus proche sous la cloture)
    assert trigs[0].side == 1
    assert trigs[0].kind == "level_breakout"
    assert trigs[0].ts == bar.close_ts


def test_short_breakout_emits_trigger():
    z = Zone(103.0, 104.0, 1, "val", 100.0)
    bar = _bar(o=105.0, h=105.0, l=102.0, c=102.0)  # corps ouvre au-dessus, cloture sous z.lo
    trigs = level_breakout_triggers(bar, [z])
    assert len(trigs) == 1
    assert trigs[0].side == -1 and trigs[0].price == 103.0


def test_no_breakout_when_close_inside_zone():
    z = Zone(99.0, 100.0, 0, "npoc", 105.0)
    bar = _bar(o=98.0, h=99.8, l=98.0, c=99.5)      # cloture DANS la zone, pas au-dela
    assert level_breakout_triggers(bar, [z]) == []


def test_no_breakout_when_open_already_beyond():
    z = Zone(96.0, 97.0, 0, "lvn", 100.0)
    bar = _bar(o=98.0, h=101.0, l=98.0, c=100.0)    # corps deja AU-DESSUS au depart -> pas une cassure
    assert level_breakout_triggers(bar, [z]) == []


def test_no_breakout_when_bar_misses_zone():
    z = Zone(90.0, 91.0, 0, "lvn", 95.0)
    bar = _bar(o=100.0, h=101.0, l=99.5, c=100.5)   # n'atteint jamais la zone
    assert level_breakout_triggers(bar, [z]) == []

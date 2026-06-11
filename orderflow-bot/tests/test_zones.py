from orderflow_bot.strategy.context import DailyLevels
from orderflow_bot.strategy.zones import Zone, build_zones, zone_at

PREV = DailyLevels(day=1, poc=100.0, vah=103.0, val=97.0, high=105.0, low=95.0)


def test_build_zones_val_vah():
    zones = build_zones(PREV, npocs=[], lvn_prices=[], margin_pct=0.002)
    val = next(z for z in zones if z.kind == "val")
    vah = next(z for z in zones if z.kind == "vah")
    m = 100.0 * 0.002
    assert (val.lo, val.hi, val.side, val.target) == (97.0 - m, 97.0 + m, 1, 100.0)
    assert (vah.lo, vah.hi, vah.side, vah.target) == (103.0 - m, 103.0 + m, -1, 100.0)


def test_build_zones_npoc_lvn_both_sides():
    zones = build_zones(PREV, npocs=[92.0], lvn_prices=[99.0], margin_pct=0.002)
    npoc = next(z for z in zones if z.kind == "npoc")
    lvn = next(z for z in zones if z.kind == "lvn")
    assert npoc.side == 0 and npoc.target == 100.0
    assert lvn.side == 0


def test_zone_at():
    zones = build_zones(PREV, npocs=[], lvn_prices=[], margin_pct=0.002)
    z = zone_at(zones, 97.1)
    assert z is not None and z.kind == "val"
    assert zone_at(zones, 100.0) is None

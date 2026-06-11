from orderflow_bot.features.volume_profile import VolumeProfile
from orderflow_bot.strategy.context import (
    Bias, DailyLevels, levels_from_profile, market_bias, naked_pocs,
)


def _levels(day: int, poc: float, lo: float = 0.0, hi: float = 1e9) -> DailyLevels:
    return DailyLevels(day=day, poc=poc, vah=poc + 3, val=poc - 3, high=hi, low=lo)


def test_levels_from_profile():
    p = VolumeProfile(bin_size=1.0)
    for b, q in {98: 5, 99: 10, 100: 30, 101: 10, 102: 5}.items():
        p.add(float(b), q)
    lv = levels_from_profile(day=10, profile=p, high=103.0, low=97.0)
    assert lv.poc == 100.0
    assert (lv.val, lv.vah) == (99.0, 101.0)
    assert (lv.low, lv.high) == (97.0, 103.0)


def test_bias_long_on_rising_pocs():
    assert market_bias([_levels(1, 100), _levels(2, 101), _levels(3, 102)]) is Bias.LONG
    assert market_bias([_levels(1, 102), _levels(2, 101), _levels(3, 100)]) is Bias.SHORT
    assert market_bias([_levels(1, 100), _levels(2, 103), _levels(3, 101)]) is Bias.BOTH
    assert market_bias([_levels(1, 100)]) is Bias.BOTH   # historique insuffisant


def test_naked_pocs():
    lv = [
        _levels(1, 100.0),                      # retouche au jour 2 -> pas naked
        _levels(2, 95.0, lo=94.0, hi=101.0),    # jour 2 : range couvre 100
        _levels(3, 97.0, lo=96.0, hi=98.0),     # ne couvre pas 95 -> 95 naked
    ]
    assert naked_pocs(lv) == [95.0]             # dernier jour exclu par definition

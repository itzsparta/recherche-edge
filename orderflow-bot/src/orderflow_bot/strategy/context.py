from dataclasses import dataclass
from enum import Enum

from orderflow_bot.binning import price_of
from orderflow_bot.features.volume_profile import VolumeProfile


class Bias(Enum):
    LONG = "long"
    SHORT = "short"
    BOTH = "both"


@dataclass(frozen=True, slots=True)
class DailyLevels:
    day: int        # epoch days (ts // 86_400_000)
    poc: float
    vah: float
    val: float
    high: float
    low: float


def levels_from_profile(
    day: int, profile: VolumeProfile, high: float, low: float
) -> DailyLevels:
    val_b, vah_b = profile.value_area()
    s = profile.bin_size
    return DailyLevels(day=day, poc=price_of(profile.poc(), s),
                       vah=price_of(vah_b, s), val=price_of(val_b, s),
                       high=high, low=low)


def market_bias(levels: list[DailyLevels]) -> Bias:
    """POC strictement montants sur 3 jours -> LONG ; descendants -> SHORT ;
    sinon range -> BOTH (les deux sens aux extremes de la value area)."""
    if len(levels) < 3:
        return Bias.BOTH
    a, b, c = levels[-3:]
    if a.poc < b.poc < c.poc:
        return Bias.LONG
    if a.poc > b.poc > c.poc:
        return Bias.SHORT
    return Bias.BOTH


def naked_pocs(levels: list[DailyLevels]) -> list[float]:
    """POC des jours passes jamais retraverses par le range d'un jour ulterieur.
    Le dernier jour est exclu (aucun jour ulterieur pour le tester)."""
    out = []
    for i, lv in enumerate(levels[:-1]):
        if all(not (nxt.low <= lv.poc <= nxt.high) for nxt in levels[i + 1:]):
            out.append(lv.poc)
    return out

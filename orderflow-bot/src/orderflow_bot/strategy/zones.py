from dataclasses import dataclass

from orderflow_bot.strategy.context import DailyLevels


@dataclass(frozen=True, slots=True)
class Zone:
    lo: float
    hi: float
    side: int      # +1 long only (VAL), -1 short only (VAH), 0 selon trigger (nPOC/LVN)
    kind: str      # val | vah | npoc | lvn
    target: float


def build_zones(
    prev: DailyLevels,
    npocs: list[float],
    lvn_prices: list[float],
    margin_pct: float,
) -> list[Zone]:
    """Zones du jour depuis les niveaux de la veille. Target v1 = POC veille
    (bord conservateur de la rotation attendue)."""
    m = prev.poc * margin_pct
    zones = [
        Zone(prev.val - m, prev.val + m, 1, "val", prev.poc),
        Zone(prev.vah - m, prev.vah + m, -1, "vah", prev.poc),
    ]
    zones += [Zone(p - m, p + m, 0, "npoc", prev.poc) for p in npocs]
    zones += [Zone(p - m, p + m, 0, "lvn", prev.poc) for p in lvn_prices]
    return zones


def zone_at(zones: list[Zone], price: float) -> Zone | None:
    for z in zones:
        if z.lo <= price <= z.hi:
            return z
    return None

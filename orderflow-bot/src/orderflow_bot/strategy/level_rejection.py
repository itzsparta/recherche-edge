"""Couche 3 swing : rejet d'un niveau de volume profile sur barre resamplee.

Une barre qui teste une zone puis re-cloture en dehors = rejet du niveau ->
Trigger reversal (fade vers value). On n'emet qu'un trigger par sens, sur la
zone testee la PLUS PROCHE de la cloture (evite les candidats correles d'un
meme grand mouvement). La compatibilite du sens est validee ensuite par
ConfluenceEngine (zone VAL/VAH contrainte, npoc/lvn libre)."""

from orderflow_bot.models import FootprintBar
from orderflow_bot.strategy.confluence import Trigger
from orderflow_bot.strategy.zones import Zone


def level_rejection_triggers(bar: FootprintBar, zones: list[Zone]) -> list[Trigger]:
    # support teste par le bas, cloture revenue au-dessus de la zone -> long
    longs = [z for z in zones if bar.low <= z.hi < bar.close]
    # resistance testee par le haut, cloture revenue sous la zone -> short
    shorts = [z for z in zones if bar.close < z.lo <= bar.high]
    out: list[Trigger] = []
    if longs:
        z = max(longs, key=lambda z: z.hi)        # support le plus proche sous la cloture
        out.append(Trigger(ts=bar.close_ts, side=1, kind="level_rejection", price=z.hi))
    if shorts:
        z = min(shorts, key=lambda z: z.lo)       # resistance la plus proche au-dessus
        out.append(Trigger(ts=bar.close_ts, side=-1, kind="level_rejection", price=z.lo))
    return out

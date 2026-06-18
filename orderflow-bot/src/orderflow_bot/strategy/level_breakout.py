"""Couche 3 swing : cassure/acceptance d'un niveau de volume profile sur barre
resamplee. Le CORPS de la barre traverse le bord (open d'un cote, close de
l'autre) = acceptance au-dela de la value -> Trigger continuation. Complement
geometrique exact de level_rejection (meche pique + cl, retour = rejet). On
n'emet qu'un trigger par sens, sur la zone cassee la PLUS PROCHE de la cloture
(evite les candidats correles d'un meme grand mouvement). La compatibilite du
sens (VAH casse en haut=long, VAL casse en bas=short) est validee ensuite par
ConfluenceEngine mode continuation."""

from orderflow_bot.models import FootprintBar
from orderflow_bot.strategy.confluence import Trigger
from orderflow_bot.strategy.zones import Zone


def level_breakout_triggers(bar: FootprintBar, zones: list[Zone]) -> list[Trigger]:
    # corps ouvre au/sous le bord-haut, cloture au-dessus -> cassure haussiere
    longs = [z for z in zones if bar.open <= z.hi < bar.close]
    # corps ouvre au/sur le bord-bas, cloture en-dessous -> cassure baissiere
    shorts = [z for z in zones if bar.close < z.lo <= bar.open]
    out: list[Trigger] = []
    if longs:
        z = max(longs, key=lambda z: z.hi)        # bord casse le plus proche sous la cloture
        out.append(Trigger(ts=bar.close_ts, side=1, kind="level_breakout", price=z.hi))
    if shorts:
        z = min(shorts, key=lambda z: z.lo)       # bord casse le plus proche au-dessus
        out.append(Trigger(ts=bar.close_ts, side=-1, kind="level_breakout", price=z.lo))
    return out

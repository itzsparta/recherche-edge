"""Gate 2b du redeploy swing-continuation (cf. spec 2026-06-17-swing-continuation).

Helpers PURS du NOYAU kill-fast, drift-controle. Reutilise brut/_realized/
mirror_plan d'etage 1 (swing_gate). Le brut se mesure sur des labels frais=0 ;
le 'net' se mesure en passant le MEME jeu relabele aux frais reels. DSR/CSCV
(stade full-history post-greenlight) vivent dans scripts/overfit_audit.py, hors
de ce noyau. Le KILL dur central est brut_long>0 ET brut_short>0 : un edge qui
gagne long ET short ne peut pas vivre du drift directionnel."""

import math
from collections.abc import Callable

from orderflow_bot.backtest.swing_gate import _realized, brut
from orderflow_bot.models import ClosedTrade

_DAY_MS = 86_400_000


def brut_by_side(labels: list[ClosedTrade]) -> tuple[float, float]:
    """(brut_long, brut_short) sur les labels realises (censure 'eod' exclue)."""
    real = _realized(labels)
    longs = [c for c in real if c.plan.side == 1]
    shorts = [c for c in real if c.plan.side == -1]
    bl = sum(c.r_multiple for c in longs) / len(longs) if longs else 0.0
    bs = sum(c.r_multiple for c in shorts) / len(shorts) if shorts else 0.0
    return bl, bs


def t_stat(labels: list[ClosedTrade]) -> float:
    """t de Student sur la serie des R par trade (H0 : moyenne = 0)."""
    real = _realized(labels)
    n = len(real)
    if n < 2:
        return 0.0
    rs = [c.r_multiple for c in real]
    mean = sum(rs) / n
    var = sum((r - mean) ** 2 for r in rs) / (n - 1)
    sd = math.sqrt(var)
    if sd == 0.0:
        return 0.0
    return mean / (sd / math.sqrt(n))


def regime_fn_from_closes(
    closes: dict[int, float], lookback_days: int = 90
) -> Callable[[int], int]:
    """Construit regime(opened_ts) -> +1 (retour 90j > 0) / -1 (< 0) / 0 (inconnu).
    `closes` : {epoch_day -> close du jour}. Diagnostic, pas de gating."""
    def regime(ts: int) -> int:
        day = ts // _DAY_MS
        prev = day - lookback_days
        if day not in closes or prev not in closes:
            return 0
        d = closes[day] - closes[prev]
        return 1 if d > 0 else (-1 if d < 0 else 0)
    return regime


def regime_split(
    labels: list[ClosedTrade], regime_of_ts: Callable[[int], int]
) -> dict[int, dict]:
    """Diagnostic NON-gating : brut / brut_long / brut_short / n par regime."""
    real = _realized(labels)
    out: dict[int, dict] = {}
    for reg in (1, -1, 0):
        grp = [c for c in real if regime_of_ts(c.opened_ts) == reg]
        if not grp:
            continue
        # grp est deja realise ; brut_by_side re-filtre (idempotent, sans effet ici)
        bl, bs = brut_by_side(grp)
        out[reg] = {
            "n": len(grp),
            "brut": round(sum(c.r_multiple for c in grp) / len(grp), 4),
            "brut_long": round(bl, 4),
            "brut_short": round(bs, 4),
        }
    return out


def gate2(
    labels: list[ClosedTrade],
    mirror: list[ClosedTrade],
    net_labels: list[ClosedTrade],
    regime_of_ts: Callable[[int], int],
) -> dict:
    """Noyau kill-fast du gate 2b. core_greenlight = brut>0 ET t>2 ET
    brut_long>0 ET brut_short>0 ET net>0 ET brut>brut_miroir. DSR/CSCV
    (full-history) ajoutes en aval par l'orchestrateur si le noyau passe."""
    real = _realized(labels)               # une seule passe ; n = denominateur du brut
    b = brut(labels)                       # frais=0
    bl, bs = brut_by_side(labels)
    t = t_stat(labels)
    b_mirror = brut(mirror)
    net = brut(net_labels)                 # MEME jeu relabele aux frais reels -> R net moyen
    core = bool(b > 0 and t > 2 and bl > 0 and bs > 0 and net > 0 and b > b_mirror)
    return {
        "n": len(real),
        "brut": round(b, 4),
        "t": round(t, 2),
        "brut_long": round(bl, 4),
        "brut_short": round(bs, 4),
        "brut_mirror": round(b_mirror, 4),
        "net": round(net, 4),
        "regime": regime_split(labels, regime_of_ts),
        "core_greenlight": core,
    }

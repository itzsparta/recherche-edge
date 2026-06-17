"""Gate 1 du redeploy swing (cf. spec 2026-06-17-swing-redeploy-design.md).

Helpers PURS (testables, sans I/O) : mesure du brut directionnel du fade-vers-value
et verdict greenlight. Le brut se mesure sur des labels produits a frais=0
(relabel direct, jamais net+frais/risk0). Les labels censures (position encore
ouverte en fin de data, fermes en kind 'eod' par simulate_isolated eod_flat=False)
sont exclus du brut. L'orchestration (lecture data, run) vit dans
scripts/swing_smoke.py."""

from orderflow_bot.models import ClosedTrade, OrderPlan


def mirror_plan(p: OrderPlan) -> OrderPlan:
    """Null directionnel (#5) : meme entry, sens inverse, stop/target reflechis a
    travers l'entry. Un signal sans info directionnelle -> brut_fade ~ brut_miroir."""
    return OrderPlan(ts=p.ts, side=-p.side, entry=p.entry,
                     stop=2 * p.entry - p.stop, target=2 * p.entry - p.target,
                     meta={**p.meta, "mirror": True})


def _realized(labels: list[ClosedTrade]) -> list[ClosedTrade]:
    # censure = fermeture forcee en fin de data (kind 'eod' en mode eod_flat=False)
    return [ct for ct in labels if ct.fills[-1].kind != "eod"]


def brut(labels: list[ClosedTrade]) -> float:
    real = _realized(labels)
    return sum(ct.r_multiple for ct in real) / len(real) if real else 0.0


def dead_born_rate(labels: list[ClosedTrade]) -> float:
    real = _realized(labels)
    return sum(1 for ct in real if ct.mfe_r < 0.5) / len(real) if real else 1.0


def both_halves_positive(labels: list[ClosedTrade]) -> bool:
    real = sorted(_realized(labels), key=lambda ct: ct.opened_ts)
    if len(real) < 2:
        return False
    mid = len(real) // 2
    h1, h2 = real[:mid], real[mid:]
    a1 = sum(c.r_multiple for c in h1) / len(h1)
    a2 = sum(c.r_multiple for c in h2) / len(h2)
    return a1 > 0 and a2 > 0


def gate1(fade: list[ClosedTrade], mirror: list[ClosedTrade]) -> dict:
    """Gate 1 (smoke, permissif) : brut_fade>0 ET signe stable sur les 2 moities
    ET brut_fade>brut_miroir (info directionnelle) -> greenlight klines."""
    b_fade, b_mirror = brut(fade), brut(mirror)
    halves = both_halves_positive(fade)
    return {
        "n": len(_realized(fade)),
        "brut_fade": round(b_fade, 4),
        "brut_mirror": round(b_mirror, 4),
        "dead_born": round(dead_born_rate(fade), 3),
        "both_halves_pos": halves,
        "greenlight": bool(b_fade > 0 and halves and b_fade > b_mirror),
    }

"""Smoke-plomberie etage 2a : asserts PASS/FAIL purs sur la chaine
klines->zones->plans->labels. AUCUNE mesure d'edge (spec etage 2a). Chaque
fonction renvoie une liste de violations ; vide = PASS."""

import math

from orderflow_bot.models import ClosedTrade, OrderPlan
from orderflow_bot.strategy.context import DailyLevels


def zone_violations(levels: list[DailyLevels]) -> list[str]:
    """A : VAL<=POC<=VAH, POC dans le range, largeur VA dans ]0, range]."""
    out: list[str] = []
    if not levels:
        return ["aucun DailyLevels"]
    for lv in levels:
        if not (lv.val <= lv.poc <= lv.vah):
            out.append(f"jour {lv.day}: VAL<=POC<=VAH viole "
                       f"({lv.val}, {lv.poc}, {lv.vah})")
        if not (lv.low <= lv.poc <= lv.high):
            out.append(f"jour {lv.day}: POC hors range "
                       f"({lv.low}, {lv.poc}, {lv.high})")
        w = lv.vah - lv.val
        if not (0 < w <= lv.high - lv.low):
            out.append(f"jour {lv.day}: largeur VA aberrante ({w})")
    return out


def plan_violations(plans: list[OrderPlan], min_rr: float) -> list[str]:
    """B : geometrie reversal coherente + RR>=min_rr (tolerance flottante)."""
    out: list[str] = []
    if not plans:
        return ["aucun plan"]
    for p in plans:
        if p.side == 1 and not (p.stop < p.entry < p.target):
            out.append(f"long incoherent: stop {p.stop} entry {p.entry} "
                       f"target {p.target}")
        elif p.side == -1 and not (p.target < p.entry < p.stop):
            out.append(f"short incoherent: stop {p.stop} entry {p.entry} "
                       f"target {p.target}")
        risk = abs(p.entry - p.stop)
        reward = abs(p.target - p.entry)
        if risk <= 0 or reward / risk < min_rr - 1e-9:
            out.append(f"RR < {min_rr}: risk {risk} reward {reward}")
    return out


def label_violations(labels: list[ClosedTrade]) -> list[str]:
    """C : r_multiple fini pour tout label realise."""
    out: list[str] = []
    if not labels:
        return ["aucun label"]
    for ct in labels:
        if not math.isfinite(ct.r_multiple):
            out.append(f"r non fini: {ct.r_multiple} (ouvert {ct.opened_ts})")
    return out

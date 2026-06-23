"""Analyse biais net-de-vig — pré-enregistré docs/SPEC.md (Piste 16).

Devig la cote de clôture Pinnacle (sharp) -> proba « fair ». Courbe winrate-vs-proba
(test favorite-longshot). ROI net de vig à la cote OFFERTE (la courbe winrate ≠ le
prix offert : un biais peut être réel sans franchir le vig). Sharp (Pinnacle close)
vs soft (Bet365), et CLV (mispricing soft vs clôture).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from data import Match

OUTCOMES = ("H", "D", "A")


@dataclass(frozen=True)
class Leg:
    p_sharp: float       # proba dévigée Pinnacle-closing (estimateur efficient)
    o_psc: float         # cote offerte Pinnacle closing (SHARP)
    o_b365: float        # cote offerte Bet365 (SOFT)
    won: bool
    season: str
    league: str
    is_fav: bool         # plus courte cote du match (favori)


def devig(odds3: tuple[float, float, float]) -> tuple[tuple[float, float, float], float]:
    """3 cotes -> (probas normalisées sommant à 1, vig)."""
    inv = [1.0 / o for o in odds3]
    s = sum(inv)
    return (inv[0] / s, inv[1] / s, inv[2] / s), s - 1.0


def explode(matches: list[Match]) -> list[Leg]:
    """Chaque match -> 3 legs (H/D/A) avec proba sharp dévigée + flag favori."""
    legs: list[Leg] = []
    for m in matches:
        probs, _ = devig(m.psc)
        fav_idx = min(range(3), key=lambda i: m.psc[i])  # favori = plus courte cote
        for i, oc in enumerate(OUTCOMES):
            legs.append(Leg(
                p_sharp=probs[i],
                o_psc=m.psc[i],
                o_b365=m.b365[i],
                won=(m.result == oc),
                season=m.season,
                league=m.league,
                is_fav=(i == fav_idx),
            ))
    return legs


def roi(legs: list[Leg], book: str) -> tuple[float, float, int]:
    """ROI mise-à-plat à la cote OFFERTE du `book` ('psc'|'b365'). Retourne (roi, t, n).

    profit_i = (cote-1) si gagné sinon -1.  t = moyenne / (écart-type / sqrt(n)).
    """
    pnls: list[float] = []
    for lg in legs:
        o = lg.o_psc if book == "psc" else lg.o_b365
        pnls.append((o - 1.0) if lg.won else -1.0)
    n = len(pnls)
    if n == 0:
        return 0.0, 0.0, 0
    mean = sum(pnls) / n
    var = sum((x - mean) ** 2 for x in pnls) / (n - 1) if n > 1 else 0.0
    sd = math.sqrt(var)
    t = mean / (sd / math.sqrt(n)) if sd > 0 else 0.0
    return mean, t, n


def bias_curve(legs: list[Leg], n_bins: int = 10) -> list[dict]:
    """Buckets par proba sharp : winrate réalisé vs proba implicite + ROI net Pinnacle.

    Favorite-longshot = aux basses probas (longshots) winrate < proba (surpaiement).
    """
    s = sorted(legs, key=lambda l: l.p_sharp)
    per = max(1, len(s) // n_bins)
    out: list[dict] = []
    for b in range(n_bins):
        chunk = s[b * per: (b + 1) * per] if b < n_bins - 1 else s[b * per:]
        if not chunk:
            continue
        mp = sum(l.p_sharp for l in chunk) / len(chunk)
        wr = sum(1 for l in chunk if l.won) / len(chunk)
        r_psc, t_psc, _ = roi(chunk, "psc")
        out.append({
            "bin": b, "n": len(chunk), "p_sharp": mp, "winrate": wr,
            "edge_pp": (wr - mp) * 100,  # winrate − proba implicite, en points
            "roi_psc": r_psc, "t_psc": t_psc,
        })
    return out


def clv_value_legs(legs: list[Leg], min_edge: float = 0.0) -> list[Leg]:
    """Legs où la cote soft (B365) > cote sharp closing (Pinnacle) = CLV positif.

    Parier ces legs À LA COTE SOFT : on a obtenu un meilleur prix que la clôture
    efficiente. +EV en théorie — MAIS c'est exactement ce qui fait limiter le compte.
    `min_edge` = surcote relative minimale exigée (0 = toute surcote).
    """
    return [lg for lg in legs if lg.o_b365 > lg.o_psc * (1.0 + min_edge)]


def by_key(legs: list[Leg], key) -> dict:
    d: dict = {}
    for lg in legs:
        d.setdefault(key(lg), []).append(lg)
    return d

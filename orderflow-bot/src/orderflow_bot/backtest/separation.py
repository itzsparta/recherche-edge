"""Stats de separation (Phase 0 DOM) : AUC tie-aware + lift par quantile +
verdict greenlight pre-enregistre. Pur, sans I/O. Classe positive = mort-ne."""
from __future__ import annotations

import math


def auc(scores: list[float], labels: list[bool]) -> float:
    """AUC pour predire label=True a partir du score (haut score -> positif),
    via Mann-Whitney (rangs moyens sur les ex aequo). NaN exclus. NaN si une
    seule classe presente."""
    pairs = [(s, l) for s, l in zip(scores, labels) if not math.isnan(s)]
    n_pos = sum(1 for _, l in pairs if l)
    n_neg = len(pairs) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = sorted(range(len(pairs)), key=lambda k: pairs[k][0])
    ranks = [0.0] * len(pairs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and pairs[order[j + 1]][0] == pairs[order[i]][0]:
            j += 1
        avg = (i + j) / 2.0 + 1.0                 # rangs 1-based, moyenne sur ties
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    sum_pos = sum(ranks[k] for k in range(len(pairs)) if pairs[k][1])
    u = sum_pos - n_pos * (n_pos + 1) / 2.0
    return u / (n_pos * n_neg)


def quartile_lift(scores: list[float], labels: list[bool], q: int = 4) -> list[float]:
    """Taux de positifs par quantile croissant du score. NaN exclus."""
    pairs = sorted(((s, l) for s, l in zip(scores, labels) if not math.isnan(s)),
                   key=lambda x: x[0])
    n = len(pairs)
    if n == 0:
        return [float("nan")] * q
    out = []
    for b in range(q):
        chunk = pairs[b * n // q:(b + 1) * n // q]
        out.append(sum(1 for _, l in chunk if l) / len(chunk)
                   if chunk else float("nan"))
    return out

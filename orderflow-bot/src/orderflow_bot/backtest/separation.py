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


def evaluate_greenlight(rows, days, orient, tape_feats, *, auc_min=0.60,
                        delta_min=0.05, day_min=6, day_min_n=5):
    """Applique les 4 conditions pre-enregistrees (cf. spec). orient = {feat: +/-1}
    (signe tel que haut -> plus de morts-nes). tape_feats = liste de features tape
    baseline (sens libre -> on prend max(auc, 1-auc)). Retourne un dict de verdict."""
    labels = [r["mort_ne"] for r in rows]

    def oriented(rs, feat):
        sign = orient[feat]
        return [sign * r[feat] for r in rs], [r["mort_ne"] for r in rs]

    book_auc = {f: auc(*oriented(rows, f)) for f in orient}
    best_feat = max(book_auc, key=lambda f: book_auc[f] if not math.isnan(book_auc[f]) else -1.0)
    best_auc = book_auc[best_feat]

    tape_auc = {}
    for f in tape_feats:
        a = auc([r[f] for r in rows], labels)
        tape_auc[f] = max(a, 1 - a) if not math.isnan(a) else float("nan")
    best_tape = max((v for v in tape_auc.values() if not math.isnan(v)), default=0.5)

    lift = quartile_lift(*oriented(rows, best_feat))
    clean = [x for x in lift if not math.isnan(x)]
    # anti-mirage : un lift incomplet (NaN = quartile vide) ne permet PAS de confirmer
    # la monotonie -> c2 echoue plutot que de "ponter" les trous vers un faux-green
    monotone = (len(clean) == len(lift) and len(clean) >= 2
                and all(clean[k] <= clean[k + 1] for k in range(len(clean) - 1)))

    by_day_ok = 0
    for day in days:
        dr = [r for r in rows if r["day"] == day]
        if len(dr) < day_min_n:
            continue
        a = auc(*oriented(dr, best_feat))
        if not math.isnan(a) and a > 0.5:
            by_day_ok += 1

    c1 = (not math.isnan(best_auc)) and best_auc >= auc_min
    c2 = monotone
    c3 = by_day_ok >= day_min
    c4 = (not math.isnan(best_auc)) and (best_auc - best_tape) >= delta_min
    return {"best_feat": best_feat, "best_auc": best_auc, "best_tape": best_tape,
            "book_auc": book_auc, "tape_auc": tape_auc, "lift": lift,
            "by_day_ok": by_day_ok, "c1": c1, "c2": c2, "c3": c3, "c4": c4,
            "green": bool(c1 and c2 and c3 and c4)}

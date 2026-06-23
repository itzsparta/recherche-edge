"""Stratégies GEX + régimes — pré-enregistré docs/SPEC.md (Piste 18).

S1 = switch mean-rev/momentum conditionné au GEX. S2 = overlay vol-timing.
Régime « GEX haut » = au-dessus de la médiane TRAILING 252j (pas de look-ahead).
Signal en t-1, rendement en t, coûts 1 bp par unité de turnover.
"""
from __future__ import annotations

import math

import data_gex

COST = 1e-4  # 1 bp par unité de |Δposition|


def _trailing_median(vals: list[float], i: int, win: int = 252) -> float:
    """Médiane des gex sur [i-win, i) — connue à la clôture de t-1 (i = index du signal)."""
    lo = max(0, i - win)
    s = sorted(vals[lo:i])
    if not s:
        return 0.0
    return s[len(s) // 2]


def strategies() -> dict[str, list[float]]:
    """Renvoie les rendements quotidiens nets de S1, S2, et buy-hold, alignés (à partir de j=253)."""
    d = data_gex.load()
    gex = [x.gex for x in d]
    n = len(d)
    s1: list[float] = []
    s2: list[float] = []
    bh: list[float] = []
    pos1_prev = 0.0
    pos2_prev = 1.0
    start = 253  # besoin de la fenêtre trailing + un lag
    for i in range(start, n):
        g = d[i - 1].gex                  # signal laggé (clôture veille)
        r_prev = d[i - 1].ret
        r_now = d[i].ret
        thr = _trailing_median(gex, i - 1)

        # S1 : fade si GEX haut, follow si GEX négatif, flat sinon
        if g > thr:
            pos1 = -(1.0 if r_prev > 0 else (-1.0 if r_prev < 0 else 0.0))
        elif g < 0:
            pos1 = (1.0 if r_prev > 0 else (-1.0 if r_prev < 0 else 0.0))
        else:
            pos1 = 0.0
        s1.append(pos1 * r_now - abs(pos1 - pos1_prev) * COST)
        pos1_prev = pos1

        # S2 : plein SPX si GEX haut (régime supprimé), 0 sinon
        pos2 = 1.0 if g > thr else 0.0
        s2.append(pos2 * r_now - abs(pos2 - pos2_prev) * COST)
        pos2_prev = pos2

        bh.append(r_now)
    return {"S1_switch": s1, "S2_voltiming": s2, "buyhold": bh}


def pearson(xs: list[float], ys: list[float]) -> float:
    n = min(len(xs), len(ys))
    if n < 3:
        return 0.0
    mx = sum(xs[:n]) / n
    my = sum(ys[:n]) / n
    cov = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    vx = sum((xs[i] - mx) ** 2 for i in range(n))
    vy = sum((ys[i] - my) ** 2 for i in range(n))
    return cov / math.sqrt(vx * vy) if vx > 0 and vy > 0 else 0.0


def mechanism() -> tuple[float, int]:
    """corr(gex_{t-1}, |ret_t|) — le mécanisme gamma->vol. Renvoie (corr, n)."""
    d = data_gex.load()
    g = [d[i - 1].gex for i in range(1, len(d))]
    v = [abs(d[i].ret) for i in range(1, len(d))]
    return pearson(g, v), len(g)


if __name__ == "__main__":
    c, n = mechanism()
    print(f"  (A) corr(GEX_lag, |ret|) = {c:+.3f}  (n={n})")
    for k, v in strategies().items():
        m = sum(v) / len(v)
        print(f"  {k:14s} ann={m*252*100:+.2f}%  n={len(v)}")

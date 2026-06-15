"""Levier #13 (pre-enregistre) : la cohorte SURVIVANTE du regime vol (#12, moitie
basse-RV / Q2) peut-elle franchir le mur de frais par l'EXECUTION seule, sans
toucher au signal ? La branche signal est morte (un oracle de regime PARFAIT te
plafonne a la meilleure cellule, Q2 brut ~+0.067R, deja sous le mur ~0.21R).
Reste l'axe cout x magnitude-R. Produit croise sur le journal, AVANT tout build.

  Fork A (frais) : maker-out asymetrique est DEJA le baseline (target=maker,
    stop=taker, cf. paper.py). Ce qui reste exploitable = rebate (maker < 0) +
    baisse taker. Instrument NQ ~ frais x0.1 (meme commission, 10x notionnel) =
    un point du sweep. On cherche le break-even net>0 conditionne basse-RV/Q2.
  Fork B1 (laisser courir) : cible structurelle (POC veille) -> cible =
    entree + k*risk0 (stop inchange -> risk0 inchange -> fraction-frais
    inchangee ; ce qui monte = le multiple-R des gagnants). Sweep k, localise
    ou le brut decroche.

OPTIMISATION : les frais sont LINEAIRES et n'alterent NI les fills NI les labels
(le chemin de prix ignore les frais). Donc on simule UNE fois par (cible-k,
entry_mode) a frais=0, on capture les fills, puis on applique n'importe quelle
grille de frais analytiquement -> l'axe frais est gratuit (~14 sims, pas ~140).

PRE-ENREGISTREMENT (fige AVANT le run) :
  - cohorte = moitie basse-RV (partition #12, RV-24h, mediane globale) = porte
    PRIMAIRE ; Q2 (meilleure cellule) = borne OPTIMISTE.
  - metrique de decision = NET. Bornes REALISTES : maker in [-0.00025, 0.0002],
    taker in [0.0001, 0.0005], k in [1.5, 8].
  - FORK D (abandon these intraday-orderflow) SI : meme au MEILLEUR point realiste
    (maker -0.00025, taker 0.0001, k* optimal), le NET sur Q2 (optimiste) reste
    < 0 -> aucun cherry-pick ne peut sauver la these.
  - v1-EXECUTION SI : net>0 sur la moitie basse-RV (porte primaire) a un point
    realiste -> c'est de l'execution, pas du signal. On note le point.
  - COROLLAIRE (hole-2) : le bump non-monotone Q1<Q2 en BRUT est-il un artefact
    cible-structurelle x vol (POC a distance-R enorme en basse-vol -> jamais
    atteint) ? Test : si sous cible k-FIXE la non-monotonie Q1<Q2 disparait ->
    artefact mecanique, le +0.067 est encore plus illusoire.

Usage: python -u scripts/exec_wall.py [config.yaml] [cache.jsonl] START END
"""
import dataclasses
import math
import os
import statistics as st
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rv_regime import rv_series, rv_at, _DAY          # memes labels regime que #12

from orderflow_bot.cache import load_plans
from orderflow_bot.config import load_config
from orderflow_bot.pipeline import simulate_isolated_parallel
from orderflow_bot.__main__ import _ms

N_BLOCKS = 16
K_GRID = [None, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0]          # None = cible structurelle (POC)
# (label, maker_pct, taker_pct) ; dernier realiste = meilleur cas autorise
FEE_GRID = [
    ("brut (0/0)",        0.0,      0.0),
    ("base .0002/.0005",  0.0002,   0.0005),
    ("taker=mk .0002",    0.0002,   0.0002),
    ("VIP .0001/.0003",   0.0001,   0.0003),
    ("NQ-like x0.1",      0.00002,  0.00005),
    ("rebate 0/-.0001",   0.0,      0.0001),
    ("rebate -1e4/.0001", -0.0001,  0.0001),
    ("BEST -2.5e4/.0001", -0.00025, 0.0001),           # meilleur point realiste pre-enregistre
]
BEST_FEE = (-0.00025, 0.0001)


def records(cts, entry_mode):
    """ClosedTrade -> dicts {gross, risk0, legs, et, mfe, ots}. Frais recomputes
    analytiquement depuis les legs ; gross/risk0 ignorent les frais."""
    out = []
    for ct in cts:
        ef = next((f for f in ct.fills if f.kind == "entry"), None)
        if ef is None:
            continue
        side = ct.plan.side
        risk0 = (ct.plan.entry - ct.plan.stop) * side
        if risk0 <= 0:
            continue
        gross = sum((f.price - ef.price) * side * f.qty for f in ct.fills if f.kind != "entry")
        legs = [(f.kind, f.price, f.qty) for f in ct.fills]
        out.append({"gross": gross, "risk0": risk0, "legs": legs,
                    "et": entry_mode == "stop", "mfe": ct.mfe_r, "ots": ct.opened_ts})
    return out


def net_r(r, mk, tk):
    fee = 0.0
    for kind, price, qty in r["legs"]:
        if kind in ("stop", "eod"):
            rate = tk
        elif kind == "entry":
            rate = tk if r["et"] else mk
        else:                                   # partial, target -> maker (limit)
            rate = mk
        fee += price * qty * rate
    return (r["gross"] - fee) / r["risk0"]


def brut_r(r):
    return r["gross"] / r["risk0"]


def label_rv(recs, end_ms, cumsq):
    """Affecte rv (24h), half (low/high mediane globale), q (1..4) a chaque rec.
    Identique a #12 sur (limit, structurel). recs sans warmup RV -> rv=nan, ecartes."""
    for r in recs:
        r["rv"] = rv_at(end_ms, cumsq, r["ots"], _DAY)
    rv = np.array([r["rv"] for r in recs])
    ok = ~np.isnan(rv)
    med = float(np.median(rv[ok]))
    qs = np.quantile(rv[ok], [0.25, 0.5, 0.75])
    edges = [-np.inf, *qs, np.inf]
    for r in recs:
        v = r["rv"]
        if math.isnan(v):
            r["half"] = r["q"] = None
            continue
        r["half"] = "low" if v <= med else "high"
        r["q"] = next(i for i in range(4) if edges[i] < v <= edges[i + 1])
    return med, int((~ok).sum())


def cell(recs, key, val):
    return [r for r in recs if r.get(key) == val]


def summ(recs, mk, tk):
    if not recs:
        return None
    nets = [net_r(r, mk, tk) for r in recs]
    return {"n": len(recs), "net": st.mean(nets), "brut": st.mean(brut_r(r) for r in recs),
            "wr": sum(x > 0 for x in nets) / len(nets),
            "morts": sum(r["mfe"] < 0.5 for r in recs) / len(recs)}


def retarget(plans, k):
    if k is None:
        return plans
    out = []
    for p in plans:
        risk = abs(p.entry - p.stop)
        out.append(dataclasses.replace(p, target=p.entry + p.side * k * risk))
    return out


def run_mode(base, plans, start, end, entry_mode, frac, end_ms, cumsq, primary):
    print(f"\n{'='*72}\n### ENTRY={entry_mode} frac={frac}"
          f"{'  (PRIMAIRE = config #12)' if primary else '  (robustesse)'}\n{'='*72}")
    by_k = {}
    for k in K_GRID:
        cfg = base.model_copy(deep=True)
        cfg.strategy.entry_mode, cfg.strategy.entry_confirm_frac = entry_mode, frac
        cfg.fees.maker_pct = cfg.fees.taker_pct = 0.0          # sim brute, frais analytiques ensuite
        cts = simulate_isolated_parallel(cfg, start, end, retarget(plans, k), n_blocks=N_BLOCKS)
        recs = records(cts, entry_mode)
        label_rv(recs, end_ms, cumsq)
        by_k[k] = recs

    # --- B1 + COROLLAIRE : brut par quartile RV, par cible-k -----------------
    print("\n-- BRUT par quartile RV (B1: ou le brut decroche ; corollaire: Q1<Q2 persiste ?)")
    print(f"   {'cible':>10} | {'Q1':>8} {'Q2':>8} {'Q3':>8} {'Q4':>8} | {'low':>8} {'high':>8} | {'n':>5}")
    for k in K_GRID:
        recs = by_k[k]
        qb = [summ(cell(recs, "q", i), 0, 0) for i in range(4)]
        lo, hi = summ(cell(recs, "half", "low"), 0, 0), summ(cell(recs, "half", "high"), 0, 0)
        kl = "struct" if k is None else f"{k:g}R"
        row = " ".join(f"{(q['brut'] if q else float('nan')):+8.3f}" for q in qb)
        n = sum(1 for r in recs if r["half"])
        print(f"   {kl:>10} | {row} | {lo['brut']:+8.3f} {hi['brut']:+8.3f} | {n:5d}")

    # k* = cible maximisant le brut sur la moitie basse-RV
    kstar = max(K_GRID, key=lambda k: (summ(cell(by_k[k], "half", "low"), 0, 0) or {"brut": -9})["brut"])
    print(f"\n   k* (brut max sur low-RV) = {'struct' if kstar is None else f'{kstar:g}R'}")

    # --- FORK A : grille de frais a k*, NET sur Q2 (optimiste) + low (primaire)
    print(f"\n-- FORK A : NET par grille de frais (cible k*={'struct' if kstar is None else f'{kstar:g}R'})")
    print(f"   {'frais':>20} | {'net Q2':>9} {'wr Q2':>6} | {'net low':>9} {'wr low':>6} {'morts':>6} | {'net all':>9}")
    recs = by_k[kstar]
    q2 = cell(recs, "q", 1)
    low = cell(recs, "half", "low")
    for lab, mk, tk in FEE_GRID:
        a, b, c = summ(q2, mk, tk), summ(low, mk, tk), summ(recs, mk, tk)
        print(f"   {lab:>20} | {a['net']:+9.3f} {a['wr']:6.0%} | {b['net']:+9.3f} {b['wr']:6.0%} "
              f"{b['morts']:6.0%} | {c['net']:+9.3f}")

    # break-even realiste : 1er point (hors brut) avec net_low>0 ET net_Q2>0
    be = None
    for lab, mk, tk in FEE_GRID[1:]:
        if summ(low, mk, tk)["net"] > 0 and summ(q2, mk, tk)["net"] > 0:
            be = lab
            break
    print(f"   break-even realiste (net>0 sur low ET Q2) : {be or 'AUCUN'}")

    best = {"q2": summ(q2, *BEST_FEE)["net"], "low": summ(low, *BEST_FEE)["net"],
            "kstar": kstar, "be": be}
    return best


def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    cache = sys.argv[2] if len(sys.argv) > 2 else "plans_cache.jsonl"
    start = _ms(sys.argv[3]) if len(sys.argv) > 3 else _ms("2025-12-01")
    end = _ms(sys.argv[4]) if len(sys.argv) > 4 else _ms("2026-06-11")
    base = load_config(cfg_path)
    plans = load_plans(cache)
    print(__doc__.split("Usage")[0])
    print(f"=== {len(plans)} plans | fenetre {sys.argv[3] if len(sys.argv)>3 else '2025-12-01'}"
          f" -> {sys.argv[4] if len(sys.argv)>4 else '2026-06-11'} ===")
    end_ms, cumsq = rv_series(base, start, end)

    prim = run_mode(base, plans, start, end, "limit", 0.0, end_ms, cumsq, primary=True)
    robu = run_mode(base, plans, start, end, "stop", 1.0, end_ms, cumsq, primary=False)

    # --- VERDICT pre-enregistre ---------------------------------------------
    print(f"\n{'#'*72}\n# VERDICT pre-enregistre (porte primaire = ENTRY=limit, config #12)\n{'#'*72}")
    ks = "struct" if prim["kstar"] is None else f"{prim['kstar']:g}R"
    print(f"  meilleur point realiste (maker -0.00025, taker 0.0001, k*={ks}) :")
    print(f"    net Q2 (optimiste) = {prim['q2']:+.3f}R | net low-RV (primaire) = {prim['low']:+.3f}R")
    if prim["q2"] < 0:
        print("\n  => Q2 NET<0 meme au meilleur point realiste : aucun cherry-pick ne sauve.")
        print("     FORK D — these intraday-orderflow morte SOUS frais. Redeployer la machinerie.")
    elif prim["be"]:
        print(f"\n  => net>0 sur low-RV au point realiste '{prim['be']}'.")
        print("     v1-EXECUTION : l'edge est atteignable par l'EXECUTION (rebate/cible), pas le signal.")
    else:
        print("\n  => Q2 franchit zero mais pas la moitie basse-RV a un point realiste.")
        print("     Cellule mince / cherry-pick — penche FORK D, verifier robustesse stop-entry.")
    print(f"\n  robustesse ENTRY=stop : net Q2={robu['q2']:+.3f} net low={robu['low']:+.3f} "
          f"be={robu['be'] or 'AUCUN'}")


if __name__ == "__main__":
    main()

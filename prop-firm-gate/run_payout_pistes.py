"""
Pistes E/F/G — « pas besoin d'edge, juste UN payout » (question de Remi, 2026-06-25).

Suite directe de l'etude #24. Le run #24 testait FTMO (2 phases) et lisait P(net>0)
no-edge = 9.7%. Objection : on n'a pas besoin de GARDER le compte, juste d'atteindre
UN payout (avec refund, net>0 <=> 1er payout atteint). Le vrai objectif devient donc
P(net>0) > 0.50 (mediane positive), pas un Sharpe de break-even.

On teste les 3 structures que #24 n'a pas couvertes :
  E  smash-and-grab : sizing qui MAXIMISE P(net>0) (pas P(pass)), variance balayee
                      -> montre si "grossir une fois finance" aide (intuition variance).
  F  une-phase a ratio FAVORABLE : casser le P1*P2 qui ecrase P(funded) a 18%.
  G  instant funding : zero eval = UNE seule barriere (le + proche de flipper la mediane),
                      avec et sans "buffer" de retrait (friction reelle #16).

Decisif : si max P(net>0) sans edge < 0.50 PARTOUT (meilleure firme + meilleure sizing),
alors la mediane est negative par construction -> un edge EST necessaire pour la flipper.

Note de modele : on borne funded_horizon a ~3 fenetres de payout (on teste "atteindre
LE 1er payout", pas l'extraction a vie) -> sim plus rapide, fidele a la these de Remi.

Usage : <venv>/python.exe run_payout_pistes.py
"""
from __future__ import annotations

import json
import os
import time
import multiprocessing as mp
import numpy as np

from challenge import ChallengeConfig, parallel_pipeline
from run_gate import drift, TREND_SHARPE, COST_BASE

HERE = os.path.dirname(os.path.abspath(__file__))

SIGMA_GRID = [0.002, 0.004, 0.006, 0.01, 0.015, 0.02, 0.03]
K_GRID = [1, 2, 4]
N_SCAN = 80_000
FUNDED_H = 42          # ~3 fenetres de payout : on vise LE 1er payout, pas l'extraction a vie


# --- Configs (best-case DONNE a la these : ratios/refund genereux ; realisme note en FINDINGS) ---

def onephase_fav():
    # F : une seule phase, ratio TRES favorable (gros maxloss, petite cible) + refund 100%.
    # Driftless gambler's ruin P(pass) ~ 0.10/(0.10+0.06) = 0.625. Best-case structurel.
    return ChallengeConfig(
        name="F: 1-phase favorable (cible+6%, maxloss 10% stat)",
        account=100_000.0, fee=500.0, refund_frac=1.0, phases=(0.06,),
        max_dd=0.10, daily_dd=0.05, trailing=False, min_trading_days=0,
        consistency=0.0, split=0.80, payout_days=14, funded_horizon_days=FUNDED_H,
    )


def onephase_real():
    # 1-step typique du marche : cible HAUTE, maxloss SERRE -> ratio defavorable (#16).
    # Driftless P(pass) ~ 0.06/(0.06+0.10) = 0.375 < 0.5.
    return ChallengeConfig(
        name="1-phase realiste (cible+10%, maxloss 6% stat)",
        account=100_000.0, fee=300.0, refund_frac=1.0, phases=(0.10,),
        max_dd=0.06, daily_dd=0.04, trailing=False, min_trading_days=0,
        consistency=0.0, split=0.80, payout_days=14, funded_horizon_days=FUNDED_H,
    )


def instant_nobuffer():
    # G best-case absolu : zero eval (cible ~0 = finance d'emblee), UNE barriere = atteindre
    # un payout avant breach. Retrait de tout profit a J+14. Pas de refund (instant funding).
    return ChallengeConfig(
        name="G: instant funding SANS buffer (1 barriere)",
        account=25_000.0, fee=600.0, refund_frac=0.0, phases=(0.0005,),
        max_dd=0.08, daily_dd=0.04, trailing=False, min_trading_days=0,
        consistency=0.0, split=0.70, payout_days=14, funded_horizon_days=FUNDED_H,
    )


def instant_buffer():
    # G realiste : instant funding mais retrait conditionne a un BUFFER +4% (friction #16).
    # = une-phase a petite cible deguisee.
    return ChallengeConfig(
        name="G: instant funding AVEC buffer +4% (realiste)",
        account=25_000.0, fee=600.0, refund_frac=0.0, phases=(0.04,),
        max_dd=0.08, daily_dd=0.04, trailing=False, min_trading_days=0,
        consistency=0.0, split=0.70, payout_days=14, funded_horizon_days=FUNDED_H,
    )


def mu_from_sharpe(sharpe, sigma, k):
    """Drift/trade donnant un Sharpe annualise cible (invariant a la taille)."""
    return sharpe * sigma / np.sqrt(252 * k)


def scan_maximize_ppos(cfg, edge_sharpe, pool, W):
    """Balaye la sizing pour MAXIMISER P(net>0) (objectif smash-and-grab : sortir positif).

    edge_sharpe=0 -> no-edge (drift = -couts). Sinon on injecte un Sharpe annualise.
    Retourne (best dict, courbe sigma de p_pos au meilleur k) -> montre l'effet variance.
    """
    best = None
    for k in K_GRID:
        for sigma in SIGMA_GRID:
            mu = (drift(0.0, sigma, COST_BASE) if edge_sharpe == 0
                  else mu_from_sharpe(edge_sharpe, sigma, k) - COST_BASE - 0.02 * sigma)
            r = parallel_pipeline(cfg, mu, sigma, k, n=N_SCAN, seed=11,
                                  with_funded=True, pool=pool, n_workers=W)
            if best is None or r["p_pos"] > best["p_pos"]:
                best = r
    # courbe variance au meilleur k (no-edge) : l'intuition "grossir = grab plus vite" testee
    kbest = best["k"]
    curve = []
    for sigma in SIGMA_GRID:
        mu = (drift(0.0, sigma, COST_BASE) if edge_sharpe == 0
              else mu_from_sharpe(edge_sharpe, sigma, kbest) - COST_BASE - 0.02 * sigma)
        r = parallel_pipeline(cfg, mu, sigma, kbest, n=N_SCAN, seed=11,
                              with_funded=True, pool=pool, n_workers=W)
        curve.append((sigma, r["p_pos"], r["EV"], r["median"]))
    return best, curve


def run_config(cfg, pool, W):
    print("\n" + "=" * 76)
    print(f"{cfg.name}")
    print(f"  account ${cfg.account:,.0f} | fee ${cfg.fee:.0f} | refund {cfg.refund_frac:.0%} "
          f"| split {cfg.split:.0%} | phases {cfg.phases} | maxloss {cfg.max_dd:.0%}")
    print("=" * 76)

    ne, curve = scan_maximize_ppos(cfg, 0.0, pool, W)
    ed, _ = scan_maximize_ppos(cfg, TREND_SHARPE, pool, W)

    print(f"  [no-edge]  best P(net>0)={ne['p_pos']:.3f}  (sigma={ne['sigma_t']:.3f} k={ne['k']})"
          f"  EV=${ne['EV']:,.0f}  med=${ne['median']:,.0f}  "
          f"P(funded)={ne['Pboth']:.3f}  P(payout|fund)={ne['P_payout_funded']:.3f}")
    print(f"  [trend .42] best P(net>0)={ed['p_pos']:.3f}  (sigma={ed['sigma_t']:.3f} k={ed['k']})"
          f"  EV=${ed['EV']:,.0f}  med=${ed['median']:,.0f}  "
          f"P(funded)={ed['Pboth']:.3f}  P(payout|fund)={ed['P_payout_funded']:.3f}")
    print("  Effet VARIANCE (no-edge, meilleur k) -- teste l'intuition smash-and-grab :")
    for sigma, pp, ev, med in curve:
        print(f"    sigma={sigma:.3f}  P(net>0)={pp:.3f}  EV=${ev:8,.0f}  med=${med:7,.0f}")

    return {
        "name": cfg.name, "fee": cfg.fee,
        "noedge": {"p_pos": ne["p_pos"], "EV": ne["EV"], "median": ne["median"],
                   "Pboth": ne["Pboth"], "P_payout_funded": ne["P_payout_funded"],
                   "sigma": ne["sigma_t"], "k": ne["k"]},
        "trend": {"p_pos": ed["p_pos"], "EV": ed["EV"], "median": ed["median"],
                  "Pboth": ed["Pboth"], "P_payout_funded": ed["P_payout_funded"],
                  "sigma": ed["sigma_t"], "k": ed["k"]},
        "variance_curve": [{"sigma": s, "p_pos": pp, "EV": ev, "median": m}
                           for s, pp, ev, m in curve],
    }


def main():
    t0 = time.time()
    W = os.cpu_count() or 1
    print(f"Pistes E/F/G — 'juste UN payout'.  Parallelisation : {W} coeurs")
    print(f"Decisif : max P(net>0) sans edge >= 0.50 ?  (sinon mediane<0 => edge requis)")

    configs = [onephase_fav(), onephase_real(), instant_nobuffer(), instant_buffer()]
    with mp.Pool(W) as pool:
        results = [run_config(c, pool, W) for c in configs]

    print("\n" + "=" * 76)
    print("VERDICT pistes E/F/G")
    print("=" * 76)
    max_ne = max(r["noedge"]["p_pos"] for r in results)
    max_ed = max(r["trend"]["p_pos"] for r in results)
    for r in results:
        flip_ne = "MEDIANE>0" if r["noedge"]["median"] > 0 else "med<0"
        flip_ed = "MEDIANE>0" if r["trend"]["median"] > 0 else "med<0"
        print(f"  {r['name'][:46]:46s} | no-edge P(>0)={r['noedge']['p_pos']:.3f} ({flip_ne})"
              f" | trend P(>0)={r['trend']['p_pos']:.3f} ({flip_ed})")
    print("-" * 76)
    print(f"  MAX P(net>0) sans edge = {max_ne:.3f}   |   avec trend 0.42 = {max_ed:.3f}")
    if max_ne >= 0.50:
        print("  >>> SURPRISE : une structure flippe la mediane SANS edge -> a creuser.")
    elif max_ed >= 0.50:
        print("  >>> Sans edge la mediane reste <0 (edge requis), MAIS le trend 0.42 la flippe")
        print("      sur au moins une structure -> piste deployable conditionnelle a l'edge.")
    else:
        print("  >>> Mediane <0 PARTOUT, meme avec le trend 0.42. Un seul payout ne suffit pas :")
        print("      on enchaine >=2 barrieres sans drift (eval/buffer + payout), produit < 0.5.")
        print("      'Juste UN payout' reste une loterie. Edge requis pour flipper la mediane.")

    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(os.path.join(HERE, "data", "payout_pistes.json"), "w", encoding="utf-8") as f:
        json.dump({"trend_sharpe": TREND_SHARPE, "cost_base": COST_BASE,
                   "funded_horizon": FUNDED_H, "max_ppos_noedge": max_ne,
                   "max_ppos_trend": max_ed, "configs": results}, f, indent=2, ensure_ascii=False)
    print(f"\nResultats -> data/payout_pistes.json   ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()

"""
Meta-gate prop firm DURCI + PARALLELISE (docs/SPEC.md, + note de correction du cout).

Durcissements vs run #1 (qui rendait un faux-GO EV>0 sans edge) :
  - COUT/TRADE REALISTE. Le run #1 utilisait 0.00005 (0.5 bp de compte) = 20-30x trop
    bas pour du futures actif. Corrige a ~5 bp + slippage proportionnel a la taille.
    C'est une correction d'ERREUR d'input vers la realite documentee, PAS un tuning vers
    le KILL : on rapporte la SENSIBILITE complete EV(cout) + le cout de break-even.
  - DISTRIBUTION : on rapporte EV (mean) MAIS AUSSI mediane + P(net>0). Un EV>0 porte par
    une queue chanceuse = loterie, pas un edge (lecon airdrop #14 jackpots).
  - PARALLELISE : sims independantes decoupees sur tous les coeurs CPU (multiprocessing).

Usage : <venv>/python.exe run_gate.py
"""
from __future__ import annotations

import json
import os
import time
import multiprocessing as mp
import numpy as np

from challenge import (ChallengeConfig, simulate_phase, annualized_sharpe,
                       parallel_pipeline)

TREND_SHARPE = 0.42      # barre pre-enregistree : Sharpe du seul signal directionnel reel (#1)
COST_BASE = 0.0005       # cout/trade (fraction de compte) ~5 bp : commissions + ~1 tick, taille moderee
SLIP = 0.02              # slippage proportionnel au risque/trade (impact de taille) : 2% du risque
COST_GRID = [0.0001, 0.0002, 0.0005, 0.0008, 0.0012, 0.002]   # sensibilite au cout
SIGMA_GRID = [0.0025, 0.005, 0.0075, 0.01, 0.015, 0.02]
K_GRID = [1, 2, 4, 6]
N_SWEEP = 60_000
N_FINAL = 300_000
N_BISECT = 150_000

HERE = os.path.dirname(os.path.abspath(__file__))


def drift(edge, sigma, cost):
    """Drift net/trade = edge brut - cout fixe - slippage(taille)."""
    return edge - cost - SLIP * sigma


def base_config():
    return ChallengeConfig(
        name="FTMO-static", account=100_000.0, fee=540.0, refund_frac=1.0,
        phases=(0.10, 0.05), max_dd=0.10, daily_dd=0.05, trailing=False,
        min_trading_days=0, max_days=0, consistency=0.0,
        split=0.80, payout_days=14, funded_horizon_days=504,
    )


def stress_config():
    return ChallengeConfig(
        name="Topstep-trailing", account=50_000.0, fee=330.0, refund_frac=0.0,
        phases=(0.06,), max_dd=0.04, daily_dd=0.03, trailing=True,
        min_trading_days=2, max_days=0, consistency=0.50,
        split=0.90, payout_days=14, funded_horizon_days=504,
    )


def sanity_checks():
    print("=" * 72)
    print("0. SANITY-CHECKS (gambler's ruin, mu=0, daily-DD desactivee)")
    print("=" * 72)
    rng = np.random.default_rng(1)
    cfg = ChallengeConfig(max_dd=0.10, daily_dd=9.99, trailing=False, min_trading_days=0)
    n = 200_000
    p1, _, _ = simulate_phase(n, 0.10, cfg, 0.0, 0.01, 4, rng)
    p2, _, _ = simulate_phase(n, 0.05, cfg, 0.0, 0.01, 4, rng)
    print(f"  P(+10% | maxloss 10%, sym) = {p1.mean():.4f}  (attendu ~0.500)")
    print(f"  P( +5% | maxloss 10%)      = {p2.mean():.4f}  (attendu ~0.667)")
    ok = abs(p1.mean() - 0.5) < 0.02 and abs(p2.mean() - 2 / 3) < 0.02
    print(f"  --> moteur {'VALIDE' if ok else 'SUSPECT'}")
    return ok


def best_sizing(cfg, cost, pool, W):
    best = None
    for k in K_GRID:
        for sigma in SIGMA_GRID:
            r = parallel_pipeline(cfg, drift(0.0, sigma, cost), sigma, k,
                                  n=N_SWEEP, seed=7, with_funded=False, pool=pool, n_workers=W)
            if best is None or r["Pboth"] > best["Pboth"]:
                best = r
    return best


def breakeven_edge(cfg, sigma, k, cost, pool, W):
    lo, hi = 0.0, cost + 0.0008
    for _ in range(9):
        r = parallel_pipeline(cfg, drift(hi, sigma, cost), sigma, k,
                              n=80_000, seed=3, with_funded=True, pool=pool, n_workers=W)
        if r["EV"] > 0:
            break
        hi *= 1.7
    for _ in range(16):
        mid = 0.5 * (lo + hi)
        r = parallel_pipeline(cfg, drift(mid, sigma, cost), sigma, k,
                              n=N_BISECT, seed=3, with_funded=True, pool=pool, n_workers=W)
        if r["EV"] > 0:
            hi = mid
        else:
            lo = mid
    edge_star = 0.5 * (lo + hi)
    mu_star = drift(edge_star, sigma, cost)           # drift net realise au break-even
    return edge_star, annualized_sharpe(mu_star, sigma, k)


def cost_sensitivity(cfg, sigma, k, pool, W):
    rows = []
    for c in COST_GRID:
        r = parallel_pipeline(cfg, drift(0.0, sigma, c), sigma, k,
                              n=120_000, seed=5, with_funded=True, pool=pool, n_workers=W)
        rows.append((c, r["EV"], r["median"], r["p_pos"]))
    # cout de break-even (EV change de signe) par interpolation lineaire
    be_cost = None
    for (c0, e0, *_), (c1, e1, *_) in zip(rows, rows[1:]):
        if (e0 > 0) != (e1 > 0):
            be_cost = c0 + (c1 - c0) * (0 - e0) / (e1 - e0)
            break
    return rows, be_cost


def run_archetype(cfg, pool, W):
    print("\n" + "=" * 72)
    print(f"ARCHETYPE : {cfg.name}  (account ${cfg.account:,.0f}, fee ${cfg.fee:.0f}, "
          f"refund {cfg.refund_frac:.0%}, trailing={cfg.trailing}, consist={cfg.consistency})")
    print("=" * 72)

    bs = best_sizing(cfg, COST_BASE, pool, W)
    sigma, k = bs["sigma_t"], bs["k"]
    fin = parallel_pipeline(cfg, drift(0.0, sigma, COST_BASE), sigma, k,
                            n=N_FINAL, seed=21, with_funded=True, pool=pool, n_workers=W)
    print(f"  Sizing best-P(pass) : sigma/trade={sigma:.4f}  k={k}/jour  "
          f"(cout effectif {drift(0,sigma,COST_BASE)*-1:.5f}/trade)")
    print(f"  P(phase1)={fin['P1']:.3f}  P(both)={fin['Pboth']:.4f}  "
          f"P(payout|finance)={fin['P_payout_funded']:.3f}")
    print(f"  >>> EV(no-edge) = ${fin['EV']:,.0f}   mediane=${fin['median']:,.0f}   "
          f"P(net>0)={fin['p_pos']:.3f}   (fee=${cfg.fee:.0f})")

    rows, be_cost = cost_sensitivity(cfg, sigma, k, pool, W)
    print("  Sensibilite au cout (no-edge, best sizing) :")
    for c, ev, med, pp in rows:
        print(f"    cout={c:.4f}  EV=${ev:8,.0f}  mediane=${med:7,.0f}  P(>0)={pp:.3f}")
    print(f"  Cout de break-even EV=0 : {('%.5f' % be_cost) if be_cost else 'hors grille'}  "
          f"(base pre-enreg={COST_BASE})")

    edge_star, sr_star = breakeven_edge(cfg, sigma, k, COST_BASE, pool, W)
    print(f"  Break-even edge (sur la MOYENNE) : Sharpe annualise requis = {sr_star:.2f}  "
          f"(barre trend={TREND_SHARPE})")

    # Evaluation AVEC le seul edge directionnel reel (trend, Sharpe net 0.42), meme sizing.
    # mu_edge = drift net donnant un Sharpe annualise de 0.42 (Sharpe invariant a la taille).
    mu_edge = TREND_SHARPE * sigma / np.sqrt(252 * k)
    ed = parallel_pipeline(cfg, mu_edge, sigma, k, n=N_FINAL, seed=33,
                           with_funded=True, pool=pool, n_workers=W)
    print(f"  AVEC edge trend (Sharpe {TREND_SHARPE}) : EV=${ed['EV']:,.0f}  "
          f"mediane=${ed['median']:,.0f}  P(net>0)={ed['p_pos']:.3f}  P(both)={ed['Pboth']:.3f}")

    return {
        "name": cfg.name, "fee": cfg.fee, "best_sizing": {"sigma_t": sigma, "k": k},
        "EV_no_edge": fin["EV"], "median_no_edge": fin["median"], "p_pos_no_edge": fin["p_pos"],
        "P1": fin["P1"], "Pboth": fin["Pboth"], "P_payout_funded": fin["P_payout_funded"],
        "cost_curve": [{"cost": c, "EV": e, "median": m, "p_pos": p} for c, e, m, p in rows],
        "breakeven_cost": be_cost, "breakeven_edge": edge_star, "breakeven_sharpe": sr_star,
        "edge_EV": ed["EV"], "edge_median": ed["median"], "edge_p_pos": ed["p_pos"],
        "edge_Pboth": ed["Pboth"],
    }


def verdict(results):
    print("\n" + "=" * 72)
    print("VERDICT (gates pre-enregistres + honnetete distributionnelle)")
    print("=" * 72)
    # Gate durci : un PASS exige une DEPLOYABILITE reelle = avec le seul edge directionnel
    # reel (trend 0.42), l'achat doit etre +EV ET mediane>0 (pas une loterie). Le break-even
    # sur la MOYENNE est contamine par la queue chanceuse (lecon airdrop #14) -> insuffisant.
    all_kill = True
    lines = []
    for r in results:
        noedge_lottery = r["median_no_edge"] <= 0       # sans edge : on perd la fee (mediane)
        deployable = (r["edge_median"] > 0) and (r["edge_EV"] > 0)
        passes = deployable
        if passes:
            all_kill = False
        tag = "PASS" if passes else "KILL"
        ne = "loterie/-EV" if noedge_lottery else f"+EV mediane>0"
        lines.append(
            f"  [{tag}] {r['name']:18s} | no-edge: EV=${r['EV_no_edge']:,.0f} med=${r['median_no_edge']:,.0f} "
            f"P(>0)={r['p_pos_no_edge']:.2f} ({ne}) | avec-trend-0.42: EV=${r['edge_EV']:,.0f} "
            f"med=${r['edge_median']:,.0f} P(>0)={r['edge_p_pos']:.2f}")
    for l in lines:
        print(l)
    print("-" * 72)
    if all_kill:
        print("  KILL. Sans edge = loterie (mediane = -fee, queue chanceuse porte la moyenne,")
        print("  motif airdrop #14). MEME avec le seul edge reel (trend 0.42), la mediane reste")
        print("  <=0 ou l'EV <=0 -> pas deployable en solo one-shot. Produit a marge maison (#16).")
    else:
        print("  PASS : avec le trend, l'achat devient +EV ET mediane>0 (deployable, pas loterie).")
        print("  -> piste B (overlay GEX-survie + execution trend) justifiee sur cet archetype.")
    return {"all_kill": all_kill, "lines": lines}


def main():
    t0 = time.time()
    W = os.cpu_count() or 1
    print(f"Parallelisation : {W} coeurs CPU\n")
    if not sanity_checks():
        print("\n!! Sanity-check echoue -> stop.")
        return
    with mp.Pool(W) as pool:
        results = [run_archetype(base_config(), pool, W),
                   run_archetype(stress_config(), pool, W)]
        v = verdict(results)
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(os.path.join(HERE, "data", "gate_results.json"), "w", encoding="utf-8") as f:
        json.dump({"trend_sharpe_bar": TREND_SHARPE, "cost_base": COST_BASE, "slip": SLIP,
                   "archetypes": results, "verdict": v}, f, indent=2, ensure_ascii=False)
    print(f"\nResultats -> data/gate_results.json   ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()

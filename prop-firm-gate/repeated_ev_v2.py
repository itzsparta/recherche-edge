"""
Étude #26 — SIM v2 : coût SCALÉ-LEVIER (réponse à la revue technique du Brief #26).

La revue soulève 5 points. Tri honnête :
  1. Daily-DD = 2e barrière absorbante mobile  -> DÉJÀ modélisé (challenge.py:77 /
     repeated_ev.py:62 : floor = max(static, s - daily_dd)). PAS un gap. Faux.
  3. Voiding discrétionnaire ciblé (signature buffer-skim) -> NON simulable, déjà
     porté en résidu n°1 ; break-even p_void déjà dans repeated_ev_stress.py.
  4. K achats séquentiels indépendants -> légal sous règles actuelles, rien à coder ;
     la LLN ne sauve QUE si l'EV/achat reste >0 (ce que cette v2 teste).
  2+5. σ haute coûte cher + swap/spread-minuit/slippage -> LE vrai gap. Ces frictions
     scalent en LEVIER L = σ_day / σ_actif. Le modèle v1 a cost = c_fixe + SLIP·σ :
     linéaire en σ mais NE divise PAS par σ_actif -> sous-estime le coût de sizer haut.

v2 = re-coût levier-aware, ré-optimise σ (le harvest VOULAIT σ haute pour skim vite ;
maintenant σ haute = L haut = swap haut -> nouvel optimum), puis re-run G1/G2/G3 et
compare l'EV/break-even à v1. Slippage-au-stop (5.c) : NON ajouté — au-delà de la
barrière, la firme absorbe la perte (le trader ne perd jamais > le compte), donc ce
n'est pas un coût trader. Noté, écarté avec raison.

Deux régimes de tenue de position, on prend le MOINS cher (le harvester optimise) :
  hold  : tient overnight  -> swap + notch-spread-minuit, ∝ L
  flat  : flat-avant-minuit -> pas de swap, mais +1 franchissement de spread/j, ∝ L

Discipline INVERSEE conservée : seuils figés (G1 EV>0 @5bp & break-even≥5bp ; G2
trailing≤0 ; G3 K=20 P>0.5). Params friction bornés CONSERVATEURS (= rendent le GO
plus dur), balayés en sensibilité sur σ_actif (le driver de L).

Usage : <venv>/python.exe repeated_ev_v2.py
"""
from __future__ import annotations
import importlib.util, os, sys, json, time
from multiprocessing import Pool, cpu_count
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("rev", os.path.join(HERE, "repeated_ev.py"))
rev = importlib.util.module_from_spec(spec); sys.modules["rev"] = rev
spec.loader.exec_module(rev)
DATA = os.path.join(HERE, "data")

rev.SUB = 24                 # monitoring réaliste (stress montre convergence EV @48 ; 24 = compromis)
N = 40_000
C_FIXED = 0.0005             # commission/half-spread de base 5 bp/j (hors levier)
SIGMA_GRID_V2 = [0.007, 0.010, 0.015, 0.020, 0.025, 0.030, 0.040]  # étendu : ferme le caveat de bord

# --- friction scalée-levier (bp par unité de levier par jour), bornées conservateur ---
SWAP_BP   = 1.5   # swap/rollover overnight, asymétrique retail (~rate/252 sur indices)
WIDEN_BP  = 0.5   # notch mark-to-market d'élargissement du spread à minuit (hold only)
REENTRY_BP = 1.0  # franchissement de spread supplémentaire si on flatte avant minuit
SIGMA_ASSET_GRID = [0.005, 0.007, 0.010]   # σ/jour de l'actif NON levé (FX ~0.5%, indice ~1%)
SIGMA_ASSET_BASE = 0.007


def lev_cost(c_fixed, sigma, sigma_asset, mode):
    """Coût/jour scalé-levier. L = sigma/sigma_asset (levier requis pour viser sigma)."""
    L = sigma / sigma_asset
    base = c_fixed + rev.SLIP * sigma
    if mode == "hold":
        return base + (SWAP_BP + WIDEN_BP) * 1e-4 * L
    return base + REENTRY_BP * 1e-4 * L     # flat


BREAKEVEN_GRID = (0.0003, 0.0005, 0.0010, 0.0020, 0.0030)


def _ev_task(args):
    """Worker : un point (kind, r_dict, c_fixe, σ, σ_actif, mode). Sims indép. = exactes."""
    kind, r_dict, c_fixed, sigma, sigma_asset, mode, n, seed = args
    r = rev.Rules(**r_dict)
    rng = np.random.default_rng(seed)
    cd = rev.cost_day(c_fixed, sigma) if kind == "v1" else lev_cost(c_fixed, sigma, sigma_asset, mode)
    e = rev.ev_components(r, cd, sigma, n, rng)
    e.update(kind=kind, mode=mode, sigma_asset=sigma_asset, c_fixed=c_fixed,
             cost_day_eff=cd, L=(sigma / sigma_asset if sigma_asset else 0.0))
    return e


def _dist_worker(args):
    """Worker bankroll : un chunk de traders -> tableau net$ (concat = distribution exacte)."""
    r_dict, cost_day, sigma_day, n, seed = args
    rng = np.random.default_rng(seed)
    return rev.sim_pipeline_net(n, rev.Rules(**r_dict), cost_day, sigma_day, rng).astype(np.float32)


def _pipeline_dist(pool, nproc, r, cost_day, sigma_day, n, seed):
    """Distribution net$/achat en chunks parallèles (sims indépendantes = exactes)."""
    rd = dict(r.__dict__)
    base_n = n // nproc
    sizes = [base_n + (1 if i < n % nproc else 0) for i in range(nproc)]
    args = [(rd, cost_day, sigma_day, s, seed * 131 + i) for i, s in enumerate(sizes) if s > 0]
    return np.concatenate(pool.map(_dist_worker, args))


def _best(results, kind, sigma_asset=None):
    cand = [e for e in results if e["kind"] == kind
            and (sigma_asset is None or e["sigma_asset"] == sigma_asset)]
    return max(cand, key=lambda e: e["EV"])


def main():
    t0 = time.time()
    base = rev.base(); stress = rev.stress()
    bd = dict(base.__dict__); sd = dict(stress.__dict__)
    out = {"params": {"C_FIXED": C_FIXED, "SWAP_BP": SWAP_BP, "WIDEN_BP": WIDEN_BP,
                      "REENTRY_BP": REENTRY_BP, "SIGMA_ASSET_GRID": SIGMA_ASSET_GRID,
                      "SUB": rev.SUB}, "static": {}, "trailing": {}}
    nproc = max(1, cpu_count() - 1)
    print(f"[parallel] {nproc} workers, SUB={rev.SUB}, N={N:,}", flush=True)

    # --- Phase 1 : tous les points de sweep en parallèle (indépendants) ---
    tasks = []
    for sg in rev.SIGMA_GRID:                                   # v1 réf (coût sans levier)
        tasks.append(("v1", bd, C_FIXED, sg, None, "none", N, 0))
    for sa in SIGMA_ASSET_GRID:                                 # static best_sizing par σ_actif
        for mode in ("hold", "flat"):
            for sg in SIGMA_GRID_V2:
                tasks.append(("static", bd, C_FIXED, sg, sa, mode, N, 0))
    for mode in ("hold", "flat"):                              # trailing best_sizing (σ_actif base)
        for sg in SIGMA_GRID_V2:
            tasks.append(("trailing", sd, C_FIXED, sg, SIGMA_ASSET_BASE, mode, N, 0))
    tasks = [t[:-1] + (1000 + i,) for i, t in enumerate(tasks)]  # seed distinct/tâche

    with Pool(nproc) as pool:
        ph1 = pool.map(_ev_task, tasks)

        v1 = _best(ph1, "v1")
        out["v1_ref"] = {"EV": v1["EV"], "sigma": v1["sigma_day"], "Pboth": v1["Pboth"]}
        static_best = {sa: _best(ph1, "static", sa) for sa in SIGMA_ASSET_GRID}
        rt_b = _best(ph1, "trailing")

        # --- Phase 2 : break-even (au sizing/mode optimal du σ_actif base) en parallèle ---
        bb = static_best[SIGMA_ASSET_BASE]
        be_tasks = [("static", bd, c, bb["sigma_day"], SIGMA_ASSET_BASE, bb["mode"], N, 5000 + j)
                    for j, c in enumerate(BREAKEVEN_GRID)]
        be_res = pool.map(_ev_task, be_tasks)
        curve = sorted([(e["c_fixed"], e["EV"]) for e in be_res])
        be = next((c0 + (c1 - c0) * (0 - e0) / (e1 - e0)
                   for (c0, e0), (c1, e1) in zip(curve, curve[1:]) if (e0 > 0) != (e1 > 0)), None)

        # --- bankroll : distribution réelle, chunks parallèles via parallel_pipeline ---
        cd_b = lev_cost(C_FIXED, bb["sigma_day"], SIGMA_ASSET_BASE, bb["mode"])
        D = _pipeline_dist(pool, nproc, base, cd_b, bb["sigma_day"], n=120_000, seed=55)

    camp = rev.campaign(D, base.fee_paid, [1, 5, 10, 20, 50])

    print("=" * 78 + "\n#26 SIM v2 — coût scalé-levier (swap+spread-minuit ∝ L=σ/σ_actif)\n" + "=" * 78)
    print(f"  v1 réf (coût sans levier) : EV=${v1['EV']:,.0f}  @σ={v1['sigma_day']:.3f}\n")
    print("STATIC FTMO-like — EV @5bp + sizing/mode optimal, sensibilité σ_actif :")
    for sa in SIGMA_ASSET_GRID:
        b = static_best[sa]
        be_show = be * 1e4 if (sa == SIGMA_ASSET_BASE and be) else 0
        k20p = (next(c for c in camp if c["K"] == 20)["P_profit"]
                if sa == SIGMA_ASSET_BASE else float("nan"))
        out["static"][f"sa_{sa}"] = {"best": b, "breakeven_cfixed": (be if sa == SIGMA_ASSET_BASE else None)}
        print(f"  σ_actif={sa:.3f} (L*={b['L']:.1f}, mode={b['mode']:4s})  "
              f"EV=${b['EV']:8,.0f}  σ*={b['sigma_day']:.3f}  "
              f"cout_eff={b['cost_day_eff']*1e4:4.1f}bp  Pboth={b['Pboth']:.3f}  "
              f"break-even={be_show:4.1f}bp  K20 P(>0)={k20p:.2f}")
    out["static"][f"sa_{SIGMA_ASSET_BASE}"].update(
        cost_curve=[{"c": c, "EV": e} for c, e in curve], bankroll=camp,
        net_mean=float(D.mean()), net_median=float(np.median(D)), net_p_pos=float((D > 0).mean()))
    out["trailing"][f"sa_{SIGMA_ASSET_BASE}"] = {"best": rt_b}
    print("\nTRAILING Topstep-like (doit rester ≤0) :")
    print(f"  σ_actif={SIGMA_ASSET_BASE}  EV=${rt_b['EV']:,.0f}  (mode={rt_b['mode']})")

    rt = {"best": rt_b}
    base_res = out["static"][f"sa_{SIGMA_ASSET_BASE}"]
    EV = base_res["best"]["EV"]; be = base_res["breakeven_cfixed"] or 0
    k20 = next(c for c in base_res["bankroll"] if c["K"] == 20)
    G1 = EV > 0 and be >= C_FIXED
    G2 = rt["best"]["EV"] <= 0
    G3 = k20["P_profit"] > 0.50
    go = G1 and G2 and G3
    print("\n" + "=" * 78 + "\nVERDICT v2 (σ_actif=0.007, coût base 5bp + levier)\n" + "=" * 78)
    print(f"  G1 EV=${EV:,.0f} & break-even={be*1e4:.1f}bp (≥5) -> {'PASS' if G1 else 'FAIL'}")
    print(f"  G2 trailing EV=${rt['best']['EV']:,.0f} (≤0)        -> {'PASS' if G2 else 'FAIL'}")
    print(f"  G3 K=20 P(>0)={k20['P_profit']:.3f} (>0.5)          -> {'PASS' if G3 else 'FAIL'}")
    print("-" * 78)
    print(f"  >>> v2 {'GO maintenu' if go else 'KILL — le coût-levier mange le buffer'}")
    print(f"      EV v1=${v1['EV']:,.0f} -> v2=${EV:,.0f} "
          f"(dégradation {100*(1-EV/v1['EV']) if v1['EV'] else 0:.0f}%)")
    print("      résidu non-simulable inchangé : voiding/résiliation sur signature (point 3)")
    out["verdict"] = {"G1": bool(G1), "G2": bool(G2), "G3": bool(G3),
                      "verdict": "GO" if go else "KILL", "EV_v1": v1["EV"], "EV_v2": EV}
    json.dump(out, open(os.path.join(DATA, "repeated_ev_v2.json"), "w"),
              indent=2, ensure_ascii=False)
    print(f"\n  -> data/repeated_ev_v2.json   ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()

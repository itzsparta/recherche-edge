"""
Etude #26 — CHASSE AU FAUX-GO (post-GO mirage hunt), monitoring REALISTE.

repeated_ev.py rend GO (1er du programme). Le programme a deja produit 2 faux-GO
(VRP t=1.86, CEF t=7.13) qui passaient les gates et mouraient en post-GO. Discipline :
un GO declenche une chasse adverse OBLIGATOIRE avant verdict. On frappe les 3 axes qui
ont tue les faux-GO precedents :

  A. MONITORING (discretisation type-VRP) : SUB=6 sous-detecte les breach intraday
     => sur-estime la survie => gonfle l'EV. On raffine SUB et on re-optimise sigma.
  B. FRICTION DE PAYOUT (lag d'entree type-CEF) : le skim 'every 14d, reset 1.0' suppose
     une extraction on-demand frictionless. Reel : delai 1er payout + cycles plus longs
     => l'excursion s'evapore / breach avant de banker, sous cout-drift.
  C. VOIDING (residuel non-simulable) : p_void de break-even (firme qui refuse les
     payouts 'non-real-trading').

Fait porteur VERIFIE (web, 2026) : FTMO 2-Step funded = max loss 10% STATIQUE (ne trail
pas) + daily 5%. C'est l'archetype base() => la martingale buffer-harvest est reelle.
Le 1-Step (trailing EOD) serait le cas KILL : non utilise.

Usage : <venv>/python.exe repeated_ev_stress.py
"""
from __future__ import annotations
import importlib.util, os, sys, json, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("rev", os.path.join(HERE, "repeated_ev.py"))
rev = importlib.util.module_from_spec(spec); sys.modules["rev"] = rev
spec.loader.exec_module(rev)
COST = rev.cost_day
DATA = os.path.join(HERE, "data")

N = 90_000
SIG = 0.020          # sigma* du run principal (confirme stable, cf. A)
C_REAL = 0.0005      # cout realiste 5 bp/j (+ slip => ~7 bp @ sigma 0.02)


def sim_funded_friction(n, r, cost_day, sigma_day, rng, first_payout_day=0):
    """sim_funded + delai 1er payout (pas de skim avant first_payout_day)."""
    eq = np.ones(n); peak = np.ones(n); alive = np.ones(n, bool)
    skim = np.zeros(n); got = np.zeros(n, bool); mu = -cost_day
    for day in range(r.funded_horizon):
        idx = np.where(alive)[0]
        if idx.size == 0:
            break
        s = eq[idx]; pk = peak[idx]
        end, low, high, bidx, path, floor = rev._day_step(s, pk, mu, sigma_day,
                                                          r.max_dd, r.daily_dd, r.trailing, rng)
        breach = bidx <= rev.SUB
        eq[idx] = end; peak[idx] = np.maximum(pk, high)
        if (day + 1) >= first_payout_day and (day + 1) % r.payout_days == 0:
            excess = np.maximum(eq[idx] - 1.0, 0.0)
            if r.funded_consistency > 0:
                excess = np.minimum(excess, r.funded_consistency)
            skim[idx] += excess; got[idx[excess > 0]] = True; eq[idx] -= excess
        alive[idx[breach]] = False
    return skim, got


def ev_with(r, c_fixed, sigma, payout_days=14, first_payout_day=0, n=N, seed=21):
    rng = np.random.default_rng(seed)
    cd = COST(c_fixed, sigma)
    Pboth = rev.sim_phase(n, r.phases[0], r, cd, sigma, rng).mean() * \
            rev.sim_phase(n, r.phases[1], r, cd, sigma, rng).mean()
    rr = rev.Rules(**{**r.__dict__, "payout_days": payout_days})
    skim, got = sim_funded_friction(n, rr, cd, sigma, rng, first_payout_day)
    skim_usd = skim.mean() * r.account * r.split
    refund = Pboth * got.mean() * r.refund_frac * r.fee_nominal
    funded = Pboth * skim_usd
    return dict(EV=funded + refund - r.fee_paid, Pboth=float(Pboth), skim=float(skim.mean()),
                Ppay=float(got.mean()), funded=float(funded), refund=float(refund),
                fee=float(r.fee_paid), gross=float(funded + refund))


def main():
    t0 = time.time(); r = rev.base(); out = {}

    print("=" * 74 + "\nA. MONITORING : EV(static, cout 5bp, sigma 0.020) vs finesse SUB\n" + "=" * 74)
    out["A_sub"] = []
    for sub in [6, 12, 24, 48]:
        rev.SUB = sub
        e = rev.ev_components(r, COST(C_REAL, SIG), SIG, 200_000, np.random.default_rng(21))
        out["A_sub"].append(dict(SUB=sub, EV=e["EV"], Pboth=e["Pboth"],
                                 skim=e["E_skim_frac_given_funded"]))
        print(f"  SUB={sub:3d}  EV=${e['EV']:8,.0f}  Pboth={e['Pboth']:.3f}  "
              f"skim={e['E_skim_frac_given_funded']:.4f}")
    print("  re-sizing @SUB=48 (sigma* peut chuter si l'optimum etait un artefact) :")
    rev.SUB = 48; best = None; rng = np.random.default_rng(7)
    out["A_resize48"] = []
    for sg in rev.SIGMA_GRID:
        e = rev.ev_components(r, COST(C_REAL, sg), sg, 200_000, rng)
        out["A_resize48"].append(dict(sigma=sg, EV=e["EV"], Pboth=e["Pboth"]))
        print(f"    sigma={sg:.3f}  EV=${e['EV']:8,.0f}")
        if best is None or e["EV"] > best["EV"]:
            best = e
    out["A_sigma_star_48"] = best["sigma_day"]
    print(f"  -> sigma* @SUB48 = {best['sigma_day']:.3f} (EV ${best['EV']:,.0f})")

    rev.SUB = 48      # tout le reste a monitoring REALISTE
    print("\n" + "=" * 74 + "\nB. break-even cout HONNETE @ SUB=48, sigma=0.020\n" + "=" * 74)
    curve = []
    for c in [0.0003, 0.0005, 0.0010, 0.0015, 0.0020, 0.0030]:
        e = ev_with(r, c, SIG)
        curve.append((c, e["EV"]))
        print(f"  cout={c:.4f} ({c*1e4:2.0f}bp)  EV=${e['EV']:8,.0f}  Pboth={e['Pboth']:.3f}")
    be = next((c0 + (c1 - c0) * (0 - e0) / (e1 - e0)
               for (c0, e0), (c1, e1) in zip(curve, curve[1:]) if (e0 > 0) != (e1 > 0)), None)
    out["B_breakeven_cost"] = be
    out["B_cost_curve"] = [{"cost": c, "EV": e} for c, e in curve]
    print(f"  -> break-even cout = {('%.4f/j (%.1f bp)' % (be, be*1e4)) if be else 'hors grille'}")

    print("\n" + "=" * 74 + "\nC. FRICTION PAYOUT @ cout 5bp, sigma 0.020, SUB=48\n" + "=" * 74)
    out["C_friction"] = []; base_e = None
    for pd_ in [14, 30, 60]:
        for fd in [0, 30, 60]:
            if fd and fd < pd_:
                continue
            e = ev_with(r, C_REAL, SIG, payout_days=pd_, first_payout_day=fd)
            if pd_ == 14 and fd == 0:
                base_e = e
            out["C_friction"].append(dict(cycle=pd_, delay=fd, EV=e["EV"], gross=e["gross"]))
            print(f"  cycle={pd_:2d}j delai1er={fd:2d}j  EV=${e['EV']:8,.0f}  gross=${e['gross']:,.0f}")

    pv = 1 - base_e["fee"] / base_e["gross"]
    out["D_pvoid_breakeven"] = pv
    print("\n" + "=" * 74 + "\nD. VOIDING break-even (cycle 14, cout 5bp, SUB=48)\n" + "=" * 74)
    print(f"  gross extractible=${base_e['gross']:,.0f}  fee=${base_e['fee']:,.0f}  "
          f"-> EV=0 si p_void={pv:.1%}  (EV>0 tant que p_void<{pv:.1%})")

    out["survives"] = bool(base_e["EV"] > 0 and (be or 0) >= C_REAL and
                           all(c["EV"] > 0 for c in out["C_friction"]))
    print("\n" + "=" * 74)
    print(f"  >>> GO survit a la chasse adverse : {out['survives']}  "
          f"(EV>0 a tous les axes simulables ; residu = voiding)")
    json.dump(out, open(os.path.join(DATA, "repeated_ev_stress.json"), "w"),
              indent=2, ensure_ascii=False)
    print(f"  -> data/repeated_ev_stress.json  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()

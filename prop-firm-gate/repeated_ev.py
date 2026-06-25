"""
Etude #26 — Prop firm en JEU REPETE : EV par achat (pas mediane) + bankroll.
Pre-enregistre : docs/SPEC-repeated.md.

Re-ouverture de #24 sous le bon critere (objection Remi : 'un payout suffit, pas besoin
de battre le marche'). En jeu repete, c'est la MOYENNE (EV) qui gouverne, pas la mediane.

Mecanisme : martingale d'extraction du buffer. Compte static-maxDD, skim+reset, drift nul
=> E[skim] = m (le buffer). +EV reel sous no-edge = le buffer que la firme offre. Ennemis :
cout (drift), trailing (casse le buffer), regles funded, variance/bankroll, voiding.

Modele daily vectorise. Gates G1 (EV>0 cout reel) / G2 (vraies regles) / G3 (bankroll).
Discipline INVERSEE : biaise vers GO => seuils figes avant run, pas de KILL par prior #16.

Usage : <venv>/python.exe repeated_ev.py
"""
from __future__ import annotations
from dataclasses import dataclass
import json, os, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)
SUB = 6                      # sous-etapes intraday (daily-DD)
HARD_CAP = 1000             # borne dure jours/phase


@dataclass
class Rules:
    name: str = "FTMO-static"
    account: float = 100_000.0
    fee_nominal: float = 540.0
    discount: float = 0.30          # codes promo => fee payee = nominal*(1-discount)
    refund_frac: float = 1.0        # remboursement sur fee NOMINALE au 1er payout
    phases: tuple = (0.10, 0.05)
    max_dd: float = 0.10
    daily_dd: float = 0.05
    trailing: bool = False
    funded_min_days_cycle: int = 4
    funded_consistency: float = 0.0  # 0 = aucune ; sinon cap skim/cycle = consistency*account
    split: float = 0.80
    payout_days: int = 14
    funded_horizon: int = 504

    @property
    def fee_paid(self):
        return self.fee_nominal * (1 - self.discount)


def _first_idx(mask, big):
    any_ = mask.any(axis=1)
    return np.where(any_, mask.argmax(axis=1), big)


def _day_step(s, peak, mu_day, sigma_day, max_dd, daily_dd, trailing, rng):
    """Un jour, sous-etapes intraday. Retourne (end_eq, low, high, breach_first_idx, path, floor)."""
    m = s.size
    z = rng.standard_normal((m, SUB))
    incr = mu_day / SUB + (sigma_day / np.sqrt(SUB)) * z
    path = s[:, None] + np.cumsum(incr, axis=1)
    ofloor = (peak - max_dd) if trailing else np.full(m, 1.0 - max_dd)
    floor = np.maximum(ofloor, s - daily_dd)
    breach = path < floor[:, None]
    return path[:, -1], path.min(1), path.max(1), _first_idx(breach, SUB + 1), path, floor


def sim_phase(n, target, r: Rules, cost_day, sigma_day, rng):
    """n traders sur une phase. Retourne passed bool[n]."""
    eq = np.ones(n); peak = np.ones(n)
    status = np.zeros(n, np.int8)
    mu = -cost_day
    tgt = 1.0 + target
    for _ in range(HARD_CAP):
        act = status == 0
        if not act.any():
            break
        idx = np.where(act)[0]
        s = eq[idx]; pk = peak[idx]
        end, low, high, bidx, path, floor = _day_step(s, pk, mu, sigma_day,
                                                      r.max_dd, r.daily_dd, r.trailing, rng)
        tmask = path >= tgt
        tidx = _first_idx(tmask, SUB + 1)
        reached = tidx < bidx
        breached = (bidx <= SUB) & ~reached
        new = np.zeros(idx.size, np.int8)
        new[reached] = 1
        new[breached] = -1
        status[idx] = new
        eq[idx] = end
        peak[idx] = np.maximum(pk, high)
    return status == 1


def sim_funded(n, r: Rules, cost_day, sigma_day, rng):
    """n comptes finances. Retourne (skim_fraction[n] pre-split, got_payout bool[n])."""
    eq = np.ones(n); peak = np.ones(n)
    alive = np.ones(n, bool)
    skim = np.zeros(n)
    got = np.zeros(n, bool)
    mu = -cost_day
    for day in range(r.funded_horizon):
        idx = np.where(alive)[0]
        if idx.size == 0:
            break
        s = eq[idx]; pk = peak[idx]
        end, low, high, bidx, path, floor = _day_step(s, pk, mu, sigma_day,
                                                      r.max_dd, r.daily_dd, r.trailing, rng)
        breach = bidx <= SUB
        eq[idx] = end
        peak[idx] = np.maximum(pk, high)
        if (day + 1) % r.payout_days == 0:
            excess = np.maximum(eq[idx] - 1.0, 0.0)
            if r.funded_consistency > 0:
                excess = np.minimum(excess, r.funded_consistency)
            pay = excess > 0
            skim[idx] += excess
            got[idx[pay]] = True
            eq[idx] -= excess
            if r.trailing:
                peak[idx] = np.maximum(1.0, eq[idx])     # reset trailing apres retrait (approx)
        alive[idx[breach]] = False
    return skim, got


def ev_components(r: Rules, cost_day, sigma_day, n, rng):
    """EV decompose + P(both), E[skim|funded], P(payout)."""
    p1 = sim_phase(n, r.phases[0], r, cost_day, sigma_day, rng)
    P1 = p1.mean()
    if len(r.phases) > 1:
        p2 = sim_phase(n, r.phases[1], r, cost_day, sigma_day, rng)
        P2 = p2.mean()
    else:
        P2 = 1.0
    Pboth = P1 * P2
    skim, got = sim_funded(n, r, cost_day, sigma_day, rng)
    E_skim_frac = skim.mean()
    P_payout = got.mean()
    skim_usd = E_skim_frac * r.account * r.split
    refund = Pboth * P_payout * r.refund_frac * r.fee_nominal
    funded_term = Pboth * skim_usd
    ev = funded_term + refund - r.fee_paid
    return {"P1": float(P1), "P2": float(P2), "Pboth": float(Pboth),
            "E_skim_frac_given_funded": float(E_skim_frac), "P_payout": float(P_payout),
            "skim_usd_per_funded": float(skim_usd), "funded_term": float(funded_term),
            "refund_term": float(refund), "fee_paid": float(r.fee_paid), "EV": float(ev),
            "cost_day": float(cost_day), "sigma_day": float(sigma_day)}


def sim_pipeline_net(n, r: Rules, cost_day, sigma_day, rng):
    """Distribution du net $ par achat (pour le bankroll)."""
    net = np.full(n, -r.fee_paid)
    p1 = sim_phase(n, r.phases[0], r, cost_day, sigma_day, rng)
    i1 = np.where(p1)[0]
    if len(r.phases) > 1 and i1.size:
        p2 = sim_phase(i1.size, r.phases[1], r, cost_day, sigma_day, rng)
        funded = i1[p2]
    else:
        funded = i1
    if funded.size:
        skim, got = sim_funded(funded.size, r, cost_day, sigma_day, rng)
        net[funded] += skim * r.account * r.split + np.where(got, r.refund_frac * r.fee_nominal, 0.0)
    return net


SIGMA_GRID = [0.004, 0.007, 0.01, 0.015, 0.02, 0.03]
COST_GRID = [0.0001, 0.0003, 0.0005, 0.001, 0.002, 0.004, 0.008]   # /jour : 1bp -> 80bp
SLIP = 0.01
N = 120_000


def cost_day(c_fixed, sigma):
    return c_fixed + SLIP * sigma


def best_sizing(r, c_fixed, seed=1):
    rng = np.random.default_rng(seed)
    best = None
    for sg in SIGMA_GRID:
        e = ev_components(r, cost_day(c_fixed, sg), sg, N, rng)
        if best is None or e["EV"] > best["EV"]:
            best = e
    return best


def sanity(r: Rules):
    print("=" * 74 + "\n0. SANITY\n" + "=" * 74)
    rng = np.random.default_rng(7)
    # martingale : cost=0, static, skim => E[skim|funded] ~ m
    r0 = Rules(max_dd=r.max_dd, daily_dd=9.9, trailing=False, payout_days=14,
               funded_consistency=0.0, funded_horizon=2000)
    skim, got = sim_funded(120_000, r0, 0.0, 0.01, rng)
    print(f"  Martingale cost=0 : E[skim|funded]={skim.mean():.4f}  attendu m={r.max_dd:.4f}  "
          f"P(payout)={got.mean():.3f}")
    g = Rules(max_dd=0.10, daily_dd=9.9)
    p1 = sim_phase(120_000, 0.10, g, 0.0, 0.01, rng)
    p2 = sim_phase(120_000, 0.05, g, 0.0, 0.01, rng)
    print(f"  Gambler ruin : P(+10%|10%)={p1.mean():.3f} (~0.5)  P(+5%|10%)={p2.mean():.3f} (~0.667)")
    ok = abs(skim.mean() - r.max_dd) < 0.02 and abs(p1.mean() - 0.5) < 0.03
    print(f"  --> moteur {'VALIDE' if ok else 'SUSPECT'}")
    return ok


def campaign(D, fee_paid, Ks, sims=200_000, seed=3):
    """Mode budget fixe : acheter K challenges. P(somme net>0), mediane, EV*K."""
    rng = np.random.default_rng(seed)
    out = []
    for K in Ks:
        draws = rng.choice(D, size=(sims, K), replace=True).sum(axis=1)
        out.append({"K": K, "P_profit": float((draws > 0).mean()),
                    "median": float(np.median(draws)), "mean": float(draws.mean()),
                    "budget": float(K * fee_paid)})
    return out


def run(r: Rules):
    print("\n" + "=" * 74 + f"\nARCHETYPE {r.name}  (fee payee ${r.fee_paid:.0f} / nominale "
          f"${r.fee_nominal:.0f}, refund {r.refund_frac:.0%}, trailing={r.trailing})\n" + "=" * 74)
    # G1 : EV vs cout, sizing-optimale a chaque cout
    print("  EV(no-edge) vs cout/jour (sizing harvest-optimale) :")
    curve = []
    for c in COST_GRID:
        b = best_sizing(r, c)
        curve.append((c, b["EV"], b["sigma_day"], b["Pboth"], b["E_skim_frac_given_funded"]))
        print(f"    cout/j={c:.4f}  EV=${b['EV']:8,.0f}  (sigma*={b['sigma_day']:.3f} "
              f"Pboth={b['Pboth']:.3f}  E[skim|fund]={b['E_skim_frac_given_funded']:.3f})")
    be = None
    for (c0, e0, *_), (c1, e1, *_) in zip(curve, curve[1:]):
        if (e0 > 0) != (e1 > 0):
            be = c0 + (c1 - c0) * (0 - e0) / (e1 - e0)
            break
    print(f"  Cout de break-even EV=0 : {('%.4f/j (%.1f bp)' % (be, be*1e4)) if be else 'hors grille'}")

    # point realiste : cout 5 bp/jour
    c_real = 0.0005
    bbest = best_sizing(r, c_real)
    full = ev_components(r, cost_day(c_real, bbest["sigma_day"]), bbest["sigma_day"], 300_000,
                         np.random.default_rng(21))
    print(f"\n  @ cout realiste 5bp/j, sizing* sigma={bbest['sigma_day']:.3f} :")
    print(f"    EV=${full['EV']:,.0f}  = funded ${full['funded_term']:,.0f} + refund "
          f"${full['refund_term']:,.0f} - fee ${full['fee_paid']:,.0f}")
    print(f"    Pboth={full['Pboth']:.3f}  E[skim|funded]={full['E_skim_frac_given_funded']:.3f} "
          f"(buffer m={r.max_dd})  P(payout|funded)={full['P_payout']:.3f}")

    # G3 : bankroll (distribution reelle)
    rng = np.random.default_rng(55)
    D = sim_pipeline_net(300_000, r, cost_day(c_real, bbest["sigma_day"]), bbest["sigma_day"], rng)
    Ks = [1, 5, 10, 20, 50]
    camp = campaign(D, r.fee_paid, Ks)
    print(f"  Bankroll (budget fixe K achats, cout 5bp/j) :")
    for c in camp:
        print(f"    K={c['K']:2d} (budget ${c['budget']:6,.0f})  P(somme>0)={c['P_profit']:.3f}  "
              f"mediane=${c['median']:8,.0f}  moyenne=${c['mean']:8,.0f}")

    return {"name": r.name, "ev_cost_curve": [{"cost": c, "EV": e, "sigma": s, "Pboth": p,
            "skim": k} for c, e, s, p, k in curve], "breakeven_cost": be,
            "realistic": full, "bankroll": camp, "net_dist_mean": float(D.mean()),
            "net_dist_median": float(np.median(D)), "net_dist_p_pos": float((D > 0).mean())}


def base():  # STATIC FTMO-like
    return Rules(name="FTMO-static", trailing=False, max_dd=0.10, daily_dd=0.05,
                 phases=(0.10, 0.05), funded_consistency=0.0, split=0.80)


def stress():  # TRAILING Topstep-like (devrait tuer le buffer)
    return Rules(name="Topstep-trailing", account=50_000.0, fee_nominal=330.0, discount=0.0,
                 refund_frac=0.0, phases=(0.06,), max_dd=0.04, daily_dd=0.03, trailing=True,
                 funded_consistency=0.20, split=0.90)


def verdict(res):
    print("\n" + "=" * 74 + "\nVERDICT (G1 EV>0 cout reel / G2 vraies regles+trailing tue / G3 bankroll)\n" + "=" * 74)
    st = next(r for r in res if not r["name"].endswith("trailing"))
    tr = next(r for r in res if r["name"].endswith("trailing"))
    G1 = st["realistic"]["EV"] > 0 and (st["breakeven_cost"] or 0) >= 0.0005
    G2 = (tr["realistic"]["EV"] <= 0)            # le trailing DOIT tuer le buffer (coherence)
    k20 = next(c for c in st["bankroll"] if c["K"] == 20)
    G3 = k20["P_profit"] > 0.50
    print(f"  G1 static EV@5bp=${st['realistic']['EV']:,.0f}  break-even cout="
          f"{(st['breakeven_cost'] or 0)*1e4:.1f}bp/j  -> {'PASS' if G1 else 'FAIL'}")
    print(f"  G2 trailing EV@5bp=${tr['realistic']['EV']:,.0f} (doit etre <=0) -> {'PASS' if G2 else 'FAIL'}")
    print(f"  G3 bankroll K=20 P(somme>0)={k20['P_profit']:.3f} (>0.5) -> {'PASS' if G3 else 'FAIL'}")
    go = G1 and G2 and G3
    print("-" * 74)
    print(f"  >>> {'GO' if go else 'KILL'}")
    if go:
        print("  +EV REPETE REEL sous no-edge (buffer-harvest static survit au cout) ET realisable")
        print("  bankroll modeste. Risque residuel n1 = VOIDING discretionnaire (non modelise, ne")
        print("  peut que nuire) : clause anti-'non-real-trading'. PREMIER GO du programme.")
    else:
        why = []
        if not G1: why.append("cout mange le buffer (G1)")
        if not G2: why.append("trailing ne tue pas = modele suspect (G2)")
        if not G3: why.append("variance exige un bankroll deraisonnable (G3)")
        print("  Killer(s) : " + " ; ".join(why))
    return {"G1": bool(G1), "G2": bool(G2), "G3": bool(G3), "verdict": "GO" if go else "KILL"}


def main():
    t0 = time.time()
    if not sanity(base()):
        print("Sanity echoue -> stop."); return
    res = [run(base()), run(stress())]
    v = verdict(res)
    json.dump({"archetypes": res, "verdict": v, "cost_grid": COST_GRID, "slip": SLIP},
              open(os.path.join(DATA, "repeated_ev_results.json"), "w"), indent=2, ensure_ascii=False)
    print(f"\n-> data/repeated_ev_results.json   ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()

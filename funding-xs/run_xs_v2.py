"""Piste 11-v2 — funding XS lissé 7j, holding 7j. Gates A-F pré-enregistrés (docs/SPEC-v2.md).

Même univers/terciles/coût que v1 ; seuls changent le signal (funding moyen 21 périodes, ≥15 obs)
et la fréquence de re-tri (tous les 21 stamps 8h). Poids constants entre re-tris : la dérive des
poids est ignorée (équivaut à un rebalancement intra-bloc gratuit — générosité déclarée dans la
SPEC ; un KILL sous hypothèse généreuse reste robuste)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_CARRY = (Path(__file__).resolve().parent.parent / "carry")
sys.path.insert(0, str(_CARRY))
from audit import sharpe, tstat  # noqa: E402

from run_xs import MIN_PRESENT, PERIODS_Y, REGIMES, load  # loader et constantes v1

SMOOTH = 21              # fenêtre de lissage du signal (≈7 j de fundings 8h)
MIN_OBS = 15             # observations minimum dans la fenêtre de lissage
HOLD = 21                # re-tri tous les HOLD stamps actifs (≈7 j)
COST_PER_TURN = 0.0005   # 5 bps par unité tournée (pré-enregistré, identique v1) — GATING
COST_MAKER = 0.0002      # 2 bps maker moderne — diagnostic NON-gating
HURDLE_ANN = 0.08        # gate F : hurdle de déploiement hérité piste 6


def backtest_v2(F: pd.DataFrame, R: pd.DataFrame):
    """Poids re-triés tous les HOLD stamps sur funding lissé ; PnL décomposé à chaque stamp 8h."""
    F_sig = F.rolling(SMOOTH, min_periods=MIN_OBS).mean()
    idx = F.index
    r_next = R.shift(-1)
    f_next = F.shift(-1)

    w = pd.Series(0.0, index=F.columns)
    steps_since = HOLD  # force un tri au premier stamp valide
    rec = []
    for t in idx:
        # re-tri si le bloc de holding est écoulé ET que le signal est formable
        if steps_since >= HOLD:
            sig = F_sig.loc[t].dropna()
            if len(sig) >= MIN_PRESENT:
                k = len(sig) // 3
                ranked = sig.sort_values()
                longs_new = ranked.index[:k]     # funding lissé le plus négatif
                shorts_new = ranked.index[-k:]   # funding lissé le plus positif
                w_new = pd.Series(0.0, index=F.columns)
                w_new[longs_new] = 1.0 / k
                w_new[shorts_new] = -1.0 / k
                turn = float((w_new - w).abs().sum())
                w = w_new
                steps_since = 0
            else:
                turn = 0.0
        else:
            turn = 0.0
        if (w == 0).all():
            continue
        steps_since += 1

        longs = w[w > 0].index
        shorts = w[w < 0].index
        rn, fn = r_next.loc[t], f_next.loc[t]
        contrib = pd.Series(0.0, index=F.columns)
        wl = 1.0 / len(longs)
        ws = 1.0 / len(shorts)
        contrib[longs] = wl * (rn[longs] - fn[longs])
        contrib[shorts] = ws * (fn[shorts] - rn[shorts])
        contrib = contrib.fillna(0.0)
        rec.append({
            "t": t,
            "gross": contrib.sum(),
            # équipondération : .mean() suffit — pas de wl/ws en plus (bug v1 : double division par k,
            # décomposition affichée k-fois trop petite ; gates v1 non affectés, signes/gross corrects)
            "price_spread": rn[longs].mean() - rn[shorts].mean(),
            "fund_spread": fn[shorts].mean() - fn[longs].mean(),
            "long_leg": (rn[longs] - fn[longs]).mean(),
            "short_leg": (fn[shorts] - rn[shorts]).mean(),
            "btc_ret": rn.get("BTC", np.nan),
            "turnover": turn,
            **{f"c_{s}": contrib[s] for s in F.columns},
        })
    out = pd.DataFrame(rec).set_index("t").dropna(subset=["gross"])
    out["cost"] = out["turnover"] * COST_PER_TURN
    out["net"] = out["gross"] - out["cost"]
    out["net_maker"] = out["gross"] - out["turnover"] * COST_MAKER
    return out


def ann(series: pd.Series) -> float:
    return float(series.mean() * PERIODS_Y)


def report(out: pd.DataFrame):
    g = out["gross"].tolist()
    n = out["net"].tolist()
    print("\n" + "=" * 64)
    print(f"PISTE 11-v2 — funding XS lissé {SMOOTH}p / holding {HOLD}p  | n périodes 8h = {len(out)}")
    print(f"  fenêtre : {out.index.min().date()} -> {out.index.max().date()}")
    print("=" * 64)

    print("\n[GATE A] dispersion lissée paie  (PASS: brut>0 ET t>2)")
    print(f"  brut/8h    = {out['gross'].mean()*1e4:+.3f} bps   annualisé = {ann(out['gross'])*100:+.2f}%")
    print(f"  t-stat     = {tstat(g):+.2f}")
    print(f"  sharpe ann = {sharpe(g)*np.sqrt(PERIODS_Y):+.2f}")
    print(f"    dont spread FUNDING = {ann(out['fund_spread'])*100:+.2f}%/an")
    print(f"    dont spread PRIX    = {ann(out['price_spread'])*100:+.2f}%/an")
    a_pass = out["gross"].mean() > 0 and tstat(g) > 2
    print(f"  => {'PASS' if a_pass else 'KILL'}")

    print("\n[GATE B] net après frais @5 bps  (PASS: net>0 ET t>2)")
    print(f"  turnover moyen/8h = {out['turnover'].mean():.4f} (v1: 1.32)")
    print(f"  coût annualisé    = {ann(out['cost'])*100:+.2f}%/an (v1: ~72%)")
    print(f"  NET annualisé     = {ann(out['net'])*100:+.2f}%   t={tstat(n):+.2f}")
    print(f"  [diag NON-gating] net @2 bps maker = {ann(out['net_maker'])*100:+.2f}%   t={tstat(out['net_maker'].tolist()):+.2f}")
    b_pass = out["net"].mean() > 0 and tstat(n) > 2
    print(f"  => {'PASS' if b_pass else 'KILL'}")

    print("\n[GATE C] market-neutral  (PASS: |corr BTC|<0.2 ET long>0 ET short>0)")
    corr = float(np.corrcoef(out["gross"], out["btc_ret"].fillna(0))[0, 1])
    print(f"  corr(brut, BTC)   = {corr:+.3f}")
    print(f"  jambe LONG  /an   = {ann(out['long_leg'])*100:+.2f}%")
    print(f"  jambe SHORT /an   = {ann(out['short_leg'])*100:+.2f}%")
    c_pass = abs(corr) < 0.2 and out["long_leg"].mean() > 0 and out["short_leg"].mean() > 0
    print(f"  => {'PASS' if c_pass else 'KILL'}")

    print("\n[GATE D] drop-top  (PASS: sans top-2 contributeurs, net>0 ET t>2)")
    contrib_cols = [c for c in out.columns if c.startswith("c_")]
    totals = out[contrib_cols].sum().sort_values(ascending=False)
    top2 = [c[2:] for c in totals.index[:2]]
    print(f"  top-2 contributeurs : {top2}  (parts brut: {totals.iloc[0]/out['gross'].sum():.1%}, {totals.iloc[1]/out['gross'].sum():.1%})")
    net_excl = out["gross"] - out[[f"c_{s}" for s in top2]].sum(axis=1) - out["cost"]
    print(f"  net SANS top-2    = {ann(net_excl)*100:+.2f}%   t={tstat(net_excl.tolist()):+.2f}")
    d_pass = net_excl.mean() > 0 and tstat(net_excl.tolist()) > 2
    print(f"  => {'PASS' if d_pass else 'KILL'}")

    print("\n[GATE E] split régime  (PASS: net>0 dans >=2/3 régimes)")
    n_pos = 0
    for name, (a, b) in REGIMES.items():
        seg = out.loc[(out.index >= a) & (out.index <= b), "net"]
        if len(seg) < 30:
            print(f"  {name:14s}: n={len(seg):5d}  (insuffisant)")
            continue
        pos = seg.mean() > 0
        n_pos += pos
        print(f"  {name:14s}: net/an={ann(seg)*100:+7.2f}%  t={tstat(seg.tolist()):+5.2f}  {'+' if pos else '-'}")
    e_pass = n_pos >= 2
    print(f"  => {'PASS' if e_pass else 'KILL'}")

    print(f"\n[GATE F] hurdle déploiement  (PASS: net @5 bps > {HURDLE_ANN:.0%}/an — hérité piste 6)")
    f_pass = ann(out["net"]) > HURDLE_ANN
    print(f"  net {ann(out['net'])*100:+.2f}% vs hurdle {HURDLE_ANN*100:.0f}%  => {'PASS' if f_pass else 'FAIL'}")

    print("\n" + "=" * 64)
    gates = {"A": a_pass, "B": b_pass, "C": c_pass, "D": d_pass, "E": e_pass, "F": f_pass}
    if all(gates.values()):
        verdict = "GO"
    elif all(v for k, v in gates.items() if k != "F"):
        verdict = "DOWNGRADE (réel non-déployable, F fail)"
    else:
        verdict = "KILL"
    print(f"VERDICT : {verdict}   " + "  ".join(f"{k}={'P' if v else 'K'}" for k, v in gates.items()))
    print("=" * 64)


if __name__ == "__main__":
    print("Chargement univers funding + prix perp 8h (cache carry/)...")
    F, R = load()
    print(f"\nPanel : {F.shape[1]} symboles, {len(F)} stamps 8h, "
          f"{F.index.min().date()} -> {F.index.max().date()}")
    out = backtest_v2(F, R)
    report(out)

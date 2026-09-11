"""Étude #36 — vol-target du deliverable levé. Gates R, G1-G5 pré-enregistrés (docs/SPEC-voltarget.md).

Même portefeuille que #34 (0.80 base6040 + 0.20 trend). Teste si le diagnostic vol-target de #34
survit à ses 3 confounds : fenêtre (warmup excluant 2008), quantité de levier (comparateur à
volatilité ÉGALE), coût de rotation du levier (5 bps × |ΔL|).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

import audit
import sleeves
from run_lever import WEIGHTS, SPREAD_FUT, load_tbill_monthly, maxdd, ann_ret, ann_sharpe, year_ret

TARGET = 0.10
CAP = 3.0
K_COST = 0.0005          # 5 bps de notionnel par unité de ΔL
WINDOWS = [12, 24, 36, 48]
PRIMARY = 36
RUIN_DD = -0.35
N_TRIALS = len(WINDOWS)
ANN = math.sqrt(12)


def fin_cost(tbm: pd.Series, L) -> pd.Series:
    """Coût mensuel par unité d'écart au 1× : emprunt T-bill+spread si L>1, cash T-bill si L<1."""
    L = pd.Series(L, index=tbm.index) if np.isscalar(L) else L
    return pd.Series(np.where(L > 1, (tbm + SPREAD_FUT) / 12, tbm / 12), index=tbm.index)


def vt_series(rp: pd.Series, tb: pd.Series, W: int, cap: float = CAP):
    sig = rp.rolling(W).std().shift(1) * ANN
    L = (TARGET / sig).clip(upper=cap).dropna()
    r = rp.reindex(L.index)
    tbm = tb.reindex(L.index).ffill()
    dL = L.diff().abs().fillna(0.0)
    out = L * r - (L - 1) * fin_cost(tbm, L) - K_COST * dL
    return out, L


def const_series(rp: pd.Series, tb: pd.Series, Lc: float, idx) -> pd.Series:
    r = rp.reindex(idx)
    tbm = tb.reindex(idx).ffill()
    return Lc * r - (Lc - 1) * fin_cost(tbm, Lc)


def vol_matched(rp, tb, idx, target_std: float) -> tuple[float, pd.Series]:
    """Levier constant L_c tel que std(r_C) = target_std sur idx (bissection)."""
    lo, hi = 0.05, 6.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if const_series(rp, tb, mid, idx).std() < target_std:
            lo = mid
        else:
            hi = mid
    Lc = (lo + hi) / 2
    return Lc, const_series(rp, tb, Lc, idx)


def main() -> None:
    S = sleeves.load_sleeves()
    rp = sum(S[c] * w for c, w in WEIGHTS.items()).dropna()
    tb = load_tbill_monthly()
    print("=" * 76)
    print(f"#36 — vol-target du deliverable | r_p {rp.index.min()}->{rp.index.max()} ({len(rp)} mois)")

    # --- sanity : reproduire le diagnostic #34 à l'identique (formule d'origine, sans coût) ---
    vol = rp.rolling(36).std().shift(1) * ANN
    Lvt = (0.10 / vol).clip(upper=3.0)
    r34 = (Lvt * rp - (Lvt - 1.0) * ((tb.reindex(rp.index).ffill() + SPREAD_FUT) / 12)).dropna()
    print(f"  sanity diag #34 : ann={ann_ret(r34)*100:+.2f}%  Sharpe={ann_sharpe(r34):+.2f}  "
          f"maxDD={maxdd(r34)*100:+.1f}%  (attendu +11.48 / 1.16 / −17.2)  début {r34.index.min()}")
    c15_full = const_series(rp, tb, 1.5, rp.index)
    c15_win = const_series(rp, tb, 1.5, r34.index)
    print(f"  confound fenêtre : const 1.5 FULL {rp.index.min()}→ : Sharpe {ann_sharpe(c15_full):+.2f} "
          f"maxDD {maxdd(c15_full)*100:+.1f}%  |  même fenêtre que VT ({r34.index.min()}→) : "
          f"Sharpe {ann_sharpe(c15_win):+.2f} maxDD {maxdd(c15_win)*100:+.1f}%")

    # --- par fenêtre : VT vs C* (volatilité égale) ---
    print("\n" + "=" * 76 + "\nVT vs C* (constant à volatilité égale, même fenêtre) — coût |ΔL| inclus")
    print(f"  {'W':>3s} {'début':>8s} {'n':>4s} | {'VT net':>7s} {'Sh':>5s} {'DD':>6s} | "
          f"{'L_c':>4s} {'C* net':>7s} {'Sh':>5s} {'DD':>6s} | {'ΔSh':>6s} | L̄  %cap")
    res = {}
    for W in WINDOWS:
        rv, L = vt_series(rp, tb, W)
        Lc, rc = vol_matched(rp, tb, rv.index, rv.std())
        dS = ann_sharpe(rv) - ann_sharpe(rc)
        res[W] = dict(rv=rv, rc=rc, L=L, Lc=Lc, dS=dS)
        print(f"  {W:3d} {str(rv.index.min()):>8s} {len(rv):4d} | {ann_ret(rv)*100:+6.2f}% "
              f"{ann_sharpe(rv):+5.2f} {maxdd(rv)*100:+5.1f}% | {Lc:4.2f} {ann_ret(rc)*100:+6.2f}% "
              f"{ann_sharpe(rc):+5.2f} {maxdd(rc)*100:+5.1f}% | {dS:+6.3f} | {L.mean():.2f} "
              f"{(L >= CAP - 1e-9).mean()*100:3.0f}%")

    P = res[PRIMARY]
    rv, rc = P["rv"], P["rc"]

    # --- gates ---
    print("\n" + "=" * 76 + "\nGATES (W=36 primaire)")
    R = maxdd(rv) > RUIN_DD
    print(f"[R ] ruine : maxDD(VT)={maxdd(rv)*100:+.1f}% > {RUIN_DD*100:.0f}%  => {'PASS' if R else 'FAIL'}")
    g1 = P["dS"] >= 0.10
    print(f"[G1] timing paie : ΔSharpe = {P['dS']:+.3f} ≥ +0.10  => {'PASS' if g1 else 'FAIL'}")
    g2 = maxdd(rv) >= maxdd(rc)
    print(f"[G2] drawdown : VT {maxdd(rv)*100:+.1f}% vs C* {maxdd(rc)*100:+.1f}%  => {'PASS' if g2 else 'FAIL'}")
    g3 = all(res[W]["dS"] > 0 for W in WINDOWS)
    print(f"[G3] robuste à W : " + "  ".join(f"W{W}:{res[W]['dS']:+.3f}" for W in WINDOWS)
          + f"  => {'PASS' if g3 else 'FAIL'}")
    half = len(rv) // 2
    hs = []
    for lab, ix in (("H1", rv.index[:half]), ("H2", rv.index[half:])):
        d = ann_sharpe(rv.reindex(ix)) - ann_sharpe(rc.reindex(ix))
        hs.append(d)
        print(f"[G4] {lab} {ix.min()}→{ix.max()} : ΔSharpe {d:+.3f}")
    g4 = all(d > 0 for d in hs)
    print(f"[G4] both-halves => {'PASS' if g4 else 'FAIL'}")
    d = (rv - rc).dropna()
    srs = [audit.sharpe(list((res[W]["rv"] - res[W]["rc"]).dropna())) for W in WINDOWS]
    dsr, sr_hat, sr0 = audit.deflated_sharpe(list(d), N_TRIALS, float(np.var(srs)))
    g5 = dsr > 0.95
    print(f"[G5] DSR(r_VT − r_C*, n={N_TRIALS}) = {dsr:.3f} (SR/mois {sr_hat:+.3f} vs SR0 {sr0:+.3f}, "
          f"t={audit.tstat(list(d)):+.2f}, écart moyen {d.mean()*12*100:+.2f}%/an)  => {'PASS' if g5 else 'FAIL'}")

    # --- diagnostics ---
    print("\n" + "=" * 76 + "\nDIAGNOSTICS (non-gating)")
    for W in WINDOWS:
        rvW, LW = res[W]["rv"], res[W]["L"]
        rcW = res[W]["rc"]
        Lbar = const_series(rp, tb, float(LW.mean()), rvW.index)
        c15 = const_series(rp, tb, 1.5, rvW.index)
        yrs = "  ".join(f"{y}: VT {year_ret(rvW, y)*100:+5.1f} C* {year_ret(rcW, y)*100:+5.1f}"
                        for y in (2008, 2020, 2022) if year_ret(rvW, y) == year_ret(rvW, y))
        print(f"  W{W}: Sharpe const-L̄({LW.mean():.2f}) {ann_sharpe(Lbar):+.2f} | const-1.5 {ann_sharpe(c15):+.2f} "
              f"DD {maxdd(c15)*100:+.1f}% | L min {LW.min():.2f} max {LW.max():.2f}")
        print(f"       {yrs}")
    rv2, L2 = vt_series(rp, tb, PRIMARY, cap=2.0)
    Lc2, rc2 = vol_matched(rp, tb, rv2.index, rv2.std())
    print(f"  cap 2× (W36) : VT Sharpe {ann_sharpe(rv2):+.2f} DD {maxdd(rv2)*100:+.1f}% vs C* "
          f"{ann_sharpe(rc2):+.2f} DD {maxdd(rc2)*100:+.1f}% → ΔSharpe {ann_sharpe(rv2)-ann_sharpe(rc2):+.3f}")
    wm = rv.idxmin()
    print(f"  pire mois VT(W36) : {wm} {rv.min()*100:+.1f}% à L={P['L'][wm]:.2f} "
          f"(coût |ΔL| total {K_COST*P['L'].diff().abs().sum()*100:.2f} pts sur la période)")

    # --- verdict ---
    print("\n" + "=" * 76)
    if R and g1 and g2 and g3 and g4 and g5:
        v = "PROMOTION — vol-target remplace le levier constant 1.5 comme règle du deliverable."
    elif R and g1 and g2 and g3 and g4:
        v = "DOWNGRADE — timing réel et robuste mais non significatif ; deliverable reste L=1.5 constant."
    elif not (g1 and g3):
        v = "KILL artefact — la domination du diag #34 = fenêtre sans 2008 / quantité de levier, pas le timing."
    else:
        v = "KILL — " + ", ".join(n for n, ok in (("ruine", R), ("DD", g2), ("régime", g4)) if not ok)
    print(f"VERDICT (#36, pré-enregistré) : {v}")
    print("=" * 76)


if __name__ == "__main__":
    main()

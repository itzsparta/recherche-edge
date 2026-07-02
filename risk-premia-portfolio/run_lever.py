"""Étude #34 — le deliverable #22 levé. Gates A-D pré-enregistrés (docs/SPEC-lever.md).

Portefeuille fixe 80/20 (base6040, trend), levier constant rebalancé mensuellement,
financement = T-bill 3M + spread. Grille L pré-committée, contrainte de ruine −35 %.
Pas un test d'hypothèse de marché : ingénierie du deliverable validé (#22).
"""
from __future__ import annotations

import io
import math
import os
import urllib.request

import numpy as np
import pandas as pd

import audit
import sleeves

HERE = os.path.dirname(os.path.abspath(__file__))
IRX_CACHE = os.path.join(HERE, "data", "irx.csv")

WEIGHTS = {"base6040": 0.80, "trend": 0.20}   # pré-committé (milieu 15-35 %)
GRID = [1.0, 1.25, 1.5, 2.0, 3.0]             # pré-committé
SPREAD_FUT = 0.004                              # +0.40 %/an futures/box — GATING
SPREAD_BROKER = 0.015                           # +1.50 %/an marge broker — diagnostic
RUIN_DD = -0.35                                 # contrainte de ruine
ANN = math.sqrt(12)


def load_tbill_monthly() -> pd.Series:
    """Taux T-bill 3M annualisé (décimal), indexé Period[M]. Cache local, sinon FRED TB3MS."""
    if os.path.exists(IRX_CACHE):
        s = pd.read_csv(IRX_CACHE, parse_dates=["Date"]).set_index("Date").iloc[:, 0]
    else:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=TB3MS"
        raw = urllib.request.urlopen(url, timeout=30).read().decode()
        df = pd.read_csv(io.StringIO(raw))
        df.columns = ["Date", "rate"]
        df["Date"] = pd.to_datetime(df["Date"])
        df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
        df = df.dropna().set_index("Date")
        os.makedirs(os.path.dirname(IRX_CACHE), exist_ok=True)
        df.to_csv(IRX_CACHE)
        s = df["rate"]
    s.index = pd.PeriodIndex(s.index, freq="M")
    s = s[~s.index.duplicated(keep="last")] / 100.0
    return s


def lever(rp: pd.Series, tbill: pd.Series, L: float, spread: float) -> pd.Series:
    """r_L = L·r_p − (L−1)·(tbill+spread)/12, alignement mensuel strict."""
    c = (tbill.reindex(rp.index).ffill() + spread) / 12.0
    return L * rp - (L - 1.0) * c


def maxdd(r: pd.Series) -> float:
    eq = (1 + r).cumprod()
    return float((eq / eq.cummax() - 1).min())


def ann_ret(r: pd.Series) -> float:
    return float(r.mean() * 12)


def ann_sharpe(r: pd.Series) -> float:
    return audit.sharpe(list(r.dropna())) * ANN


def year_ret(r: pd.Series, year: int) -> float:
    m = r[[p.year == year for p in r.index]]
    return float((1 + m).prod() - 1) if len(m) else float("nan")


def main() -> None:
    S = sleeves.load_sleeves()
    rp = sum(S[c] * w for c, w in WEIGHTS.items()).dropna()
    tb = load_tbill_monthly()
    print("=" * 72)
    print(f"#34 — deliverable #22 levé | fixe 80/20 | {rp.index.min()}->{rp.index.max()} ({len(rp)} mois)")
    print(f"  base non-levée : ann={ann_ret(rp)*100:+.2f}%  Sharpe={ann_sharpe(rp):+.2f}  maxDD={maxdd(rp)*100:+.1f}%")
    print(f"  T-bill moyen fenêtre = {tb.reindex(rp.index).ffill().mean()*100:.2f}%/an")

    # --- grille @ spread futures (GATING) ---
    print("\n" + "=" * 72)
    print(f"GRILLE L @ financement T3M+{SPREAD_FUT*100:.1f}% (futures/box) — GATING")
    print(f"  {'L':>5s} {'net/an':>8s} {'Sharpe':>7s} {'maxDD':>8s} {'2008':>8s} {'2022':>8s}")
    rows = {}
    for L in GRID:
        r = lever(rp, tb, L, SPREAD_FUT)
        rows[L] = r
        print(f"  {L:5.2f} {ann_ret(r)*100:+7.2f}% {ann_sharpe(r):+7.2f} {maxdd(r)*100:+7.1f}% "
              f"{year_ret(r,2008)*100:+7.1f}% {year_ret(r,2022)*100:+7.1f}%")

    # sélection L* : plus grand L respectant la ruine
    admissible = [L for L in GRID if maxdd(rows[L]) > RUIN_DD]
    L_star = max(admissible) if admissible else 1.0
    print(f"\n  contrainte ruine maxDD > {RUIN_DD*100:.0f}%  =>  L* = {L_star}")

    r1, rL = rows[1.0], rows[L_star]

    # --- gates ---
    print("\n" + "=" * 72 + "\nGATES")
    a_pass = ann_ret(rL) >= ann_ret(r1) + 0.01
    print(f"[A] levier paie : net(L*)={ann_ret(rL)*100:+.2f}% vs net(1)+1pt={ann_ret(r1)*100+1:+.2f}%  "
          f"=> {'PASS' if a_pass else 'KILL'}")
    b_pass = L_star > 1.0
    print(f"[B] levier tenable existe : L*={L_star}  => {'PASS' if b_pass else 'KILL'}")
    half = len(rp) // 2
    idx1, idx2 = rp.index[:half], rp.index[half:]
    c_ok = []
    for lab, ix in (("1re moitié", idx1), ("2e moitié", idx2)):
        d = ann_ret(rL.reindex(ix)) - ann_ret(r1.reindex(ix))
        c_ok.append(d > 0)
        print(f"[C] {lab} {ix.min()}->{ix.max()} : net(L*)−net(1) = {d*100:+.2f} pts/an  {'+' if d>0 else '-'}")
    c_pass = all(c_ok)
    print(f"[C] both-halves => {'PASS' if c_pass else 'KILL'}")
    d_pass = ann_sharpe(rL) >= ann_sharpe(r1) - 0.10
    print(f"[D] sanity : Sharpe(L*)={ann_sharpe(rL):+.2f} vs Sharpe(1)−0.10={ann_sharpe(r1)-0.10:+.2f}  "
          f"=> {'PASS' if d_pass else 'KILL'}")

    # --- diagnostics non-gating ---
    print("\n" + "=" * 72 + "\nDIAGNOSTICS (non-gating)")
    print(f"  broker T3M+{SPREAD_BROKER*100:.1f}% :")
    for L in GRID:
        r = lever(rp, tb, L, SPREAD_BROKER)
        print(f"    L={L:4.2f}  net={ann_ret(r)*100:+7.2f}%  maxDD={maxdd(r)*100:+7.1f}%")
    # vol-target 10 % dynamique (fenêtre 36 m, laggée)
    vol = rp.rolling(36).std().shift(1) * ANN
    Lvt = (0.10 / vol).clip(upper=3.0)
    rvt = (Lvt * rp - (Lvt - 1.0) * ((tb.reindex(rp.index).ffill() + SPREAD_FUT) / 12)).dropna()
    print(f"  vol-target 10% (36m, cap 3x) : ann={ann_ret(rvt)*100:+.2f}%  Sharpe={ann_sharpe(rvt):+.2f}  "
          f"maxDD={maxdd(rvt)*100:+.1f}%  L moyen={float(Lvt.mean()):.2f}")
    worst = rp.min()
    print(f"  pire mois base = {worst*100:+.1f}%  =>  à L=3 : {worst*3*100:+.1f}% (call de marge probable intra-mois)")

    # --- verdict ---
    print("\n" + "=" * 72)
    gates = {"A": a_pass, "B": b_pass, "C": c_pass, "D": d_pass}
    verdict = "EXTENSION-LEVIER" if all(gates.values()) else "KILL (deliverable reste non-levé)"
    print(f"VERDICT : {verdict}  L*={L_star}  " + "  ".join(f"{k}={'P' if v else 'K'}" for k, v in gates.items()))
    print("=" * 72)


if __name__ == "__main__":
    main()

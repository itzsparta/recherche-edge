"""Piste 10 — favorite-longshot bias Polymarket — PHASE 1 : Gate A (le biais existe ?).

Critère PASS pré-enregistré (docs/SPEC.md) :
  (A) legs implied<0.10 : mean(realized) < mean(implied), t-stat de l'écart < −2
  (C) dose-réponse monotone de l'écart, (E) présent dans ≥2 catégories.
  KILL si bien calibré ou biais inverse.
"""
from __future__ import annotations

import datetime as dt
import warnings

import numpy as np
import pandas as pd

from data_pm import resolved_markets, price_history

warnings.simplefilter("ignore")
LONGSHOT = 0.10


def _unix(iso: str) -> float:
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def build_legs() -> pd.DataFrame:
    mkts = resolved_markets(max_markets=3000)
    print(f"Marchés résolus (vol≥5k, binaires) : {len(mkts)}. Fetch historiques prix…")
    legs = []
    for i, m in enumerate(mkts):
        try:
            su, eu = _unix(m["start"]), _unix(m["end"])
        except Exception:
            continue
        if eu <= su:
            continue
        h = price_history(m["tok0"])
        if len(h) < 2:
            continue
        tmid = (su + eu) / 2
        pt = min(h, key=lambda x: abs(x["t"] - tmid))
        if pt["t"] > eu - 43200 or pt["t"] < su:    # trop près de la résolution / hors fenêtre
            continue
        p0 = float(np.clip(pt["p"], 0.001, 0.999))
        y0 = m["y0"]
        legs.append({"implied": p0, "realized": y0, "cat": m["cat"]})
        legs.append({"implied": 1 - p0, "realized": 1 - y0, "cat": m["cat"]})
        if (i + 1) % 1000 == 0:
            print(f"  …{i + 1}/{len(mkts)} marchés ({len(legs)} legs)")
    return pd.DataFrame(legs)


def _gap_t(df: pd.DataFrame) -> tuple:
    g = (df["realized"] - df["implied"]).values
    n = len(g)
    if n < 2:
        return float("nan"), float("nan"), float("nan"), float("nan"), n
    mean = g.mean()
    t = mean / (g.std(ddof=1) / np.sqrt(n)) if g.std() > 0 else 0.0
    return df["implied"].mean(), df["realized"].mean(), mean, t, n


def main() -> None:
    print("Piste 10 favorite-longshot Polymarket — Phase-1 Gate A\n" + "=" * 64)
    legs = build_legs()
    n_mkt = len(legs) // 2
    print(f"\nLegs totaux : {len(legs)} ({n_mkt} marchés). Cible N>500 : "
          f"{'OK' if n_mkt > 500 else 'INSUFFISANT'}")

    # ---- calibration / dose-réponse ----
    bins = [0, .02, .05, .10, .20, .35, .50, .65, .80, .90, .95, .98, 1.0]
    print("\n--- Calibration (dose-réponse) ---")
    print(f"{'bucket':>12}{'n':>7}{'implied':>10}{'realized':>10}{'gap':>9}")
    legs["bk"] = pd.cut(legs["implied"], bins, include_lowest=True)
    dose = []
    for b, grp in legs.groupby("bk"):
        if len(grp) < 5:
            continue
        imp, rea = grp["implied"].mean(), grp["realized"].mean()
        dose.append((imp, rea - imp))
        print(f"{str(b):>12}{len(grp):>7}{imp:>10.3f}{rea:>10.3f}{rea-imp:>+9.3f}")

    # ---- Gate A : longshot ----
    ls = legs[legs["implied"] < LONGSHOT]
    imp, rea, gap, t, n = _gap_t(ls)
    print(f"\n--- Gate A : longshots (implied<{LONGSHOT}) ---")
    print(f"  n_legs={n}  mean implied={imp:.4f}  mean realized={rea:.4f}  "
          f"gap={gap:+.4f}  t={t:.2f}   [PASS si gap<0 ∧ t<−2]")

    # ---- Gate E : split catégorie ----
    print("\n--- Gate E : split catégorie (longshots) ---")
    cat_neg = 0
    for c, grp in ls.groupby("cat"):
        _, _, g, tc, nc = _gap_t(grp)
        if nc < 20:
            print(f"  {c:<9}: n={nc} (trop peu)")
            continue
        sig = g < 0 and tc < -2
        cat_neg += sig
        print(f"  {c:<9}: n={nc}  gap={g:+.4f}  t={tc:.2f}  {'BIAIS' if sig else '-'}")

    # ---- dose-réponse monotonicité (sur buckets implied<0.5) ----
    low = [(i, gp) for i, gp in dose if i < 0.5]
    mono = all(low[k][1] <= low[k + 1][1] + 0.01 for k in range(len(low) - 1)) if len(low) > 2 else False

    gA = (gap < 0) and (t < -2) and (n_mkt > 500)
    gE = cat_neg >= 2
    print("\n" + "=" * 64)
    print(f"  A(longshot overpricing)={'PASS' if gA else 'KILL'}   "
          f"E(≥2 catégories)={'PASS' if gE else 'KILL'}   "
          f"C(dose monotone)={'PASS' if mono else 'faible'}")
    if gA and gE:
        print("\nVERDICT Phase-1 : PASS — biais favorite-longshot réel et multi-catégorie.")
        print("  -> Phase-2 : survit-il au SPREAD du longshot (Gate B) ? = le vrai combat.")
    else:
        why = "bien calibré / biais inverse" if not gA else "biais mono-catégorie (artefact)"
        print(f"\nVERDICT Phase-1 : KILL — {why}. Polymarket trop efficient pour ce solo.")


if __name__ == "__main__":
    main()

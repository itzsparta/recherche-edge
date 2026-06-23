"""Piste 8 — robustesse / chasse au mirage du GO provisoire Phase-2.

3 tueurs non-modélisés : (1) bid-ask bounce → test de lag d'entrée 1 mois ;
(2) short infaisable → borrow stressé 15 % + variante long-only ; (3) survivorship
= NON corrigeable ici (univers CEFConnect = fonds vivants) → caveat, pas un test.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from data_cef import universe, fetch_all
from run_phase2 import monthly_panels, run_strategy, net_series, stats, RT, ANN

warnings.simplefilter("ignore")


def net_with(df: pd.DataFrame, borrow_ann: float) -> pd.Series:
    return df["brut"] - RT * df["turn"] - borrow_ann / 12


def longonly_net(df: pd.DataFrame) -> pd.Series:
    return df["long"] - RT * df["turn_l"]          # pas de borrow, coût jambe longue seule


def main() -> None:
    print("Piste 8 — robustesse du GO provisoire\n" + "=" * 64)
    uni = universe()
    cats = dict(zip(uni["Ticker"], uni.get("CategoryName")))
    hist = fetch_all(uni["Ticker"].dropna().unique().tolist())
    prem, fwd = monthly_panels(hist)
    conv = np.log1p(prem / 100.0)
    fwd_lag1 = conv.diff().shift(-2)        # empocher m+1->m+2 (saute 1 mois = test bounce)

    base = run_strategy(prem, fwd)
    lag1 = run_strategy(prem, fwd, ret_override=fwd_lag1)

    print("\n--- (1) Test bid-ask bounce : lag d'entrée 1 mois ---")
    sb, sl = stats(net_series(base)), stats(net_series(lag1))
    print(f"  net lag0 (base) : ann {sb['ann']:+.2%}  t {sb['t']:.2f}")
    print(f"  net lag1 (+1mo) : ann {sl['ann']:+.2%}  t {sl['t']:.2f}")
    keep = sl["ann"] / sb["ann"] if sb["ann"] else float("nan")
    print(f"  → survie alpha au lag : {keep:.0%}  "
          f"({'persistant (≠bounce)' if keep > 0.5 else 'EFFONDRE = bounce'})")

    print("\n--- (2) Short fragile : borrow stressé + long-only ---")
    for b in (0.04, 0.15, 0.30):
        s = stats(net_with(base, b))
        print(f"  borrow {b:>4.0%}/an : net ann {s['ann']:+.2%}  t {s['t']:.2f}")
    lo = stats(longonly_net(base))
    print(f"  LONG-ONLY (pas de short) : net ann {lo['ann']:+.2%}  t {lo['t']:.2f}")

    print("\n--- (3) Forme déployable = intra-catégorie + lag1 + borrow 15% ---")
    ecat_lag = run_strategy(prem, fwd, cats=cats, ret_override=fwd_lag1)
    se = stats(net_with(ecat_lag, 0.15))
    print(f"  intra-cat, lag1, borrow15% : net ann {se['ann']:+.2%}  t {se['t']:.2f}")
    elo = stats(longonly_net(run_strategy(prem, fwd, cats=cats, ret_override=fwd_lag1)))
    print(f"  intra-cat, lag1, LONG-ONLY : net ann {elo['ann']:+.2%}  t {elo['t']:.2f}")

    print("\n--- (4) Sensibilité au démarrage (survivorship indirect) ---")
    for start in ("1996", "2010", "2015", "2020"):
        seg = net_series(base).loc[start:]
        s = stats(seg)
        print(f"  net depuis {start} : ann {s['ann']:+.2%}  t {s['t']:.2f}  (n={s['n']})")

    print("\n" + "=" * 64)
    print("Survivorship NON corrigé (univers = fonds vivants) = caveat dominant restant.")


if __name__ == "__main__":
    main()

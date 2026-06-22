"""Durcissement du gate (B) tail — le Sharpe mensuel ment sur le short-vol.

Le gate (B) de run.py passe sur un maxDD sigma-normalise (aveugle au skew) et un
echantillon MENSUEL qui lisse le krach intramois. Ici on confronte le premium a la
realite tradable : SVXY (vrai ETF short-VIX) + le gap quotidien du VIX. C'est la
queue que Sharpe=1.86 cache.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import data
import vrp


def episode(ret: pd.Series, start: str, end: str) -> tuple[float, float, float]:
    w = ret.loc[start:end]
    if w.empty:
        return float("nan"), float("nan"), float("nan")
    cum = (1 + w).cumprod()
    dd = (cum / cum.cummax() - 1).min()
    return float(w.min()), float(dd), float(cum.iloc[-1] - 1)


def main() -> None:
    df = data.load()
    svxy = data.close_series("SVXY", auto_adjust=True)
    r = svxy.pct_change().dropna()
    cum = (1 + r).cumprod()
    maxdd = float((cum / cum.cummax() - 1).min())

    print("\n" + "=" * 70)
    print("REALITE TRADABLE : SVXY (short VIX short-term futures, le harvest VRP reel)")
    print("=" * 70)
    print(f"  historique : {r.index.min().date()} -> {r.index.max().date()}  ({len(r)} jours)")
    print(f"  pire jour      : {r.min():+.1%}  ({r.idxmin().date()})")
    print(f"  max drawdown   : {maxdd:+.1%}")
    for label, a, b in [("Volmageddon", "2018-01-15", "2018-03-01"),
                        ("COVID", "2020-02-15", "2020-04-15")]:
        wd, dd, tot = episode(r, a, b)
        print(f"  {label:12s} [{a}->{b}] : pire jour {wd:+.1%}  maxDD {dd:+.1%}  total {tot:+.1%}")

    vix_chg = df["vix"].pct_change().dropna()
    print(f"\n  gap VIX : pire +1j = {vix_chg.max():+.0%} ({vix_chg.idxmax().date()}) "
          f"= le choc qu'un short-vol encaisse a levier")

    print("\n" + "=" * 70)
    print("PREUVE DU LISSAGE MENSUEL : 5 pires mois du harvest (run.py)")
    print("=" * 70)
    t = vrp.monthly_table(df)
    worst = t.nsmallest(5, "pnl_net")[["pnl_net", "vix", "rv_vol", "regime"]]
    for d, row in worst.iterrows():
        print(f"  {d.date()}  pnl_net={row['pnl_net']:+6.1f} pts vol  "
              f"VIX={row['vix']:.1f}  RV={100*row['rv_vol']:.1f}  {row['regime']}")
    feb18 = t.loc[(t.index.year == 2018) & (t.index.month.isin([1, 2]))]
    print("\n  -> mois Jan/Fev 2018 dans le harvest mensuel :")
    for d, row in feb18.iterrows():
        print(f"     {d.date()}  pnl_net={row['pnl_net']:+6.1f} pts vol  (krach du 5 fev INVISIBLE)")


if __name__ == "__main__":
    main()

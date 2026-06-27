"""B2-propre : le carry énergie ajoute-t-il au méta 60/40+trend (pas juste 60/40) ?
Trend trade déjà l'énergie (momentum) → carry-backwardation pourrait être redondant.
"""
from __future__ import annotations
import math, pathlib, sys
import numpy as np, pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
FH = HERE.parent / "factor-harvest"
sys.path.insert(0, str(HERE)); sys.path.append(str(FH))

import data_eia, run_carry            # carry (local)
import data as fhdata, backtest as fhbt   # trend (factor-harvest)
ANN = math.sqrt(12)


def ann_sharpe(m):
    from audit import sharpe
    return sharpe(list(pd.Series(m).dropna())) * ANN


def main():
    # --- carry mensuel ---
    panel = data_eia.discover()
    monthly = run_carry.build_monthly(panel)
    carry = run_carry.portfolio(monthly, list(panel)).rename("carry")

    # --- trend mensuel (même construction que le méta : 32 futures, LB12, union) ---
    import run_futures
    px = fhdata.load_universe(list(run_futures.FUTURES)).dropna(how="all")
    trend = fhbt.run_strategy(px, lookback_months=12, require_all=False)["monthly"].rename("trend")

    # --- 60/40 ---
    core = run_carry.sixty_forty_monthly().rename("core")

    df = pd.concat([carry, trend, core], axis=1).dropna()
    print(f"\nÉchantillon commun : {df.index.min().date()} → {df.index.max().date()} ({len(df)} mois)")
    print(f"corr(carry, trend) = {df['carry'].corr(df['trend']):+.2f}")
    print(f"corr(carry, core)  = {df['carry'].corr(df['core']):+.2f}")
    print(f"corr(trend, core)  = {df['trend'].corr(df['core']):+.2f}")

    # vol-match les sleeves au cœur
    cs = df["carry"] * (df["core"].std() / df["carry"].std())
    ts = df["trend"] * (df["core"].std() / df["trend"].std())
    print(f"\nSharpe(ann) — cœur {ann_sharpe(df['core']):+.2f} | trend {ann_sharpe(df['trend']):+.2f} | "
          f"carry {ann_sharpe(df['carry']):+.2f}")
    print("\nSleeve sur 60/40 :")
    combos = {
        "60/40":                     df["core"],
        "+trend 20%":                0.80 * df["core"] + 0.20 * ts,
        "+trend 20% +carry 15%":     0.65 * df["core"] + 0.20 * ts + 0.15 * cs,
        "+carry 15% (sans trend)":   0.85 * df["core"] + 0.15 * cs,
    }
    for name, series in combos.items():
        print(f"  {name:26s} Sharpe {ann_sharpe(series):+.3f}")

    # increment net du carry PAR-DESSUS 60/40+trend
    base = 0.80 * df["core"] + 0.20 * ts
    plus = 0.65 * df["core"] + 0.20 * ts + 0.15 * cs
    print(f"\nIncrément carry sur (60/40+trend) : {ann_sharpe(plus) - ann_sharpe(base):+.3f} Sharpe")
    print("→ redondant si ≈0 (trend capte déjà la backwardation énergie) ; sleeve réel si >0 net.")


if __name__ == "__main__":
    main()

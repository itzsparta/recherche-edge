"""Portefeuille FX carry + proxy trend — pré-enregistré docs/SPEC.md (Piste 17).

Carry : long 3 plus hauts différentiels de taux / short 3 plus bas, dollar-neutral,
rebalance mensuel, signal & accrual LAGGÉS (rate_{t-1}) = pas de look-ahead.
Trend proxy : TSMOM 12 m sur l'univers futures factor-harvest (les mêmes actifs que
le sleeve trend +0.12) pour le test d'orthogonalité (gate D).
"""
from __future__ import annotations

import glob
import os

import pandas as pd

import data_fx

COST_BPS = 2.0  # par jambe au rebalance, FX liquide
HERE = os.path.dirname(os.path.abspath(__file__))
FX_DIR = os.path.join(HERE, "..", "factor-harvest", "data")


def carry_portfolio(n_side: int = 3) -> pd.DataFrame:
    """Retourne DataFrame mensuel : gross, net (après coûts), + n_long/n_short."""
    ret, rate = data_fx.load()
    ccys = list(ret.columns)
    diff = rate[ccys].sub(rate["USD"], axis=0)  # rate_i - rate_usd
    sig = diff.shift(1)            # signal laggé (connu en début de mois t)
    accrual = diff.shift(1) / 100.0 / 12.0       # carry mensuel locké à t-1
    excess = ret + accrual        # rendement excédentaire par devise

    rows = []
    prev_w = pd.Series(0.0, index=ccys)
    for t in sig.index:
        s = sig.loc[t].dropna()
        if len(s) < 2 * n_side:
            rows.append((t, float("nan"), float("nan"), 0, 0))
            prev_w = pd.Series(0.0, index=ccys)
            continue
        ranked = s.sort_values()
        shorts = ranked.index[:n_side]
        longs = ranked.index[-n_side:]
        w = pd.Series(0.0, index=ccys)
        w[longs] = 1.0 / n_side
        w[shorts] = -1.0 / n_side
        r = excess.loc[t]
        gross = float((w * r).sum())
        turnover = float((w - prev_w).abs().sum())
        cost = turnover * COST_BPS / 1e4
        rows.append((t, gross, gross - cost, len(longs), len(shorts)))
        prev_w = w
    df = pd.DataFrame(rows, columns=["date", "gross", "net", "n_long", "n_short"]).set_index("date")
    return df.dropna()


def trend_proxy() -> pd.Series:
    """TSMOM 12 m sur l'univers futures factor-harvest = proxy du sleeve trend (+0.12).
    Signal = signe du return trailing 12 m (laggé), position = signe × return du mois, equal-weight."""
    paths = sorted(glob.glob(os.path.join(FX_DIR, "*.csv")))
    monthly = {}
    for p in paths:
        name = os.path.basename(p)[:-4]
        df = pd.read_csv(p)
        df.columns = ["date", "px"]
        df["date"] = pd.to_datetime(df["date"])
        df["px"] = pd.to_numeric(df["px"], errors="coerce")
        s = df.dropna().set_index("date")["px"].resample("MS").last()
        if s.notna().sum() > 60:
            monthly[name] = s
    px = pd.DataFrame(monthly)
    ret = px.pct_change()
    mom = px.pct_change(12).shift(1)        # return trailing 12m, laggé
    pos = mom.apply(lambda c: c.map(lambda x: 1.0 if x > 0 else (-1.0 if x < 0 else 0.0)))
    strat = (pos * ret).mean(axis=1)        # equal-weight TSMOM
    return strat.dropna()


if __name__ == "__main__":
    c = carry_portfolio()
    print(f"  carry mois={len(c)}  net mean/mois={c['net'].mean()*100:.3f}%  "
          f"ann={c['net'].mean()*12*100:.2f}%")
    t = trend_proxy()
    print(f"  trend proxy mois={len(t)}  ann={t.mean()*12*100:.2f}%")

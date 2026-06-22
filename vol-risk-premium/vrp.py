"""Calcul du Volatility Risk Premium — pré-enregistré dans docs/SPEC.md.

Phase 0 : premium = VIX^2 (implied var 30j) vs variance realisee forward 21j sur GSPC,
echantillonne mensuel non-chevauchant.
Phase 1 : rendement de recolte (short-variance synthetique, points de vol) net d'un cout.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

H = 21        # jours de bourse forward (~30j calendaires = horizon VIX)
COST = 0.5    # points de vol / mois, round-trip (pre-enregistre)


def regime_of(d: pd.Timestamp) -> str:
    y = d.year
    if y <= 2007:
        return "1_pre/dotcom"
    if y <= 2009:
        return "2_GFC"
    if y <= 2017:
        return "3_recovery"
    if y <= 2019:
        return "4_late2010s"
    if y == 2020:
        return "5_COVID"
    return "6_2021+"


def monthly_table(df: pd.DataFrame, h: int = H, cost: float = COST) -> pd.DataFrame:
    """Table mensuelle non-chevauchante du premium + P&L de recolte net.

    A chaque fin de mois de bourse t : VIX(t) implied, variance realisee sur les h
    rendements suivants (t->t+h). Aucun look-ahead pour le trade (on vend en t, on
    realise dans le futur).
    """
    df = df.dropna(subset=["vix", "gspc"]).sort_index().copy()
    logp = np.log(df["gspc"].to_numpy())
    r = np.diff(logp)                       # r[i] = rendement dates[i] -> dates[i+1]
    n = len(df)
    pos = {d: i for i, d in enumerate(df.index)}
    # fins de mois de bourse
    me = df.index.to_series().groupby([df.index.year, df.index.month]).tail(1)

    rows = []
    for d in me.index:
        k = pos[d]
        if k + h > len(r):                  # besoin de r[k..k+h-1]
            continue
        fwd = r[k:k + h]
        rv_var = 252.0 / h * float(np.sum(fwd ** 2))
        rv_vol = float(np.sqrt(rv_var))
        vix = float(df["vix"].iloc[k])
        iv_vol = vix / 100.0
        iv_var = iv_vol ** 2
        rows.append({
            "date": d,
            "vix": vix,
            "iv_var": iv_var,
            "rv_var": rv_var,
            "rv_vol": rv_vol,
            "vrp_var": iv_var - rv_var,         # >0 = prime au vendeur (variance, decimal^2)
            "vrp_vol": vix - 100.0 * rv_vol,    # points de vol (intuition)
        })
    t = pd.DataFrame(rows).set_index("date")
    t["pnl_net"] = t["vrp_vol"] - cost          # Phase 1 : recolte nette, vega-flat 1x
    t["regime"] = [regime_of(d) for d in t.index]
    return t


def spy_monthly_returns(df: pd.DataFrame, sample_dates: pd.DatetimeIndex) -> pd.Series:
    """Rendements SPY total entre fins de mois consecutives du meme echantillon."""
    spy = df["spy"].dropna()
    lvl = spy.reindex(sample_dates, method="ffill")
    return lvl.pct_change().dropna()


def abs_maxdd(ret) -> float:
    """Max drawdown absolu (rendements simples)."""
    s = pd.Series(ret).dropna()
    cum = (1 + s).cumprod()
    return float((cum / cum.cummax() - 1).min())


def standardized_tail(x: np.ndarray) -> dict:
    """Stats de queue en unites comparables (sigma) : worst-month en z, maxDD/sigma."""
    x = np.asarray(x, dtype=float)
    mu, sd = x.mean(), x.std(ddof=0)
    cum = np.cumsum(x - 0.0)                  # P&L additif cumule
    dd = cum - np.maximum.accumulate(cum)     # drawdown (meme unite que x)
    return {
        "worst_z": float((x.min() - mu) / sd) if sd > 0 else 0.0,
        "maxdd_sigma": float(dd.min() / sd) if sd > 0 else 0.0,
        "skew": float(np.mean(((x - mu) / sd) ** 3)) if sd > 0 else 0.0,
        "kurt": float(np.mean(((x - mu) / sd) ** 4)) if sd > 0 else 0.0,
    }

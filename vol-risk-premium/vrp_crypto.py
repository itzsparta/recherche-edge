"""Calcul du VRP crypto — pré-enregistré dans docs/SPEC-crypto.md (Piste 12).

Phase 0 : premium = DVOL^2 (implied var 30j) vs variance réalisée forward 30j daily,
échantillonné mensuel non-chevauchant. Crypto trade 365 j/an.
Phase 1 : récolte synthétique short-vol (points de vol) nette d'un coût plus lourd
qu'en actions (spreads crypto larges + provision d'aile du defined-risk).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

H = 30          # jours forward (crypto = calendaires = de bourse, 365/an)
ANN_D = 365.0   # annualisation variance (crypto trade tous les jours)
COST = 3.0      # points de vol / mois (pré-enregistré : bid-ask Deribit + provision d'aile)
MAG_BAR = 8.0   # barre de magnitude pré-enregistrée : mean(vrp_vol) doit dépasser (actions=4.07)


def regime_of(d: pd.Timestamp) -> str:
    """Régimes crypto — krachs isolés pour voir la signature assurance."""
    if d.year == 2021 and d.month <= 4:
        return "1_2021H1_bull"
    if d.year == 2021 and d.month <= 7:
        return "2_2021_crash"      # −50 % du 19 mai 2021
    if d.year == 2021:
        return "3_2021H2_recov"
    if d.year == 2022:
        return "4_2022_bear"       # LUNA / 3AC / FTX
    if d.year == 2023:
        return "5_2023_recov"
    return "6_2024plus_bull"


def monthly_table(df: pd.DataFrame, h: int = H, cost: float = COST) -> pd.DataFrame:
    """Table mensuelle non-chevauchante du premium + P&L de récolte net.

    Fin de mois t : DVOL(t) implicite, variance réalisée sur les h rendements daily
    suivants (t->t+h). Aucun look-ahead (on vend en t, on réalise dans le futur).
    """
    df = df.dropna(subset=["dvol", "spot"]).sort_index().copy()
    logp = np.log(df["spot"].to_numpy())
    r = np.diff(logp)                       # r[i] = rendement dates[i] -> dates[i+1]
    pos = {d: i for i, d in enumerate(df.index)}
    me = df.index.to_series().groupby([df.index.year, df.index.month]).tail(1)

    rows = []
    for d in me.index:
        k = pos[d]
        if k + h > len(r):                  # besoin de r[k..k+h-1]
            continue
        fwd = r[k:k + h]
        rv_var = ANN_D / h * float(np.sum(fwd ** 2))
        rv_vol = float(np.sqrt(rv_var))
        dvol = float(df["dvol"].iloc[k])
        iv_vol = dvol / 100.0
        iv_var = iv_vol ** 2
        rows.append({
            "date": d,
            "dvol": dvol,
            "iv_var": iv_var,
            "rv_var": rv_var,
            "rv_vol": rv_vol,
            "vrp_var": iv_var - rv_var,          # >0 = prime au vendeur (decimal^2)
            "vrp_vol": dvol - 100.0 * rv_vol,    # points de vol
        })
    t = pd.DataFrame(rows).set_index("date")
    t["pnl_net"] = t["vrp_vol"] - cost           # Phase 1 : récolte nette, vega-flat 1x
    t["regime"] = [regime_of(d) for d in t.index]
    return t


def spot_monthly_returns(df: pd.DataFrame, sample_dates: pd.DatetimeIndex) -> pd.Series:
    """Rendements buy-hold du sous-jacent entre fins de mois consécutives (bench)."""
    spot = df["spot"].dropna()
    lvl = spot.reindex(sample_dates, method="ffill")
    return lvl.pct_change().dropna()

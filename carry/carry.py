"""Carry quotidien depuis le funding 8h — pré-enregistré dans docs/SPEC.md."""
from __future__ import annotations

import pandas as pd


def regime_of(d: pd.Timestamp) -> str:
    y = d.year
    if y <= 2020:
        return "1_launch/covid"
    if y == 2021:
        return "2_bull"
    if y == 2022:
        return "3_bear"
    if y <= 2024:
        return "4_recovery"
    return "5_2025+"


def daily(df: pd.DataFrame) -> pd.DataFrame:
    """carry_jour = somme des funding 8h du jour (collecté par le short perp)."""
    d = df.copy()
    d["date"] = d.index.normalize()
    g = d.groupby("date")
    out = pd.DataFrame({"carry": g["fundingRate"].sum(), "price": g["markPrice"].last()})
    out.index = pd.DatetimeIndex(out.index)
    out = out.sort_index()
    out["btc_ret"] = out["price"].pct_change()
    out["regime"] = [regime_of(x) for x in out.index]
    return out.dropna(subset=["carry"])

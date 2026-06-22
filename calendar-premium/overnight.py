"""Décomposition overnight / intraday — pré-enregistré dans docs/SPEC.md (5a)."""
from __future__ import annotations

import pandas as pd


def legs(df: pd.DataFrame) -> pd.DataFrame:
    """overnight = Open_d/Close_{d-1}-1 ; intraday = Close_d/Open_d-1 ; cc = buy-hold."""
    o, c = df["Open"], df["Close"]
    cl_prev = c.shift(1)
    out = pd.DataFrame({
        "overnight": o / cl_prev - 1.0,
        "intraday": c / o - 1.0,
        "cc": c / cl_prev - 1.0,
    }).dropna()
    return out

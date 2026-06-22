"""Event-study pré-FOMC drift — pré-enregistré dans docs/SPEC.md (5b)."""
from __future__ import annotations

import pandas as pd


def event_table(spy: pd.DataFrame, dates: list[pd.Timestamp]):
    """Renvoie (ev, cc) : ev = rendements par event ; cc = série close-to-close SPY."""
    c = spy["Close"]
    idx = c.index
    cc = c / c.shift(1) - 1.0
    rows = []
    for d in dates:
        pos = idx.searchsorted(d)            # 1er jour de bourse >= date d'annonce
        if pos >= len(idx):
            continue
        td = idx[pos]
        p = idx.get_loc(td)
        if p < 2:
            continue
        rows.append({
            "date": td,
            "announce_day": cc.iloc[p],          # close[d-1] -> close[d]  (primaire)
            "day_before": cc.iloc[p - 1],        # close[d-2] -> close[d-1]
            "window2": c.iloc[p] / c.iloc[p - 2] - 1.0,  # close[d-2] -> close[d]
        })
    ev = pd.DataFrame(rows).set_index("date")
    return ev, cc

"""Event-study CAR market-adjusted autour des cliff unlocks.

AR_d = r_token,d - r_BTC,d (excès marché, β=1 base). CAR = Σ AR sur fenêtres
pré [-10,-1] / event [-1,+1] / post [+1,+10]. Taille = tokens / circ_supply(t0).
"""
from __future__ import annotations

import bisect

import pandas as pd

LO, HI = -10, 10


def returns_from_csv(path) -> pd.Series:
    df = pd.read_csv(path)
    df["d"] = pd.to_datetime(df["ts"], unit="ms").dt.normalize()
    s = df.set_index("d")["close"].astype(float).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return s.pct_change(fill_method=None)


def _supply_asof(ev: dict) -> float:
    ts_list = ev["_supply_ts"]
    if not ts_list:
        return 0.0
    i = bisect.bisect_right(ts_list, ev["ts"]) - 1
    return ev["_supply"][ts_list[i]] if i >= 0 else 0.0


def build_event_table(events: list[dict], rets: dict, btc: pd.Series,
                      perp: set) -> pd.DataFrame:
    """Une ligne par event exploitable (prix dispo sur la fenêtre)."""
    rows = []
    for ev in events:
        sym = ev["symbol"]
        tr = rets.get(sym)
        if tr is None:
            continue
        t0 = pd.Timestamp(ev["ts"], unit="s").normalize()
        days = pd.date_range(t0 + pd.Timedelta(days=LO), t0 + pd.Timedelta(days=HI), freq="D")
        ar = tr.reindex(days) - btc.reindex(days)
        if ar.isna().mean() > 0.3:  # token pas encore listé / trop de trous
            continue
        ar = ar.fillna(0.0).to_numpy()
        # index i = offset - LO ; -10→0, -1→9, 0→10, +1→11, +10→20
        car_pre = float(ar[0:10].sum())
        car_event = float(ar[9:12].sum())
        car_post = float(ar[11:21].sum())
        circ = _supply_asof(ev)
        size = ev["tokens"] / circ if circ > 0 else float("nan")
        rows.append({
            "symbol": sym, "slug": ev["slug"], "date": t0, "year": t0.year,
            "category": ev["category"], "size": size,
            "car_pre": car_pre, "car_event": car_event, "car_post": car_post,
            "shortable": sym in perp,
        })
    return pd.DataFrame(rows)

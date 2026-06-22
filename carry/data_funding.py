"""Historique funding des perpetuals Binance (fapi), urllib paginé. Cache data/."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

_DATA = Path(__file__).parent / "data"
_BASE = "https://fapi.binance.com/fapi/v1/fundingRate"
_START = 1567296000000  # 2019-09-01 UTC (ms)


_WINDOW = 300 * 86400 * 1000  # 300 j en ms (< 1000 fundings 8h/fenêtre)


def _fetch(symbol: str, start: int, end: int) -> list[dict]:
    # IMPORTANT : startTime SEUL est ignoré par l'endpoint (renvoie le récent).
    # Il faut borner start ET end pour walker l'historique complet.
    url = f"{_BASE}?symbol={symbol}&startTime={start}&endTime={end}&limit=1000"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def funding(symbol: str, refresh: bool = False) -> pd.DataFrame:
    """DataFrame indexé par temps (8h) : fundingRate, markPrice."""
    _DATA.mkdir(exist_ok=True)
    path = _DATA / f"funding_{symbol}.csv"
    if refresh or not path.exists():
        rows: list[dict] = []
        now = int(time.time() * 1000)
        start = _START
        while start < now:
            end = min(start + _WINDOW, now)
            rows.extend(_fetch(symbol, start, end))
            start = end + 1
            time.sleep(0.15)
        df = pd.DataFrame(rows)[["fundingTime", "fundingRate", "markPrice"]]
        df = df.drop_duplicates(subset="fundingTime")
        df.to_csv(path, index=False)
    df = pd.read_csv(path)
    df["time"] = pd.to_datetime(df["fundingTime"], unit="ms")
    df["fundingRate"] = pd.to_numeric(df["fundingRate"], errors="coerce")
    df["markPrice"] = pd.to_numeric(df["markPrice"], errors="coerce")
    df.loc[df["markPrice"] <= 0, "markPrice"] = float("nan")  # markPrice absent avant ~2023
    df = df.dropna(subset=["fundingRate"])
    out = df.set_index("time").sort_index()
    print(f"  {symbol}: {len(out)} points funding 8h, "
          f"{out.index.min().date()} -> {out.index.max().date()}")
    return out

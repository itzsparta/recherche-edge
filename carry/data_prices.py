"""Klines spot + perp Binance (urllib paginé) pour le P&L delta-neutre RÉEL.

Phase-2 : la Phase-1 utilisait markPrice (proxy, legs circulaires). Ici on fetch le **vrai**
spot (api.binance.com) et le **vrai** perp (fapi.binance.com) séparément.
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

_DATA = Path(__file__).parent / "data"
_START = 1567296000000  # 2019-09-01 UTC (ms), aligné sur le funding Phase-1
_SPOT = "https://api.binance.com/api/v3/klines"
_PERP = "https://fapi.binance.com/fapi/v1/klines"
_MS = {"1d": 86_400_000, "8h": 28_800_000}


def _fetch(base: str, symbol: str, interval: str, start: int, end: int) -> list:
    url = (f"{base}?symbol={symbol}&interval={interval}"
           f"&startTime={start}&endTime={end}&limit=1000")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _klines(base: str, symbol: str, interval: str, tag: str, refresh: bool) -> pd.DataFrame:
    _DATA.mkdir(exist_ok=True)
    path = _DATA / f"klines_{tag}_{symbol}_{interval}.csv"
    if refresh or not path.exists():
        rows: list = []
        now = int(time.time() * 1000)
        step = _MS[interval] * 1000
        start = _START
        while start < now:
            end = min(start + step, now)
            batch = _fetch(base, symbol, interval, start, end)
            if not batch:
                start = end + 1
                continue
            rows.extend(batch)
            start = batch[-1][0] + _MS[interval]
            time.sleep(0.12)
        df = pd.DataFrame(rows).iloc[:, :6]
        df.columns = ["openTime", "open", "high", "low", "close", "volume"]
        df = df.drop_duplicates(subset="openTime")
        df.to_csv(path, index=False)
    df = pd.read_csv(path)
    df["time"] = pd.to_datetime(df["openTime"], unit="ms")
    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    out = df.set_index("time").sort_index()[["open", "high", "low", "close"]]
    print(f"  {tag} {symbol} {interval}: {len(out)} barres, "
          f"{out.index.min().date()} -> {out.index.max().date()}")
    return out


def spot_daily(symbol: str, refresh: bool = False) -> pd.DataFrame:
    return _klines(_SPOT, symbol, "1d", "spot", refresh)


def perp_daily(symbol: str, refresh: bool = False) -> pd.DataFrame:
    return _klines(_PERP, symbol, "1d", "perp", refresh)


def perp_8h(symbol: str, refresh: bool = False) -> pd.DataFrame:
    return _klines(_PERP, symbol, "8h", "perp", refresh)

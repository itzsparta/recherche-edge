"""Klines spot daily Binance pour la piste 7 (RV BTC/ETH cointegration daily).

Réutilise le pattern urllib paginé de carry/data_prices.py mais remonte au listing
Binance (2017-08) pour couvrir l'IS 2017-2021 du gate pré-enregistré.
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

_DATA = Path(__file__).parent / "data"
_START = 1502928000000  # 2017-08-17 UTC (ms) ~ listing BTCUSDT/ETHUSDT Binance
_SPOT = "https://api.binance.com/api/v3/klines"
_DAY_MS = 86_400_000


def _fetch(symbol: str, start: int, end: int) -> list:
    url = (f"{_SPOT}?symbol={symbol}&interval=1d"
           f"&startTime={start}&endTime={end}&limit=1000")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def spot_daily(symbol: str, refresh: bool = False) -> pd.DataFrame:
    _DATA.mkdir(exist_ok=True)
    path = _DATA / f"spot_{symbol}_1d.csv"
    if refresh or not path.exists():
        rows: list = []
        now = int(time.time() * 1000)
        step = _DAY_MS * 1000
        start = _START
        while start < now:
            end = min(start + step, now)
            batch = _fetch(symbol, start, end)
            if not batch:
                start = end + 1
                continue
            rows.extend(batch)
            start = batch[-1][0] + _DAY_MS
            time.sleep(0.12)
        df = pd.DataFrame(rows).iloc[:, :6]
        df.columns = ["openTime", "open", "high", "low", "close", "volume"]
        df = df.drop_duplicates(subset="openTime")
        df.to_csv(path, index=False)
    df = pd.read_csv(path)
    df["time"] = pd.to_datetime(df["openTime"], unit="ms")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    out = df.set_index("time").sort_index()[["close"]]
    print(f"  {symbol} 1d: {len(out)} barres, "
          f"{out.index.min().date()} -> {out.index.max().date()}")
    return out

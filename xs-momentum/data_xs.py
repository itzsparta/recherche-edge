"""Univers + klines daily perp Binance (fapi) pour le momentum cross-sectionnel.

Univers FIXE pré-enregistré (docs/SPEC.md) : perps USDT-margined onboardés < 2021-06-01
et TRADING aujourd'hui. Biais survivant assumé (alts morts exclus) => résultats optimistes.
Fetch paginé urllib, cache CSV data/. Gratuit.
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

_DATA = Path(__file__).parent / "data"
_FAPI = "https://fapi.binance.com/fapi/v1"
_START = 1_577_836_800_000   # 2020-01-01 UTC (ms)
_DAY_MS = 86_400_000
_CUT_ONBOARD = 1_622_505_600_000  # 2021-06-01


def _get(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def get_universe(refresh: bool = False) -> list[str]:
    """Symboles perp USDT, onboard < 2021-06-01, TRADING. Liste figée, déterministe."""
    _DATA.mkdir(exist_ok=True)
    path = _DATA / "universe.json"
    if refresh or not path.exists():
        info = _get(f"{_FAPI}/exchangeInfo")
        u = sorted(s["symbol"] for s in info["symbols"]
                   if s.get("quoteAsset") == "USDT"
                   and s.get("contractType") == "PERPETUAL"
                   and s.get("status") == "TRADING"
                   and s.get("onboardDate", 9e18) < _CUT_ONBOARD)
        path.write_text(json.dumps(u))
    return json.loads(path.read_text())


def fetch_close(symbol: str, refresh: bool = False) -> pd.Series:
    """Close daily d'un perp, paginé, cache CSV. Série float indexée date."""
    _DATA.mkdir(exist_ok=True)
    path = _DATA / f"k_{symbol}.csv"
    if refresh or not path.exists():
        rows: list = []
        now = int(time.time() * 1000)
        start = _START
        step = _DAY_MS * 1000
        while start < now:
            end = min(start + step, now)
            batch = _get(f"{_FAPI}/klines?symbol={symbol}&interval=1d"
                         f"&startTime={start}&endTime={end}&limit=1000")
            if not batch:
                break
            rows.extend(batch)
            start = int(batch[-1][0]) + _DAY_MS
            time.sleep(0.05)
        if not rows:
            raise RuntimeError(f"klines vides {symbol}")
        df = pd.DataFrame(rows).iloc[:, [0, 4]]
        df.columns = ["ts", "close"]
        df["date"] = pd.to_datetime(df["ts"].astype("int64"), unit="ms").dt.normalize()
        df = df.drop_duplicates("date").set_index("date")["close"].astype(float)
        df.to_csv(path)
    s = pd.read_csv(path, parse_dates=["date"]).set_index("date")["close"].astype(float)
    s.name = symbol
    return s.sort_index()


def load_panel(refresh: bool = False) -> pd.DataFrame:
    """Panel daily close aligné (colonnes = symboles de l'univers fixe)."""
    syms = get_universe(refresh=refresh)
    cols = {}
    for i, sym in enumerate(syms):
        try:
            cols[sym] = fetch_close(sym, refresh=refresh)
        except Exception as e:
            print(f"  skip {sym}: {e}")
    panel = pd.DataFrame(cols).sort_index()
    print(f"  univers {len(cols)} perps, panel {panel.shape[0]}j "
          f"[{panel.index.min().date()} -> {panel.index.max().date()}]")
    return panel

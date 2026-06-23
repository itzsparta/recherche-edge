"""Données crypto via API publique Deribit (gratuit). Cache data/.

DVOL = indice de vol implicite 30 j (analogue VIX) pour BTC/ETH.
PERP close = spot (pour la variance réalisée). Source unique = Deribit, zéro
dépendance yfinance. Pré-enregistré dans docs/SPEC-crypto.md.
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

_DATA = Path(__file__).parent / "data"
_BASE = "https://www.deribit.com/api/v2/public"
_START_MS = 1_609_459_200_000   # 2021-01-01 (avant inception DVOL ; on garde ce qui existe)
_DAY_MS = 86_400_000
_STEP_MS = 200 * _DAY_MS         # chunk de 200 j (sous la limite Deribit)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _get(endpoint: str, params: dict) -> dict:
    r = requests.get(f"{_BASE}/{endpoint}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()["result"]


def _to_date_series(pairs: dict[int, float], name: str) -> pd.Series:
    """{ts_ms: valeur} -> série float indexée par date (UTC, normalisée jour)."""
    idx = pd.to_datetime(sorted(pairs), unit="ms", utc=True).tz_localize(None).normalize()
    s = pd.Series([pairs[k] for k in sorted(pairs)], index=idx, name=name)
    return s[~s.index.duplicated(keep="last")].sort_index()


def fetch_dvol(currency: str, refresh: bool = False) -> pd.Series:
    """Indice DVOL daily (close) pour BTC/ETH, depuis cache ou Deribit."""
    _DATA.mkdir(exist_ok=True)
    path = _DATA / f"DVOL_{currency}.csv"
    if refresh or not path.exists():
        pairs: dict[int, float] = {}
        a, end = _START_MS, _now_ms()
        while a < end:
            b = min(a + _STEP_MS, end)
            res = _get("get_volatility_index_data", {
                "currency": currency, "start_timestamp": a,
                "end_timestamp": b, "resolution": "1D"})
            for ts, _o, _h, _l, c in res.get("data", []):
                pairs[int(ts)] = float(c)
            a = b + _DAY_MS
            time.sleep(0.1)
        if not pairs:
            raise RuntimeError(f"Deribit: pas de DVOL pour {currency}")
        _to_date_series(pairs, f"dvol_{currency}").to_csv(path)
    df = pd.read_csv(path, parse_dates=[0]).set_index(pd.read_csv(path, parse_dates=[0]).columns[0])
    s = df.iloc[:, 0].astype(float)
    s.index.name = "date"
    s.name = f"dvol_{currency}"
    return s.sort_index()


def fetch_spot(currency: str, refresh: bool = False) -> pd.Series:
    """Close daily du perpétuel (proxy spot) pour la variance réalisée."""
    _DATA.mkdir(exist_ok=True)
    instr = f"{currency}-PERPETUAL"
    path = _DATA / f"SPOT_{currency}.csv"
    if refresh or not path.exists():
        pairs: dict[int, float] = {}
        a, end = _START_MS, _now_ms()
        while a < end:
            b = min(a + _STEP_MS, end)
            res = _get("get_tradingview_chart_data", {
                "instrument_name": instr, "start_timestamp": a,
                "end_timestamp": b, "resolution": "1D"})
            ticks, close = res.get("ticks", []), res.get("close", [])
            for ts, c in zip(ticks, close):
                pairs[int(ts)] = float(c)
            a = b + _DAY_MS
            time.sleep(0.1)
        if not pairs:
            raise RuntimeError(f"Deribit: pas de spot pour {instr}")
        _to_date_series(pairs, f"spot_{currency}").to_csv(path)
    df = pd.read_csv(path, parse_dates=[0]).set_index(pd.read_csv(path, parse_dates=[0]).columns[0])
    s = df.iloc[:, 0].astype(float)
    s.index.name = "date"
    s.name = f"spot_{currency}"
    return s.sort_index()


def load(currency: str, refresh: bool = False) -> pd.DataFrame:
    """DataFrame daily aligné {dvol, spot} pour une crypto."""
    dvol = fetch_dvol(currency, refresh=refresh)
    spot = fetch_spot(currency, refresh=refresh)
    out = pd.DataFrame({"dvol": dvol, "spot": spot}).sort_index()
    print(f"  {currency}: dvol {len(dvol)}j [{dvol.index.min().date()} -> {dvol.index.max().date()}]"
          f"  spot {len(spot)}j  aligné {out.dropna().shape[0]}j")
    return out

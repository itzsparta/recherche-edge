"""Piste 8 — données CEFConnect (univers + historique prix/NAV/discount hebdo).

API publique CEFConnect. Tout est caché sur disque (data/) ; reproductible.
Convention DiscountData : positif = premium (price > NAV), négatif = discount.
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

_DATA = Path(__file__).parent / "data"
_H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
_FUNDS = "https://www.cefconnect.com/api/v3/funds"
_DAILY = "https://www.cefconnect.com/api/v3/DailyPricing"
_HIST = "https://www.cefconnect.com/api/v3/pricinghistory/{t}/All"


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers=_H)
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode()


def universe(refresh: bool = False) -> pd.DataFrame:
    """Liste {Ticker, Name} + métadonnée (catégorie, sponsor, discount courant)."""
    _DATA.mkdir(exist_ok=True)
    fp, dp = _DATA / "funds.json", _DATA / "daily.json"
    if refresh or not fp.exists():
        fp.write_text(_get(_FUNDS), encoding="utf-8")
    if refresh or not dp.exists():
        dp.write_text(_get(_DAILY), encoding="utf-8")
    funds = pd.DataFrame(json.loads(fp.read_text(encoding="utf-8")))
    daily = pd.DataFrame(json.loads(dp.read_text(encoding="utf-8")))
    keep = [c for c in ["Ticker", "Discount", "CategoryName", "SponsorName",
                        "DistributionRateNAV"] if c in daily.columns]
    out = funds.merge(daily[keep], on="Ticker", how="left")
    return out


def history(ticker: str, refresh: bool = False) -> pd.DataFrame | None:
    """Série hebdo prix/NAV/discount d'un fonds. None si vide/erreur."""
    _DATA.mkdir(exist_ok=True)
    raw = _DATA / "hist"
    raw.mkdir(exist_ok=True)
    path = raw / f"{ticker}.json"
    if refresh or not path.exists():
        try:
            body = _get(_HIST.format(t=ticker))
        except Exception:
            return None
        path.write_text(body, encoding="utf-8")
        time.sleep(0.12)
    try:
        ph = json.loads(path.read_text(encoding="utf-8"))["Data"]["PriceHistory"]
    except Exception:
        return None
    if not ph:
        return None
    df = pd.DataFrame(ph)
    df["date"] = pd.to_datetime(df["DataDate"])
    df = df.rename(columns={"Data": "price", "NAVData": "nav", "DiscountData": "prem"})
    df = df.set_index("date").sort_index()[["price", "nav", "prem"]]
    for c in ["price", "nav", "prem"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["prem"])


def fetch_all(tickers: list[str], refresh: bool = False) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for i, t in enumerate(tickers):
        h = history(t, refresh=refresh)
        if h is not None and len(h) > 0:
            out[t] = h
        if (i + 1) % 50 == 0:
            print(f"  …{i + 1}/{len(tickers)} fonds récupérés ({len(out)} valides)")
    return out

"""Récupération données daily via yfinance (auto_adjust = rendement total). Cache data/.

auto_adjust=True → Close ajusté splits ET dividendes = vrai rendement total (pas de
caveat coupon obligataire). Cache CSV local pour runs rapides/offline.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import yfinance as yf

_DATA = Path(__file__).parent / "data"
_START = "2003-01-01"


def close_series(ticker: str, refresh: bool = False) -> pd.Series:
    """Série Close (rendement total) daily indexée par date, depuis cache ou yfinance."""
    _DATA.mkdir(exist_ok=True)
    path = _DATA / f"{ticker}.csv"
    if refresh or not path.exists():
        df = yf.download(ticker, start=_START, auto_adjust=True, progress=False)
        if df is None or df.empty:
            raise RuntimeError(f"yfinance: pas de données pour {ticker}")
        close = df["Close"]
        s = close[ticker] if isinstance(close, pd.DataFrame) else close  # MultiIndex
        s.to_csv(path)
    df = pd.read_csv(path, parse_dates=["Date"]).set_index("Date").sort_index()
    s = df.iloc[:, 0].astype(float)
    s.name = ticker
    return s


def load_universe(tickers: list[str], refresh: bool = False, workers: int = 8) -> pd.DataFrame:
    """DataFrame des Close alignés (colonnes = tickers). Fetch parallèle (threads, I/O)."""
    def _one(t):
        return t, close_series(t, refresh=refresh)
    cols = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for t, s in ex.map(_one, tickers):
            cols[t] = s
    for t in tickers:  # log ordonné
        s = cols[t]
        print(f"  {t}: {len(s)} jours, {s.index.min().date()} → {s.index.max().date()}")
    return pd.DataFrame(cols).sort_index()

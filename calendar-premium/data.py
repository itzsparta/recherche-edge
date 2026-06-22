"""Récupération OHLC daily via yfinance (auto_adjust). Cache data/.

Open + Close ajustés (splits/dividendes) pour la décomposition overnight/intraday.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf

_DATA = Path(__file__).parent / "data"
_START = "1990-01-01"


def ohlc(ticker: str, refresh: bool = False) -> pd.DataFrame:
    """DataFrame [Open, Close] daily ajuste, depuis cache ou yfinance."""
    _DATA.mkdir(exist_ok=True)
    path = _DATA / f"{ticker}.csv"
    if refresh or not path.exists():
        df = yf.download(ticker, start=_START, auto_adjust=True, progress=False)
        if df is None or df.empty:
            raise RuntimeError(f"yfinance: pas de données pour {ticker}")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df[["Open", "Close"]].to_csv(path)
    df = pd.read_csv(path, parse_dates=["Date"]).set_index("Date").sort_index()
    out = df[["Open", "Close"]].astype(float)
    out = out[(out["Open"] > 0) & (out["Close"] > 0)]  # garde anti-prix nuls
    print(f"  {ticker}: {len(out)} jours, {out.index.min().date()} -> {out.index.max().date()}")
    return out

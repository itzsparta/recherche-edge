"""Récupération données daily via yfinance. Cache data/.

VIX = niveau d'indice (vol implicite), GSPC = niveau S&P 500 (pour la réalisée),
SPY = rendement total (auto_adjust) pour le benchmark buy-hold. Cache CSV local.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf

_DATA = Path(__file__).parent / "data"
_START = "1990-01-01"


def _safe(ticker: str) -> str:
    """Nom de fichier sûr (^VIX -> VIX)."""
    return ticker.lstrip("^").replace("=", "_")


def close_series(ticker: str, auto_adjust: bool, refresh: bool = False) -> pd.Series:
    """Série Close daily indexée par date, depuis cache ou yfinance."""
    _DATA.mkdir(exist_ok=True)
    path = _DATA / f"{_safe(ticker)}.csv"
    if refresh or not path.exists():
        df = yf.download(ticker, start=_START, auto_adjust=auto_adjust, progress=False)
        if df is None or df.empty:
            raise RuntimeError(f"yfinance: pas de données pour {ticker}")
        close = df["Close"]
        s = close[ticker] if isinstance(close, pd.DataFrame) else close  # MultiIndex
        s.to_csv(path)
    df = pd.read_csv(path, parse_dates=["Date"]).set_index("Date").sort_index()
    s = df.iloc[:, 0].astype(float)
    s.name = ticker
    return s


def load(refresh: bool = False) -> pd.DataFrame:
    """DataFrame aligné: vix (niveau), gspc (niveau), spy (total return)."""
    vix = close_series("^VIX", auto_adjust=False, refresh=refresh)
    gspc = close_series("^GSPC", auto_adjust=False, refresh=refresh)
    spy = close_series("SPY", auto_adjust=True, refresh=refresh)
    for name, s in [("vix", vix), ("gspc", gspc), ("spy", spy)]:
        print(f"  {name}: {len(s)} jours, {s.index.min().date()} -> {s.index.max().date()}")
    return pd.DataFrame({"vix": vix, "gspc": gspc, "spy": spy}).sort_index()

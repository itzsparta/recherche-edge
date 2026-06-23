"""Ingestion FX carry — pré-enregistré docs/SPEC.md (Piste 17).

Spot FX = futures front-month réutilisés de factor-harvest/data/ (returns mensuels,
scale-invariants donc le quoting du future importe peu). Taux 3m interbancaires = FRED
IR3TIB01* (mensuel, gratuit, caché). Sortie = deux DataFrames mensuels alignés :
`ret` (spot returns par devise) et `rate` (taux % par devise + US funding).
"""
from __future__ import annotations

import io
import os
import urllib.request

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FX_DIR = os.path.join(HERE, "..", "factor-harvest", "data")
CACHE = os.path.join(HERE, "data")

# devise -> (ticker future FX, code pays FRED)
CCY = {
    "AUD": ("6A=F", "AU"),
    "GBP": ("6B=F", "GB"),
    "CAD": ("6C=F", "CA"),
    "EUR": ("6E=F", "EZ"),
    "JPY": ("6J=F", "JP"),
    "CHF": ("6S=F", "CH"),
}
USD_FRED = "US"


def _fred(code: str) -> pd.Series:
    """Taux 3m interbancaire FRED IR3TIB01{code}M156N, mensuel (début de mois)."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"fred_{code}.csv")
    if not (os.path.exists(path) and os.path.getsize(path) > 0):
        sid = f"IR3TIB01{code}M156N"
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
        with open(path, "w", encoding="utf-8") as f:
            f.write(raw)
    df = pd.read_csv(path)
    df.columns = ["date", "rate"]
    df["date"] = pd.to_datetime(df["date"])
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
    s = df.dropna().set_index("date")["rate"]
    return s.resample("MS").last()  # month-start


def _fx_monthly_return(ticker: str) -> pd.Series:
    """Return mensuel du future FX (last du mois -> pct_change)."""
    path = os.path.join(FX_DIR, f"{ticker}.csv")
    df = pd.read_csv(path)
    df.columns = ["date", "px"]
    df["date"] = pd.to_datetime(df["date"])
    df["px"] = pd.to_numeric(df["px"], errors="coerce")
    px = df.dropna().set_index("date")["px"].resample("MS").last()
    return px.pct_change()


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Renvoie (ret, rate) mensuels alignés. ret: spot returns par devise.
    rate: taux % par devise + colonne 'USD'."""
    rets = {ccy: _fx_monthly_return(tk) for ccy, (tk, _) in CCY.items()}
    rates = {ccy: _fred(code) for ccy, (_, code) in CCY.items()}
    rates["USD"] = _fred(USD_FRED)
    ret = pd.DataFrame(rets)
    rate = pd.DataFrame(rates)
    # fenêtre commune
    idx = ret.dropna(how="all").index.intersection(rate.dropna(how="all").index)
    idx = idx[idx >= pd.Timestamp("2003-01-01")]
    return ret.reindex(idx), rate.reindex(idx)


if __name__ == "__main__":
    ret, rate = load()
    print(f"  mois={len(ret)}  {ret.index.min():%Y-%m} -> {ret.index.max():%Y-%m}")
    print(f"  devises spot: {list(ret.columns)}")
    print(f"  taux moyens %: " + ", ".join(f"{c}={rate[c].mean():.2f}" for c in rate.columns))
    print(f"  NaN spot par devise: {ret.isna().sum().to_dict()}")

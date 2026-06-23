"""Régénère les 3 sleeves RÉELS en rendements mensuels alignés — pré-enregistré docs/SPEC.md.

Réutilise les moteurs DÉJÀ VALIDÉS (pas de réimplémentation = pas de triche) :
  - trend 12m + 60/40 = factor-harvest/backtest.py (vol-targeté, no-look-ahead)
  - FX carry G10     = fx-carry/carry.py (net de coûts, signal laggé)
Lecture directe des caches CSV (pas d'import yfinance). Sortie = DataFrame mensuel
indexé Period[M], colonnes {base6040, trend, carry}, sur l'intersection commune.
"""
from __future__ import annotations

import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FH = os.path.join(HERE, "..", "factor-harvest")
FX = os.path.join(HERE, "..", "fx-carry")
sys.path.insert(0, FX)
sys.path.insert(0, FH)

import backtest  # noqa: E402  (factor-harvest, numpy/pandas only)
import carry     # noqa: E402  (fx-carry, importe data_fx — pas de yfinance)

UNIVERSE = ["SPY", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC", "USO", "VNQ"]


def _load_prices(universe: list[str]) -> pd.DataFrame:
    """Lit les Close cachés (rendement total) factor-harvest/data/*.csv."""
    cols = {}
    for t in universe:
        path = os.path.join(FH, "data", f"{t}.csv")
        df = pd.read_csv(path, parse_dates=["Date"]).set_index("Date").sort_index()
        cols[t] = df.iloc[:, 0].astype(float)
    return pd.DataFrame(cols).sort_index()


def _to_period(s: pd.Series) -> pd.Series:
    """Réindexe une série mensuelle (month-end OU month-start) sur Period[M]."""
    out = s.copy()
    out.index = pd.PeriodIndex(out.index, freq="M")
    return out[~out.index.duplicated(keep="last")]


def load_sleeves() -> pd.DataFrame:
    """DataFrame mensuel Period[M] : colonnes base6040, trend, carry (intersection)."""
    prices = _load_prices(UNIVERSE).dropna()
    trend = backtest.run_strategy(prices, lookback_months=12)["monthly"]
    base = backtest.benchmark_6040(prices)["monthly"]
    carry_net = carry.carry_portfolio()["net"]

    s = pd.DataFrame({
        "base6040": _to_period(base),
        "trend": _to_period(trend),
        "carry": _to_period(carry_net),
    }).dropna()
    return s


if __name__ == "__main__":
    import math
    import audit
    s = load_sleeves()
    print(f"  échantillon: {s.index.min()} -> {s.index.max()}  ({len(s)} mois)")
    for c in s.columns:
        sr = audit.sharpe(list(s[c])) * math.sqrt(12)
        print(f"  {c:9s} ann={s[c].mean()*12*100:+6.2f}%  Sharpe={sr:+.2f}  "
              f"t={audit.tstat(list(s[c])):+.2f}")
    print("  corr:\n", s.corr().round(3).to_string())

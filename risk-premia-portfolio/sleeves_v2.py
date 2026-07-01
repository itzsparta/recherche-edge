"""Méta v2 — 4 sleeves RÉELS mensuels alignés. Réutilise les moteurs DÉJÀ VALIDÉS (no triche) :
  - base6040 + trend : factor-harvest/backtest.py sur l'univers ETF (comme sleeves.py v1)
  - carry_energy     : commodity-carry/run_carry.py (#30, TS-carry énergie EIA, cache)
  - ils              : ils-catbond/run_ils.py (#31, equal-weight funds ILS total-return, cache)
Remplace le FX-carry diluant (corr +0.41) par les 2 sleeves ORTHOGONAUX neufs. Sortie Period[M], union.

NB clash : run_carry.py existe aussi dans fx-carry/ → on force commodity-carry en tête de sys.path
et on charge via importlib en purgeant les modules stale (sinon AttributeError build_monthly).
"""
from __future__ import annotations
import importlib, os, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FH = os.path.join(HERE, "..", "factor-harvest")
CC = os.path.join(HERE, "..", "commodity-carry")
ILS = os.path.join(HERE, "..", "ils-catbond")

sys.path.insert(0, HERE)
import sleeves as _v1               # noqa: E402 amène FH+FX sur le path, backtest, carry(fx)
for p in (FH, ILS, CC):            # insert(0) successifs → CC finit en position 0 (devant fx-carry)
    sys.path.insert(0, p)
import backtest                     # noqa: E402 (cached depuis _v1)


def _carry_energy() -> pd.Series:
    for m in ("run_carry", "data_eia"):
        sys.modules.pop(m, None)    # purge un éventuel fx-carry/run_carry stale
    data_eia = importlib.import_module("data_eia")     # commodity-carry (CC en tête)
    run_carry = importlib.import_module("run_carry")
    panel = data_eia.discover()
    monthly = run_carry.build_monthly(panel)
    return run_carry.portfolio(monthly, list(panel)).rename("carry_energy")


def _ils() -> pd.Series:
    sys.modules.pop("run_ils", None)
    run_ils = importlib.import_module("run_ils")        # ils-catbond
    ew = pd.concat([run_ils.monthly_ret(t) for t in run_ils.FUNDS], axis=1).mean(axis=1)
    return ew.dropna().rename("ils")


def load_sleeves_v2() -> pd.DataFrame:
    """DataFrame Period[M] : base6040, trend, carry_energy, ils (union outer-join)."""
    prices = _v1._load_prices(_v1.UNIVERSE).dropna()
    trend = backtest.run_strategy(prices, lookback_months=12)["monthly"]
    base = backtest.benchmark_6040(prices)["monthly"]
    cols = {
        "base6040": _v1._to_period(base),
        "trend": _v1._to_period(trend),
        "carry_energy": _v1._to_period(_carry_energy()),
        "ils": _v1._to_period(_ils()),
    }
    return pd.DataFrame(cols).sort_index()


if __name__ == "__main__":
    import math, audit
    s = load_sleeves_v2()
    print(f"  union: {s.index.min()} -> {s.index.max()} ({len(s)} mois)")
    for c in s.columns:
        x = s[c].dropna()
        print(f"  {c:13s} {x.index.min()}->{x.index.max()} n={len(x):3d} "
              f"ann={x.mean()*12*100:+6.2f}% Sharpe={audit.sharpe(list(x))*math.sqrt(12):+.2f}")
    print("\n  corr (paires complètes):\n" + s.corr().round(3).to_string())

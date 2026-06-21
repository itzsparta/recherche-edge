"""Pré-test piste 1 : verdict contre les critères PRÉ-ENREGISTRÉS de docs/SPEC.md.

Usage: .venv/Scripts/python run.py [--refresh]
"""
from __future__ import annotations

import argparse
import math

import numpy as np
import pandas as pd

import audit
import backtest
import data

UNIVERSE = ["SPY", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC", "USO", "VNQ"]
LOOKBACKS = [6, 9, 12, 15]
BASE_LB = 12

REGIMES = [
    ("pré-GFC", None, "2007-12-31"),
    ("GFC 2008", "2008-01-01", "2009-06-30"),
    ("reprise 2010s", "2009-07-01", "2019-12-31"),
    ("COVID 2020", "2020-01-01", "2020-12-31"),
    ("2021+ (infl/2022)", "2021-01-01", None),
]


def ann_sharpe(monthly: pd.Series) -> float:
    return audit.sharpe(list(monthly.dropna())) * math.sqrt(12)


def t_stat(monthly: pd.Series) -> float:
    return audit.tstat(list(monthly.dropna()))


def total_ret(monthly: pd.Series, a, b) -> float:
    m = monthly.loc[a:b].dropna()
    return float((1 + m).prod() - 1) if len(m) else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    print("=== Chargement univers (stooq) ===")
    prices = data.load_universe(UNIVERSE, refresh=args.refresh)
    prices = prices.dropna()
    print(f"\nÉchantillon commun : {prices.index.min().date()} → {prices.index.max().date()} "
          f"({len(prices)} jours, {prices.shape[1]} actifs)\n")

    # --- config de base 12m ---
    base = backtest.run_strategy(prices, lookback_months=BASE_LB)
    m = base["monthly"]
    sr, t = ann_sharpe(m), t_stat(m)
    bench = backtest.benchmark_6040(prices)
    sr_b = ann_sharpe(bench["monthly"])

    print("=" * 64)
    print(f"STRAT trend 12m  | Sharpe(ann) {sr:+.2f}  t={t:+.2f}  "
          f"vol réalisée {base['realized_vol']*100:.1f}%  levier moy {base['leverage_mean']:.2f}x")
    print(f"60/40 passif     | Sharpe(ann) {sr_b:+.2f}  vol {bench['realized_vol']*100:.1f}%")
    cagr = base["equity"].iloc[-1] ** (252 / len(base["net"])) - 1
    print(f"CAGR net strat {cagr*100:+.1f}%  | equity final {base['equity'].iloc[-1]:.2f}x")

    # ============ (A) L'EDGE EXISTE ============
    print("\n" + "=" * 64 + "\n(A) L'EDGE EXISTE")
    a_sharpe_t = sr > 0 and t > 2
    print(f"  [{'PASS' if a_sharpe_t else 'FAIL'}] Sharpe>0 & t>2 : SR={sr:+.2f}, t={t:+.2f}")

    # régimes
    pos_reg = 0
    print("  Sous-périodes régime (rendement net total) :")
    for name, a, b in REGIMES:
        tr = total_ret(m, a, b)
        ok = tr > 0
        pos_reg += ok
        print(f"      {name:20s} {tr*100:+7.1f}%  {'ok' if ok else '—'}")
    a_regimes = pos_reg >= 3
    print(f"  [{'PASS' if a_regimes else 'FAIL'}] majorité régimes positifs : {pos_reg}/5")

    # drop-one
    drop_srs = {}
    for tk in UNIVERSE:
        sub = prices.drop(columns=[tk])
        drop_srs[tk] = ann_sharpe(backtest.run_strategy(sub, lookback_months=BASE_LB)["monthly"])
    worst_tk = min(drop_srs, key=drop_srs.get)
    a_dropone = drop_srs[worst_tk] > 0
    print(f"  [{'PASS' if a_dropone else 'FAIL'}] drop-one : pire = sans {worst_tk} → SR {drop_srs[worst_tk]:+.2f}")

    # robustesse lookback + DSR
    lb_monthly = {lb: backtest.run_strategy(prices, lookback_months=lb)["monthly"] for lb in LOOKBACKS}
    lb_sr = {lb: ann_sharpe(mm) for lb, mm in lb_monthly.items()}
    all_pos = all(v > 0 for v in lb_sr.values())
    print("  Robustesse lookback :", "  ".join(f"{lb}m:{v:+.2f}" for lb, v in lb_sr.items()),
          f" [{'PASS' if all_pos else 'FAIL'}] tous positifs")
    # DSR sur le meilleur lookback
    srs_period = [audit.sharpe(list(mm.dropna())) for mm in lb_monthly.values()]
    var_trials = float(np.var(srs_period))
    best_lb = max(lb_sr, key=lb_sr.get)
    best_m = list(lb_monthly[best_lb].dropna())
    dsr4, _, sr0_4 = audit.deflated_sharpe(best_m, len(LOOKBACKS), var_trials)
    dsr20, _, _ = audit.deflated_sharpe(best_m, 20, var_trials)
    a_dsr = dsr4 > 0.95
    print(f"  [{'PASS' if a_dsr else 'FAIL'}] DSR(best={best_lb}m, N=4)={dsr4:.3f}  (N=20:{dsr20:.3f}) "
          f"seuil 0.95")

    A = a_sharpe_t and a_regimes and a_dropone and all_pos and a_dsr
    print(f"  ==> (A) {'PASS' if A else 'FAIL'}")

    # ============ (B) L'EDGE VAUT LE COUP ============
    print("\n" + "=" * 64 + "\n(B) L'EDGE VAUT LE COUP")
    b_beats = sr > sr_b
    print(f"  [{'PASS' if b_beats else 'FAIL'}] bat 60/40 risk-adj : {sr:+.2f} vs {sr_b:+.2f}")
    r2008, r2022 = total_ret(m, "2008-01-01", "2008-12-31"), total_ret(m, "2022-01-01", "2022-12-31")
    spy_m = prices["SPY"].pct_change(fill_method=None).resample("ME").apply(lambda x: (1+x).prod()-1)
    corr = float(m.corr(spy_m))
    b_crisis = r2008 > 0 and r2022 > 0
    print(f"  [{'PASS' if b_crisis else 'FAIL'}] crisis-alpha : 2008 {r2008*100:+.1f}% & 2022 {r2022*100:+.1f}% "
          f"(corr actions {corr:+.2f})")
    B = b_beats or b_crisis
    print(f"  ==> (B) {'PASS' if B else 'FAIL'}")

    # ============ VERDICT ============
    print("\n" + "=" * 64)
    if A and B:
        verdict = "GO — protocole complet (walk-forward, MC, paper)"
    elif A and not B:
        verdict = "DOWNGRADE — premium réel mais le passif fait pareil, pas worth solo"
    else:
        verdict = "KILL — pas d'edge robuste cross-régime"
    print(f"VERDICT (standalone, pré-enregistré) : {verdict}")
    print("=" * 64)

    # ===== DIAGNOSTIC (hors verdict) : valeur comme SLEEVE dans un portefeuille passif =====
    # (B)-crisis a passé (corr faible) → question légitime distincte : un sleeve trend
    # améliore-t-il un cœur 60/40 ? Diagnostic, NE change PAS le verdict standalone.
    print("\nDIAGNOSTIC — trend comme sleeve diversifiant (hors verdict standalone)")
    bm = bench["monthly"].reindex(m.index).dropna()
    tm = m.reindex(bm.index).dropna()
    bm = bm.reindex(tm.index)
    tm_scaled = tm * (bm.std() / tm.std())  # même vol que le 60/40 pour un blend équitable
    rho = float(bm.corr(tm))
    for x in (0.0, 0.15, 0.25, 0.35):
        blend = (1 - x) * bm + x * tm_scaled
        print(f"  sleeve {int(x*100):2d}% trend : Sharpe {ann_sharpe(blend):+.2f}")
    sr1, sr2 = ann_sharpe(bm), ann_sharpe(tm)
    opt = math.sqrt(max(0.0, (sr1**2 - 2*rho*sr1*sr2 + sr2**2) / (1 - rho**2)))
    print(f"  Sharpe blend optimal (théorique, ρ={rho:+.2f}) = {opt:+.2f}  vs 60/40 seul {sr1:+.2f}")


if __name__ == "__main__":
    main()

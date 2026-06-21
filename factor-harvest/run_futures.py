"""Pré-test piste 1bis : trend-following univers FUTURES riche (32 marchés).

Critères identiques à run.py / SPEC.md, univers futures (mode union), compute
parallélisé sur le CPU (ProcessPoolExecutor : drop-one ×32 + lookbacks ×4).

Usage: .venv/Scripts/python run_futures.py [--refresh] [--workers N]
"""
from __future__ import annotations

import argparse
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

import audit
import backtest
import data

FUTURES = {
    "ES=F": "SP500", "NQ=F": "Nasdaq", "YM=F": "Dow", "RTY=F": "Russell",
    "ZB=F": "30Y", "ZN=F": "10Y", "ZF=F": "5Y",
    "CL=F": "WTI", "NG=F": "NatGas", "HO=F": "Heating", "RB=F": "Gasoline", "BZ=F": "Brent",
    "GC=F": "Gold", "SI=F": "Silver", "HG=F": "Copper", "PL=F": "Platinum", "PA=F": "Palladium",
    "ZC=F": "Corn", "ZW=F": "Wheat", "ZS=F": "Soybean",
    "KC=F": "Coffee", "SB=F": "Sugar", "CC=F": "Cocoa", "CT=F": "Cotton",
    "LE=F": "Cattle", "HE=F": "Hogs",
    "6E=F": "EUR", "6J=F": "JPY", "6B=F": "GBP", "6A=F": "AUD", "6C=F": "CAD", "6S=F": "CHF",
}
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


def total_ret(monthly: pd.Series, a, b) -> float:
    m = monthly.loc[a:b].dropna()
    return float((1 + m).prod() - 1) if len(m) else float("nan")


# ---- workers (process pool) : prix partagés via initializer ----
_PX = None


def _init_px(px):
    global _PX
    _PX = px


def _drop_one(tk):
    sub = _PX.drop(columns=[tk])
    m = backtest.run_strategy(sub, lookback_months=BASE_LB, require_all=False)["monthly"]
    return tk, ann_sharpe(m)


def _lookback(lb):
    m = backtest.run_strategy(_PX, lookback_months=lb, require_all=False)["monthly"]
    return lb, list(m.dropna())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    args = ap.parse_args()
    nproc = max(1, min(args.workers, os.cpu_count()))

    print(f"=== Univers FUTURES ({len(FUTURES)} marchés) — fetch parallèle ({nproc} threads) ===")
    prices = data.load_universe(list(FUTURES), refresh=args.refresh, workers=nproc)
    prices = prices.dropna(how="all")
    print(f"\nÉchantillon (union) : {prices.index.min().date()} → {prices.index.max().date()} "
          f"({len(prices)} jours, {prices.shape[1]} marchés)\n")

    base = backtest.run_strategy(prices, lookback_months=BASE_LB, require_all=False)
    m = base["monthly"]
    sr, t = ann_sharpe(m), audit.tstat(list(m.dropna()))

    bench_px = pd.DataFrame({"SPY": data.close_series("SPY"), "IEF": data.close_series("IEF")})
    bench = backtest.benchmark_6040(bench_px)
    sr_b = ann_sharpe(bench["monthly"])

    # ---- compute parallèle : drop-one ×N + lookbacks ----
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=nproc, initializer=_init_px, initargs=(prices,)) as ex:
        lb_res = dict(ex.map(_lookback, LOOKBACKS))
        drop_res = dict(ex.map(_drop_one, list(FUTURES)))
    par_s = time.perf_counter() - t0
    print(f"[parallèle] {len(FUTURES)} drop-one + {len(LOOKBACKS)} lookbacks sur {nproc} "
          f"process en {par_s:.1f}s\n")

    print("=" * 64)
    print(f"STRAT trend 12m  | Sharpe(ann) {sr:+.2f}  t={t:+.2f}  "
          f"vol {base['realized_vol']*100:.1f}%  levier {base['leverage_mean']:.2f}x")
    print(f"60/40 passif     | Sharpe(ann) {sr_b:+.2f}")
    cagr = base["equity"].iloc[-1] ** (252 / len(base["net"])) - 1
    print(f"CAGR net strat {cagr*100:+.1f}%  | equity final {base['equity'].iloc[-1]:.2f}x")

    # ===== (A) =====
    print("\n" + "=" * 64 + "\n(A) L'EDGE EXISTE")
    a_st = sr > 0 and t > 2
    print(f"  [{'PASS' if a_st else 'FAIL'}] Sharpe>0 & t>2 : SR={sr:+.2f}, t={t:+.2f}")
    pos_reg = 0
    print("  Sous-périodes régime (rendement net total) :")
    for name, a, b in REGIMES:
        tr = total_ret(m, a, b)
        ok = tr > 0
        pos_reg += ok
        print(f"      {name:20s} {tr*100:+7.1f}%  {'ok' if ok else '—'}")
    a_reg = pos_reg >= 3
    print(f"  [{'PASS' if a_reg else 'FAIL'}] majorité régimes positifs : {pos_reg}/5")

    worst = min(drop_res, key=drop_res.get)
    a_drop = drop_res[worst] > 0
    print(f"  [{'PASS' if a_drop else 'FAIL'}] drop-one : pire = sans {worst} ({FUTURES[worst]}) "
          f"→ SR {drop_res[worst]:+.2f}")

    lb_sr = {lb: audit.sharpe(r) * math.sqrt(12) for lb, r in lb_res.items()}
    all_pos = all(v > 0 for v in lb_sr.values())
    print("  Robustesse lookback :", "  ".join(f"{lb}m:{v:+.2f}" for lb, v in sorted(lb_sr.items())),
          f" [{'PASS' if all_pos else 'FAIL'}] tous positifs")
    srs_period = [audit.sharpe(r) for r in lb_res.values()]
    var_trials = float(np.var(srs_period))
    best_lb = max(lb_sr, key=lb_sr.get)
    dsr4, _, _ = audit.deflated_sharpe(lb_res[best_lb], len(LOOKBACKS), var_trials)
    dsr20, _, _ = audit.deflated_sharpe(lb_res[best_lb], 20, var_trials)
    a_dsr = dsr4 > 0.95
    print(f"  [{'PASS' if a_dsr else 'FAIL'}] DSR(best={best_lb}m, N=4)={dsr4:.3f}  (N=20:{dsr20:.3f})")
    A = a_st and a_reg and a_drop and all_pos and a_dsr
    print(f"  ==> (A) {'PASS' if A else 'FAIL'}")

    # ===== (B) =====
    print("\n" + "=" * 64 + "\n(B) L'EDGE VAUT LE COUP")
    b_beats = sr > sr_b
    print(f"  [{'PASS' if b_beats else 'FAIL'}] bat 60/40 : {sr:+.2f} vs {sr_b:+.2f}")
    r08, r22 = total_ret(m, "2008-01-01", "2008-12-31"), total_ret(m, "2022-01-01", "2022-12-31")
    spy_m = bench_px["SPY"].pct_change(fill_method=None).resample("ME").apply(lambda x: (1+x).prod()-1)
    corr = float(m.reindex(spy_m.index).corr(spy_m))
    b_cri = r08 > 0 and r22 > 0
    print(f"  [{'PASS' if b_cri else 'FAIL'}] crisis-alpha : 2008 {r08*100:+.1f}% & 2022 {r22*100:+.1f}% "
          f"(corr actions {corr:+.2f})")
    B = b_beats or b_cri
    print(f"  ==> (B) {'PASS' if B else 'FAIL'}")

    # ===== VERDICT =====
    print("\n" + "=" * 64)
    if A and B:
        v = "GO — protocole complet (walk-forward, MC, paper)"
    elif A and not B:
        v = "DOWNGRADE — premium réel mais le passif fait pareil"
    else:
        v = "KILL — pas d'edge robuste cross-régime"
    print(f"VERDICT (standalone, pré-enregistré) : {v}")
    print("=" * 64)

    # diagnostic sleeve
    bm = bench["monthly"].reindex(m.index).dropna()
    tm = m.reindex(bm.index).dropna()
    bm = bm.reindex(tm.index)
    tm_s = tm * (bm.std() / tm.std())
    print("\nDIAGNOSTIC — sleeve trend sur cœur 60/40 :")
    for x in (0.0, 0.15, 0.25, 0.35):
        print(f"  sleeve {int(x*100):2d}% : Sharpe {ann_sharpe((1-x)*bm + x*tm_s):+.2f}")


if __name__ == "__main__":
    main()

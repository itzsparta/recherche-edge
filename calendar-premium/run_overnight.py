"""Runner pre-test 5a overnight — applique les gates pre-enregistres de docs/SPEC.md.

Usage:  python run_overnight.py [--refresh]
"""
from __future__ import annotations

import math
import sys

import audit
import data
import overnight

ANN = math.sqrt(252)       # daily -> annuel
COST = 0.0005              # 5 bps round-trip / cycle overnight (pre-enregistre)
TICKERS = ["SPY", "QQQ", "IWM"]


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def ann_mean(xs) -> float:
    return sum(xs) / len(xs) * 252


def main() -> None:
    refresh = "--refresh" in sys.argv
    section("DONNEES")
    legs = {t: overnight.legs(data.ohlc(t, refresh=refresh)) for t in TICKERS}

    # ---------- (A) L'EFFET EXISTE ----------
    section("(A) L'EFFET EXISTE  [overnight>0 t>2, overnight>intraday, majorite instruments]")
    print(f"  {'tkr':4s} {'on_ann':>9s} {'on_t':>7s} {'id_ann':>9s} {'id_t':>7s} "
          f"{'diff_t':>7s}  pass")
    n_pass = 0
    for t in TICKERS:
        on = legs[t]["overnight"].tolist()
        idy = legs[t]["intraday"].tolist()
        diff = (legs[t]["overnight"] - legs[t]["intraday"]).tolist()
        t_on, t_id, t_diff = audit.tstat(on), audit.tstat(idy), audit.tstat(diff)
        ok = (ann_mean(on) > 0) and (t_on > 2) and (t_diff > 2)
        n_pass += ok
        print(f"  {t:4s} {ann_mean(on):+8.1%} {t_on:+7.2f} {ann_mean(idy):+8.1%} "
              f"{t_id:+7.2f} {t_diff:+7.2f}  {'OK' if ok else '--'}")
    gate_A = n_pass > len(TICKERS) / 2
    print(f"\n  instruments OK: {n_pass}/{len(TICKERS)}  >>> (A) {'PASS' if gate_A else 'FAIL'}")

    # ---------- (B) CAPTURABLE NET (SPY) ----------
    section("(B) CAPTURABLE NET  [SPY: Sharpe net overnight > buy-hold, t>2 ; cout 5bps/cycle]")
    spy = legs["SPY"]
    on = spy["overnight"]
    net = (on - COST).tolist()
    cc = spy["cc"].tolist()
    sr_net = audit.sharpe(net) * ANN
    sr_cc = audit.sharpe(cc) * ANN
    t_net = audit.tstat(net)
    print(f"  overnight BRUT : ann {ann_mean(on.tolist()):+.1%}  Sharpe {audit.sharpe(on.tolist())*ANN:+.2f}")
    print(f"  overnight NET  : ann {ann_mean(net):+.1%}  Sharpe {sr_net:+.2f}  t {t_net:+.2f}")
    print(f"  cout annuel    : {252*COST:.1%}  (252 cycles x 5bps)")
    print(f"  SPY buy-hold   : ann {ann_mean(cc):+.1%}  Sharpe {sr_cc:+.2f}")
    gate_B = (sr_net > sr_cc) and (t_net > 2)
    print(f"\n  >>> (B) {'PASS' if gate_B else 'FAIL'}  (Sharpe_net>{sr_cc:+.2f}? {sr_net > sr_cc}, t>2? {t_net > 2})")

    # ---------- VERDICT ----------
    section("VERDICT PRE-ENREGISTRE (5a overnight)")
    if gate_A and gate_B:
        print("  (A) ^ (B) => GO")
    elif gate_A and not gate_B:
        print("  (A) ^ -(B) => DOWNGRADE : prime overnight REELLE mais mangee par le")
        print("                cout du turnover quotidien (252 cycles/an). Pas worth solo.")
    else:
        print("  -(A) => KILL : effet absent / non robuste cross-instrument.")


if __name__ == "__main__":
    main()

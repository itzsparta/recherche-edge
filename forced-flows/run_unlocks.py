"""Pré-test piste 2 : cliff unlocks (SPEC-unlocks.md). Verdict pré-enregistré.

Signal tradeable = SHORT l'unlock → ret = -CAR market-adjusted. Significativité
CLUSTERÉE par token (moyenne par token puis t cross-token) car events corrélés
intra-token (n brut ~30k gonflerait le t).

Usage: .venv/Scripts/python run_unlocks.py [--refresh] [--workers N]
"""
from __future__ import annotations

import argparse
import os
import time

import numpy as np
import pandas as pd

import audit
import data
import event_study as es

COST = 0.002  # round-trip short (taker x2 + funding ~10j), pré-enregistré


def per_token_short(df: pd.DataFrame, col="car_post", cost=0.0) -> list[float]:
    """Moyenne par token du rendement short net (-CAR - coût)."""
    g = df.assign(r=-df[col] - cost).groupby("symbol")["r"].mean()
    return list(g.dropna())


def report_gate(df, label, cost=0.0, col="car_post"):
    r = per_token_short(df, col=col, cost=cost)
    n_tok, n_ev = len(r), len(df)
    mean, t = (np.mean(r) if r else 0.0), audit.tstat(r)
    print(f"  {label}: events={n_ev} tokens={n_tok} | short net moyen/token "
          f"{mean*100:+.2f}% | t(clusteré)={t:+.2f}")
    return mean, t, n_tok, n_ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    print("=== Events cliff (DefiLlama) ===")
    details = data.load_details(refresh=args.refresh)
    symap = data.symbol_map()
    events = data.cliff_events(details, symap)
    syms = sorted({e["symbol"] for e in events})
    print(f"{len(events)} cliff events | {len(syms)} symboles uniques")

    print(f"\n=== Prix Binance (parallèle {args.workers}) ===")
    t0 = time.perf_counter()
    paths = data.fetch_klines(syms + ["BTC"], refresh=args.refresh, workers=args.workers)
    print(f"klines: {len(paths)}/{len(syms)+1} symboles dispo en {time.perf_counter()-t0:.0f}s")
    btc = es.returns_from_csv(paths["BTC"])
    rets = {s: es.returns_from_csv(p) for s, p in paths.items() if s != "BTC"}
    perp = data.perp_bases()

    df = es.build_event_table(events, rets, btc, perp)
    df = df[df["date"] >= "2021-01-01"]
    print(f"\nEvents exploitables (prix dispo, >=2021) : {len(df)} sur {df['symbol'].nunique()} tokens")

    # ============ (A) L'EFFET EXISTE ============
    print("\n" + "=" * 64 + "\n(A) L'EFFET EXISTE — short l'unlock, market-adjusted, BRUT")
    mean_a, t_a, ntok, nev = report_gate(df, "fenêtre post [+1,+10]")
    report_gate(df, "fenêtre event [-1,+1]", col="car_event")  # diagnostic décompo
    pre_mean = np.mean(per_token_short(df, col="car_pre"))
    print(f"  (diag priced-in: short pré [-10,-1] moyen/token {pre_mean*100:+.2f}%)")

    a_sig = mean_a > 0 and t_a > 2

    # dose-réponse par quartile de taille
    dsz = df.dropna(subset=["size"])
    print("  Dose-réponse (quartile taille unlock/supply → short net moyen/token) :")
    dose = []
    if len(dsz) >= 40:
        dsz = dsz.assign(q=pd.qcut(dsz["size"], 4, labels=False, duplicates="drop"))
        for q in sorted(dsz["q"].dropna().unique()):
            sub = dsz[dsz["q"] == q]
            mq = np.mean(per_token_short(sub))
            dose.append(mq)
            print(f"      Q{int(q)+1} (n={len(sub)}) {mq*100:+.2f}%")
    a_dose = len(dose) >= 2 and dose[-1] > dose[0]
    print(f"  [{'PASS' if a_dose else 'FAIL'}] dose-réponse (Q4>Q1) : "
          f"{dose[-1]*100:+.2f}% vs {dose[0]*100:+.2f}%" if dose else "  [FAIL] dose-réponse: data insuffisante")

    # par année
    print("  Par année (short net moyen/token) :")
    yr_pos = 0
    yrs = sorted(df["year"].unique())
    for y in yrs:
        my = np.mean(per_token_short(df[df["year"] == y]))
        yr_pos += my > 0
        print(f"      {y}: {my*100:+.2f}%")
    a_year = yr_pos >= (len(yrs) + 1) // 2
    print(f"  [{'PASS' if a_year else 'FAIL'}] majorité années positives : {yr_pos}/{len(yrs)}")

    # drop-top-5 tokens (pas porté par une poignée)
    contrib = df.assign(r=-df["car_post"]).groupby("symbol")["r"].mean().sort_values(ascending=False)
    drop5 = set(contrib.head(5).index)
    t_drop = audit.tstat(per_token_short(df[~df["symbol"].isin(drop5)]))
    a_robust = t_drop > 2
    print(f"  [{'PASS' if a_robust else 'FAIL'}] drop-top-5 tokens : t reste {t_drop:+.2f}")

    # DSR multi-essais (fenêtres x specs)
    variants = [per_token_short(df, col=c) for c in ("car_post", "car_event")]
    var_tr = float(np.var([audit.sharpe(v) for v in variants]))
    best = max(variants, key=lambda v: audit.sharpe(v))
    dsr, _, _ = audit.deflated_sharpe(best, 6, var_tr)
    a_dsr = dsr > 0.95
    print(f"  [{'PASS' if a_dsr else 'FAIL'}] DSR(N=6) = {dsr:.3f}")

    print(f"  [{'PASS' if a_sig else 'FAIL'}] effet significatif : {mean_a*100:+.2f}%/token t={t_a:+.2f}")
    A = a_sig and a_dose and a_year and a_robust and a_dsr
    print(f"  ==> (A) {'PASS' if A else 'FAIL'}")

    # ============ (B) CAPTURABLE NET (SHORTABLE) ============
    print("\n" + "=" * 64 + "\n(B) CAPTURABLE NET — sous-ensemble SHORTABLE (perp), net de coûts")
    sh = df[df["shortable"]]
    mean_b, t_b, ntok_b, nev_b = report_gate(sh, "shortable, net coûts", cost=COST)
    evyr = nev_b / max(1, len(sh["year"].unique()))
    B = mean_b > 0 and t_b > 2 and evyr >= 20
    print(f"  events/an shortable ≈ {evyr:.0f}")
    print(f"  ==> (B) {'PASS' if B else 'FAIL'}")

    # ============ VERDICT ============
    print("\n" + "=" * 64)
    if A and B:
        v = "GO — protocole complet"
    elif A and not B:
        v = "KILL-objectif — effet réel mais pas capturable net/shortable"
    else:
        v = "KILL — pas d'effet anormal robuste"
    print(f"VERDICT (pré-enregistré) : {v}")
    print("=" * 64)


if __name__ == "__main__":
    main()

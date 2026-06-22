"""Runner pre-test 5b pré-FOMC drift — gates pré-enregistrés de docs/SPEC.md.

Usage:  python run_fomc.py [--refresh]
"""
from __future__ import annotations

import math
import sys

import pandas as pd

import data
import data_fomc
import fomc

SPLIT = pd.Timestamp("2015-01-01")   # post-publication Lucca-Moench


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def welch(a: list[float], b: list[float]):
    """Two-sample Welch : renvoie (mean_a, mean_b, excess, t)."""
    na, nb = len(a), len(b)
    ma, mb = sum(a) / na, sum(b) / nb
    va = sum((x - ma) ** 2 for x in a) / (na - 1)
    vb = sum((x - mb) ** 2 for x in b) / (nb - 1)
    se = math.sqrt(va / na + vb / nb)
    t = (ma - mb) / se if se > 0 else 0.0
    return ma, mb, ma - mb, t


def main() -> None:
    refresh = "--refresh" in sys.argv
    section("DONNEES")
    spy = data.ohlc("SPY", refresh=refresh)
    dates = data_fomc.announcement_dates(refresh=refresh)
    ev, cc = fomc.event_table(spy, dates)
    cc = cc.dropna()
    fomc_days = set(ev.index)
    base_all = [r for d, r in cc.items() if d not in fomc_days]
    yrs = (ev.index.max() - ev.index.min()).days / 365.25
    per_yr = len(ev) / yrs
    print(f"  events utilisés: {len(ev)}  (~{per_yr:.1f}/an)   baseline non-FOMC: {len(base_all)} jours")

    # ---------- (A) LE DRIFT EXISTE (full) ----------
    section("(A) LE DRIFT EXISTE  [excès FOMC vs non-FOMC > 0, t>2 ; full 1994-2026]")
    for col in ("announce_day", "day_before", "window2"):
        s = ev[col].dropna().tolist()
        ma, mb, exc, t = welch(s, base_all)
        tag = "  <- primaire" if col == "announce_day" else ""
        print(f"  {col:12s}: excès {exc * 1e4:+6.1f} bps/event  (FOMC {ma*1e4:+.1f} vs base "
              f"{mb*1e4:+.1f})  t={t:+.2f}  ann≈{exc*per_yr*100:+.2f}%{tag}")
    s = ev["announce_day"].dropna().tolist()
    _, _, exc_full, t_full = welch(s, base_all)
    gate_A = (exc_full > 0) and (t_full > 2)
    print(f"\n  >>> (A) {'PASS' if gate_A else 'FAIL'}")

    # ---------- (B) ENCORE TRADABLE POST-2015 ----------
    section(f"(B) ENCORE TRADABLE  [excès announce_day > 0, t>2 ; sous-échantillon {SPLIT.year}+]")
    for label, lo, hi in [("pré-2015", pd.Timestamp.min, SPLIT), ("2015+", SPLIT, pd.Timestamp.max)]:
        evs = ev[(ev.index >= lo) & (ev.index < hi)]["announce_day"].dropna().tolist()
        bs = [r for d, r in cc.items() if (lo <= d < hi) and d not in fomc_days]
        if not evs:
            continue
        ma, mb, exc, t = welch(evs, bs)
        print(f"  {label:9s} (n={len(evs):3d}): excès {exc*1e4:+6.1f} bps/event  "
              f"(FOMC {ma*1e4:+.1f} vs base {mb*1e4:+.1f})  t={t:+.2f}")
    evp = ev[ev.index >= SPLIT]["announce_day"].dropna().tolist()
    bp = [r for d, r in cc.items() if (d >= SPLIT) and d not in fomc_days]
    _, _, exc_post, t_post = welch(evp, bp)
    gate_B = (exc_post > 0) and (t_post > 2)
    print(f"\n  >>> (B) {'PASS' if gate_B else 'FAIL'}")

    # ---------- VERDICT ----------
    section("VERDICT PRE-ENREGISTRE (5b pré-FOMC)")
    if gate_A and gate_B:
        print("  (A) ^ (B) => GO")
    elif gate_A and not gate_B:
        print("  (A) ^ -(B) => KILL priced-in : drift réel historiquement mais mort/érodé")
        print("                après publication (2015+). Comme les unlocks.")
    else:
        print("  -(A) => KILL : pas de drift même historiquement dans nos données.")


if __name__ == "__main__":
    main()

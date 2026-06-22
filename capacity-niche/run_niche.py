"""Verdict piste 3 (SPEC-niche.md). Gates A/B PRÉ-ENREGISTRÉS, capacité réelle via /depth.

Usage: .venv/Scripts/python run_niche.py [--workers 8]
"""
from __future__ import annotations

import argparse
import statistics as st
from concurrent.futures import ThreadPoolExecutor

import audit
import data
import scan

PERSIST = 0.60     # net>0 sur >=60 % des snapshots (pré-enregistré)
MIN_PAIRS = 20     # >=20 paires persistantes (A)
CAP_TARGET = 2_000.0   # $ agrégé déployable/cycle (B)
MIN_QUAL = 10      # >=10 paires qualifiées simultanées (B)


def median(xs):
    xs = [x for x in xs if x == x]
    return st.median(xs) if xs else float("nan")


def real_capacity(base, snap, vol, workers_depth=False) -> float:
    """$ exécutable net>0 (break-even), profondeur réelle des 2 jambes. min(buy, sell)."""
    c = scan.cross(base, snap, vol)
    if c is None:
        return 0.0
    ask_v, bid_v = c["ask_v"], c["bid_v"]
    best_bid_other = snap[bid_v][base]["bid"]   # on vend ici (jambe fixe pour le buy-walk)
    best_ask_other = snap[ask_v][base]["ask"]   # on achète ici (jambe fixe pour le sell-walk)
    buy_usd = scan.book_capacity_usd(ask_v, base, "ask", 0.0, best_bid_other)
    sell_usd = scan.book_capacity_usd(bid_v, base, "bid", 0.0, best_ask_other)
    return min(buy_usd, sell_usd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    vol = data.volumes()
    snaps = scan.load_snapshots()
    print(f"=== {len(snaps)} snapshots chargés ===")
    if len(snaps) < 5:
        print("Pas assez de snapshots (collect.py pas fini ?)")
        return
    last = snaps[-1]

    rows = scan.persistence(snaps, vol)
    rows.sort(key=lambda r: -r["mean_net"])
    cross_count = len(rows)
    print(f"paires avec ≥1 cross valide : {cross_count}")

    # ============ (A) LE SPREAD EXISTE ET EST SOLO-CAPTURABLE ============
    print("\n" + "=" * 64 + "\n(A) SPREAD PERSISTANT (net>0 sur ≥60 % des snapshots)")
    persist = [r for r in rows if r["frac_pos"] >= PERSIST]
    print(f"  paires persistantes : {len(persist)} (seuil ≥{MIN_PAIRS})")
    a_count = len(persist) >= MIN_PAIRS
    print("  top persistantes :")
    for r in persist[:12]:
        print(f"    {r['base']:>10} net_moy={r['mean_net']*100:+.2f}% "
              f"frac_pos={r['frac_pos']*100:.0f}% vol${r['small_vol']:,.0f}")

    # dose-réponse : net médian plus grand en BASSE liquidité (Q1) qu'en HAUTE (Q4)
    a_dose = False
    if len(persist) >= 8:
        sv = sorted(persist, key=lambda r: r["small_vol"])
        k = len(sv) // 4
        q1, q4 = sv[:k], sv[-k:]   # Q1 = plus basse liquidité, Q4 = plus haute
        m1, m4 = median([r["mean_net"] for r in q1]), median([r["mean_net"] for r in q4])
        a_dose = m1 > m4
        print(f"  dose-réponse : Q1(basse-liq) net méd {m1*100:+.2f}% vs "
              f"Q4(haute-liq) {m4*100:+.2f}% → [{'PASS' if a_dose else 'FAIL'}]")
    else:
        print("  dose-réponse : data insuffisante [FAIL]")

    # pas porté par 1-2 paires : retirer top-3 par net, persistance toujours ≥ seuil-3
    a_robust = len(persist) - 3 >= MIN_PAIRS - 3 and len(persist) > 3
    print(f"  drop-top-3 : {len(persist)-3} restantes [{'PASS' if a_robust else 'FAIL'}]")

    t_cross = audit.tstat([r["mean_net"] for r in persist]) if persist else 0.0
    print(f"  (diag t cross-paires du net moyen = {t_cross:+.2f})")

    A = a_count and a_dose and a_robust
    print(f"  ==> (A) {'PASS' if A else 'FAIL'}")

    # ============ (B) CAPACITÉ RÉELLE (/depth) ============
    print("\n" + "=" * 64 + "\n(B) CAPACITÉ $ NET>0 (profondeur réelle des carnets)")
    cand = persist if persist else rows[:30]
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        caps = list(ex.map(lambda r: real_capacity(r["base"], last, vol), cand))
    qual = [(r, cusd) for r, cusd in zip(cand, caps) if cusd > 0]
    qual.sort(key=lambda x: -x[1])
    total_cap = sum(c for _, c in qual)
    print(f"  paires qualifiées (cap>0) : {len(qual)} (seuil ≥{MIN_QUAL})")
    print(f"  capacité agrégée déployable/cycle : ${total_cap:,.0f} (seuil ≥${CAP_TARGET:,.0f})")
    print("  top capacité :")
    for r, cusd in qual[:12]:
        print(f"    {r['base']:>10} cap=${cusd:,.0f} net_moy={r['mean_net']*100:+.2f}% "
              f"vol${r['small_vol']:,.0f}")
    B = total_cap >= CAP_TARGET and len(qual) >= MIN_QUAL
    print(f"  ==> (B) {'PASS' if B else 'FAIL'}")

    # ============ VERDICT ============
    print("\n" + "=" * 64)
    if A and B:
        v = "GO — seule piste vivante ; passer au gate transfert/inventaire"
    elif A and not B:
        v = "KILL-trop-petit — spread réel mais capacité jouet (le piège piste-3 prédit)"
    else:
        v = "KILL-pas-de-spread — small-caps arbitrés / flicker non capturable"
    print(f"VERDICT (pré-enregistré) : {v}")
    print("=" * 64)


if __name__ == "__main__":
    main()

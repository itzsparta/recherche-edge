"""
run_small.py — Étude #40 : capture de dividende PEA sur les sociétés exonérées de TTF (< 1 Md€).
Gates figés dans docs/SPEC-smallcap.md (9dd1675). Mécanique et statistique de #39 (run.py) :
AR = (O_J + D)/C_{J−1} − 1 − Rm_J, moyenne et t sur la série des cohortes mensuelles.
Nouveau : benchmark = payeurs de l'univers, filtre de turnover ex ante, G0 par période, placebos J±3.
"""
import numpy as np
import pandas as pd

from data import panel_small
from run import SEG, cal, fmt, rho, welch

START = pd.Timestamp("2009-01-01")
COST = 0.0040                 # courtage 2 × 0,10 % + écart au fixing 2 × 0,10 % (SPEC)
Y_HI = 0.03
TO_MIN = 200_000              # turnover médian [J−60, J−2] en €
MIN_BENCH = 20
PERIODS = {"P1": ("2009-01-01", "2014-12-31"), "P2": ("2015-01-01", "2020-12-31"),
           "P3": ("2021-01-01", "2099-12-31")}
KS = (-3, -2, -1, 1, 2, 3)
SBF_2015_GROSS = (0.00521, 7.38)   # #39 : SBF 120, y ≥ 3 %, 2015+, brut (docs/FINDINGS.md)


def build(pan):
    payers = {tk: h for tk, h in pan.items() if (h.Dividends[h.index >= START] > 0).any()}
    cols = {k: pd.concat({tk: h[k] for tk, h in payers.items()}, axis=1, sort=True)
            for k in ("Open", "Close", "Volume", "Dividends")}
    keep = cols["Close"].notna().sum(axis=1) >= MIN_BENCH
    O, C, V, DV = (cols[k].loc[keep] for k in ("Open", "Close", "Volume", "Dividends"))
    DV = DV.fillna(0)
    Cp = C.shift(1)
    on = O / Cp - 1
    valid = O.gt(0) & V.gt(0) & Cp.gt(0) & (O != Cp)
    ex = DV.gt(0)
    bm = valid & ~ex
    nb = bm.sum(axis=1)
    Rm = on.where(bm).mean(axis=1).where(nb >= MIN_BENCH)
    Rm_med = on.where(bm).median(axis=1).where(nb >= MIN_BENCH)
    vc = C.gt(0) & Cp.gt(0) & V.gt(0)
    Rcc = (C / Cp - 1).where(vc & ~ex).mean(axis=1).where((vc & ~ex).sum(axis=1) >= MIN_BENCH)
    TO = (C * V).shift(2).rolling(59, min_periods=30).median()
    drop = (Cp.mul(1 + Rm, axis=0) - O).where(valid)
    arn = on.sub(Rm, axis=0).where(valid)
    dates, n = C.index, len(C.index)
    rows = []
    for j, tk in enumerate(C.columns):
        for p in np.flatnonzero(ex[tk].values):
            if dates[p] < START:
                continue
            r = dict(date=dates[p], ticker=tk, D=DV.iat[p, j], Cp=Cp.iat[p, j], O=O.iat[p, j], C=C.iat[p, j],
                     valid=bool(valid.iat[p, j]), Rm=Rm.iat[p], Rm_med=Rm_med.iat[p], Rcc=Rcc.iat[p],
                     to=TO.iat[p, j])
            for k in KS:
                r[f"drop{k:+d}"] = drop.iat[p + k, j] if 0 <= p + k < n else np.nan
            for k in (-2, 2):
                r[f"ar{k:+d}"] = arn.iat[p + k, j] if 0 <= p + k < n else np.nan
            rows.append(r)
    ev = pd.DataFrame(rows)
    ev["y"] = ev.D / ev.Cp
    ev["AR"] = (ev.O + ev.D) / ev.Cp - 1 - ev.Rm
    ev["AR_med"] = (ev.O + ev.D) / ev.Cp - 1 - ev.Rm_med
    ev["AR_cc"] = (ev.C + ev.D) / ev.Cp - 1 - ev.Rcc
    ev["drop"] = ev.Cp * (1 + ev.Rm) - ev.O
    ev["month"] = ev.date.dt.to_period("M")
    ev["year"] = ev.date.dt.year
    return ev, len(payers)


def filters(ev):
    steps = [("ex-dates ≥ 2009", ev)]
    e = ev[ev.valid]; steps.append(("nuit valide (O, volume, pas périmée)", e))
    e = e[e.Rm.notna()]; steps.append((f"benchmark ≥ {MIN_BENCH} payeurs", e))
    e = e[e.y <= 0.10]; steps.append(("y ≤ 10 %", e))
    no_ar = e
    e = e[e.AR.abs() <= 0.15]; steps.append(("|AR| ≤ 15 %", e))
    return e, no_ar, steps


def in_period(ev, pid):
    lo, hi = PERIODS[pid]
    return ev[(ev.date >= lo) & (ev.date <= hi)]


def g0(ev):
    """ρ̂ nuit J ∈ [0,5 ; 1,5] et |ρ̂| < 0,3 sur J±1..3, période par période (moins de 30 évts = échec)."""
    out = {}
    for pid in PERIODS:
        s = in_period(ev, pid)
        if len(s) < 30:
            out[pid] = (False, np.nan, {}, len(s))
            continue
        rk = {}
        for k in KS:
            c = s[s[f"drop{k:+d}"].notna()]
            rk[k] = c[f"drop{k:+d}"].sum() / c.D.sum() if len(c) else np.nan
        rJ = rho(s)
        out[pid] = (0.5 <= rJ <= 1.5 and all(abs(v) < 0.3 for v in rk.values()), rJ, rk, len(s))
    return out


def main():
    pan, u = panel_small()
    seg_of = dict(zip(u.ticker, u.segment))
    ev_all, npay = build(pan)
    ev_all["segment"] = ev_all.ticker.map(seg_of)
    ev, no_ar, steps = filters(ev_all)
    print(f"#40 capture de dividende PEA, exonérés TTF — {len(pan)} titres avec prix, {npay} payeurs ≥ 2009,"
          f" {ev.date.min().date()} → {ev.date.max().date()}")
    print("\n== Événements par filtre ==")
    for lab, e in steps:
        print(f"  {lab:<40} {len(e):>6}")
    print(f"  noms avec ≥ 1 événement retenu : {ev.ticker.nunique()}  | segments : {ev.segment.value_counts().to_dict()}")

    # G0 par période
    g = g0(ev)
    print("\n== G0 fidélité, par période ==")
    for pid, (ok, rJ, rk, ne) in g.items():
        ks = "  ".join(f"{k:+d}:{v:+.2f}" for k, v in rk.items())
        print(f"  {pid} {PERIODS[pid][0][:4]}-{PERIODS[pid][1][:4] if pid != 'P3' else 'fin '} n={ne:>4}"
              f"  ρ̂ J = {rJ:.3f}   {ks}   → {'PASS' if ok else 'FAIL (exclue)'}")
    kept = [pid for pid, v in g.items() if v[0]]
    evr = pd.concat([in_period(ev, pid) for pid in kept]) if kept else ev.iloc[:0]
    hiB = evr[(evr.y >= Y_HI) & (evr.to >= TO_MIN) & (evr.date >= "2015-01-01")].copy()
    hiB["net"] = hiB.AR - COST
    N = len(hiB) >= 100
    print(f"  périodes retenues : {kept}   | N segment B 2015+ = {len(hiB)} → {'PASS' if N else 'FAIL'}")
    if "P3" not in kept or len(kept) < 2 or not N:
        print("\n>>> VERDICT : UNTESTABLE")
        return

    # A
    mA, tA, nA, _ = cal(evr, "AR")
    seg = []
    for lo, hi, lab in SEG:
        s = evr[(evr.y >= lo) & (evr.y < hi)]
        m, t, n, _ = cal(s, "AR")
        seg.append((lab, len(s), m, t, n, s.AR.mean(), 1 - (s.AR * s.Cp).sum() / s.D.sum(), s.y.median()))
    mono = seg[0][2] < seg[1][2] < seg[2][2]
    A = mA > 0 and tA > 2 and mono
    print("\n== A existence (périodes retenues, AR brut) ==")
    print(f"  AR {fmt(mA, tA, nA)}   ρ̂ = {rho(evr):.3f}   n = {len(evr)}")
    for lab, ne, m, t, n, me, rh, ym in seg:
        print(f"  {lab:<10} n={ne:>5}  y méd {ym*100:.2f} %  AR cal {fmt(m, t, n)}  AR évt {me*100:+.3f} %  ρ̂ {rh:.3f}")
    print(f"  monotone : {mono}   → {'PASS' if A else 'FAIL'}")

    # B
    mB, tB, nB, sB = cal(hiB, "net")
    B = mB > 0 and tB > 2
    print(f"\n== B déployable (y ≥ 3 %, turnover ≥ 200 k€, 2015+, net de {COST*100:.2f} %) ==")
    print(f"  net {fmt(mB, tB, nB)}   n = {len(hiB)}   brut {hiB.AR.mean()*100:+.3f} % (évt)   → {'PASS' if B else 'FAIL'}")

    # C
    per = {pid: cal(in_period(hiB, pid), "net") for pid in ("P2", "P3") if pid in kept}
    C_ = all(v[0] > 0 for v in per.values())
    print("\n== C stabilité (segment B net, P2 et P3) ==")
    for pid, (m, t, n, _) in per.items():
        print(f"  {pid} {fmt(m, t, n)}")
    print(f"  → {'PASS' if C_ else 'FAIL'}")

    # D
    top5 = hiB.groupby("ticker").AR.sum().nlargest(5)
    mD, tD, nD, _ = cal(hiB[~hiB.ticker.isin(top5.index)], "net")
    D_ = mD > 0 and tD > 2
    print("\n== D concentration (segment B net, hors top-5 ΣAR) ==")
    print(f"  top-5 : {', '.join(f'{k} {v*100:+.1f}' for k, v in top5.items())}")
    print(f"  net {fmt(mD, tD, nD)}   → {'PASS' if D_ else 'FAIL'}")

    if not A:
        v = "KILL ρ ≈ 1"
    elif not B:
        v = "KILL borne d'arbitrage"
    elif not (C_ and D_):
        v = "DOWNGRADE"
    else:
        v = "GO phase 2"
    print(f"\n>>> VERDICT : {v}   (G0 {kept} | N {N} | A {A} | B {B} | C {C_} | D {D_})")

    # ------------------------------------------------------------ diagnostics
    print("\n== Diagnostics (non-gating) ==")
    y15 = evr[(evr.y >= Y_HI) & (evr.date >= "2015-01-01")]
    for lo, hi, lab in ((0, TO_MIN, "< 200 k€ (non tradable)"), (TO_MIN, 1e6, "200 k€-1 M€"), (1e6, 1e15, "> 1 M€")):
        s = y15[(y15.to >= lo) & (y15.to < hi)]
        m, t, n, _ = cal(s.assign(x=s.AR - COST), "x")
        print(f"  liquidité {lab:<24} n={len(s):>4}  net {fmt(m, t, n) if n >= 3 else '—'}  ρ̂ {rho(s) if len(s) else np.nan:.3f}")
    for sg in ("reglemente", "growth"):
        s = hiB[hiB.segment == sg]
        m, t, n, _ = cal(s, "net")
        print(f"  segment B, {sg:<11} n={len(s):>4}  net {fmt(m, t, n) if n >= 3 else '—'}")
    m, t, n, _ = cal(hiB.assign(x=hiB.AR), "x")
    print(f"  comparaison borne d'arbitrage, y ≥ 3 % 2015+ BRUT : petites (liquides) {fmt(m, t, n)}"
          f"  vs SBF 120 (#39) {SBF_2015_GROSS[0]*100:+.3f} % t={SBF_2015_GROSS[1]:+.2f}")
    for c, lab in ((0.0020, "coût 0,20 %"), (0.0060, "coût 0,60 %")):
        m, t, n, _ = cal(hiB.assign(x=hiB.AR - c), "x")
        print(f"  segment B, {lab:<12} {fmt(m, t, n)}")
    b, a = np.polyfit(evr.y, evr.AR, 1)
    print(f"  pente AR ~ y : {b:+.3f} → ρ marginal {1-b:.3f} ; ordonnée {a*100:+.3f} %")
    for pid in kept:
        s = in_period(evr, pid)
        m, t, n, _ = cal(s, "AR")
        print(f"  {pid} n={len(s):>5}  ρ̂ {rho(s):.3f}  AR {fmt(m, t, n)}")
    for col, lab in (("AR_cc", "clôture-clôture"), ("AR_med", "benchmark médian")):
        s = evr[evr[col].notna() & (evr[col].abs() <= 0.15)]
        m, t, n, _ = cal(s, col)
        print(f"  variante {lab:<18} n={len(s):>5}  {fmt(m, t, n)}")
    for k in (-2, 2):
        s = evr[evr[f"ar{k:+d}"].notna()]
        m, t, n, _ = cal(s, f"ar{k:+d}")
        print(f"  placebo AR nuit J{k:+d} (sans dividende) {fmt(m, t, n)}")
    nar = no_ar[no_ar.date.isin(evr.date)]
    m, t, n, _ = cal(nar, "AR")
    print(f"  sans filtre |AR| ≤ 15 %  n={len(nar):>5}  {fmt(m, t, n)}")
    nights = hiB.groupby("date").net.mean()
    yr = nights.groupby(nights.index.year).agg(["size", "sum"])
    print("  segment B : nuits investies et net cumulé par an :",
          {k: (int(r["size"]), round(r["sum"] * 100, 2)) for k, r in yr.iterrows()})
    print("  événements par an :", evr.groupby("year").size().to_dict())


if __name__ == "__main__":
    main()

"""
run.py — Étude #39 : capture de dividende sous statut PEA. Gates figés dans docs/SPEC.md (880db7b).

Capture = achat au fixing de clôture J−1, vente au fixing d'ouverture J (ex), dividende brut (PEA).
AR = (O_J + D)/C_{J−1} − 1 − Rm_J ; Rm_J = overnight équipondéré des titres de l'univers sans ex en J.
t calendar-time : moyenne des cohortes mensuelles, t sur la série des cohortes.
"""
import numpy as np
import pandas as pd

from data import panel

START = pd.Timestamp("2005-01-01")
COST = 0.0060            # TTF 0,40 % + 2 × 0,10 % (SPEC)
COST_OPT = 0.0044        # TTF + 2 × 0,02 % (diagnostic)
COST_NOTTF = 0.0020      # courtage seul (diagnostic : porte < 1 Md€)
Y_HI = 0.03
SEG = [(0.0, 0.015, "y < 1,5 %"), (0.015, 0.03, "1,5-3 %"), (0.03, 1.0, "y ≥ 3 %")]
MIN_BENCH = 20


# ------------------------------------------------------------------ panel large
def wide(pan):
    cols = {k: pd.concat({tk: h[k] for tk, h in pan.items()}, axis=1, sort=True)
            for k in ("Open", "Close", "Volume", "Dividends")}
    C = cols["Close"]
    keep = C.notna().sum(axis=1) >= MIN_BENCH
    return {k: v.loc[keep].sort_index() for k, v in cols.items()}


def cal(ev, col):
    """Moyenne des cohortes mensuelles, t, nb de mois, série."""
    s = ev.groupby("month")[col].mean().dropna()
    n = len(s)
    if n < 3:
        return np.nan, np.nan, n, s
    return s.mean(), s.mean() / s.std(ddof=1) * np.sqrt(n), n, s


def welch(a, b):
    return (a.mean() - b.mean()) / np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


def rho(ev, drop_col="drop"):
    return ev[drop_col].sum() / ev.D.sum()


def fmt(m, t, n):
    return f"{m*100:+.3f} %  t={t:+.2f}  ({n} mois)"


# ------------------------------------------------------------------ construction
def build(pan, idx):
    W = wide(pan)
    O, C, V, DV = W["Open"], W["Close"], W["Volume"], W["Dividends"].fillna(0)
    Cp = C.shift(1)
    on = O / Cp - 1
    valid = O.gt(0) & V.gt(0) & Cp.gt(0) & (O != Cp)
    ex = DV.gt(0)
    bm = valid & ~ex
    Rm = on.where(bm).mean(axis=1).where(bm.sum(axis=1) >= MIN_BENCH)
    Rm_med = on.where(bm).median(axis=1).where(bm.sum(axis=1) >= MIN_BENCH)
    # clôture-clôture (variante) et rendements totaux (Hartzmark-Solomon)
    vc = C.gt(0) & Cp.gt(0) & V.gt(0)
    cc = C / Cp - 1
    Rcc = cc.where(vc & ~ex).mean(axis=1).where((vc & ~ex).sum(axis=1) >= MIN_BENCH)
    TR = ((C + DV) / Cp - 1).where(vc)
    M = TR.mean(axis=1).where(vc.sum(axis=1) >= MIN_BENCH)
    XR = TR.sub(M, axis=0).fillna(0).cumsum()
    # indice CAC 40 (marché alternatif)
    ix = idx.reindex(C.index)
    Rix = (ix.Open / ix.Close.shift(1) - 1).where(ix.Open.gt(0) & (ix.Open != ix.Close.shift(1)))

    dates = C.index
    pos = {d: i for i, d in enumerate(dates)}
    rows = []
    for tk in C.columns:
        for d in DV.index[ex[tk]]:
            if d < START:
                continue
            p = pos[d]
            r = dict(date=d, ticker=tk, D=DV.at[d, tk], Cp=Cp.at[d, tk], O=O.at[d, tk], C=C.at[d, tk],
                     valid=bool(valid.at[d, tk]), Rm=Rm.iat[p], Rm_med=Rm_med.iat[p], Rcc=Rcc.iat[p],
                     Rix=Rix.iat[p])
            for k, lab in ((p - 1, "m1"), (p + 1, "p1")):       # nuits placebo J−1, J+1
                if 0 < k < len(dates):
                    ok = bool(valid.iat[k, C.columns.get_loc(tk)]) and pd.notna(Rm.iat[k])
                    r[f"drop_{lab}"] = (Cp.iat[k, C.columns.get_loc(tk)] * (1 + Rm.iat[k])
                                        - O.iat[k, C.columns.get_loc(tk)]) if ok else np.nan
                else:
                    r[f"drop_{lab}"] = np.nan
            j = C.columns.get_loc(tk)
            r["pre"] = XR.iat[p - 1, j] - XR.iat[p - 22, j] if p >= 22 else np.nan
            r["post"] = XR.iat[min(p + 5, len(dates) - 1), j] - XR.iat[p - 1, j] if p >= 1 else np.nan
            rows.append(r)
    ev = pd.DataFrame(rows)
    ev["y"] = ev.D / ev.Cp
    ev["AR"] = (ev.O + ev.D) / ev.Cp - 1 - ev.Rm
    ev["AR_med"] = (ev.O + ev.D) / ev.Cp - 1 - ev.Rm_med
    ev["AR_cc"] = (ev.C + ev.D) / ev.Cp - 1 - ev.Rcc
    ev["AR_ix"] = (ev.O + ev.D) / ev.Cp - 1 - ev.Rix
    ev["drop"] = ev.Cp * (1 + ev.Rm) - ev.O
    ev["month"] = ev.date.dt.to_period("M")
    ev["year"] = ev.date.dt.year
    return ev, len(dates)


def filters(ev):
    steps = [("ex-dates ≥ 2005", ev)]
    e = ev[ev.valid]; steps.append(("nuit valide (O, volume, pas périmée)", e))
    e = e[e.Rm.notna()]; steps.append((f"benchmark ≥ {MIN_BENCH} titres", e))
    e = e[e.y <= 0.10]; steps.append(("y ≤ 10 %", e))
    no_ar = e
    e = e[e.AR.abs() <= 0.15]; steps.append(("|AR| ≤ 15 %", e))
    return e, no_ar, steps


# ------------------------------------------------------------------ main
def main():
    pan, idx = panel()
    ev_all, ndays = build(pan, idx)
    ev, no_ar, steps = filters(ev_all)
    print(f"#39 capture de dividende PEA — {len(pan)} titres FR, {ev.date.min().date()} → {ev.date.max().date()}")
    print("\n== Événements par filtre ==")
    for lab, e in steps:
        print(f"  {lab:<40} {len(e):>6}")
    print(f"  noms avec ≥ 1 événement retenu : {ev.ticker.nunique()}")

    # G0
    r_J = rho(ev)
    pm1 = ev[ev.drop_m1.notna()]; pp1 = ev[ev.drop_p1.notna()]
    r_m1 = pm1.drop_m1.sum() / pm1.D.sum(); r_p1 = pp1.drop_p1.sum() / pp1.D.sum()
    G0 = (0.5 <= r_J <= 1.5) and abs(r_m1) < 0.3 and abs(r_p1) < 0.3
    print("\n== G0 fidélité ==")
    print(f"  ρ̂ nuit J = {r_J:.3f}   placebo J−1 = {r_m1:+.3f} (n={len(pm1)})   J+1 = {r_p1:+.3f} (n={len(pp1)})"
          f"   → {'PASS' if G0 else 'FAIL'}")

    # A
    mA, tA, nA, _ = cal(ev, "AR")
    seg = []
    for lo, hi, lab in SEG:
        s = ev[(ev.y >= lo) & (ev.y < hi)]
        m, t, n, _ = cal(s, "AR")
        seg.append((lab, len(s), m, t, n, s.AR.mean(), 1 - (s.AR * s.Cp).sum() / s.D.sum(), s.y.median()))
    mono = seg[0][2] < seg[1][2] < seg[2][2]
    A = mA > 0 and tA > 2 and mono
    print("\n== A existence (tous événements, AR brut) ==")
    print(f"  AR {fmt(mA, tA, nA)}   ρ̂ = {r_J:.3f}   n = {len(ev)}")
    for lab, ne, m, t, n, me, rh, ym in seg:
        print(f"  {lab:<10} n={ne:>5}  y méd {ym*100:.2f} %  AR cal {fmt(m, t, n)}  AR évt {me*100:+.3f} %  ρ̂ {rh:.3f}")
    print(f"  monotone : {mono}   → {'PASS' if A else 'FAIL'}")

    # B
    hi = ev[ev.y >= Y_HI].copy()
    hi["net"] = hi.AR - COST
    mB, tB, nB, sB = cal(hi, "net")
    B = mB > 0 and tB > 2
    print(f"\n== B déployable (y ≥ 3 %, net de {COST*100:.2f} %) ==")
    print(f"  net {fmt(mB, tB, nB)}   n = {len(hi)}   → {'PASS' if B else 'FAIL'}")

    # C
    pre = sB[sB.index < pd.Period("2015-01", "M")]; post = sB[sB.index >= pd.Period("2015-01", "M")]
    tw = welch(pre, post)
    C_ = post.mean() > 0 and tw < 2
    print("\n== C maturité (segment B net) ==")
    print(f"  < 2015 {pre.mean()*100:+.3f} % ({len(pre)} m)   2015+ {post.mean()*100:+.3f} % ({len(post)} m)"
          f"   Welch t = {tw:+.2f}   → {'PASS' if C_ else 'FAIL'}")

    # D
    top5 = hi.groupby("ticker").AR.sum().nlargest(5)
    mD, tD, nD, _ = cal(hi[~hi.ticker.isin(top5.index)], "net")
    D_ = mD > 0 and tD > 2
    print("\n== D concentration (segment B net, hors top-5 ΣAR) ==")
    print(f"  top-5 : {', '.join(f'{k} {v*100:+.1f}' for k, v in top5.items())}")
    print(f"  net {fmt(mD, tD, nD)}   → {'PASS' if D_ else 'FAIL'}")

    # verdict
    if not G0:
        v = "UNTESTABLE"
    elif not A:
        v = "KILL ρ ≈ 1"
    elif not B:
        v = "KILL friction"
    elif not (C_ and D_):
        v = "DOWNGRADE"
    else:
        v = "GO phase 2"
    print(f"\n>>> VERDICT : {v}   (G0 {G0} | A {A} | B {B} | C {C_} | D {D_})")

    # ------------------------------------------------------------ diagnostics
    print("\n== Diagnostics (non-gating) ==")
    for c, lab in ((COST_OPT, "coût optimiste 0,44 %"), (COST_NOTTF, "coût hors TTF 0,20 %"), (0.0, "brut")):
        m, t, n, _ = cal(hi.assign(x=hi.AR - c), "x")
        print(f"  segment y ≥ 3 %, {lab:<22} {fmt(m, t, n)}")
    b, a = np.polyfit(ev.y, ev.AR, 1)
    res = ev.AR - (a + b * ev.y)
    se = np.sqrt(res.var(ddof=2) / ((ev.y - ev.y.mean()) ** 2).sum())
    print(f"  pente AR ~ y : {b:+.3f} (t évt {b/se:+.2f}) → ρ marginal {1-b:.3f} ; ordonnée {a*100:+.3f} %")
    for lo, hi_, lab in (("2005-01", "2012-07", "2005-2012/07 (sans TTF)"), ("2012-08", "2016-12", "TTF 0,20 %"),
                         ("2017-01", "2025-03", "TTF 0,30 %"), ("2025-04", "2099-12", "TTF 0,40 % + cum-cum")):
        s = ev[(ev.date >= lo) & (ev.date <= pd.Period(hi_, "M").end_time)]
        if len(s) > 5:
            m, t, n, _ = cal(s, "AR")
            print(f"  {lab:<26} n={len(s):>5}  ρ̂ {rho(s):.3f}  AR {fmt(m, t, n)}")
    for col, lab in (("AR_cc", "clôture-clôture"), ("AR_ix", "marché = ^FCHI overnight"), ("AR_med", "benchmark médian")):
        s = ev[ev[col].notna() & (ev[col].abs() <= 0.15)]
        m, t, n, _ = cal(s, col)
        print(f"  variante {lab:<26} n={len(s):>5}  {fmt(m, t, n)}")
    m, t, n, _ = cal(no_ar, "AR")
    print(f"  sans filtre |AR| ≤ 15 %            n={len(no_ar):>5}  {fmt(m, t, n)}")
    for col, lab in (("pre", "H-S run-up [J−21, J−1]"), ("post", "H-S [J, J+5]")):
        s = ev[ev[col].notna()]
        m, t, n, _ = cal(s, col)
        print(f"  {lab:<30} {fmt(m, t, n)}")
    nights = hi.groupby("date").net.mean()
    yrs = (ev.date.max() - START).days / 365.25
    cagr = (1 + nights).prod() ** (1 / yrs) - 1
    print(f"  segment B net, capital réparti par nuit : CAGR {cagr*100:+.2f} %/an sur {yrs:.1f} ans,"
          f" {len(nights)} nuits investies ({len(nights)/(yrs*252)*100:.1f} % des nuits)")
    print("  événements par an :", ev.groupby("year").size().to_dict())
    posthoc(ev, hi)
    align(pan, ev)


def posthoc(ev, hi):
    """POST-HOC (après lecture des gates) : le ρ̂ 0,33 de 2005-12 est-il un artefact d'ouverture ?
    Si les `Open` anciens sont quasi périmés (O ≈ C_{J−1} sans égalité exacte), la baisse à
    l'ouverture est ~0 → ρ̂ → 0 et AR → y. La clôture-clôture ne dépend pas de `Open`."""
    print("\n== POST-HOC (non pré-enregistré) : qualité des ouvertures anciennes ==")
    ev = ev.assign(drop_cc=ev.Cp * (1 + ev.Rcc) - ev.C,
                   stale=(ev.O / ev.Cp - 1).abs() < 0.0005,
                   intra=ev.AR_cc - ev.AR)
    per = (("2005-01", "2008-12"), ("2009-01", "2012-07"), ("2012-08", "2014-12"),
           ("2015-01", "2016-12"), ("2017-01", "2020-12"), ("2021-01", "2025-03"), ("2025-04", "2026-12"))
    print(f"  {'période':<17} {'n':>4} {'ρ̂ on':>6} {'ρ̂ cc':>6} {'O≈C':>5} {'|Rm|':>6} {'intra':>7}   segment B net (overnight)")
    for lo, h_ in per:
        s = ev[(ev.date >= lo) & (ev.date <= pd.Period(h_, "M").end_time)]
        c = s[s.drop_cc.notna()]
        b = hi[(hi.date >= lo) & (hi.date <= pd.Period(h_, "M").end_time)]
        m, t, n, _ = cal(b, "net")
        print(f"  {lo}→{h_}  {len(s):>4} {rho(s):6.3f} {c.drop_cc.sum()/c.D.sum():6.3f} {s.stale.mean()*100:4.1f}%"
              f" {s.Rm.abs().mean()*100:5.2f}% {s.intra.mean()*100:+6.2f}%   {fmt(m, t, n) if n >= 3 else f'n={len(b)}'}")
    yr = ev.groupby("year").apply(lambda s: pd.Series({"rho_on": rho(s),
                                                       "rho_cc": s.drop_cc.sum() / s.D.sum()}))
    print("  ρ̂ annuel overnight :", {k: round(v, 2) for k, v in yr.rho_on.items()})
    print("  ρ̂ annuel clôt-clôt :", {k: round(v, 2) for k, v in yr.rho_cc.items()})
    old = ev[ev.date < "2012-08-01"].nlargest(12, "AR")
    print("  12 plus forts AR avant 2012-08 :")
    print(old[["date", "ticker", "D", "Cp", "O", "C", "y", "AR", "AR_cc"]].assign(
        date=old.date.dt.date).round(4).to_string(index=False))
    yb = hi[hi.date >= "2015-01-01"].groupby("year").net.agg(["size", "mean"])
    print("  segment B net 2015+ par an :", {k: (int(r["size"]), round(r["mean"] * 100, 2)) for k, r in yb.iterrows()})
    for lo in ("2009-01-01", "2015-01-01"):
        b = hi[hi.date >= lo]
        out = []
        for c, lab in ((0.0, "brut"), (COST_NOTTF, "0,20"), (COST_OPT, "0,44"), (COST, "0,60")):
            m, t, n, _ = cal(b.assign(x=b.AR - c), "x")
            out.append(f"{lab} {m*100:+.3f} % t={t:+.2f}")
        print(f"  segment B {lo[:4]}+ (n={len(b)}) : " + " | ".join(out))


def align(pan, ev):
    """POST-HOC : ρ̂ sur les nuits J+k (k = −5..+5) par période. Si la date yfinance est la bonne,
    la baisse (ρ ≈ 1) est en k = 0 et ≈ 0 ailleurs ; sinon elle apparaît sur un autre k."""
    W = wide(pan)
    O, C, V, DV = W["Open"], W["Close"], W["Volume"], W["Dividends"].fillna(0)
    Cp = C.shift(1)
    valid = O.gt(0) & V.gt(0) & Cp.gt(0) & (O != Cp)
    bm = valid & ~DV.gt(0)
    Rm = (O / Cp - 1).where(bm).mean(axis=1).where(bm.sum(axis=1) >= MIN_BENCH)
    dropw = (Cp.mul(1 + Rm, axis=0) - O).where(valid)
    pos = {d: i for i, d in enumerate(C.index)}
    ks = range(-5, 6)
    print("\n== POST-HOC : alignement des ex-dates, ρ̂ par nuit J+k ==")
    for lo, hi_ in (("2005-01-01", "2008-12-31"), ("2009-01-01", "2012-12-31"), ("2013-01-01", "2026-12-31")):
        s = ev[(ev.date >= lo) & (ev.date <= hi_)]
        num = {k: 0.0 for k in ks}; den = {k: 0.0 for k in ks}
        for tk, d, D in zip(s.ticker, s.date, s.D):
            p, j = pos[d], C.columns.get_loc(tk)
            for k in ks:
                if 0 <= p + k < len(C.index):
                    x = dropw.iat[p + k, j]
                    if pd.notna(x):
                        num[k] += x; den[k] += D
        print(f"  {lo[:4]}-{hi_[:4]} (n={len(s)}) : " +
              "  ".join(f"{k:+d}:{num[k]/den[k]:+.2f}" for k in ks if den[k]))


if __name__ == "__main__":
    main()

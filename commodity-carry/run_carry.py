"""#30 carry énergie : sim + gates pré-enregistrés (docs/SPEC.md). 100% EIA, zéro splice.

Construction (mensuelle, fin de mois d → réalisation d+1) :
  carry(d)   = C1(d)/C2(d) − 1              (backwardation>0 → long)
  ret(d+1)   = C1(d+1)/C2(d) − 1            (détention de la 2e échéance, devenue front)
  pnl(d+1)   = Σ_m w_m(d)·sign(carry_m(d))·ret_m(d+1)   (vol-scalé equal-risk, gross=1)
A2 (les 2 côtés) testé sur les cellules brutes (carry,ret) par marché.
"""
from __future__ import annotations
import math, pathlib
import numpy as np, pandas as pd
import audit, data_eia

HERE = pathlib.Path(__file__).resolve().parent
FH_DATA = HERE.parent / "factor-harvest" / "data"      # caches SPY/IEF déjà présents
REGIMES = [("pré-GFC", None, "2007-12-31"), ("GFC08", "2008-01-01", "2009-06-30"),
           ("2010s", "2009-07-01", "2019-12-31"), ("COVID20", "2020-01-01", "2020-12-31"),
           ("2021+", "2021-01-01", None)]
ANN = math.sqrt(12)


def month_end(s: pd.Series) -> pd.Series:
    return s.resample("ME").last()


def build_monthly(panel: dict) -> dict:
    """Par marché : DataFrame indexé fin-de-mois avec carry(d) et ret(d→d+1)."""
    out = {}
    for m, cc in panel.items():
        c1, c2 = month_end(cc["C1"]), month_end(cc["C2"])
        df = pd.DataFrame({"c1": c1, "c2": c2}).dropna()
        df["carry"] = df["c1"] / df["c2"] - 1.0
        df["ret"] = df["c1"].shift(-1) / df["c2"] - 1.0      # réalisé le mois suivant
        out[m] = df.dropna(subset=["carry"])
    return out


def portfolio(monthly: dict, markets: list[str], vol_win: int = 12) -> pd.Series:
    """Rendement mensuel du portefeuille TS-carry (réalisation indexée au mois d+1)."""
    dates = sorted(set().union(*[set(monthly[m].index) for m in markets]))
    # rendements bruts par marché (réalisés), pour la vol trailing
    raw = {m: monthly[m]["ret"].dropna() for m in markets}
    pnl = {}
    for i in range(len(dates) - 1):
        d, dn = dates[i], dates[i + 1]
        contribs, invvols = {}, {}
        for m in markets:
            dfm = monthly[m]
            if d not in dfm.index or pd.isna(dfm.at[d, "ret"]):
                continue
            carry = dfm.at[d, "carry"]
            ret = dfm.at[d, "ret"]                            # = C1(d+1)/C2(d)-1
            hist = raw[m].loc[:d].iloc[:-1]      # exclut ret courant (réalisé en d+1) = pas de lookahead
            if len(hist) < 6:
                continue
            vol = hist.tail(vol_win).std()
            if not vol or vol <= 0:
                continue
            invvols[m] = 1.0 / vol
            contribs[m] = np.sign(carry) * ret
        if not contribs:
            continue
        tot = sum(invvols.values())
        pnl[dn] = sum(invvols[m] / tot * contribs[m] for m in contribs)   # gross=1
    return pd.Series(pnl).sort_index()


def xs_portfolio(monthly: dict, markets: list[str]) -> pd.Series:
    """XS-carry : long moitié haut-carry / short moitié bas-carry (equal weight)."""
    dates = sorted(set().union(*[set(monthly[m].index) for m in markets]))
    pnl = {}
    for i in range(len(dates) - 1):
        d, dn = dates[i], dates[i + 1]
        cells = [(m, monthly[m].at[d, "carry"], monthly[m].at[d, "ret"])
                 for m in markets if d in monthly[m].index and not pd.isna(monthly[m].at[d, "ret"])]
        if len(cells) < 2:
            continue
        cells.sort(key=lambda x: x[1])
        k = len(cells) // 2
        shorts, longs = cells[:k], cells[-k:]
        r = (sum(c[2] for c in longs) / k - sum(c[2] for c in shorts) / k)
        pnl[dn] = r
    return pd.Series(pnl).sort_index()


def ann_sharpe(m: pd.Series) -> float:
    return audit.sharpe(list(m.dropna())) * ANN


def spy_monthly() -> pd.Series:
    s = pd.read_csv(FH_DATA / "SPY.csv", parse_dates=["Date"]).set_index("Date").iloc[:, 0]
    return s.resample("ME").last().pct_change()


def sixty_forty_monthly() -> pd.Series:
    spy = pd.read_csv(FH_DATA / "SPY.csv", parse_dates=["Date"]).set_index("Date").iloc[:, 0]
    ief = pd.read_csv(FH_DATA / "IEF.csv", parse_dates=["Date"]).set_index("Date").iloc[:, 0]
    r = pd.DataFrame({"s": spy, "b": ief}).resample("ME").last().pct_change()
    return (0.6 * r["s"] + 0.4 * r["b"]).dropna()


def main():
    print("=== EIA pull ===")
    panel = data_eia.discover()
    if len(panel) < 2:
        print("INSUFFISANT : <2 marchés avec term structure. Stop."); return
    monthly = build_monthly(panel)
    markets = list(panel)
    p = portfolio(monthly, markets)
    sr, t = ann_sharpe(p), audit.tstat(list(p.dropna()))
    print(f"\nÉchantillon : {p.index.min().date()} → {p.index.max().date()} ({len(p)} mois), "
          f"marchés={markets}")
    print(f"\nTS-carry : Sharpe(ann) {sr:+.2f}  t={t:+.2f}  "
          f"vol {p.std()*ANN*100:.1f}%  CAGR {((1+p).prod()**(12/len(p))-1)*100:+.1f}%")

    # ===== (A) =====
    print("\n" + "=" * 60 + "\n(A) L'EDGE EXISTE")
    a1 = sr > 0 and t > 2
    print(f"  A1 [{'PASS' if a1 else 'FAIL'}] Sharpe>0 ∧ t>2 : SR={sr:+.2f} t={t:+.2f}")

    # A2 : les DEUX côtés paient (cellules brutes carry,ret)
    longs = [d["ret"] for m in markets for _, d in monthly[m].iterrows() if d["carry"] > 0 and not pd.isna(d["ret"])]
    shorts = [d["ret"] for m in markets for _, d in monthly[m].iterrows() if d["carry"] < 0 and not pd.isna(d["ret"])]
    ml, ms = np.mean(longs), np.mean(shorts)
    tl = audit.tstat(longs); ts = audit.tstat(shorts)
    a2 = ml > 0 and ms < 0
    print(f"  A2 [{'PASS' if a2 else 'FAIL'}] 2 côtés : long-backw E[ret]={ml*100:+.2f}% (t={tl:+.1f}, n={len(longs)}) "
          f"∧ short-contango E[ret]={ms*100:+.2f}% (t={ts:+.1f}, n={len(shorts)})")
    print(f"       (prime carry = ml>0 ET ms<0 ; sinon beta. spread long−short = {(ml-ms)*100:+.2f}%/mois)")

    # A3 régimes
    pos = 0
    print("  A3 régimes (rendement net total) :")
    for name, a, b in REGIMES:
        sub = p.loc[a:b].dropna()
        tr = (1 + sub).prod() - 1 if len(sub) else float("nan")
        ok = tr > 0
        pos += ok
        print(f"      {name:8s} {tr*100:+7.1f}%  {'ok' if ok else '—'}  ({len(sub)}m)")
    a3 = pos >= 3
    print(f"  A3 [{'PASS' if a3 else 'FAIL'}] ≥3/5 régimes positifs : {pos}/5")

    # A4 drop-one
    print("  A4 drop-one :")
    a4 = True
    for m in markets:
        sub = [x for x in markets if x != m]
        if len(sub) < 1:
            continue
        srd = ann_sharpe(portfolio(monthly, sub))
        a4 &= srd > 0
        print(f"      sans {m:9s} → SR {srd:+.2f} {'ok' if srd > 0 else '—'}")
    print(f"  A4 [{'PASS' if a4 else 'FAIL'}] tous drop-one Sharpe>0")

    # A5 DSR : essais TS-sign / TS-mag / XS
    p_xs = xs_portfolio(monthly, markets)
    trials = {"TS-sign": list(p.dropna()), "XS": list(p_xs.dropna())}
    srs = {k: audit.sharpe(v) for k, v in trials.items()}
    var_trials = float(np.var(list(srs.values()))) if len(srs) > 1 else 1e-6
    best = max(srs, key=srs.get)
    dsr4, _, sr0 = audit.deflated_sharpe(trials[best], 4, var_trials)
    dsr10, _, _ = audit.deflated_sharpe(trials[best], 10, var_trials)
    a5 = dsr4 > 0.95
    print(f"  A5 [{'PASS' if a5 else 'FAIL'}] DSR(best={best}, N=4)={dsr4:.3f} (N=10:{dsr10:.3f}) "
          f"| XS Sharpe(ann)={ann_sharpe(p_xs):+.2f}")
    A = a1 and a2 and a3 and a4 and a5
    print(f"  ==> (A) {'PASS' if A else 'FAIL'}")

    # ===== (B) =====
    print("\n" + "=" * 60 + "\n(B) L'EDGE VAUT LE COUP (sleeve)")
    spy = spy_monthly()
    al = p.dropna().reindex(spy.index).dropna()
    corr = float(al.corr(spy.reindex(al.index)))
    b1 = abs(corr) < 0.30
    print(f"  B1 [{'PASS' if b1 else 'FAIL'}] |corr actions| < 0.30 : corr(SPY)={corr:+.2f}")
    core = sixty_forty_monthly()
    cm = core.reindex(p.index).dropna()
    pm = p.reindex(cm.index).dropna()
    cm = cm.reindex(pm.index)
    pm_s = pm * (cm.std() / pm.std())             # vol-match au cœur
    print("  B2 sleeve carry sur 60/40 :")
    base = ann_sharpe(cm)
    b2 = False
    for x in (0.0, 0.10, 0.15, 0.25):
        srx = ann_sharpe((1 - x) * cm + x * pm_s)
        if x > 0 and srx > base:
            b2 = True
        print(f"      sleeve {int(x*100):2d}% : Sharpe {srx:+.2f}{'  (>base)' if x>0 and srx>base else ''}")
    print(f"  B2 [{'PASS' if b2 else 'FAIL'}] améliore 60/40 (note : méta complet = +trend, séparé)")
    B = b1 and b2

    # ===== VERDICT =====
    print("\n" + "=" * 60)
    if A and B:
        v = "GO-narrow — prime carry énergie réelle+orthogonale+sleeve. CONFIRMER univers large (non-free)."
    elif a1 and not a2:
        v = "DOWNGRADE — beta énergie, pas prime carry (A2 fail : un seul côté paie)."
    elif (not a1) and a2 and a3 and b1:
        v = "DOWNGRADE-to-watch — directionnellement réel mais sous-puissant au breadth free (t<2)."
    elif (not a2) and not a3:
        v = "KILL — pas de prime."
    else:
        v = f"MIXTE — A={'PASS' if A else 'FAIL'} B={'PASS' if B else 'FAIL'} : voir gates."
    print(f"VERDICT (#30, pré-enregistré) : {v}")
    print("=" * 60)


if __name__ == "__main__":
    main()

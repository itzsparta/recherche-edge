"""Piste 8 — CEF discount mean-reversion — PHASE 2 : gates B-G.

Opérationalisation pré-enregistrée (docs/SPEC.md). Stratégie = L/S mensuel sur z-score
trailing du discount propre au fonds ; rendement market-neutral = Δlog(1+prem).
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

import audit
from data_cef import universe, fetch_all

warnings.simplefilter("ignore")

ONEWAY = 0.0030          # 30 bps/côté
RT = 2 * ONEWAY          # round-trip par fraction-jambe tournée
BORROW_M = 0.04 / 12     # 4 %/an borrow short, mensuel
ANN = 12


# ---------- panels ----------
def monthly_panels(hist: dict[str, pd.DataFrame]):
    prem = pd.DataFrame({t: df["prem"].resample("ME").last() for t, df in hist.items()})
    prem = prem.sort_index()
    conv = np.log1p(prem / 100.0)        # log(1 + prem/100) = composante discount pure
    fwd = conv.diff().shift(-1)          # fwd.loc[m] = conv_{m+1} - conv_m (P&L market-neutral)
    return prem, fwd


def _z(prem: pd.DataFrame, lookback: int) -> pd.DataFrame:
    mp = max(12, lookback // 2)
    mu = prem.rolling(lookback, min_periods=mp).mean()
    sd = prem.rolling(lookback, min_periods=mp).std()
    return (prem - mu) / sd


# ---------- moteur stratégie ----------
def run_strategy(prem, fwd, lookback=24, n_groups=5, reverse=False, cats=None,
                 ret_override=None):
    """ret_override : DataFrame de rendement à empocher (défaut fwd) — pour test de lag."""
    if ret_override is not None:
        fwd = ret_override
    z = _z(prem, lookback)
    q = 1.0 / n_groups
    recs, prev_lo, prev_hi = [], set(), set()
    for m in prem.index:
        zr = z.loc[m].dropna()
        fr = fwd.loc[m].dropna()
        common = zr.index.intersection(fr.index)
        zr = zr.loc[common]
        if len(zr) < n_groups * 5:
            continue
        if cats is None:                              # cross-sectional global
            lo = set(zr[zr <= zr.quantile(q)].index)
            hi = set(zr[zr >= zr.quantile(1 - q)].index)
        else:                                          # intra-catégorie (Gate E)
            lo, hi = set(), set()
            cser = pd.Series({t: cats.get(t) for t in zr.index})
            for c, grp in zr.groupby(cser):
                if len(grp) < 6:
                    continue
                lo |= set(grp[grp <= grp.quantile(q)].index)
                hi |= set(grp[grp >= grp.quantile(1 - q)].index)
            if len(lo) < 5 or len(hi) < 5:
                continue
        if reverse:
            lo, hi = hi, lo
        lr = fr[list(lo)].mean()
        sr = fr[list(hi)].mean()
        f_l = 1 - len(lo & prev_lo) / max(len(lo), 1) if prev_lo else 1.0
        f_s = 1 - len(hi & prev_hi) / max(len(hi), 1) if prev_hi else 1.0
        recs.append({"m": m, "brut": lr - sr, "long": lr, "short": sr,
                     "turn": f_l + f_s, "turn_l": f_l, "turn_s": f_s})
        prev_lo, prev_hi = lo, hi
    return pd.DataFrame(recs).set_index("m")


def net_series(df: pd.DataFrame) -> pd.Series:
    return df["brut"] - RT * df["turn"] - BORROW_M


def stats(x: pd.Series) -> dict:
    x = x.dropna()
    n = len(x)
    mu, sd = x.mean(), x.std()
    return {"n": n, "ann": mu * ANN, "sharpe": (mu / sd * np.sqrt(ANN)) if sd else 0,
            "t": (mu / sd * np.sqrt(n)) if sd else 0, "mean_m": mu}


def main() -> None:
    print("Piste 8 CEF discount — Phase-2 (gates B-G)\n" + "=" * 64)
    uni = universe()
    cats = dict(zip(uni["Ticker"], uni.get("CategoryName")))
    hist = fetch_all(uni["Ticker"].dropna().unique().tolist())
    prem, fwd = monthly_panels(hist)
    print(f"Panel mensuel : {prem.shape[1]} fonds × {prem.shape[0]} mois "
          f"({prem.index.min().date()}..{prem.index.max().date()})")

    base = run_strategy(prem, fwd, lookback=24, n_groups=5)
    bn = net_series(base)
    sb, sn = stats(base["brut"]), stats(bn)

    print("\n--- Gate B : brut > 0, t > 2 (L/S quintile, z-24m, rebal mensuel) ---")
    print(f"  brut : ann {sb['ann']:+.2%}  Sharpe {sb['sharpe']:.2f}  t {sb['t']:.2f}  (n={sb['n']})")
    print(f"  long-leg conv {stats(base['long'])['ann']:+.2%}/an   "
          f"short-leg conv {stats(base['short'])['ann']:+.2%}/an")

    print("\n--- Gate C : net > 0 (coûts 30bps/côté + borrow 4%/an) ---")
    mt = base["turn"].mean()
    c_be = (sb["mean_m"] - BORROW_M) / (2 * mt) if mt else float("nan")
    print(f"  turnover moyen {mt:.2f}/mois  →  net : ann {sn['ann']:+.2%}  "
          f"Sharpe {sn['sharpe']:.2f}  t {sn['t']:.2f}")
    print(f"  break-even cost one-way = {c_be*1e4:.0f} bps  (pré-enreg. 30 bps)")

    print("\n--- Gate D : les deux jambes contribuent + miroir ---")
    lc, sc = stats(base["long"])["mean_m"], stats(base["short"])["mean_m"]
    print(f"  long conv mean {lc:+.4%} (>0 attendu)   short conv mean {sc:+.4%} (<0 attendu)")
    mir = run_strategy(prem, fwd, reverse=True)
    print(f"  miroir (signal inversé) brut ann {stats(mir['brut'])['ann']:+.2%} (doit être <0)")

    print("\n--- Gate E : L/S intra-catégorie (forme déployable sans hedge NAV) ---")
    ecat = run_strategy(prem, fwd, cats=cats)
    en = net_series(ecat)
    se, see = stats(ecat["brut"]), stats(en)
    print(f"  brut ann {se['ann']:+.2%}  t {se['t']:.2f}   |   net ann {see['ann']:+.2%}  t {see['t']:.2f}")

    print("\n--- Gate F : split régime (net) ---")
    for lab, sl in {"2018": ("2018-01", "2018-12"), "2020-COVID": ("2020-02", "2020-06"),
                    "2022-bear": ("2022-01", "2022-12")}.items():
        seg = bn.loc[sl[0]:sl[1]]
        if len(seg):
            print(f"  {lab:<11}: net mean {seg.mean():+.4%}/mois  (n={len(seg)})  "
                  f"{'POS' if seg.mean() > 0 else 'NEG'}")

    print("\n--- Gate G : DSR sur grille de variantes ---")
    sharpes, series = [], {}
    for lb in (12, 24, 36):
        for ng in (5, 3):
            s = net_series(run_strategy(prem, fwd, lookback=lb, n_groups=ng))
            sp = audit.sharpe(s.dropna().tolist())
            sharpes.append(sp)
            series[(lb, ng)] = s
    best = max(range(len(sharpes)), key=lambda i: sharpes[i])
    var_tr = float(np.var(sharpes, ddof=1))
    best_key = list(series)[best]
    dsr, sr_hat, sr0 = audit.deflated_sharpe(series[best_key].dropna().tolist(), len(sharpes), var_tr)
    print(f"  N variantes={len(sharpes)}  best={best_key}  SR/mois={sr_hat:.3f}  "
          f"SR0={sr0:.3f}  DSR={dsr:.3f}  [PASS si >0.95]")

    # ---- verdict ----
    gB = sb["ann"] > 0 and sb["t"] > 2
    gC = sn["ann"] > 0 and sn["t"] > 2
    gD = lc > 0 and sc < 0 and stats(mir["brut"])["ann"] < 0
    gE = see["ann"] > 0 and see["t"] > 2
    gG = dsr > 0.95
    print("\n" + "=" * 64)
    print(f"  B(brut t>2)={'PASS' if gB else 'FAIL'}   C(net t>2)={'PASS' if gC else 'FAIL'}   "
          f"D(2 jambes)={'PASS' if gD else 'FAIL'}")
    print(f"  E(intra-cat net t>2)={'PASS' if gE else 'FAIL'}   G(DSR>0.95)={'PASS' if gG else 'FAIL'}")
    verdict = "GO" if (gB and gC and gD and gE and gG) else ("KILL" if not gC else "DOWNGRADE")
    print(f"\n  VERDICT Phase-2 (provisoire) : {verdict}")


if __name__ == "__main__":
    main()

"""#31 prime ILS/cat-bond : sim + gates pré-enregistrés (docs/SPEC.md). Data free yfinance.

ILS funds (NAV total-return, fees DÉJÀ dans le NAV) vs T-bill (BIL). Excès = ret_fund − ret_BIL.
A1 magnitude (>3% ann, t>2) ; A2 survit au tail (années cat incluses) ; B1 décorrélé (corr SPY<0.20
+ stress) ; B2 sleeve sur 60/40+trend.
"""
from __future__ import annotations
import math, pathlib, sys
import numpy as np, pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"; DATA.mkdir(exist_ok=True)
FH = HERE.parent / "factor-harvest"
ANN = math.sqrt(12)
FUNDS = ["SRRIX", "SHRIX", "XILSX"]        # gating (10+ ans) ; EMPIX trop court
SECONDARY = ["EMPIX"]


def fetch(ticker: str) -> pd.Series:
    """Close total-return (auto_adjust) daily, caché."""
    import yfinance as yf
    f = DATA / f"{ticker}.csv"
    if f.exists():
        s = pd.read_csv(f, parse_dates=["Date"]).set_index("Date").iloc[:, 0]
        return s.astype(float)
    d = yf.download(ticker, start="2010-01-01", auto_adjust=True, progress=False)
    c = d["Close"]
    s = c[ticker] if isinstance(c, pd.DataFrame) else c
    s.to_csv(f)
    return s.astype(float)


def monthly_ret(ticker: str) -> pd.Series:
    return fetch(ticker).resample("ME").last().pct_change().rename(ticker)


def cal_years(m: pd.Series) -> dict:
    return {y: (1 + g).prod() - 1 for y, g in m.dropna().groupby(m.dropna().index.year)}


def trend_monthly() -> pd.Series:
    sys.path.insert(0, str(HERE)); sys.path.append(str(FH))
    import data as fhdata, backtest as fhbt, run_futures
    px = fhdata.load_universe(list(run_futures.FUTURES)).dropna(how="all")
    return fhbt.run_strategy(px, lookback_months=12, require_all=False)["monthly"].rename("trend")


def main():
    import audit
    bil = monthly_ret("BIL")
    spy = monthly_ret("SPY")
    fund_m = {t: monthly_ret(t) for t in FUNDS + SECONDARY}

    # excès sur T-bill par fund
    print("=== Prime ILS : excès sur T-bill (BIL), net de fees (NAV TR) ===")
    print(f"{'fund':7s} {'début':>10s} {'n':>4s} {'ann_excès':>10s} {'t':>6s} {'vol':>6s} "
          f"{'corrSPY':>8s} {'pire_an':>8s}")
    excess = {}
    for t in FUNDS + SECONDARY:
        ex = (fund_m[t] - bil).dropna()
        excess[t] = ex
        sr = audit.sharpe(list(ex)) * ANN
        annx = ex.mean() * 12
        cy = cal_years(fund_m[t])
        worst = min(cy.values()) if cy else float("nan")
        al = ex.reindex(spy.index).dropna()
        corr = float(al.corr(spy.reindex(al.index)))
        tag = "" if t in FUNDS else " (sec)"
        print(f"{t:7s} {str(ex.index.min().date()):>10s} {len(ex):>4d} {annx*100:>+9.2f}% "
              f"{audit.tstat(list(ex)):>+6.2f} {ex.std()*ANN*100:>5.1f}% {corr:>+8.2f} "
              f"{worst*100:>+7.1f}%{tag}")

    # portefeuille ILS equal-weight (union des funds gating)
    ew = pd.concat([excess[t] for t in FUNDS], axis=1).mean(axis=1).dropna().rename("ILS")
    annx = ew.mean() * 12
    t_ew = audit.tstat(list(ew))
    sr_ew = audit.sharpe(list(ew)) * ANN
    print(f"\nILS equal-weight ({FUNDS}) : {ew.index.min().date()}→{ew.index.max().date()} "
          f"({len(ew)} mois)")
    print(f"  excès annualisé {annx*100:+.2f}%  t={t_ew:+.2f}  Sharpe(ann) {sr_ew:+.2f}  "
          f"vol {ew.std()*ANN*100:.1f}%  skew {ew.skew():+.2f}")

    # ===== (A) =====
    print("\n" + "=" * 60 + "\n(A) LA PRIME EXISTE ET CLEAR LE HURDLE")
    a1 = annx > 0.03 and t_ew > 2
    print(f"  A1 [{'PASS' if a1 else 'FAIL'}] excès>3% ∧ t>2 : {annx*100:+.2f}% t={t_ew:+.2f}")

    # A2 tail : années calendaires (incl 2017/2022), majorité positive + full-sample >0
    ewf = pd.concat([fund_m[t] for t in FUNDS], axis=1).mean(axis=1).dropna()   # rendement brut EW
    cy = cal_years(ewf)
    npos = sum(v > 0 for v in cy.values())
    print("  A2 années calendaires (rendement brut EW, fees incl) :")
    for y, v in sorted(cy.items()):
        cat = "  <-cat" if y in (2017, 2022) else ""
        print(f"      {y}: {v*100:+6.1f}%{cat}")
    a2 = annx > 0 and npos / len(cy) >= 0.60
    print(f"  A2 [{'PASS' if a2 else 'FAIL'}] excès full>0 ∧ ≥60% années + : {npos}/{len(cy)} positives, "
          f"skew {ewf.skew():+.2f}")

    # régime soft(≤2017) vs hard(2023+)
    soft = ew.loc[:"2017-12-31"]; hard = ew.loc["2023-01-01":]
    print(f"  régime : soft ≤2017 excès {soft.mean()*12*100:+.1f}%/an ({len(soft)}m) | "
          f"hard 2023+ {hard.mean()*12*100:+.1f}%/an ({len(hard)}m)")
    A = a1 and a2
    print(f"  ==> (A) {'PASS' if A else 'FAIL'}")

    # ===== (B) =====
    print("\n" + "=" * 60 + "\n(B) VRAIMENT DÉCORRÉLÉ + SLEEVE")
    al = ew.reindex(spy.index).dropna()
    corr = float(al.corr(spy.reindex(al.index)))
    # stress : corr pendant les pires mois actions (décile bas SPY)
    sp = spy.reindex(al.index)
    thr = sp.quantile(0.10)
    stress = al[sp <= thr]
    corr_stress = float(stress.corr(sp[sp <= thr])) if len(stress) > 3 else float("nan")
    b1 = abs(corr) < 0.20
    print(f"  B1 [{'PASS' if b1 else 'FAIL'}] |corr SPY|<0.20 : corr={corr:+.2f} "
          f"(stress décile-bas SPY: corr={corr_stress:+.2f}, n={len(stress)})")

    # B2 sleeve sur 60/40 + trend
    ief = monthly_ret("IEF")
    core = (0.6 * spy + 0.4 * ief).dropna().rename("core")
    try:
        trend = trend_monthly()
    except Exception as e:
        print(f"  (trend indispo: {type(e).__name__}) → sleeve sur 60/40 seul")
        trend = None
    # rendement TOTAL ILS (pas l'excès) pour le sleeve : excès + T-bill = ret_fund EW
    ils_tot = ewf.rename("ILS")
    idx = core.index
    df = pd.concat([core, ils_tot] + ([trend] if trend is not None else []), axis=1).dropna()
    print(f"  B2 sleeve (échantillon commun {df.index.min().date()}→{df.index.max().date()}, {len(df)}m) :")
    cs = df["ILS"] * (df["core"].std() / df["ILS"].std())
    base_core = audit.sharpe(list(df["core"])) * ANN
    combos = {"60/40": df["core"], "+ILS 15%": 0.85 * df["core"] + 0.15 * cs}
    if trend is not None:
        ts = df["trend"] * (df["core"].std() / df["trend"].std())
        combos["+trend 20%"] = 0.80 * df["core"] + 0.20 * ts
        combos["+trend 20% +ILS 15%"] = 0.65 * df["core"] + 0.20 * ts + 0.15 * cs
    sh = {k: audit.sharpe(list(v)) * ANN for k, v in combos.items()}
    for k, v in sh.items():
        print(f"      {k:24s} Sharpe {v:+.3f}")
    if trend is not None:
        incr = sh["+trend 20% +ILS 15%"] - sh["+trend 20%"]
        b2 = incr > 0
        print(f"      increment ILS sur (60/40+trend) = {incr:+.3f} Sharpe")
    else:
        b2 = sh["+ILS 15%"] > base_core
    print(f"  B2 [{'PASS' if b2 else 'FAIL'}] ILS améliore le méta")
    B = b1 and b2

    # ===== VERDICT =====
    print("\n" + "=" * 60)
    if A and B:
        v = "GO — prime ILS réelle, décorrélée, clear hurdle net-du-tail, déployable retail = vrai sleeve orthogonal."
    elif a2 and b1 and not a1:
        v = "DOWNGRADE — prime réelle+décorrélée mais <hurdle 3% (mangée par fees+tail du wrapper retail)."
    elif (not b1) or (not a2):
        v = "KILL — corrélé (pas le diversificateur annoncé) ou négatif tail-inclus (peso problem)."
    else:
        v = f"MIXTE — A={'PASS' if A else 'FAIL'} B={'PASS' if B else 'FAIL'}"
    print(f"VERDICT (#31, pré-enregistré) : {v}")
    print("=" * 60)


if __name__ == "__main__":
    main()

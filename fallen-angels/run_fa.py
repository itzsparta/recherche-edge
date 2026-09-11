"""#35 prime fallen angels : régressions + gates pré-enregistrés (docs/SPEC.md). Data free yfinance.

Gating sur l'ALPHA 2F (ex_FA sur ex_HYG + ex_IEF, t Newey-West lag 3), pas sur l'écart brut
ANGL−HYG (duration + qualité BB = bêta déguisé). A prime nette de bêta ; B pas un mirage
(moitiés, drop-2020, drop-best-year, FALN) ; C déployable (WING.L UCITS) + sleeve > HYG.
"""
from __future__ import annotations
import math, pathlib, sys
import numpy as np, pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"; DATA.mkdir(exist_ok=True)
FH = HERE.parent / "factor-harvest"
ANN = math.sqrt(12)
NW_LAG = 3
N_TRIALS = 5
DROP_2020 = ("2020-02-01", "2020-12-31")


def fetch(ticker: str) -> pd.Series:
    """Close total-return (auto_adjust) daily, caché."""
    import yfinance as yf
    f = DATA / f"{ticker}.csv"
    if f.exists():
        s = pd.read_csv(f, parse_dates=["Date"]).set_index("Date").iloc[:, 0]
        return s.astype(float)
    d = yf.download(ticker, start="2007-01-01", auto_adjust=True, progress=False)
    c = d["Close"]
    s = c[ticker] if isinstance(c, pd.DataFrame) else c
    s.to_csv(f)
    return s.astype(float)


def monthly_ret(ticker: str) -> pd.Series:
    m = fetch(ticker).resample("ME").last().pct_change().rename(ticker)
    today = pd.Timestamp.today()
    m = m[m.index < pd.Timestamp(today.year, today.month, 1)]    # dernier mois COMPLET
    jumps = m[m.abs() > 0.30]
    if len(jumps):
        print(f"  ⚠ {ticker}: mois |r|>30% (unité/split ?) {[(str(i.date()), round(v, 3)) for i, v in jumps.items()]}")
    return m


def ols_nw(y: pd.Series, X: pd.DataFrame, lag: int = NW_LAG):
    """OLS avec constante, covariance Newey-West (Bartlett). Renvoie (coef, se, resid)."""
    df = pd.concat([y, X], axis=1).dropna()
    yv = df.iloc[:, 0].to_numpy()
    Xv = np.column_stack([np.ones(len(df)), df.iloc[:, 1:].to_numpy()])
    b, *_ = np.linalg.lstsq(Xv, yv, rcond=None)
    e = yv - Xv @ b
    u = Xv * e[:, None]
    S = u.T @ u
    for l in range(1, lag + 1):
        G = u[l:].T @ u[:-l]
        S += (1 - l / (lag + 1)) * (G + G.T)
    inv = np.linalg.inv(Xv.T @ Xv)
    V = inv @ S @ inv
    return b, np.sqrt(np.diag(V)), pd.Series(e, index=df.index)


def alpha(ex_fa: pd.Series, F: pd.DataFrame, mask=None):
    """α annualisé, t_NW, n, série couverte h = α + ε."""
    y = ex_fa if mask is None else ex_fa[mask(ex_fa.index)]
    b, se, e = ols_nw(y, F)
    return b[0] * 12, b[0] / se[0], len(e), b, (e + b[0])


def cal_years(m: pd.Series) -> dict:
    m = m.dropna()
    return {y: (1 + g).prod() - 1 for y, g in m.groupby(m.index.year)}


def max_dd(m: pd.Series) -> float:
    w = (1 + m.dropna()).cumprod()
    return float((w / w.cummax() - 1).min())


def trend_monthly() -> pd.Series:
    sys.path.append(str(FH))
    import data as fhdata, backtest as fhbt, run_futures
    px = fhdata.load_universe(list(run_futures.FUTURES)).dropna(how="all")
    return fhbt.run_strategy(px, lookback_months=12, require_all=False)["monthly"].rename("trend")


def main():
    import audit
    r = {t: monthly_ret(t) for t in ["ANGL", "FALN", "WING.L", "HYG", "IEF", "LQD", "BIL", "SPY"]}
    ex = {t: (r[t] - r["BIL"]).dropna().rename(t) for t in r if t != "BIL"}
    F2 = pd.concat([ex["HYG"], ex["IEF"]], axis=1)
    F3 = pd.concat([ex["HYG"], ex["IEF"], (r["LQD"] - r["IEF"]).rename("IGcredit")], axis=1)

    angl = ex["ANGL"]
    print(f"ANGL {angl.index.min().date()}→{angl.index.max().date()} ({len(angl)} mois)")

    # ===== diagnostics bruts (non-gating) =====
    raw_hyg = (r["ANGL"] - r["HYG"]).dropna()
    print("\n=== Diagnostics bruts (non-gating) ===")
    print(f"  écart brut ANGL−HYG : {raw_hyg.mean()*12*100:+.2f}%/an (t={audit.tstat(list(raw_hyg)):+.2f})")
    print(f"  excès ANGL−BIL      : {angl.mean()*12*100:+.2f}%/an  vol {angl.std()*ANN*100:.1f}%  "
          f"skew {angl.skew():+.2f}")
    for t in ["ANGL", "HYG"]:
        print(f"  maxDD {t}: {max_dd(r[t].loc[angl.index.min():])*100:+.1f}%")

    # ===== (A) =====
    print("\n" + "=" * 64 + "\n(A) PRIME NETTE DE BÊTA")
    a2f, t2f, n2f, b2f, h2f = alpha(angl, F2)
    print(f"  2F ANGL : α={a2f*100:+.2f}%/an t_NW={t2f:+.2f} n={n2f} | β_HY={b2f[1]:+.2f} β_T={b2f[2]:+.2f}")
    a3f, t3f, n3f, b3f, h3f = alpha(angl, F3)
    print(f"  3F ANGL : α={a3f*100:+.2f}%/an t_NW={t3f:+.2f} | β_HY={b3f[1]:+.2f} β_T={b3f[2]:+.2f} "
          f"β_IG={b3f[3]:+.2f}")
    drop = lambda idx: ~((idx >= DROP_2020[0]) & (idx <= DROP_2020[1]))
    ad, td, nd, _, hd = alpha(angl, F2, drop)
    af, tf, nf, _, hf = alpha(ex["FALN"], F2)
    aw, tw, nw, _, hw = alpha(ex["WING.L"], F2)

    variants = {"2F": h2f, "3F": h3f, "drop2020": hd, "FALN": hf, "WING": hw}
    srs = [audit.sharpe(list(v)) for v in variants.values()]
    dsr, sr_hat, sr0 = audit.deflated_sharpe(list(h2f), N_TRIALS, float(np.var(srs)))
    a1 = a2f >= 0.01 and t2f >= 2.0
    a2 = a3f > 0 and t3f >= 1.5
    a3 = dsr > 0.95
    print(f"  A1 [{'PASS' if a1 else 'FAIL'}] α_2F ≥1%/an ∧ t≥2")
    print(f"  A2 [{'PASS' if a2 else 'FAIL'}] α_3F >0 ∧ t≥1.5")
    print(f"  A3 [{'PASS' if a3 else 'FAIL'}] DSR(n={N_TRIALS}) = {dsr:.3f} (SR/mois {sr_hat:+.3f} vs SR0 {sr0:+.3f})")
    A = a1 and a2 and a3
    print(f"  ==> (A) {'PASS' if A else 'FAIL'}")

    # ===== (B) =====
    print("\n" + "=" * 64 + "\n(B) PAS UN MIRAGE")
    mid = angl.index[len(angl) // 2]
    ah1, th1, nh1, _, _ = alpha(angl, F2, lambda i: i < mid)
    ah2, th2, nh2, _, _ = alpha(angl, F2, lambda i: i >= mid)
    b1 = ah1 > 0 and ah2 > 0
    print(f"  B1 [{'PASS' if b1 else 'FAIL'}] moitiés : H1 α={ah1*100:+.2f}% (t={th1:+.2f}, {nh1}m) | "
          f"H2 α={ah2*100:+.2f}% (t={th2:+.2f}, {nh2}m)  coupe {mid.date()}")
    b2 = ad >= 0.005
    print(f"  B2 [{'PASS' if b2 else 'FAIL'}] drop 2020-02→12 : α={ad*100:+.2f}%/an (t={td:+.2f}, {nd}m) ≥0.5%")
    hy = h2f.groupby(h2f.index.year).sum()
    best = int(hy.idxmax())
    ab, tb, nb, _, _ = alpha(angl, F2, lambda i: i.year != best)
    b3 = ab > 0
    print(f"  B3 [{'PASS' if b3 else 'FAIL'}] drop meilleure année ({best}, h={hy.max()*100:+.1f}%) : "
          f"α={ab*100:+.2f}%/an (t={tb:+.2f})")
    b4 = af > 0
    print(f"  B4 [{'PASS' if b4 else 'FAIL'}] FALN 2F : α={af*100:+.2f}%/an (t={tf:+.2f}, {nf}m)")
    print("  h_2F par année : " + "  ".join(f"{y}:{v*100:+.1f}" for y, v in hy.items()))
    B = b1 and b2 and b3 and b4
    print(f"  ==> (B) {'PASS' if B else 'FAIL'}")

    # ===== (C) =====
    print("\n" + "=" * 64 + "\n(C) DÉPLOYABLE + SLEEVE")
    c1 = aw > 0
    print(f"  C1 [{'PASS' if c1 else 'FAIL'}] WING.L (UCITS) 2F : α={aw*100:+.2f}%/an (t={tw:+.2f}, {nw}m)")
    core = (0.6 * r["SPY"] + 0.4 * r["IEF"]).rename("core")
    try:
        trend = trend_monthly()
    except Exception as e:
        print(f"  (trend indispo: {type(e).__name__}: {e}) → C2 sur 60/40 seul")
        trend = None
    parts = [core, r["ANGL"].rename("FA"), r["HYG"].rename("HY")] + ([trend] if trend is not None else [])
    df = pd.concat(parts, axis=1).dropna()
    sc = lambda c: df[c] * (df["core"].std() / df[c].std())
    base = 0.80 * df["core"] + 0.20 * sc("trend") if trend is not None else df["core"]
    wb = 0.65 if trend is not None else 0.85
    rest = 0.20 * sc("trend") if trend is not None else 0.0
    sh = lambda s: audit.sharpe(list(s)) * ANN
    s_base = sh(base)
    s_fa = sh(wb * df["core"] + rest + 0.15 * sc("FA"))
    s_hy = sh(wb * df["core"] + rest + 0.15 * sc("HY"))
    i_fa, i_hy = s_fa - s_base, s_hy - s_base
    c2 = i_fa > 0 and i_fa > i_hy
    print(f"  échantillon {df.index.min().date()}→{df.index.max().date()} ({len(df)}m) | "
          f"base Sharpe {s_base:+.3f}")
    print(f"  C2 [{'PASS' if c2 else 'FAIL'}] incr FA {i_fa:+.3f} vs incr HYG {i_hy:+.3f}")
    C = c1 and c2

    # ===== diagnostics complémentaires =====
    print("\n=== Diagnostics (non-gating) ===")
    al = angl.reindex(ex["SPY"].index).dropna()
    sp = r["SPY"].reindex(al.index)
    thr = sp.quantile(0.10)
    print(f"  corr ANGL/SPY {al.corr(sp):+.2f} | stress décile-bas SPY {al[sp <= thr].corr(sp[sp <= thr]):+.2f}")
    ca, chy = cal_years(r["ANGL"].loc[angl.index.min():]), cal_years(r["HYG"].loc[angl.index.min():])
    print("  années  ANGL  HYG  écart")
    for y in sorted(ca):
        tag = "  <-énergie" if y in (2015, 2016) else ("  <-choc taux" if y == 2022 else "")
        print(f"    {y}  {ca[y]*100:+6.1f} {chy.get(y, float('nan'))*100:+6.1f} "
              f"{(ca[y]-chy.get(y, float('nan')))*100:+6.1f}{tag}")

    # ===== VERDICT =====
    print("\n" + "=" * 64)
    if not A:
        v = ("KILL bêta déguisé — surperformance brute = duration/qualité, pas de prime de flux."
             if raw_hyg.mean() > 0 else "KILL sec — pas même de surperformance brute.")
    elif not B:
        v = "KILL mirage — prime portée par 2020 / une moitié / une année / un seul véhicule."
    elif not c1:
        v = "DOWNGRADE non-déployable — prime réelle US, absente du véhicule UCITS."
    elif not c2:
        v = "DOWNGRADE meilleur-HY — prime réelle et déployable, pas un sleeve (remplace HYG seulement)."
    else:
        v = "GO — 1er flux forcé survivant ; intégration deliverable = étude séparée pré-enregistrée."
    print(f"VERDICT (#35, pré-enregistré) : {v}")
    print("=" * 64)


if __name__ == "__main__":
    main()

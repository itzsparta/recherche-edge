"""Étude #37 — stress séculaire du deliverable levé + puissance du trend (docs/SPEC-secular.md).

Proxys 1926+ : marché Ken French, obligation 10 ans au pair reconstruite (FRED LTGOVTBD
raccordé à GS10), cash = RF Ken French. Trend : facteur TSMOM AQR (1985+) mis à vol égale au
sleeve #22, collatéral rémunéré au cash, haircut 1 %/an ; trend = RF avant 1985 (à plat).
Gates figés dans la spec (commit 2a19aad, avant tout pull). Rien n'est optimisé ici.
"""
from __future__ import annotations

import math
import os
import re
import urllib.request
import zipfile

import numpy as np
import pandas as pd

import audit
import sleeves
from run_lever import load_tbill_monthly, maxdd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
URL_FF = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip"
URL_AQR = ("https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/"
           "Time-Series-Momentum-Factors-Monthly.xlsx")
URL_FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"

W_6040, W_TREND = 0.80, 0.20        # identique #34
GRID = [1.0, 1.25, 1.5, 2.0]        # pré-committé (spec)
L_DEPLOY = 1.5
SPREAD_FUT = 0.004                  # RF + 0,40 %/an — GATING
SPREAD_BROKER = 0.015               # diagnostic
HAIRCUT = 0.010                     # frais trend, %/an à vol du sleeve
RUIN_DD = -0.35
HURDLE_A = 0.010
SPLICE = pd.Period("1953-04", "M")  # dernier rendement calculé sur LTGOVTBD
ANN = math.sqrt(12)

W = {
    "W0": ("2006-04", "2026-02"),
    "W1": ("1926-07", "2006-03"),
    "W2": ("1966-01", "1981-12"),
    "W3": ("1985-01", "2006-03"),
    "W4": ("1985-01", None),        # fin = dernier mois AQR
}
EPISODES = [
    ("1929-09 → 1932-06", "1929-09", "1932-06"),
    ("1940-1951 répression", "1940-01", "1951-12"),
    ("1973-74", "1973-01", "1974-12"),
    ("oct. 1987", "1987-10", "1987-10"),
    ("2000-02", "2000-01", "2002-12"),
    ("2008", "2008-01", "2008-12"),
    ("2022", "2022-01", "2022-12"),
]


# ---------------------------------------------------------------- données
def _fetch(fname: str, url: str, browser_ua: bool = True) -> str:
    path = os.path.join(DATA, fname)
    if not os.path.exists(path):
        req = urllib.request.Request(url, headers={"User-Agent": UA} if browser_ua else {})
        raw = urllib.request.urlopen(req, timeout=120).read()
        os.makedirs(DATA, exist_ok=True)
        with open(path, "wb") as f:
            f.write(raw)
    return path


def load_ff() -> pd.DataFrame:
    """Colonnes mkt (rendement total marché US) et rf (T-bill 1 mois), mensuel, décimal."""
    z = zipfile.ZipFile(_fetch("ff_factors.zip", URL_FF))
    rows = []
    for line in z.read(z.namelist()[0]).decode("latin-1").splitlines():
        m = re.match(r"^\s*(\d{6})\s*,(.*)$", line)   # 6 chiffres = section mensuelle
        if m:
            rows.append((m.group(1), *[float(v) for v in m.group(2).split(",")]))
    df = pd.DataFrame(rows, columns=["ym", "mkt_rf", "smb", "hml", "rf"])
    idx = pd.PeriodIndex([pd.Period(f"{y[:4]}-{y[4:]}", "M") for y in df["ym"]])
    return pd.DataFrame({"mkt": (df["mkt_rf"] + df["rf"]).values / 100,
                         "rf": df["rf"].values / 100}, index=idx)


def load_fred(sid: str, fname: str) -> pd.Series:
    d = pd.read_csv(_fetch(fname, URL_FRED.format(sid), browser_ua=False))
    s = pd.Series(pd.to_numeric(d.iloc[:, 1], errors="coerce").values,
                  index=pd.DatetimeIndex(pd.to_datetime(d.iloc[:, 0])).to_period("M"))
    return s.dropna()


def par_bond_returns(y: pd.Series, years: float = 10.0) -> pd.Series:
    """R_t = y_{t-1}/12 + P(y_t ; coupon y_{t-1}, maturité years − 1/12) − 1, coupons semestriels."""
    y0, y1 = y.shift(1), y
    disc = (1 + y1 / 2) ** (-2 * (years - 1 / 12))
    price = (y0 / y1) * (1 - disc) + disc
    return (price - 1 + y0 / 12).dropna()


def load_bond() -> pd.Series:
    r_lt = par_bond_returns(load_fred("LTGOVTBD", "fred_ltgovtbd.csv") / 100)
    r_gs = par_bond_returns(load_fred("GS10", "fred_gs10.csv") / 100)
    return pd.concat([r_lt[r_lt.index <= SPLICE], r_gs[r_gs.index > SPLICE]]).sort_index()


def load_aqr() -> pd.DataFrame:
    raw = pd.read_excel(_fetch("aqr_tsmom.xlsx", URL_AQR), sheet_name="TSMOM Factors", header=None)
    hdr = raw.index[raw.iloc[:, 1].astype(str).str.strip() == "TSMOM"][0]
    df = raw.iloc[hdr + 1:].copy()
    df.columns = ["date"] + [str(c).strip() for c in raw.iloc[hdr, 1:]]
    df = df.dropna(subset=["date"])
    df.index = pd.DatetimeIndex(pd.to_datetime(df["date"])).to_period("M")
    return df.drop(columns="date").apply(pd.to_numeric, errors="coerce").dropna(how="all")


def load_dbmf() -> pd.Series:
    px = pd.read_csv(os.path.join(DATA, "deploy_px.csv"), parse_dates=["Date"]).set_index("Date")
    if "DBMF" not in px:
        return pd.Series(dtype=float)
    m = px["DBMF"].dropna().resample("ME").last().pct_change().dropna()
    m.index = m.index.to_period("M")
    return m


def monthly_px_returns(tickers: list[str]) -> pd.DataFrame:
    px = sleeves._load_prices(tickers).dropna()
    m = px.resample("ME").last().pct_change().dropna()
    m.index = m.index.to_period("M")
    return m


# ---------------------------------------------------------------- métriques
def win(s: pd.Series, key: str) -> pd.Series:
    a, b = W[key]
    lo = pd.Period(a, "M")
    hi = pd.Period(b, "M") if b else s.index.max()
    return s[(s.index >= lo) & (s.index <= hi)]


def span(s: pd.Series, a: str, b: str) -> pd.Series:
    return s[(s.index >= pd.Period(a, "M")) & (s.index <= pd.Period(b, "M"))]


def lever(rp: pd.Series, rf: pd.Series, L: float, spread: float = SPREAD_FUT) -> pd.Series:
    """r_L = L·r_p − (L−1)·(rf_mensuel + spread/12), levier constant rebalancé mensuellement."""
    return (L * rp - (L - 1.0) * (rf.reindex(rp.index) + spread / 12)).dropna()


def cagr(r: pd.Series) -> float:
    r = r.dropna()
    return float((1 + r).prod() ** (12 / len(r)) - 1)


def sharpe_ex(r: pd.Series, rf: pd.Series) -> float:
    x = (r - rf.reindex(r.index)).dropna()
    return float(x.mean() / x.std() * ANN)


def t_mean(x: pd.Series) -> float:
    x = x.dropna()
    return float(x.mean() / (x.std() / math.sqrt(len(x))))


def sharpe_ci(x: pd.Series) -> tuple[float, float, float]:
    """Sharpe annualisé + IC 95 % (Lo 2002, iid) sur une série d'excès."""
    x = x.dropna()
    sr = x.mean() / x.std()
    se = math.sqrt((1 + 0.5 * sr ** 2) / len(x))
    return sr * ANN, (sr - 1.96 * se) * ANN, (sr + 1.96 * se) * ANN


def incr(rp: pd.Series, rf: pd.Series, key: str, L: float = L_DEPLOY,
         spread: float = SPREAD_FUT) -> float:
    return cagr(win(lever(rp, rf, L, spread), key)) - cagr(win(lever(rp, rf, 1.0, spread), key))


def l_star(rp: pd.Series, rf: pd.Series, key: str) -> float | None:
    ok = [L for L in GRID if maxdd(win(lever(rp, rf, L), key)) > RUIN_DD]
    return max(ok) if ok else None


def grid_table(rp: pd.Series, rf: pd.Series, key: str, label: str) -> None:
    s = win(rp, key)
    print(f"\n  {key} {label} : {s.index.min()} → {s.index.max()} ({len(s)} mois)")
    print(f"    {'L':>5s} {'CAGR':>8s} {'arith':>8s} {'vol':>7s} {'Sh.ex':>6s} {'maxDD':>8s} {'pire m':>8s}")
    for L in GRID:
        r = win(lever(rp, rf, L), key)
        print(f"    {L:5.2f} {cagr(r)*100:+7.2f}% {r.mean()*1200:+7.2f}% {r.std()*ANN*100:6.1f}% "
              f"{sharpe_ex(r, rf):+6.2f} {maxdd(r)*100:+7.1f}% {r.min()*100:+7.1f}%")


def pf(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


# ---------------------------------------------------------------- run
def main() -> None:
    ff = load_ff()
    bond = load_bond()
    aqr = load_aqr()
    cpi = load_fred("CPIAUCNS", "fred_cpi.csv")
    infl = cpi.pct_change().dropna()
    W["W4"] = ("1985-01", str(aqr.index.max()))

    S = sleeves.load_sleeves()                              # #22 : base6040, trend, carry
    rf = ff["rf"]
    p6040 = (0.6 * ff["mkt"] + 0.4 * bond.reindex(ff.index)).dropna()

    vol_sleeve = float(win(S["trend"], "W0").std())
    k = vol_sleeve / float(aqr["TSMOM"].std())
    x_net = (k * aqr["TSMOM"] - HAIRCUT / 12).dropna()      # excès net du sleeve AQR
    trend = rf.reindex(p6040.index).copy()                  # à plat avant 1985
    trend.loc[x_net.index.intersection(trend.index)] += x_net
    rp = (W_6040 * p6040 + W_TREND * trend).dropna()

    print("=" * 78)
    print(f"#37 — stress séculaire | proxys {p6040.index.min()} → {p6040.index.max()} | "
          f"AQR {aqr.index.min()} → {aqr.index.max()}")
    print(f"  k = {k:.3f} (vol sleeve #22 W0 {vol_sleeve*ANN*100:.2f}% / vol TSMOM "
          f"{aqr['TSMOM'].std()*ANN*100:.2f}%) ; haircut {HAIRCUT*100:.1f}%/an")

    # ---------- G0 fidélité
    print("\n" + "=" * 78 + "\nG0 — FIDÉLITÉ DES PROXYS (W0)")
    a = win(p6040, "W0")
    b = S["base6040"].reindex(a.index).dropna()
    a = a.reindex(b.index)
    corr0 = float(a.corr(b))
    dcg = cagr(a) - cagr(b)
    g0 = corr0 >= 0.95 and abs(dcg) <= 0.015
    print(f"  corr(proxy 6040, base6040 #22) = {corr0:+.3f} ; CAGR proxy {cagr(a)*100:+.2f}% vs "
          f"#22 {cagr(b)*100:+.2f}% (écart {dcg*100:+.2f} pt)  => {pf(g0)}")
    etf = monthly_px_returns(["SPY", "IEF"])
    ix = win(ff["mkt"], "W0").index.intersection(etf.index)
    print(f"  diag : corr(mkt KF, SPY) = {ff['mkt'].reindex(ix).corr(etf['SPY'].reindex(ix)):+.3f} ; "
          f"corr(oblig 10 ans, IEF) = {bond.reindex(ix).corr(etf['IEF'].reindex(ix)):+.3f}")
    if not g0:
        print("\nVERDICT : UNTESTABLE (proxys non fidèles, aucun autre gate lu)")
        return

    # ---------- grilles
    print("\n" + "=" * 78 + f"\nGRILLES L @ RF+{SPREAD_FUT*100:.1f}% (deliverable proxy)")
    grid_table(rp, rf, "W0", "fenêtre #34 (proxys)")
    grid_table(rp, rf, "W1", "hors fenêtre séculaire")
    grid_table(rp, rf, "W2", "stagflation")
    grid_table(rp, rf, "W3", "deliverable complet, trend AQR")
    grid_table(rp, rf, "W4", "ère AQR complète")

    # ---------- gates
    print("\n" + "=" * 78 + "\nGATES")
    inc_a = incr(rp, rf, "W1")
    g_a = inc_a >= HURDLE_A
    print(f"[A] W1 CAGR(1,5) − CAGR(1) = {inc_a*100:+.2f} pt/an (hurdle +1,00)  => {pf(g_a)}")
    inc_b = incr(rp, rf, "W2")
    g_b = inc_b > 0
    print(f"[B] W2 CAGR(1,5) − CAGR(1) = {inc_b*100:+.2f} pt/an (> 0)  => {pf(g_b)}")
    dd_c = maxdd(win(lever(rp, rf, L_DEPLOY), "W3"))
    g_c = dd_c > RUIN_DD
    print(f"[C] W3 maxDD(1,5) = {dd_c*100:+.1f}% (> −35 %)  => {pf(g_c)}   L*_W3 = {l_star(rp, rf, 'W3')}")
    dd_r = maxdd(win(lever(rp, rf, L_DEPLOY), "W1"))
    dd_r1 = maxdd(win(lever(rp, rf, 1.0), "W1"))
    g_r = dd_r > RUIN_DD
    print(f"[R] W1 maxDD(1,5) = {dd_r*100:+.1f}% (> −35 %)  => {pf(g_r)}   "
          f"maxDD(1) = {dd_r1*100:+.1f}%   L*_W1 = {l_star(rp, rf, 'W1')}")
    t4 = t_mean(win(x_net, "W4"))
    sr3 = sharpe_ci(win(x_net, "W3"))[0]
    sr_post = sharpe_ci(span(x_net, "2006-04", str(aqr.index.max())))[0]
    sr4, lo4, hi4 = sharpe_ci(win(x_net, "W4"))
    g_d = t4 > 2.0 and sr3 > 0 and sr_post > 0
    print(f"[D] W4 sleeve net : t = {t4:+.2f} ; Sharpe {sr4:+.2f} [IC95 {lo4:+.2f} ; {hi4:+.2f}] ; "
          f"Sharpe W3 {sr3:+.2f} ; 2006-04→fin {sr_post:+.2f}  => {pf(g_d)}")
    rp3, b3 = win(rp, "W3"), win(p6040, "W3")
    d_e = sharpe_ex(rp3, rf) - sharpe_ex(b3, rf)
    g_e = d_e > 0
    print(f"[E] W3 Sharpe(0,8·6040+0,2·trend) {sharpe_ex(rp3, rf):+.2f} − Sharpe(6040) "
          f"{sharpe_ex(b3, rf):+.2f} = {d_e:+.3f}  => {pf(g_e)}")

    # ---------- verdict (mapping spec)
    print("\n" + "=" * 78)
    out = []
    if g_a and g_c and g_d and g_e:
        out.append("CONFIRMÉ : déploiement inchangé")
    if not g_a:
        out.append("RÉVISER LE LEVIER (cible L = 1)")
    if not g_c:
        out.append(f"RÉVISER L* À LA BAISSE (L*_W3 = {l_star(rp, rf, 'W3')})")
    if not (g_d and g_e):
        out.append("TREND DÉGRADÉ (sleeve = assurance, attente trend 0)")
    if not g_b:
        out.append(f"caveat stagflation : levier {inc_b*100:+.2f} pt/an sur 1966-81")
    if not g_r:
        if dd_r1 <= RUIN_DD:
            out.append(f"caveat ruine : règle −35 % = propriété de 2006-26 (L=1 aussi à "
                       f"{dd_r1*100:.0f}%) → DD de planification = {dd_r*100:.0f}%")
        else:
            out.append(f"levier crée la ruine sur W1 → L*_W1 = {l_star(rp, rf, 'W1')}")
    print("VERDICT : " + " | ".join(out))
    print(f"  gates : G0={pf(g0)} A={pf(g_a)} B={pf(g_b)} C={pf(g_c)} R={pf(g_r)} D={pf(g_d)} E={pf(g_e)}")

    # ---------- diagnostics
    print("\n" + "=" * 78 + "\nDIAGNOSTICS (non-gating)")
    for key in ("W1", "W2", "W3"):
        print(f"  broker RF+1,5 % {key} : incrément CAGR(1,5) = "
              f"{incr(rp, rf, key, spread=SPREAD_BROKER)*100:+.2f} pt/an")

    print("\n  Épisodes (L=1 / L=1,5 nominal ; L=1,5 réel ; maxDD L=1,5 dans l'épisode)")
    r1_all, r15_all = lever(rp, rf, 1.0), lever(rp, rf, L_DEPLOY)
    for lab, a0, b0 in EPISODES:
        e1, e15 = span(r1_all, a0, b0), span(r15_all, a0, b0)
        real = (1 + e15) / (1 + infl.reindex(e15.index)) - 1
        print(f"    {lab:22s} {((1+e1).prod()-1)*100:+7.1f}% / {((1+e15).prod()-1)*100:+7.1f}%   "
              f"réel {((1+real).prod()-1)*100:+7.1f}%   DD {maxdd(e15)*100:+6.1f}%")

    full = span(rp, "1926-07", "2026-02")
    l1 = np.log1p(lever(full, rf, 1.0)).rolling(180).sum()
    l15 = np.log1p(lever(full, rf, L_DEPLOY)).rolling(180).sum()
    d15 = (np.exp(l15 * 12 / 180) - np.exp(l1 * 12 / 180)).dropna()
    print(f"\n  Glissant 15 ans (W1 ∪ W0, {len(d15)} fenêtres) : CAGR(1,5) < CAGR(1) dans "
          f"{(d15 < 0).mean()*100:.1f}% ; < +1 pt dans {(d15 < 0.01).mean()*100:.1f}% ; "
          f"médiane {d15.median()*100:+.2f} pt ; pire {d15.min()*100:+.2f} pt (fin {d15.idxmin()})")

    print("\n  Sous-facteurs AQR (brut, W4) :")
    for c in aqr.columns:
        s = win(aqr[c].dropna(), "W4")
        print(f"    {c:9s} Sharpe {s.mean()/s.std()*ANN:+.2f}  t {t_mean(s):+.2f}  "
              f"vol {s.std()*ANN*100:5.1f}%")
    print(f"    sleeve brut (k·TSMOM, sans haircut) t W4 = {t_mean(win(k*aqr['TSMOM'], 'W4')):+.2f}")

    tr_aqr = win(x_net, "W0")
    tr22 = (S["trend"] - rf.reindex(S.index)).reindex(tr_aqr.index).dropna()
    print(f"\n  corr(sleeve AQR, trend #22) W0 = {tr_aqr.reindex(tr22.index).corr(tr22):+.3f}")
    dbmf = load_dbmf()
    if len(dbmf):
        ix = x_net.index.intersection(dbmf.index)
        print(f"  corr(sleeve AQR, DBMF) {ix.min()} → {ix.max()} ({len(ix)} m) = "
              f"{x_net.reindex(ix).corr(dbmf.reindex(ix)):+.3f}")

    tb = load_tbill_monthly()
    w0 = win(rf, "W0")
    print(f"\n  RF Ken French W0 = {w0.mean()*1200:.2f}%/an vs TB3MS {tb.reindex(w0.index).mean()*100:.2f}%/an")

    rp34 = (W_6040 * S["base6040"] + W_TREND * S["trend"]).dropna()
    tbm = tb.reindex(rp34.index).ffill() / 12
    for L in (1.0, L_DEPLOY):
        r34 = L * rp34 - (L - 1) * (tbm + SPREAD_FUT / 12)
        print(f"  #34 L={L:.1f} : Sharpe total (audit, méthode #34) {audit.sharpe(list(r34))*ANN:+.2f} "
              f"vs Sharpe excès {sharpe_ex(r34, tbm):+.2f}")
    r34_15 = L_DEPLOY * rp34 - (L_DEPLOY - 1) * (tbm + SPREAD_FUT / 12)
    px15 = win(lever(rp, rf, L_DEPLOY), "W0").reindex(r34_15.index).dropna()
    print(f"  corr(deliverable proxy L=1,5, deliverable #34) W0 = {px15.corr(r34_15.reindex(px15.index)):+.3f} ; "
          f"CAGR {cagr(px15)*100:+.2f}% vs {cagr(r34_15.reindex(px15.index))*100:+.2f}%")

    rp_flat = (W_6040 * p6040 + W_TREND * rf.reindex(p6040.index)).dropna()
    print(f"\n  W3 trend = RF (sans AQR) : incrément {incr(rp_flat, rf, 'W3')*100:+.2f} pt/an vs "
          f"{incr(rp, rf, 'W3')*100:+.2f} avec AQR ; maxDD(1,5) "
          f"{maxdd(win(lever(rp_flat, rf, L_DEPLOY), 'W3'))*100:+.1f}% vs {dd_c*100:+.1f}%")

    # ---------- post-hoc : NON pré-enregistré, ne change aucun gate ----------
    print("\n" + "=" * 78 + "\nPOST-HOC (non pré-enregistré — ne change aucun gate)")
    # 1. corr oblig/IEF = 0,72 : les taux FRED mensuels sont des MOYENNES du mois. Contrôle avec
    #    le taux de fin de mois (DGS10 quotidien, 1962+ → couvre W2 et W0).
    y_eom = load_fred("DGS10", "fred_dgs10.csv").groupby(level=0).last() / 100
    bond_eom = par_bond_returns(y_eom)
    ix = win(bond_eom, "W0").index.intersection(etf.index)
    print(f"  oblig. taux fin de mois : corr IEF W0 = {bond_eom.reindex(ix).corr(etf['IEF'].reindex(ix)):+.3f} "
          f"(moyenne mensuelle : {bond.reindex(ix).corr(etf['IEF'].reindex(ix)):+.3f})")
    p6040_e = (0.6 * ff["mkt"] + 0.4 * bond_eom.reindex(ff.index)).dropna()
    rp_e = (W_6040 * p6040_e + W_TREND * trend.reindex(p6040_e.index)).dropna()
    b0 = S["base6040"].reindex(win(p6040_e, "W0").index).dropna()
    print(f"  G0 fin de mois : corr(6040, #22) = {win(p6040_e, 'W0').reindex(b0.index).corr(b0):+.3f}")
    print(f"  B fin de mois : W2 incrément {incr(rp_e, rf, 'W2')*100:+.2f} pt/an (moyenne : {inc_b*100:+.2f}) ; "
          f"maxDD W2 L=1,5 {maxdd(win(lever(rp_e, rf, L_DEPLOY), 'W2'))*100:+.1f}%")
    w2 = win(rf, "W2")
    for L in (1.0, L_DEPLOY):
        r = win(lever(rp, rf, L), "W2")
        real = (1 + r) / (1 + infl.reindex(r.index)) - 1
        print(f"  W2 L={L:.1f} : CAGR {cagr(r)*100:+.2f}% vs cash {cagr(w2)*100:+.2f}% ; "
              f"réel {cagr(real)*100:+.2f}%/an")
    # 2. DD de planification hors 1929 (après-guerre), nominal et réel
    for a0 in ("1945-01", "1950-01"):
        for L in (1.0, L_DEPLOY):
            r = span(lever(rp, rf, L), a0, "2026-02")
            real = (1 + r) / (1 + infl.reindex(r.index)) - 1
            eq = (1 + r).cumprod()
            dd = eq / eq.cummax() - 1
            print(f"  maxDD {a0} → 2026-02 L={L:.1f} : nominal {dd.min()*100:+.1f}% (creux {dd.idxmin()}) ; "
                  f"réel {maxdd(real)*100:+.1f}%")
    # 3. décroissance du trend : différence IS/OOS testée (critique 2), pas deux t lus séparément
    xa, xb = win(x_net, "W3"), span(x_net, "2006-04", str(aqr.index.max()))
    se = math.sqrt(xa.var() / len(xa) + xb.var() / len(xb))
    print(f"  trend net : {xa.mean()*1200:+.2f}%/an (W3) vs {xb.mean()*1200:+.2f}%/an (2006-04 →) ; "
          f"Welch t différence = {(xa.mean() - xb.mean()) / se:+.2f}")
    for a0, b0_ in (("2006-04", "2015-12"), ("2016-01", str(aqr.index.max()))):
        s = span(x_net, a0, b0_)
        print(f"    {a0} → {b0_} : Sharpe net {s.mean()/s.std()*ANN:+.2f} ({len(s)} m)")
    print("=" * 78)


if __name__ == "__main__":
    main()

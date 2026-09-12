"""Étude #41 — l'or dans le cœur du deliverable, contre la stagflation (docs/SPEC-gold.md, 463fdd4).

P0 = deliverable déployé (proxy #37, levier 1,5), Pg = (1−g)·P0 + g·or, Pc = (1−g)·P0 + g·RF.
Or = Banque mondiale (Pink Sheet, moyenne mensuelle), moins 0,25 %/an de frais d'ETC.
Obligation 10 ans reconstruite sur le DGS10 de fin de mois (post-hoc #37). Rien n'est optimisé ici.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import sleeves
from run_lever import maxdd
from run_secular import (ANN, HAIRCUT, L_DEPLOY, W_6040, W_TREND, _fetch, cagr, load_aqr, load_ff, load_fred,
                         lever, monthly_px_returns, par_bond_returns, sharpe_ex, span)

G = 0.10
G_DIAG = (0.05, 0.15, 0.20)
FEE_GOLD = 0.0025
HURDLE_A, HURDLE_B = 0.010, -0.0075
INFL_S = 0.05
EPISODES = [("1973-74", "1973-01", "1974-12"), ("1979-80", "1979-01", "1980-12"),
            ("krach or 1980-82", "1980-02", "1982-06"), ("oct. 1987", "1987-10", "1987-10"),
            ("2000-02", "2000-01", "2002-12"), ("2008", "2008-01", "2008-12"), ("2013", "2013-01", "2013-12"),
            ("2020", "2020-01", "2020-12"), ("2022", "2022-01", "2022-12")]


URL_WB = ("https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/"
          "CMO-Historical-Data-Monthly.xlsx")      # version 2026-09-02 (l'URL 2025 était gelée à 2024-12)
URL_DATAHUB = "https://raw.githubusercontent.com/datasets/gold-prices/main/data/monthly.csv"


def load_gold_wb() -> pd.Series:
    raw = pd.read_excel(_fetch("wb_cmo_monthly.xlsx", URL_WB), sheet_name="Monthly Prices", header=None)
    hdr = next(i for i in range(12) if "Gold" in [str(v).strip() for v in raw.iloc[i]])
    col = [str(v).strip() for v in raw.iloc[hdr]].index("Gold")
    d = raw.iloc[hdr + 1:, [0, col]].dropna()
    d = d[d.iloc[:, 0].astype(str).str.match(r"^\d{4}M\d{2}$")]
    idx = pd.PeriodIndex([pd.Period(f"{s[:4]}-{s[5:]}", "M") for s in d.iloc[:, 0].astype(str)])
    return pd.Series(pd.to_numeric(d.iloc[:, 1], errors="coerce").values, index=idx).dropna()


def load_gold_datahub() -> pd.Series:
    d = pd.read_csv(_fetch("gold_datahub.csv", URL_DATAHUB))
    return pd.Series(d.Price.values, index=pd.PeriodIndex(d.Date, freq="M"))


def cut(s: pd.Series, a: str, b: str | None) -> pd.Series:
    return s[(s.index >= pd.Period(a, "M")) & ((s.index <= pd.Period(b, "M")) if b else True)]


def real(r: pd.Series, infl: pd.Series) -> pd.Series:
    return ((1 + r) / (1 + infl.reindex(r.index)) - 1).dropna()


def pf(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def main() -> None:
    ff = load_ff()
    rf = ff["rf"]
    aqr = load_aqr()
    cpi = load_fred("CPIAUCNS", "fred_cpi.csv")
    infl = cpi.pct_change().dropna()
    infl12 = cpi.pct_change(12).dropna()
    y_eom = load_fred("DGS10", "fred_dgs10.csv").groupby(level=0).last() / 100
    bond = par_bond_returns(y_eom)
    p6040 = (0.6 * ff["mkt"] + 0.4 * bond.reindex(ff.index)).dropna()
    S22 = sleeves.load_sleeves()
    k = float(S22["trend"][(S22.index >= pd.Period("2006-04", "M")) &
                           (S22.index <= pd.Period("2026-02", "M"))].std()) / float(aqr["TSMOM"].std())
    x_net = (k * aqr["TSMOM"] - HAIRCUT / 12).dropna()
    trend = rf.reindex(p6040.index).copy()
    trend.loc[x_net.index.intersection(trend.index)] += x_net
    rp = (W_6040 * p6040 + W_TREND * trend).dropna()
    P0 = lever(rp, rf, L_DEPLOY)

    gold_px = load_gold_wb()
    gold = (gold_px.pct_change() - FEE_GOLD / 12).dropna()
    end = min(P0.index.max(), gold.index.max(), rf.index.max())
    WG, W2g, WP = ("1968-04", str(end)), ("1968-04", "1981-12"), ("1982-01", str(end))

    def mix(g: float, other: pd.Series) -> pd.Series:
        ix = P0.index.intersection(other.index)
        return ((1 - g) * P0.reindex(ix) + g * other.reindex(ix)).dropna()

    print("=" * 78)
    print(f"#41 — or dans le cœur | or Banque mondiale {gold_px.index.min()} → {gold_px.index.max()} | "
          f"P0 {P0.index.min()} → {P0.index.max()} | fin commune {end}")

    # ---------- G0
    gld = monthly_px_returns(["GLD"])["GLD"]
    ix = gold.index.intersection(gld.index)
    ix = ix[ix >= pd.Period("2004-12", "M")]
    a, b = gold.reindex(ix) + FEE_GOLD / 12, gld.reindex(ix)       # prix brut vs GLD (TER inclus)
    ra = np.log1p(a).rolling(12).sum().dropna(); rb = np.log1p(b).rolling(12).sum().reindex(ra.index)
    c12, cm = float(ra.corr(rb)), float(a.corr(b))
    dcg = cagr(a) - cagr(b)
    g0 = c12 >= 0.95 and abs(dcg) <= 0.010
    print("\nG0 — FIDÉLITÉ (or BM vs GLD)")
    print(f"  {ix.min()} → {ix.max()} ({len(ix)} m) : corr 12 m glissants {c12:+.3f} ; corr mensuelle {cm:+.3f} "
          f"(diag) ; CAGR BM {cagr(a)*100:+.2f}% vs GLD {cagr(b)*100:+.2f}% (écart {dcg*100:+.2f} pt)  => {pf(g0)}")
    if not g0:
        print("\nVERDICT : UNTESTABLE (série or non fidèle, aucun autre gate lu)")
        return

    Pg, Pc = mix(G, gold), mix(G, rf)

    # ---------- gates
    print("\n" + "=" * 78 + "\nGATES (g = 10 %)")
    rA = cagr(real(cut(Pg, *W2g), infl)) - cagr(real(cut(P0, *W2g), infl))
    gA = rA >= HURDLE_A
    print(f"[A] W2g {W2g[0]} → {W2g[1]} réel : CAGR Pg {cagr(real(cut(Pg, *W2g), infl))*100:+.2f}% − P0 "
          f"{cagr(real(cut(P0, *W2g), infl))*100:+.2f}% = {rA*100:+.2f} pt/an (≥ +1,00)  => {pf(gA)}")
    rB = cagr(cut(Pg, *WP)) - cagr(cut(P0, *WP))
    gB = rB >= HURDLE_B
    print(f"[B] WP {WP[0]} → {WP[1]} : CAGR Pg {cagr(cut(Pg, *WP))*100:+.2f}% − P0 {cagr(cut(P0, *WP))*100:+.2f}% "
          f"= {rB*100:+.2f} pt/an (≥ −0,75)  => {pf(gB)}")
    Sm = infl12[(infl12 > INFL_S) & (infl12.index >= pd.Period(WP[0], "M")) & (infl12.index <= end)].index
    dC = (Pg.reindex(Sm) - Pc.reindex(Sm)).dropna()
    gC = dC.sum() > 0
    print(f"[C] S = {len(dC)} mois (inflation 12 m > 5 %, ≥ 1982) : Σ(Pg − Pc) = {dC.sum()*100:+.2f} pts  => {pf(gC)}")
    sg, sc = sharpe_ex(cut(Pg, *WP), rf), sharpe_ex(cut(Pc, *WP), rf)
    gD = sg > sc
    print(f"[D] WP Sharpe excès Pg {sg:+.3f} vs Pc {sc:+.3f} (P0 {sharpe_ex(cut(P0, *WP), rf):+.3f})  => {pf(gD)}")

    if not gA:
        v = "KILL (même en 1970s, l'or ne protège pas)"
    elif not gB:
        v = "TROP CHER (non ajouté, caveat stagflation reste)"
    elif not (gC and gD):
        v = "ASSURANCE 1970s SEULEMENT (non ajouté, caveat stagflation reste)"
    else:
        v = "AJOUTER (72 WTEF / 18 DBMFE / 10 or)"
    print("\n" + "=" * 78 + f"\nVERDICT : {v}\n  gates : G0={pf(g0)} A={pf(gA)} B={pf(gB)} C={pf(gC)} D={pf(gD)}")

    # ---------- diagnostics
    print("\n" + "=" * 78 + "\nDIAGNOSTICS (non-gating)")
    print(f"  {'g':>5} {'A réel W2g':>11} {'B WP':>8} {'C Σ S':>8} {'Sh Pg':>7} {'Sh Pc':>7}")
    for g in (G,) + G_DIAG:
        pg, pc = mix(g, gold), mix(g, rf)
        print(f"  {g*100:4.0f}% {(cagr(real(cut(pg, *W2g), infl)) - cagr(real(cut(P0, *W2g), infl)))*100:+10.2f} "
              f"{(cagr(cut(pg, *WP)) - cagr(cut(P0, *WP)))*100:+7.2f} "
              f"{(pg.reindex(Sm) - pc.reindex(Sm)).sum()*100:+7.2f} "
              f"{sharpe_ex(cut(pg, *WP), rf):+7.3f} {sharpe_ex(cut(pc, *WP), rf):+7.3f}")
    for a0, b0, lab in (("1982-01", "2001-12", "marché baissier de l'or"), ("2002-01", str(end), "2002 → fin"),
                        ("1982-01", "2023-12", "WP sans 2024-26")):
        d = cagr(cut(Pg, a0, b0)) - cagr(cut(P0, a0, b0))
        print(f"  B sur {a0} → {b0} ({lab}) : {d*100:+.2f} pt/an ; Sharpe Pg {sharpe_ex(cut(Pg, a0, b0), rf):+.3f}"
              f" vs Pc {sharpe_ex(cut(Pc, a0, b0), rf):+.3f}")
    print("\n  Épisodes (P0 / Pg / Pc nominal ; P0 / Pg réel)")
    for lab, a0, b0 in EPISODES:
        e = [span(x, a0, b0) for x in (P0, Pg, Pc)]
        n = [((1 + x).prod() - 1) * 100 for x in e]
        rr = [((1 + real(x, infl)).prod() - 1) * 100 for x in e[:2]]
        print(f"    {lab:18s} {n[0]:+7.1f}% / {n[1]:+7.1f}% / {n[2]:+7.1f}%   réel {rr[0]:+7.1f}% / {rr[1]:+7.1f}%")
    for lab, x in (("P0", P0), ("Pg", Pg), ("Pc", Pc)):
        print(f"  maxDD WG {lab} : nominal {maxdd(cut(x, *WG))*100:+.1f}% ; réel {maxdd(real(cut(x, *WG), infl))*100:+.1f}%")
    lg = np.log1p(cut(Pg, *WG)).rolling(180).sum(); l0 = np.log1p(cut(P0, *WG)).rolling(180).sum()
    dd = (lg - l0).dropna()
    print(f"  glissant 15 ans ({len(dd)} fenêtres) : Pg > P0 dans {(dd > 0).mean()*100:.1f}% ; "
          f"pire {np.expm1(dd.min()/15)*100:+.2f} pt/an (fin {dd.idxmin()})")
    blocks = pd.Series(Sm.year, index=Sm).groupby(lambda p: p.year // 1).size()
    print(f"  mois de S par année : {blocks.to_dict()}")
    for a0, b0 in (("1982-01", "1983-12"), ("1984-01", "1992-12"), ("2021-01", "2023-12")):
        s = dC[(dC.index >= pd.Period(a0, "M")) & (dC.index <= pd.Period(b0, "M"))]
        print(f"    S ∩ {a0} → {b0} : {len(s)} mois, Σ(Pg − Pc) {s.sum()*100:+.2f} pts")
    for a0, b0 in (WG, W2g, WP):
        g_ = cut(gold, a0, b0)
        print(f"  or seul {a0} → {b0} : CAGR {cagr(g_)*100:+.2f}% (réel {cagr(real(g_, infl))*100:+.2f}%) ; "
              f"Sharpe excès {sharpe_ex(g_, rf):+.2f} ; corr P0 {g_.corr(P0.reindex(g_.index)):+.2f}")
    dh = load_gold_datahub().pct_change().dropna()
    ixd = gold.index.intersection(dh.index)
    print(f"  cohérence datahub {ixd.min()} → {ixd.max()} : corr mensuelle {(gold + FEE_GOLD/12).reindex(ixd).corr(dh.reindex(ixd)):+.3f}")
    print("=" * 78)


if __name__ == "__main__":
    main()

"""Contrôle de déploiement du deliverable (#22 levé 1,5× constant, #34) — DESCRIPTIF.

Pas une étude : aucun edge testé, aucun gate, aucun verdict. Vérifie que les véhicules
achetables reproduisent les sleeves backtestées, et chiffre le deliverable en EUR.
  1. NTSX (US, 90 % actions + 60 % futures Treasury = 1,5× un 60/40) vs 1,5×base6040 financé
  2. DBMF (US, réplication CTA) vs sleeve trend
  3. portefeuille implémentable 80 NTSX / 20 DBMF vs deliverable (fenêtre commune)
  4. clones UCITS (WTEF.DE, DBMFE.PA) vs versions US sur leur historique court
  5. deliverable vu d'un investisseur EUR non couvert, 2006-04→
Poids 80/20 fixés par arithmétique AVANT run : 1,5×0,80 = 1,2×base6040 = 0,80 NTSX ; le reste
du capital en DBMF. Pas d'ajustement sur la fenêtre commune.
"""
from __future__ import annotations

import math
import os

import numpy as np
import pandas as pd

import sleeves
from run_lever import WEIGHTS, SPREAD_FUT, load_tbill_monthly, maxdd, ann_ret, ann_sharpe, year_ret

L = 1.5
W_CORE = 0.80
W_TREND = 0.20
ANN = math.sqrt(12)
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data", "deploy_px.csv")
TICKERS = ["NTSX", "DBMF", "EURUSD=X", "SPY", "WTEF.DE", "DBMFE.PA"]


def load_px() -> pd.DataFrame:
    if os.path.exists(CACHE):
        return pd.read_csv(CACHE, index_col=0, parse_dates=True)
    import yfinance as yf
    px = yf.download(TICKERS, start="2006-01-01", auto_adjust=True, progress=False)["Close"]
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    px.to_csv(CACHE)
    return px


def monthly(s: pd.Series) -> pd.Series:
    """Rendements mensuels Period[M], mois courant (incomplet) exclu."""
    m = s.dropna().resample("ME").last().pct_change().dropna()
    m.index = m.index.to_period("M")
    return m[m.index < pd.Timestamp.today().to_period("M")]


def stats(r: pd.Series) -> str:
    return (f"ann {ann_ret(r)*100:+6.2f}%  vol {r.std()*ANN*100:4.1f}%  "
            f"Sh {ann_sharpe(r):+.2f}  DD {maxdd(r)*100:+5.1f}%")


def track(name: str, y: pd.Series, x: pd.Series) -> pd.DataFrame:
    d = pd.concat([y, x], axis=1, keys=["y", "x"]).dropna()
    beta = np.cov(d.y, d.x)[0, 1] / d.x.var()
    diff = d.y - d.x
    print(f"\n  {name} — {d.index.min()}→{d.index.max()} ({len(d)} mois)")
    print(f"    corr {d.y.corr(d.x):+.2f}  β {beta:.2f}  TE {diff.std()*ANN*100:.1f}%/an  "
          f"écart moyen {diff.mean()*12*100:+.2f}%/an")
    print(f"    véhicule : {stats(d.y)}")
    print(f"    backtest : {stats(d.x)}")
    return d


def main() -> None:
    S = sleeves.load_sleeves()
    tb = load_tbill_monthly()
    fin = (tb.reindex(S.index).ffill() + SPREAD_FUT) / 12
    rp = sum(S[c] * w for c, w in WEIGHTS.items())
    deliv = L * rp - (L - 1) * fin
    core_bt = L * S["base6040"] - (L - 1) * fin

    px = load_px()
    m = {t: monthly(px[t]) for t in px.columns if px[t].notna().sum() > 40}
    print("=" * 76)
    print("Contrôle de déploiement — descriptif, non-gating")
    print("  historiques dispo : " + "  ".join(f"{t} {m[t].index.min()}" for t in m))

    print("\n" + "=" * 76 + "\n1-2. Véhicules US vs sleeves backtestées")
    track("NTSX vs 1,5×60/40 financé T3M+0,40 %", m["NTSX"], core_bt)
    d = track("DBMF vs sleeve trend", m["DBMF"], S["trend"])
    w_vm = 0.30 * d.x.std() / d.y.std()
    print(f"    exposition trend du deliverable = 1,5×0,20 = 0,30 sleeve ; à vol égale ≈ {w_vm:.2f} DBMF "
          f"(vol DBMF {d.y.std()*ANN*100:.1f}% vs sleeve {d.x.std()*ANN*100:.1f}%)")

    print("\n" + "=" * 76 + f"\n3. Implémentable {W_CORE:.0%} NTSX / {W_TREND:.0%} DBMF (rebal mensuel) vs deliverable")
    imp = W_CORE * m["NTSX"] + W_TREND * m["DBMF"]
    d = track("80/20 vs deliverable #34", imp, deliv)
    for y in range(2019, 2027):
        a, b = year_ret(d.y, y), year_ret(d.x, y)
        if a == a:
            print(f"    {y} : implémentable {a*100:+6.1f}%   deliverable {b*100:+6.1f}%")

    print("\n" + "=" * 76 + "\n4. Clones UCITS vs US (historique court)")
    usd_eur = monthly(1.0 / px["EURUSD=X"])
    ntsx_eur = (1 + m["NTSX"]) * (1 + usd_eur) - 1
    dbmf_eur = (1 + m["DBMF"]) * (1 + usd_eur) - 1
    for u, ref, lab in (("WTEF.DE", ntsx_eur, "WTEF (EUR, non couvert) vs NTSX converti EUR"),
                        ("DBMFE.PA", dbmf_eur, "DBMFE (EUR, non couvert) vs DBMF converti EUR")):
        if u in m:
            x = pd.concat([m[u], ref], axis=1, keys=["u", "r"]).dropna()
            print(f"  {lab} : {x.index.min()}→{x.index.max()} ({len(x)} m) corr {x.u.corr(x.r):+.2f}  "
                  f"TE {(x.u-x.r).std()*ANN*100:.1f}%/an  écart {(x.u-x.r).mean()*12*100:+.2f}%/an")
        else:
            print(f"  {u} : pas de données yfinance")

    print("\n" + "=" * 76 + "\n5. Deliverable vu en EUR (non couvert)")
    de = pd.concat([deliv, usd_eur], axis=1, keys=["r", "fx"]).dropna()
    r_eur = (1 + de.r) * (1 + de.fx) - 1
    print(f"  USD : {stats(de.r)}")
    print(f"  EUR : {stats(r_eur)}   corr(r_USD, USD/EUR) {de.r.corr(de.fx):+.2f}")
    for y in (2008, 2020, 2022):
        print(f"    {y} : USD {year_ret(de.r, y)*100:+6.1f}%   EUR {year_ret(r_eur, y)*100:+6.1f}%")

    spy = px["SPY"].dropna()
    print(f"\n  MES ≈ 5 $ × S&P ≈ 5 × 10 × SPY({spy.index[-1].date()}) = {5*10*spy.iloc[-1]:,.0f} $ de notionnel")
    print("=" * 76)


if __name__ == "__main__":
    main()

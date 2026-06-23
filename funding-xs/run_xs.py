"""Piste 11 — funding cross-sectionnel dollar-neutral. Gates A-E pré-enregistrés (docs/SPEC.md).

Long le tercile au funding le plus NÉGATIF (payé pour être long), short le tercile au funding le plus
POSITIF (payé pour être short), rebal 8h. On collecte le spread de funding ; le spread de prix est le
risque. Réutilise l'infra carry/ (data_funding, data_prices, audit)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_CARRY = (Path(__file__).resolve().parent.parent / "carry")
sys.path.insert(0, str(_CARRY))
import data_funding  # noqa: E402
import data_prices   # noqa: E402
from audit import sharpe, tstat  # noqa: E402

UNIVERS = ["BTC", "ETH", "BNB", "XRP", "ADA", "DOGE", "LTC", "BCH", "EOS",
           "TRX", "ETC", "LINK", "XLM", "XTZ", "NEO", "ATOM", "VET", "ZEC"]
MIN_PRESENT = 9          # nb minimum de symboles présents pour former des terciles
COST_PER_TURN = 0.0005   # 5 bps par unité de book tournée (pré-enregistré)
PERIODS_Y = 365 * 3      # 3 fundings/jour
REGIMES = {
    "bull 2020-21": ("2020-01-01", "2021-12-31"),
    "bear 2022":    ("2022-01-01", "2022-12-31"),
    "range 23-25":  ("2023-01-01", "2026-12-31"),
}


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    """F = funding 8h (cols=symboles), R = rendement prix close-to-close 8h, alignés."""
    f_cols, r_cols = {}, {}
    for s in UNIVERS:
        sym = f"{s}USDT"
        try:
            f = data_funding.funding(sym)["fundingRate"]
            px = data_prices.perp_8h(sym)["close"]
        except Exception as e:  # symbole jamais listé / erreur réseau
            print(f"  SKIP {sym}: {e}")
            continue
        # funding indexé à des stamps 8h ; on aligne le rendement prix sur ces mêmes stamps.
        f = f[~f.index.duplicated()].sort_index()
        px = px[~px.index.duplicated()].sort_index()
        # rendement prix sur l'intervalle se TERMINANT à chaque stamp (close-to-close)
        r = px.pct_change()
        # ré-échantillonne le prix sur l'index funding (au plus proche <=, tolérance 4h)
        r_on_f = r.reindex(f.index, method="nearest", tolerance=pd.Timedelta("4h"))
        f_cols[s], r_cols[s] = f, r_on_f
    F = pd.DataFrame(f_cols).sort_index()
    R = pd.DataFrame(r_cols).sort_index()
    common = F.index.intersection(R.index)
    return F.loc[common], R.loc[common]


def backtest(F: pd.DataFrame, R: pd.DataFrame):
    """Construit les poids dollar-neutres à chaque t, renvoie séries de P&L décomposées + poids."""
    idx = F.index
    rows = []
    weights = pd.DataFrame(0.0, index=idx, columns=F.columns)
    for t in idx:
        f_t = F.loc[t].dropna()                       # funding connu à t = signal
        present = f_t.index
        if len(present) < MIN_PRESENT:
            continue
        k = len(present) // 3
        if k < 1:
            continue
        ranked = f_t.sort_values()
        longs = ranked.index[:k]                       # funding le plus négatif
        shorts = ranked.index[-k:]                      # funding le plus positif
        w = pd.Series(0.0, index=F.columns)
        w[longs] = 1.0 / k
        w[shorts] = -1.0 / k
        weights.loc[t] = w
    # PnL réalisé sur (t, t+8h] : prix et funding STAMPÉS à t+8h (shift -1), évite le look-ahead
    r_next = R.shift(-1)
    f_next = F.shift(-1)
    rec = []
    for t in idx:
        w = weights.loc[t]
        if (w == 0).all():
            continue
        longs = w[w > 0].index
        shorts = w[w < 0].index
        rn, fn = r_next.loc[t], f_next.loc[t]
        # contribution par symbole : long => r - f ; short => -(r - f) = f - r
        contrib = pd.Series(0.0, index=F.columns)
        wl = 1.0 / len(longs)
        ws = 1.0 / len(shorts)
        contrib[longs] = wl * (rn[longs] - fn[longs])
        contrib[shorts] = ws * (fn[shorts] - rn[shorts])
        contrib = contrib.fillna(0.0)
        price_spread = wl * rn[longs].mean() - ws * rn[shorts].mean()
        fund_spread = ws * fn[shorts].mean() - wl * fn[longs].mean()
        long_leg = wl * (rn[longs] - fn[longs]).mean()       # PnL standalone jambe longue
        short_leg = ws * (fn[shorts] - rn[shorts]).mean()    # PnL standalone jambe short
        rec.append({
            "t": t,
            "gross": contrib.sum(),
            "price_spread": price_spread,
            "fund_spread": fund_spread,
            "long_leg": long_leg,
            "short_leg": short_leg,
            "btc_ret": rn.get("BTC", np.nan),
            **{f"c_{s}": contrib[s] for s in F.columns},
        })
    out = pd.DataFrame(rec).set_index("t").dropna(subset=["gross"])
    # turnover : rotation du book entre rebalancements successifs (sur les t actifs)
    active_w = weights.loc[out.index]
    dturn = active_w.diff().abs().sum(axis=1).fillna(active_w.iloc[0].abs().sum())
    out["turnover"] = dturn
    out["cost"] = dturn * COST_PER_TURN
    out["net"] = out["gross"] - out["cost"]
    return out, weights


def ann(series: pd.Series) -> float:
    return float(series.mean() * PERIODS_Y)


def report(out: pd.DataFrame, weights: pd.DataFrame):
    g = out["gross"].tolist()
    n = out["net"].tolist()
    print("\n" + "=" * 64)
    print(f"PISTE 11 — funding cross-sectionnel  | n périodes 8h = {len(out)}")
    print(f"  fenêtre : {out.index.min().date()} -> {out.index.max().date()}")
    print("=" * 64)

    # GATE A : dispersion paie (brut)
    print("\n[GATE A] dispersion paie  (PASS: brut>0 ET t>2)")
    print(f"  brut/8h    = {out['gross'].mean()*1e4:+.3f} bps   annualisé = {ann(out['gross'])*100:+.2f}%")
    print(f"  t-stat     = {tstat(g):+.2f}")
    print(f"  sharpe ann = {sharpe(g)*np.sqrt(PERIODS_Y):+.2f}")
    print(f"    dont spread FUNDING = {ann(out['fund_spread'])*100:+.2f}%/an (>0 par construction)")
    print(f"    dont spread PRIX    = {ann(out['price_spread'])*100:+.2f}%/an (le risque)")
    a_pass = out["gross"].mean() > 0 and tstat(g) > 2
    print(f"  => {'PASS' if a_pass else 'KILL'}")

    # GATE B : net
    print("\n[GATE B] net après frais  (PASS: net>0)")
    print(f"  turnover moyen/8h = {out['turnover'].mean():.3f} (book gross=2)")
    print(f"  coût/8h           = {out['cost'].mean()*1e4:.3f} bps")
    print(f"  NET annualisé     = {ann(out['net'])*100:+.2f}%   t={tstat(n):+.2f}")
    b_pass = out["net"].mean() > 0 and tstat(n) > 2
    print(f"  => {'PASS' if b_pass else 'KILL'}")

    # GATE C : market-neutral
    print("\n[GATE C] market-neutral  (PASS: corr≈0 BTC ET long>0 ET short>0)")
    corr = float(np.corrcoef(out["gross"], out["btc_ret"].fillna(0))[0, 1])
    print(f"  corr(brut, BTC)   = {corr:+.3f}")
    print(f"  jambe LONG  /an   = {ann(out['long_leg'])*100:+.2f}%")
    print(f"  jambe SHORT /an   = {ann(out['short_leg'])*100:+.2f}%")
    c_pass = abs(corr) < 0.2 and out["long_leg"].mean() > 0 and out["short_leg"].mean() > 0
    print(f"  => {'PASS' if c_pass else 'KILL'}")

    # GATE D : drop-top (capacité fantôme)
    print("\n[GATE D] drop-top  (PASS: retirer top-2 contributeurs => survit net>0)")
    contrib_cols = [c for c in out.columns if c.startswith("c_")]
    totals = out[contrib_cols].sum().sort_values(ascending=False)
    top2 = [c[2:] for c in totals.index[:2]]
    print(f"  top-2 contributeurs P&L : {top2}  (parts brut: {totals.iloc[0]/out['gross'].sum():.1%}, {totals.iloc[1]/out['gross'].sum():.1%})")
    drop_cols = [f"c_{s}" for s in top2]
    gross_excl = out["gross"] - out[drop_cols].sum(axis=1)
    net_excl = gross_excl - out["cost"]
    print(f"  net SANS top-2    = {ann(net_excl)*100:+.2f}%   t={tstat(net_excl.tolist()):+.2f}")
    d_pass = net_excl.mean() > 0 and tstat(net_excl.tolist()) > 2
    print(f"  => {'PASS' if d_pass else 'KILL'}")

    # GATE E : split régime
    print("\n[GATE E] split régime  (PASS: net>0 dans >=2/3 régimes)")
    n_pos = 0
    for name, (a, b) in REGIMES.items():
        seg = out.loc[(out.index >= a) & (out.index <= b), "net"]
        if len(seg) < 30:
            print(f"  {name:14s}: n={len(seg):5d}  (insuffisant)")
            continue
        pos = seg.mean() > 0
        n_pos += pos
        print(f"  {name:14s}: net/an={ann(seg)*100:+7.2f}%  t={tstat(seg.tolist()):+5.2f}  {'+' if pos else '-'}")
    e_pass = n_pos >= 2
    print(f"  => {'PASS' if e_pass else 'KILL'}")

    print("\n" + "=" * 64)
    gates = {"A": a_pass, "B": b_pass, "C": c_pass, "D": d_pass, "E": e_pass}
    verdict = "GO" if all(gates.values()) else "KILL"
    print(f"VERDICT : {verdict}   " + "  ".join(f"{k}={'P' if v else 'K'}" for k, v in gates.items()))
    print("=" * 64)


if __name__ == "__main__":
    print("Chargement univers funding + prix perp 8h...")
    F, R = load()
    print(f"\nPanel : {F.shape[1]} symboles, {len(F)} stamps 8h, "
          f"{F.index.min().date()} -> {F.index.max().date()}")
    out, weights = backtest(F, R)
    report(out, weights)

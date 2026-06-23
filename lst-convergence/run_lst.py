"""Piste 9 — LST convergence stETH/ETH. Gates A-E pré-enregistrés (docs/SPEC.md).

Buy-discount / hedge-ETH : entrée si discount < -1.5%, sortie à >= -0.25%. PnL hedgé = Delta log(ratio).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

import data_lst

ENTRY = -0.015        # seuil d'entrée pré-enregistré (discount < -1.5%)
EXIT = -0.0025        # sortie à >= -0.25%
RT_COST = 0.002       # swap Curve aller-retour ~20 bps (entrée+sortie), pré-enregistré
SHAPELLA = "2023-04-12"   # activation des retraits stETH->ETH


def half_life(x: pd.Series) -> float:
    x = x.dropna()
    lag = x.shift(1)
    d = (x - lag).dropna()
    lag = lag.loc[d.index]
    beta = np.polyfit(lag, d, 1)[0]
    return float(-np.log(2) / np.log(1 + beta)) if -1 < beta < 0 else float("inf")


def episodes(disc: pd.Series, entry=ENTRY, exit=EXIT) -> list[dict]:
    """Épisodes contigus : on entre quand disc<entry, on sort quand disc>=exit."""
    eps, in_pos, start, depth = [], False, None, 0.0
    for t, d in disc.items():
        if not in_pos and d < entry:
            in_pos, start, depth = True, t, d
        elif in_pos:
            depth = min(depth, d)
            if d >= exit:
                eps.append({"start": start, "end": t, "days": (t - start).days,
                            "depth": depth})
                in_pos = False
    if in_pos:
        eps.append({"start": start, "end": disc.index[-1],
                    "days": (disc.index[-1] - start).days, "depth": depth, "open": True})
    return eps


def strategy_returns(df: pd.DataFrame) -> pd.Series:
    """Rendement daily market-neutral (long stETH / short ETH) quand en position, sinon 0."""
    logr = np.log(df["ratio"])
    dlog = logr.diff()                  # PnL daily hedgé = variation du log-ratio
    disc = df["discount"]
    pos = pd.Series(0.0, index=df.index)
    in_pos = False
    for t in df.index:
        if not in_pos and disc[t] < ENTRY:
            in_pos = True
        elif in_pos and disc[t] >= EXIT:
            in_pos = False
        pos[t] = 1.0 if in_pos else 0.0
    # PnL du jour t = position tenue la veille * variation du ratio aujourd'hui
    return (pos.shift(1).fillna(0.0) * dlog).fillna(0.0), pos


def tstat(x):
    x = np.asarray(x, float)
    x = x[x != 0] if (x != 0).any() else x   # t-stat sur les jours déployés
    n = len(x)
    if n < 2 or x.std() == 0:
        return 0.0, n
    return float(x.mean() / x.std() * np.sqrt(n)), n


def main():
    df = data_lst.discount()
    disc = df["discount"]
    print("=" * 64)
    print(f"PISTE 9 — LST convergence stETH/ETH | {len(df)} jours "
          f"{df.index.min().date()} -> {df.index.max().date()}")
    print(f"  discount: min={disc.min():+.4f} max={disc.max():+.4f} "
          f"mean={disc.mean():+.4f} std={disc.std():.4f}")
    print("=" * 64)

    # GATE A : reconvergence + stationnarité
    print("\n[GATE A] reconvergence  (PASS: stationnaire ET half-life portable)")
    adf_p = adfuller(disc.dropna(), regression="c")[1]
    hl = half_life(disc)
    print(f"  ADF p={adf_p:.4f}  ({'stationnaire' if adf_p < 0.05 else 'I(1)'})")
    print(f"  half-life = {hl:.1f} jours")
    a_pass = adf_p < 0.05 and hl < 120
    print(f"  => {'PASS' if a_pass else 'KILL'}")

    # épisodes
    eps = episodes(disc)
    print(f"\n  épisodes (discount<{ENTRY:.1%} -> sortie {EXIT:.2%}) : {len(eps)}")
    for e in eps:
        tag = " [OUVERT]" if e.get("open") else ""
        print(f"    {e['start'].date()} -> {e['end'].date()}  "
              f"{e['days']:4d}j  creux={e['depth']:+.4f}{tag}")

    # GATE B : brut
    print("\n[GATE B] brut hedgé  (PASS: brut>0 ET t>2)")
    ret, pos = strategy_returns(df)
    deployed = ret[pos.shift(1).fillna(0) > 0]
    t_b, n_dep = tstat(ret.values)
    ann = ret[ret != 0].mean() * 365 if (ret != 0).any() else 0.0
    print(f"  jours déployés = {n_dep} / {len(df)}  ({n_dep/len(df):.1%} du temps)")
    print(f"  PnL total = {ret.sum()*100:+.2f}%   moyenne/jour-déployé = {deployed.mean()*1e4:+.1f} bps")
    print(f"  t-stat (jours déployés) = {t_b:+.2f}")
    b_pass = ret.sum() > 0 and t_b > 2
    print(f"  => {'PASS' if b_pass else 'KILL'}")

    # GATE C : net
    print("\n[GATE C] net après frais  (PASS: net>0)")
    n_trades = len([e for e in eps if not e.get("open")])
    cost = n_trades * RT_COST
    net = ret.sum() - cost
    print(f"  trades clos = {n_trades}  coût total = {cost*100:.2f}% ({RT_COST*100:.1f}%/trade aller-retour)")
    print(f"  NET = {net*100:+.2f}%")
    c_pass = net > 0
    print(f"  => {'PASS' if c_pass else 'KILL'}")

    # GATE D : tail break-even
    print("\n[GATE D] tail break-even  (PASS: break-even implique P(dépeg) élevée = pas priced-in)")
    max_disc = -disc.min()   # profondeur max (positive)
    for loss in (0.30, 0.50):
        p_be = max_disc / (max_disc + loss)
        print(f"  au creux {max_disc:.1%}, si perte permanente={loss:.0%} -> P_break-even = {p_be:.1%}")
    # heuristique : si la prime implique une proba de catastrophe "raisonnable" du marché, c'est priced-in
    p_be_mid = max_disc / (max_disc + 0.50)
    d_pass = p_be_mid > 0.25   # >25% de proba implicite = sur-réaction exploitable ; sinon priced-in
    print(f"  => {'PASS (sur-réaction)' if d_pass else 'KILL (priced-in plausible)'}")

    # GATE E : échantillon (nb d'épisodes de stress indépendants)
    print("\n[GATE E] échantillon  (PASS: >=2 épisodes de stress indépendants)")
    closed = [e for e in eps if not e.get("open")]
    pre_shap = [e for e in eps if e["start"] < pd.Timestamp(SHAPELLA)]
    post_shap = [e for e in eps if e["start"] >= pd.Timestamp(SHAPELLA)]
    print(f"  total épisodes={len(eps)}  pré-Shapella={len(pre_shap)}  post-Shapella={len(post_shap)}")
    print(f"  post-Shapella min discount = {disc[df.index >= SHAPELLA].min():+.4f}")
    e_pass = len(eps) >= 2 and len(post_shap) >= 1
    print(f"  => {'PASS' if e_pass else 'KILL (n=1 ou edge mort post-redemption)'}")

    print("\n" + "=" * 64)
    gates = {"A": a_pass, "B": b_pass, "C": c_pass, "D": d_pass, "E": e_pass}
    verdict = "GO" if all(gates.values()) else "KILL"
    print(f"VERDICT : {verdict}   " + "  ".join(f"{k}={'P' if v else 'K'}" for k, v in gates.items()))
    print("=" * 64)


if __name__ == "__main__":
    main()

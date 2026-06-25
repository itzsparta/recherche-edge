"""
Etude #25 — Flux force de fin de seance : rebalancement des ETF a levier (LETF).
Pre-enregistre : docs/SPEC.md. Free-data (yfinance), zero cle API.

Mecanique : un LETF de levier L doit, au close, trader Delta = AUM * r * L(L-1) pour
reset son exposition. L(L-1) > 0 pour TOUS les leviers -> long et inverse achetent du
meme cote -> flux agrege Imbalance ~ r * G, G = sum AUM_i * L_i(L_i-1). Frappe au close,
dans le sens de r. Effet predit : push late-day + reversal overnight, PLUS FORT la ou
G/volume$ est grand (l'identifiant qui separe le flux LETF du momentum generique).

Gate A : reversal overnight charge sur l'interaction I = r * G/vol$ (signe negatif, |t|>3,
         survit 2023+, dose-reponse monotone en G/vol$).
Gate B : trade de fade overnight pondere par I = brut>0 t>2, NET couts>0, both-halves,
         mur 2023+, deux cotes.
KILL si A insignifiant (= momentum generique) OU B net<=0 (reel mais arbitre au cout #2)
OU rien en 2023+.

Usage : <venv>/python.exe pull_and_gate.py
"""
from __future__ import annotations
import json, os, time, warnings
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

START = "2010-01-01"          # multi-regime
MATURE = "2023-01-01"         # sous-echantillon mur obligatoire (lecon p12/p13)
COST_RT = 0.0004              # cout round-trip overnight (spread+slippage), borne BAS = best-case these

# Panel : sous-jacent -> [(LETF, levier)]. Choisi AVANT les chiffres, large spread de G/vol$.
PANEL = {
    "SPY":  [("UPRO", 3), ("SPXU", -3), ("SPXL", 3), ("SPXS", -3), ("SSO", 2), ("SDS", -2)],
    "QQQ":  [("TQQQ", 3), ("SQQQ", -3), ("QLD", 2), ("QID", -2)],
    "SOXX": [("SOXL", 3), ("SOXS", -3)],
    "IWM":  [("TNA", 3), ("TZA", -3)],
    "XLF":  [("FAS", 3), ("FAZ", -3)],
    "XLE":  [("ERX", 2), ("ERY", -2)],
    "GDX":  [("NUGT", 2), ("DUST", -2)],
    "TLT":  [("TMF", 3), ("TMV", -3)],
    "DIA":  [("UDOW", 3), ("SDOW", -3)],
    "XBI":  [("LABU", 3), ("LABD", -3)],
    "EEM":  [("EDC", 3), ("EDZ", -3)],
}


def pull_aum():
    """AUM courant par LETF (.info totalAssets), cache. Statique = caveat v1 (SPEC)."""
    cache = os.path.join(DATA, "aum.json")
    if os.path.exists(cache):
        return json.load(open(cache))
    aum = {}
    for u, lst in PANEL.items():
        for tkr, L in lst:
            try:
                info = yf.Ticker(tkr).info
                a = info.get("totalAssets") or info.get("netAssets")
            except Exception:
                a = None
            aum[tkr] = a
            print(f"  AUM {tkr:5s} L={L:+d}  ${(a or 0)/1e9:6.2f}B")
    json.dump(aum, open(cache, "w"), indent=2)
    return aum


def compute_G(aum):
    """G_u = sum AUM_i * L_i(L_i-1) par sous-jacent ($ par unite de rendement)."""
    G = {}
    for u, lst in PANEL.items():
        g = 0.0
        for tkr, L in lst:
            a = aum.get(tkr)
            if a:
                g += a * L * (L - 1)
        G[u] = g
    return G


def pull_prices():
    cache = os.path.join(DATA, "prices.pkl")
    if os.path.exists(cache):
        return pd.read_pickle(cache)
    unders = list(PANEL.keys())
    df = yf.download(unders, start=START, progress=False, auto_adjust=True)
    df = df[["Open", "Close", "Volume"]]
    df.to_pickle(cache)
    return df


def build_panel(px, G):
    """Construit le panel name-day : r_cc, r_oc, vol$, GV=G/vol$, I, r_on_next."""
    rows = []
    for u in PANEL:
        try:
            o = px["Open"][u]; c = px["Close"][u]; v = px["Volume"][u]
        except Exception:
            continue
        d = pd.DataFrame({"open": o, "close": c, "vol": v}).dropna()
        d = d[d["vol"] > 0]
        d["r_oc"] = (d["close"] - d["open"]) / d["open"]
        d["r_cc"] = d["close"].pct_change()
        d["dollar_vol"] = d["close"] * d["vol"]
        d["GV"] = G[u] / d["dollar_vol"]                       # G/volume$ (sans dimension ~)
        d["r_on_next"] = (d["open"].shift(-1) - d["close"]) / d["close"]   # overnight reversal window
        d["name"] = u
        d = d.dropna(subset=["r_cc", "r_oc", "GV", "r_on_next"])
        rows.append(d.reset_index().rename(columns={"index": "date", "Date": "date"}))
    p = pd.concat(rows, ignore_index=True)
    p["date"] = pd.to_datetime(p["date"])
    # winsor leger des rendements (queues data-glitch), pas du signal
    for col in ["r_on_next", "r_cc", "r_oc"]:
        lo, hi = p[col].quantile([0.001, 0.999])
        p[col] = p[col].clip(lo, hi)
    return p


def cluster_t(y, X, groups):
    """OLS + SE clusterisees par groupe (date). Retourne (beta, t) par colonne de X."""
    X = np.asarray(X, float); y = np.asarray(y, float)
    XtX = X.T @ X
    XtX_inv = np.linalg.inv(XtX)
    beta = XtX_inv @ (X.T @ y)
    e = y - X @ beta
    meat = np.zeros((X.shape[1], X.shape[1]))
    for g in np.unique(groups):
        m = groups == g
        Xg = X[m]; eg = e[m]
        s = Xg.T @ eg
        meat += np.outer(s, s)
    V = XtX_inv @ meat @ XtX_inv
    se = np.sqrt(np.diag(V))
    return beta, beta / se


def gate_A(p, driver="r_cc", label=""):
    """Reversal overnight ~ I + driver + name FE. I = driver * GV (l'interaction identifiante)."""
    p = p.copy().reset_index(drop=True)
    p["I"] = p[driver] * p["GV"]
    # standardise I et driver pour des betas comparables (t invariant)
    for col in ["I", driver]:
        p[col] = (p[col] - p[col].mean()) / p[col].std()
    names = pd.get_dummies(p["name"], drop_first=True).astype(float)
    X = pd.concat([pd.Series(1.0, index=p.index, name="const"),
                   p[["I", driver]].reset_index(drop=True),
                   names.reset_index(drop=True)], axis=1)
    grp = p["date"].values
    beta, t = cluster_t(p["r_on_next"].values, X.values, grp)
    cols = list(X.columns)
    bI, tI = beta[cols.index("I")], t[cols.index("I")]
    bD, tD = beta[cols.index(driver)], t[cols.index(driver)]
    print(f"  [Gate A {label}] driver={driver}  n={len(p):,}")
    print(f"     coef(I=driver*GV)={bI:+.5f}  t={tI:+.2f}   "
          f"coef({driver})={bD:+.5f}  t={tD:+.2f}   (reversal => I<0, t<-3)")
    return {"driver": driver, "n": int(len(p)), "beta_I": float(bI), "t_I": float(tI),
            "beta_driver": float(bD), "t_driver": float(tD)}


def dose_response(p, driver="r_cc"):
    """Pente r_on_next ~ driver par quintile de GV. Monotone (plus negatif si GV grand) = identif LETF."""
    p = p.copy()
    p["q"] = pd.qcut(p["GV"], 5, labels=False, duplicates="drop")
    out = []
    for q in sorted(p["q"].dropna().unique()):
        s = p[p["q"] == q]
        b = np.polyfit(s[driver], s["r_on_next"], 1)[0]
        out.append((int(q), float(s["GV"].median()), float(b), len(s)))
    print("  Dose-reponse (pente r_on~driver par quintile GV ; attendu: plus NEGATIF si GV grand) :")
    for q, gvm, slope, n in out:
        print(f"     q{q}  GV_med={gvm:.3e}  pente={slope:+.4f}  n={n:,}")
    return out


def gate_B(p, driver="r_cc", label="", cost=COST_RT):
    """Trade fade overnight : w ~ -I (fade le flux), gross-normalise/jour. Ret = sum w*r_on_next."""
    p = p.copy()
    p["I"] = p[driver] * p["GV"]
    daily = []
    for d, g in p.groupby("date"):
        w = -g["I"].values
        s = np.abs(w).sum()
        if s == 0:
            continue
        w = w / s
        turnover = np.abs(w).sum()                      # ~1 (gross), 2 jambes overnight
        ret = float((w * g["r_on_next"].values).sum())
        daily.append((d, ret, ret - cost * turnover))
    dd = pd.DataFrame(daily, columns=["date", "gross", "net"]).set_index("date").sort_index()
    return dd


def summ(dd, label):
    g = dd["gross"]; n = dd["net"]
    def stats(x):
        mu = x.mean(); t = mu / (x.std() / np.sqrt(len(x))) if x.std() > 0 else 0
        sharpe = mu / x.std() * np.sqrt(252) if x.std() > 0 else 0
        return mu, t, sharpe
    gm, gt, gs = stats(g); nm, nt, ns = stats(n)
    h = len(g) // 2
    h1 = stats(g.iloc[:h])[0]; h2 = stats(g.iloc[h:])[0]
    print(f"  [Gate B {label}] jours={len(g):,}")
    print(f"     BRUT  mean/j={gm:+.5f}  t={gt:+.2f}  Sharpe={gs:+.2f}   both-halves:"
          f" {h1:+.5f}/{h2:+.5f} {'OK' if (h1>0)==(h2>0) and h1>0 else 'NON'}")
    print(f"     NET   mean/j={nm:+.5f}  t={nt:+.2f}  Sharpe={ns:+.2f}  (cout RT={COST_RT})")
    return {"label": label, "days": int(len(g)), "gross_mean": float(gm), "gross_t": float(gt),
            "gross_sharpe": float(gs), "net_mean": float(nm), "net_t": float(nt),
            "net_sharpe": float(ns), "h1": float(h1), "h2": float(h2)}


def main():
    t0 = time.time()
    print("Etude #25 — flux force EOD (LETF). Pull free-data yfinance.\n")
    print("1. AUM LETF (snapshot, proxy v1) :")
    aum = pull_aum()
    G = compute_G(aum)
    print("\n2. G = sum AUM*L(L-1) par sous-jacent ($B/unite de rendement) :")
    for u, g in sorted(G.items(), key=lambda x: -x[1]):
        print(f"   {u:5s} G=${g/1e9:7.1f}B")
    print("\n3. Prix daily...")
    px = pull_prices()
    p = build_panel(px, G)
    print(f"   panel : {len(p):,} name-jours, {p['name'].nunique()} sous-jacents, "
          f"{p['date'].min().date()}..{p['date'].max().date()}")
    pm = p[p["date"] >= MATURE]
    print(f"   mur (>={MATURE[:4]}) : {len(pm):,} name-jours")

    res = {"G": {u: float(v) for u, v in G.items()}, "cost_rt": COST_RT}

    print("\n" + "=" * 72 + "\nGATE A — identification (reversal ~ I=driver*GV)\n" + "=" * 72)
    res["gateA_full_cc"] = gate_A(p, "r_cc", "FULL")
    res["gateA_mature_cc"] = gate_A(pm, "r_cc", "MUR-2023+")
    res["gateA_full_oc"] = gate_A(p, "r_oc", "FULL/oc")
    res["dose_full"] = dose_response(p, "r_cc")
    res["dose_mature"] = dose_response(pm, "r_cc")

    print("\n" + "=" * 72 + "\nGATE B — deployabilite (fade overnight pondere I)\n" + "=" * 72)
    res["gateB_full"] = summ(gate_B(p, "r_cc"), "FULL")
    res["gateB_mature"] = summ(gate_B(pm, "r_cc"), "MUR-2023+")
    # up-days vs down-days (les deux cotes doivent contribuer)
    up = p[p["r_cc"] > 0]; dn = p[p["r_cc"] < 0]
    res["gateB_up"] = summ(gate_B(up, "r_cc"), "UP-days")
    res["gateB_dn"] = summ(gate_B(dn, "r_cc"), "DOWN-days")

    print("\n" + "=" * 72 + "\nVERDICT\n" + "=" * 72)
    a = res["gateA_mature_cc"]
    b = res["gateB_mature"]
    A_pass = (a["t_I"] < -3)                          # reversal identifiant, mur
    B_pass = (b["net_t"] > 2 and b["net_mean"] > 0 and (b["h1"] > 0) == (b["h2"] > 0) and b["h1"] > 0)
    verdict = "GO" if (A_pass and B_pass) else "KILL"
    print(f"  Gate A (mur) t(I)={a['t_I']:+.2f} -> {'PASS' if A_pass else 'FAIL'}")
    print(f"  Gate B (mur) net t={b['net_t']:+.2f} mean={b['net_mean']:+.5f} -> {'PASS' if B_pass else 'FAIL'}")
    print(f"  >>> {verdict}")
    if verdict == "KILL":
        if not A_pass:
            print("      Pas d'interaction LETF identifiante en 2023+ : reversal = momentum generique,")
            print("      pas de signal flux-force specifique (ou priced-in #2).")
        elif not B_pass:
            print("      Effet reel mais NET<=0 : arbitre jusqu'au cout (#2).")
    res["verdict"] = verdict
    json.dump(res, open(os.path.join(DATA, "gate_results.json"), "w"), indent=2, ensure_ascii=False)
    print(f"\n-> data/gate_results.json   ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()

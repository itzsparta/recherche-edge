"""Runner pré-test momentum cross-sectionnel crypto (Piste 13) — gates docs/SPEC.md.

L/S transversal market-neutral sur perps Binance, rebal hebdo, gap 1j anti-bounce.
Gates A-G pré-enregistrés. Data free (Binance fapi).

Usage:  python run_xs_mom.py            (cache)
        python run_xs_mom.py --refresh  (re-fetch)
"""
from __future__ import annotations

import math
import sys

import numpy as np
import pandas as pd

import audit
import data_xs

ANN_W = math.sqrt(52)          # hebdo -> annuel
L_DAYS = 28                    # lookback formation (L=4 semaines), pré-spécifié
HOLD = 7                       # holding hebdo
GAP = 1                        # gap formation->entrée (anti-bounce, leçon CEF)
COST_SIDE = 0.0010             # 10 bps/côté sur le notionnel tradé
FUND_WK = 0.0006               # funding porté 3bps/semaine x 2 côtés (gross 2)


def regime_of(d: pd.Timestamp) -> str:
    if d.year == 2021 and d.month <= 4:
        return "1_2021H1_bull"
    if d.year == 2021 and d.month <= 7:
        return "2_2021_crash"
    if d.year == 2021:
        return "3_2021H2"
    if d.year == 2022:
        return "4_2022_bear"
    if d.year == 2023:
        return "5_2023"
    return "6_2024plus"


def backtest(panel: pd.DataFrame, l_days: int = L_DAYS, exclude: set | None = None) -> pd.DataFrame:
    """Boucle de rebal hebdo. Renvoie table hebdo (gross/net/legs/regime/btc_fwd) + contrib en attr."""
    exclude = exclude or set()
    cols = [c for c in panel.columns if c not in exclude]
    P = panel[cols]
    vals = P.to_numpy()
    dates = P.index
    n = len(dates)
    sym_idx = {c: j for j, c in enumerate(cols)}
    btc_j = sym_idx.get("BTCUSDT")

    prev_w: dict[int, float] = {}
    contrib: dict[str, float] = {c: 0.0 for c in cols}
    rows = []
    s = l_days
    while s + GAP + HOLD < n:
        e, x = s + GAP, s + GAP + HOLD
        c_s, c_l = vals[s], vals[s - l_days]
        c_e, c_x = vals[e], vals[x]
        ok = (~np.isnan(c_s)) & (~np.isnan(c_l)) & (~np.isnan(c_e)) & (~np.isnan(c_x)) & (c_l > 0) & (c_e > 0)
        idx = np.where(ok)[0]
        if len(idx) < 9:
            s += HOLD
            continue
        mom = c_s[idx] / c_l[idx] - 1.0
        fwd = c_x[idx] / c_e[idx] - 1.0
        order = np.argsort(mom)
        k = len(idx) // 3
        short_i = idx[order[:k]]
        long_i = idx[order[-k:]]
        long_fwd, short_fwd = fwd[order[-k:]], fwd[order[:k]]
        mkt = float(np.mean(fwd))
        gross = float(np.mean(long_fwd) - np.mean(short_fwd))

        # poids signés, turnover one-way (Σ|Δw|), funding flat
        w = {int(j): 1.0 / k for j in long_i}
        for j in short_i:
            w[int(j)] = -1.0 / k
        traded = sum(abs(w.get(j, 0.0) - prev_w.get(j, 0.0))
                     for j in set(w) | set(prev_w))
        cost = traded * COST_SIDE + FUND_WK
        prev_w = w

        # contribution par symbole (pour drop-top-3)
        cols_arr = np.array(cols)
        for j, f in zip(long_i, long_fwd):
            contrib[cols_arr[j]] += f / k
        for j, f in zip(short_i, short_fwd):
            contrib[cols_arr[j]] += -f / k

        btc_fwd = float(c_x[btc_j] / c_e[btc_j] - 1.0) if btc_j is not None and not np.isnan(c_x[btc_j]) and c_e[btc_j] > 0 else np.nan
        rows.append({
            "date": dates[e],
            "gross": gross,
            "net": gross - cost,
            "long_exc": float(np.mean(long_fwd)) - mkt,
            "short_exc": mkt - float(np.mean(short_fwd)),
            "btc_fwd": btc_fwd,
            "regime": regime_of(dates[e]),
        })
        s += HOLD

    t = pd.DataFrame(rows).set_index("date")
    t.attrs["contrib"] = contrib
    return t


def section(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def main() -> None:
    refresh = "--refresh" in sys.argv
    section("DONNÉES")
    panel = data_xs.load_panel(refresh=refresh)

    t = backtest(panel)
    g, nt = t["gross"].tolist(), t["net"].tolist()
    print(f"  rebals hebdo: {len(t)}  [{t.index.min().date()} -> {t.index.max().date()}]")

    # ---------- (A) BRUT ----------
    section("(A) BRUT > 0, t > 2")
    mg, tg = float(np.mean(g)), audit.tstat(g)
    print(f"  gross hebdo = {mg:+.4%}  ann≈{mg*52:+.1%}  t={tg:+.2f}  Sharpe_ann={audit.sharpe(g)*ANN_W:+.2f}")
    gate_A = (mg > 0) and (tg > 2)
    print(f"  >>> (A) {'PASS' if gate_A else 'FAIL'}")

    # ---------- (B) NET ----------
    section("(B) NET > 0, t > 2  [coût turnover + funding]")
    mn, tn = float(np.mean(nt)), audit.tstat(nt)
    print(f"  net hebdo   = {mn:+.4%}  ann≈{mn*52:+.1%}  t={tn:+.2f}  Sharpe_ann={audit.sharpe(nt)*ANN_W:+.2f}")
    print(f"  break-even cost = {mg:+.4%}/semaine (coût/sem avant EV nulle)")
    gate_B = (mn > 0) and (tn > 2)
    print(f"  >>> (B) {'PASS' if gate_B else 'FAIL'}")

    # ---------- (C) LES DEUX JAMBES ----------
    section("(C) LES DEUX JAMBES PAIENT  [long_exc>0 ET short_exc>0]")
    le, se = float(t["long_exc"].mean()), float(t["short_exc"].mean())
    print(f"  long excess /marché  = {le:+.4%}  t={audit.tstat(t['long_exc'].tolist()):+.2f}")
    print(f"  short excess /marché = {se:+.4%}  t={audit.tstat(t['short_exc'].tolist()):+.2f}")
    gate_C = (le > 0) and (se > 0)
    print(f"  >>> (C) {'PASS' if gate_C else 'FAIL'}  (sinon = long-bêta déguisé)")

    # ---------- (D) MARKET-NEUTRAL ----------
    section("(D) MARKET-NEUTRAL  [|corr(net, BTC)| < 0.2]")
    d = t.dropna(subset=["btc_fwd"])
    corr = float(np.corrcoef(d["net"], d["btc_fwd"])[0, 1]) if len(d) > 2 else float("nan")
    gate_D = abs(corr) < 0.2
    print(f"  corr(net, BTC_fwd) = {corr:+.2f}   >>> (D) {'PASS' if gate_D else 'FAIL'}")

    # ---------- (E) ROBUSTESSE ----------
    section("(E) ROBUSTESSE  [drop-top-3, split régime, miroir]")
    contrib = t.attrs["contrib"]
    top3 = sorted(contrib, key=contrib.get, reverse=True)[:3]
    t_d3 = backtest(panel, exclude=set(top3))
    g_d3 = float(t_d3["gross"].mean())
    print(f"  top-3 contributeurs = {top3}")
    print(f"  drop-top-3 gross hebdo = {g_d3:+.4%}  (signe préservé: {g_d3 > 0})")
    print("  net par régime:")
    pos_reg = 0
    for name, gg in t.groupby("regime"):
        m = gg["net"].mean()
        pos_reg += m > 0
        print(f"    {name:16s}  net={m:+.4%}  n={len(gg)}")
    n_reg = t["regime"].nunique()
    mir = audit.sharpe((-t["gross"]).tolist()) * ANN_W
    drop_ok, reg_ok, mir_ok = g_d3 > 0, pos_reg > n_reg / 2, mir < 0
    gate_E = drop_ok and reg_ok and mir_ok
    print(f"  régimes net+: {pos_reg}/{n_reg}   miroir Sharpe={mir:+.2f} (<0)")
    print(f"  >>> (E) {'PASS' if gate_E else 'FAIL'}  (drop={drop_ok}, régime={reg_ok}, miroir={mir_ok})")

    # ---------- (F) DSR ----------
    section("(F) DSR  [L in {1,2,4,8} semaines]")
    srs = [audit.sharpe(backtest(panel, l_days=L)["gross"].tolist()) for L in (7, 14, 28, 56)]
    var_tr = float(np.var(srs, ddof=0))
    dsr, sr_hat, sr0 = audit.deflated_sharpe(g, n_trials=4, var_trials=max(var_tr, 1e-9))
    gate_F = dsr > 0.95
    print(f"  DSR={dsr:.3f}  SR_hat={sr_hat:.3f}  SR0={sr0:.3f}   >>> (F) {'PASS' if gate_F else 'FAIL'}")

    # ---------- (G) MARCHÉ MÛR ----------
    section("(G) MARCHÉ MÛR  [net > 0 sur 2023+]")
    mat = t[t.index.year >= 2023]["net"].tolist()
    mm, tm = float(np.mean(mat)), audit.tstat(mat)
    gate_G = mm > 0 and tm > 2
    print(f"  net 2023+ hebdo = {mm:+.4%}  ann≈{mm*52:+.1%}  t={tm:+.2f}  (n={len(mat)})")
    print(f"  >>> (G) {'PASS' if gate_G else 'FAIL'}")

    # ---------- VERDICT ----------
    section("VERDICT PRÉ-ENREGISTRÉ  (docs/SPEC.md)")
    if not gate_A:
        print("  ¬(A) => KILL : pas de signal cross-sectionnel brut (sanity).")
    elif not gate_B:
        print("  (A) ∧ ¬(B) => KILL : brut réel mangé par le turnover (motif funding-XS).")
    elif not gate_C:
        print("  ¬(C) => KILL : long-bêta déguisé, la jambe short ne paie pas.")
    elif not gate_G:
        print("  ¬(G) => KILL : artefact early-market non-répétable (motif VRP-crypto/LST).")
    elif gate_A and gate_B and gate_C and gate_D and gate_E and gate_F and gate_G:
        print("  TOUS PASS => GO PROVISOIRE : correction survivorship + Phase 2.")
        print("  Chasse au mirage post-GO OBLIGATOIRE (leçon CEF).")
    else:
        fails = [n for n, ok in [("D", gate_D), ("E", gate_E), ("F", gate_F)] if not ok]
        print(f"  KILL : gate(s) {fails} échoué(s) (neutralité/robustesse/DSR).")


if __name__ == "__main__":
    main()

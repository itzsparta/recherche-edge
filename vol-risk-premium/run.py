"""Runner pre-test VRP — applique les gates pre-enregistres de docs/SPEC.md.

Usage:  python run.py            (cache)
        python run.py --refresh  (re-fetch yfinance)
"""
from __future__ import annotations

import math
import sys

import numpy as np

import audit
import data
import vrp

ANN = math.sqrt(12)  # mensuel -> annuel


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def main() -> None:
    refresh = "--refresh" in sys.argv
    section("DONNEES")
    df = data.load(refresh=refresh)
    t = vrp.monthly_table(df)
    print(f"  echantillon mensuel non-chevauchant: {len(t)} mois, "
          f"{t.index.min().date()} -> {t.index.max().date()}")

    # ---------- (A) LE PREMIUM EXISTE ----------
    section("(A) LE PREMIUM EXISTE  [pre-enreg: mean(vrp_var)>0, t>2, majorite regimes]")
    vv = t["vrp_var"].tolist()
    mean_vv = float(np.mean(vv))
    t_vv = audit.tstat(vv)
    print(f"  mean(VRP_var) = {mean_vv:+.5f} (decimal^2)   t-stat = {t_vv:+.2f}  (n={len(vv)})")
    print(f"  mean(VRP_vol) = {t['vrp_vol'].mean():+.2f} points de vol")

    print("\n  Par regime (mean VRP_var, n):")
    pos_reg = 0
    reg = t.groupby("regime")["vrp_var"]
    for name, g in reg:
        m = g.mean()
        pos_reg += m > 0
        print(f"    {name:14s}  {m:+.5f}   n={len(g)}")
    n_reg = t["regime"].nunique()
    print(f"  regimes positifs: {pos_reg}/{n_reg}")

    # DSR diagnostic : estimateurs de realisee h in {15,21,30}
    srs = []
    for h in (15, 21, 30):
        th = vrp.monthly_table(df, h=h)
        srs.append(audit.sharpe(th["vrp_var"].tolist()))
    var_trials = float(np.var(srs, ddof=0))
    dsr, sr_hat, sr0 = audit.deflated_sharpe(vv, n_trials=3, var_trials=max(var_trials, 1e-9))
    print(f"\n  DSR diagnostic (h in 15/21/30, n_trials=3): DSR={dsr:.3f}  "
          f"SR_hat={sr_hat:.3f}  SR0={sr0:.3f}")

    gate_A = (mean_vv > 0) and (t_vv > 2) and (pos_reg > n_reg / 2) and (dsr > 0.95)
    print(f"\n  >>> (A) {'PASS' if gate_A else 'FAIL'}")

    # ---------- (B) WORTH-IT, TAIL-INCLUS ----------
    section("(B) WORTH-IT TAIL-INCLUS  [pre-enreg: Sharpe net > SPY, t>2, tail, miroir]")
    pnl = t["pnl_net"].to_numpy()
    sr_h = audit.sharpe(pnl.tolist())
    t_h = audit.tstat(pnl.tolist())
    print(f"  recolte nette : Sharpe_ann = {sr_h * ANN:+.2f}   t-stat = {t_h:+.2f}   "
          f"mean = {pnl.mean():+.2f} pts vol/mois")

    spy_r = vrp.spy_monthly_returns(df, t.index)
    sr_spy = audit.sharpe(spy_r.tolist())
    print(f"  SPY buy-hold  : Sharpe_ann = {sr_spy * ANN:+.2f}   (n={len(spy_r)})")

    th = vrp.standardized_tail(pnl)
    ts = vrp.standardized_tail(spy_r.to_numpy())
    print(f"\n  Queue NAIVE (sigma-normalisee, FLATTE le fat-tail -> ne pas trancher dessus):")
    print(f"    recolte : worst={th['worst_z']:+.2f}z  maxDD={th['maxdd_sigma']:+.2f}sig  "
          f"skew={th['skew']:+.2f}  kurt={th['kurt']:.1f}")
    print(f"    SPY     : worst={ts['worst_z']:+.2f}z  maxDD={ts['maxdd_sigma']:+.2f}sig  "
          f"skew={ts['skew']:+.2f}  kurt={ts['kurt']:.1f}")

    # miroir : long vol = signe inverse, doit perdre
    mir = (-t["vrp_vol"] - vrp.COST)
    print(f"\n  Miroir (long vol) : Sharpe_ann = {audit.sharpe(mir.tolist()) * ANN:+.2f} "
          f"(doit etre < 0)")

    # TAIL HONNETE : le modele mensuel LISSE le krach intramois (Feb-2018 invisible).
    # On tranche sur le vrai vehicule short-vol marque au quotidien (SVXY), drawdown ABSOLU.
    svxy = data.close_series("SVXY", auto_adjust=True)
    sret = svxy.pct_change().dropna()
    spy_d = df["spy"].pct_change().dropna().reindex(sret.index).dropna()
    dd_svxy, dd_spy = vrp.abs_maxdd(sret), vrp.abs_maxdd(spy_d)
    print(f"\n  Tail HONNETE (drawdown absolu, marque quotidien, fenetre SVXY 2011+):")
    print(f"    SVXY (short-vol REEL) maxDD = {dd_svxy:+.1%}   pire jour {sret.min():+.1%}")
    print(f"    SPY  buy-hold         maxDD = {dd_spy:+.1%}")

    beats_sharpe = (sr_h * ANN > sr_spy * ANN) and (t_h > 2)
    tail_ok = dd_svxy >= dd_spy            # short-vol pas plus catastrophique que l'equity
    gate_B = beats_sharpe and tail_ok
    print(f"\n  >>> (B) {'PASS' if gate_B else 'FAIL'}  "
          f"(bat_SPY={beats_sharpe}, tail_ok={tail_ok})")

    # ---------- VERDICT ----------
    section("VERDICT PRE-ENREGISTRE")
    if gate_A and gate_B:
        print("  (A) ^ (B) => GO  : protocole complet (VIX futures, options delta-hedge, WF)")
    elif gate_A and not gate_B:
        print("  (A) ^ -(B) => DOWNGRADE : prime REELLE mais = compensation d'un tail")
        print("                non-portable solo. Documenter, ne pas builder plus loin.")
    else:
        print("  -(A) => KILL : premium absent/instable cross-regime (sanity fail).")


if __name__ == "__main__":
    main()

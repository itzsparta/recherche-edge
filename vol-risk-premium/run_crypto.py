"""Runner pré-test VRP crypto (Piste 12) — gates pré-enregistrés de docs/SPEC-crypto.md.

Phase 0/1 (free-data DVOL Deribit) : tranche Gate A (premium existe ET > 8 pts de vol)
et le pré-B Phase-1 (net survit à la provision d'aile forfaitaire). Le defined-risk réel
sur surface d'options = Phase 2 (data-gated), non couvert ici.

Usage:  python run_crypto.py            (cache)
        python run_crypto.py --refresh  (re-fetch Deribit)
"""
from __future__ import annotations

import math
import sys

import numpy as np

import audit
import data_crypto
import vrp_crypto as vc

ANN = math.sqrt(12)  # mensuel -> annuel


def section(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def analyze(currency: str, refresh: bool) -> dict:
    df = data_crypto.load(currency, refresh=refresh)
    t = vc.monthly_table(df)
    print(f"  échantillon mensuel non-chevauchant: {len(t)} mois, "
          f"{t.index.min().date()} -> {t.index.max().date()}")

    # ---------- (A) LE PREMIUM EXISTE ET EST FAT ----------
    vv = t["vrp_var"].tolist()
    mean_vv = float(np.mean(vv))
    t_vv = audit.tstat(vv)
    mean_vol = float(t["vrp_vol"].mean())
    print(f"\n  (A) mean(VRP_var) = {mean_vv:+.5f} (decimal^2)  t-stat = {t_vv:+.2f}  (n={len(vv)})")
    print(f"      mean(VRP_vol) = {mean_vol:+.2f} pts de vol   [barre pré-enreg > {vc.MAG_BAR}]")

    print("\n      Par régime (mean VRP_vol, mean VRP_var, n):")
    pos_reg = 0
    for name, g in t.groupby("regime"):
        m_var = g["vrp_var"].mean()
        pos_reg += m_var > 0
        print(f"        {name:18s}  {g['vrp_vol'].mean():+6.2f} pts   {m_var:+.5f}   n={len(g)}")
    n_reg = t["regime"].nunique()
    print(f"      régimes positifs (var): {pos_reg}/{n_reg}")

    # DSR diagnostic : estimateurs de réalisée h in {21,30,45}
    srs = [audit.sharpe(vc.monthly_table(df, h=h)["vrp_var"].tolist()) for h in (21, 30, 45)]
    var_trials = float(np.var(srs, ddof=0))
    dsr, sr_hat, sr0 = audit.deflated_sharpe(vv, n_trials=3, var_trials=max(var_trials, 1e-9))
    print(f"      DSR diagnostic (h 21/30/45, n_trials=3): DSR={dsr:.3f}  SR_hat={sr_hat:.3f}  SR0={sr0:.3f}")

    gate_A = ((mean_vv > 0) and (t_vv > 2) and (mean_vol > vc.MAG_BAR)
              and (pos_reg > n_reg / 2) and (dsr > 0.95))
    mag_fail = mean_vol <= vc.MAG_BAR
    print(f"      >>> (A) {'PASS' if gate_A else 'FAIL'}"
          f"{'  [barre magnitude ratée = rien de neuf vs actions]' if mag_fail else ''}")

    # ---------- (pré-B) NET PHASE-1, TAIL-INCLUS ----------
    pnl = t["pnl_net"].to_numpy()
    sr_h = audit.sharpe(pnl.tolist())
    t_h = audit.tstat(pnl.tolist())
    print(f"\n  (pré-B) récolte nette @ coût {vc.COST} pts/mois : "
          f"mean={pnl.mean():+.2f} pts/mois  Sharpe_ann={sr_h * ANN:+.2f}  t={t_h:+.2f}")
    # break-even cost honnête (coût qui annule l'EV)
    print(f"          break-even cost = {t['vrp_vol'].mean():+.2f} pts/mois "
          f"(coût max avant EV nulle)")

    spot_r = vc.spot_monthly_returns(df, t.index)
    sr_spot = audit.sharpe(spot_r.tolist())
    print(f"          {currency} buy-hold : Sharpe_ann={sr_spot * ANN:+.2f}  (n={len(spot_r)})")

    mir = (-t["vrp_vol"] - vc.COST)
    sr_mir = audit.sharpe(mir.tolist()) * ANN
    print(f"          miroir (long vol) : Sharpe_ann={sr_mir:+.2f}  (doit être < 0)")

    preB = (pnl.mean() > 0) and (t_h > 2) and (sr_h * ANN > sr_spot * ANN) and (sr_mir < 0)
    print(f"          >>> (pré-B Phase-1) {'PASS' if preB else 'FAIL'}")

    return {"gate_A": gate_A, "preB": preB, "mag_fail": mag_fail,
            "mean_vol": mean_vol, "t_vv": t_vv}


def main() -> None:
    refresh = "--refresh" in sys.argv

    section("BTC  (primaire — porte le verdict)")
    btc = analyze("BTC", refresh)

    section("ETH  (confirmation)")
    try:
        eth = analyze("ETH", refresh)
    except Exception as e:  # ETH DVOL plus court / indispo : non bloquant
        print(f"  ETH indisponible ({e}) — verdict sur BTC seul.")
        eth = None

    # ---------- VERDICT PRE-ENREGISTRE (sur BTC) ----------
    section("VERDICT PRÉ-ENREGISTRÉ  (docs/SPEC-crypto.md)")
    if not btc["gate_A"]:
        if btc["mag_fail"]:
            print("  ¬(A) => KILL : premium réel mais NON matériellement plus gros que")
            print(f"          l'actions (mean VRP_vol={btc['mean_vol']:+.2f} ≤ {vc.MAG_BAR} pts).")
            print("          Aucune raison de porter un tail crypto pire → rien de neuf.")
        else:
            print("  ¬(A) => KILL : premium absent/instable cross-régime (sanity fail).")
    elif btc["gate_A"] and not btc["preB"]:
        print("  (A) ∧ ¬(pré-B) => DOWNGRADE : premium réel ET fat, mais déjà mangé par")
        print(f"          la provision d'aile forfaitaire ({vc.COST} pts/mois). Même mort que")
        print("          la Piste 4, déplacée tail->hedge. Phase 2 inutile.")
    else:
        print("  (A) ∧ (pré-B) => GO PROVISOIRE : Phase 1 survit. Passer Phase 2 (surface")
        print("          d'options Deribit réelle, iron-condor net des spreads d'ailes RÉELS).")
        print("          Chasse au mirage post-GO OBLIGATOIRE (leçon CEF : t aveugle au bounce).")

    if eth is not None:
        agree = "CONFIRME" if eth["gate_A"] == btc["gate_A"] else "DIVERGE"
        print(f"\n  ETH {agree} BTC sur Gate A (ETH A={eth['gate_A']}, "
              f"mean VRP_vol={eth['mean_vol']:+.2f} pts).")


if __name__ == "__main__":
    main()

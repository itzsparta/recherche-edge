"""Phase-2 carry : exécution réelle + tail + walk-forward OOS. Gates pré-enregistrés SPEC-phase2.

Usage:  python run_phase2.py [--refresh]
"""
from __future__ import annotations

import sys

import pandas as pd

import audit
import carry
import data_funding
import data_prices
import execution
import liquidation
import tail

OOS_MONTHS = 24      # fenêtre forward réaliste (régime compressé)
HURDLE_C = 0.08      # net_ann OOS — pré-enregistré
SYMBOL = "BTCUSDT"


def section(t: str) -> None:
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


def main() -> None:
    refresh = "--refresh" in sys.argv
    section("DONNÉES (funding Phase-1 + spot/perp klines réels)")
    fund = carry.daily(data_funding.funding(SYMBOL, refresh=refresh))
    spot = data_prices.spot_daily(SYMBOL, refresh=refresh)
    perp = data_prices.perp_daily(SYMBOL, refresh=refresh)
    perp8h = data_prices.perp_8h(SYMBOL, refresh=refresh)

    df = execution.build(fund, spot, perp)
    full = execution.stats(df)

    section("P&L DELTA-NEUTRE RÉEL (full history, frais 2-jambes réels)")
    print(f"  fenêtre {df.index.min().date()} -> {df.index.max().date()}  (n={full['n']})")
    print(f"  gross_ann (funding) {full['gross_ann']:+.1%}")
    print(f"  basis_ann (spot-perp, doit ~0) {full['basis_ann']:+.2%}")
    print(f"  fee_ann (réel) {full['fee_ann']:+.2%}   [Phase-1 forfait était -1.2%]")
    print(f"  NET_ann {full['net_ann']:+.1%}   corr(pnl,btc) {full['corr']:+.2f}")

    print("\n  NET annuel (compression, frais réels) :")
    for y, g in df.groupby(df.index.year):
        print(f"    {y}: net {execution.ann(g['pnl']):+.1%}")

    # ---------- OOS : régime compressé récent ----------
    cutoff = df.index.max() - pd.DateOffset(months=OOS_MONTHS)
    oos = df[df.index > cutoff]
    o = execution.stats(oos)
    t_m = audit.tstat(oos["pnl"].resample("ME").sum().dropna().tolist())
    dd = execution.max_drawdown(oos["pnl"])

    section(f"(C) SURVIE EXÉCUTION — OOS {OOS_MONTHS}m ({oos.index.min().date()} -> "
            f"{oos.index.max().date()})")
    neutral = abs(o["corr"]) < 0.2
    above = o["net_ann"] > HURDLE_C
    print(f"  net_ann OOS {o['net_ann']:+.1%}  (gross {o['gross_ann']:+.1%}, "
          f"fee {o['fee_ann']:+.2%}, basis {o['basis_ann']:+.2%})")
    print(f"  t mensuel OOS {t_m:+.2f}")
    print(f"  delta-neutre |corr(pnl,btc)| {abs(o['corr']):.2f} < 0.20 ? {neutral}  "
          f"(legs réels, pas markPrice)")
    print(f"  net_ann OOS {o['net_ann']:+.1%} > hurdle {HURDLE_C:.0%} ? {above}")
    gate_C = neutral and above
    print(f"  >>> (C) {'PASS' if gate_C else 'FAIL'}")

    # ---------- (D) tail ----------
    section("(D) SURVIE TAIL")
    print(" (D1) liquidation :")
    liq = liquidation.report(perp8h)
    gate_D1 = liq["cross_safe"]
    print(f"\n (D2) risque exchange (sur net OOS) :")
    tl = tail.report(o["net_ann"])
    gate_D2 = tl["ok"]
    print(f"\n (D3, diag) pire drawdown cumulé OOS : {dd:+.1%} "
          f"({'recouvrable < 1 an de carry' if abs(dd) < abs(o['net_ann']) else 'profond'})")
    gate_D = gate_D1 and gate_D2
    print(f"  >>> (D) {'PASS' if gate_D else 'FAIL'}  (D1 {gate_D1}, D2 {gate_D2})")

    # ---------- VERDICT ----------
    section("VERDICT PHASE-2 PRÉ-ENREGISTRÉ")
    if gate_C and gate_D:
        print("  (C) ∧ (D) => GO-DEPLOY : paper-trade puis capital réel, sizé pour survivre")
        print("              au tail exchange (position << net worth).")
    elif gate_C and not gate_D:
        print("  (C) ∧ ¬(D) => DOWNGRADE : net réel sur le forward mais le TAIL le tue")
        print("              (break-even exchange trop bas) => pas worth le capital réel solo.")
    else:
        print("  ¬(C) => KILL-FORWARD : régime compressé + frais réels tuent le net sur la")
        print("          fenêtre réaliste. Le +10.5% historique = chance de régime, pas un")
        print("          edge déployable aujourd'hui.")


if __name__ == "__main__":
    main()

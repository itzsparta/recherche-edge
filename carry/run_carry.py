"""Runner pre-test piste 6 carry crypto — gates pré-enregistrés de docs/SPEC.md.

Usage:  python run_carry.py [--refresh]
"""
from __future__ import annotations

import sys

import numpy as np

import audit
import carry
import data_funding

HURDLE = 0.05      # hurdle net annualisé
FEE_ANN = 0.012    # 1.2 %/an (rééq. mensuel)


def section(t: str) -> None:
    print(f"\n{'=' * 70}\n{t}\n{'=' * 70}")


def ann(xs) -> float:
    return float(np.mean(xs)) * 365.0


def summarize(name: str, d) -> dict:
    c = d["carry"].dropna().tolist()
    g = ann(c)
    reg = {nm: ann(s) - FEE_ANN for nm, s in d.groupby("regime")["carry"]}
    corr = d[["carry", "btc_ret"]].dropna().corr().iloc[0, 1]
    print(f"\n  [{name}]  gross_ann {g:+.1%}  net_ann {g - FEE_ANN:+.1%}  "
          f"t(carry) {audit.tstat(c):+.2f}  corr(carry,BTCret) {corr:+.2f}")
    for nm in sorted(reg):
        print(f"      {nm:16s} net_ann {reg[nm]:+8.1%}")
    return {"g": g, "net": g - FEE_ANN, "t": audit.tstat(c), "reg": reg, "mean": np.mean(c)}


def main() -> None:
    refresh = "--refresh" in sys.argv
    section("DONNEES")
    btc = carry.daily(data_funding.funding("BTCUSDT", refresh=refresh))
    eth = carry.daily(data_funding.funding("ETHUSDT", refresh=refresh))

    section("BTCUSDT (primaire)  +  ETHUSDT (robustesse)")
    s = summarize("BTCUSDT", btc)
    se = summarize("ETHUSDT", eth)

    # ---------- (A) ----------
    section("(A) LE CARRY EXISTE  [mean>0, t>2 ; BTC full]")
    monthly = btc["carry"].resample("ME").sum().dropna().tolist()
    t_m = audit.tstat(monthly)
    gate_A = (s["mean"] > 0) and (s["t"] > 2)
    print(f"  mean carry/jour {s['mean']*1e4:+.2f} bps")
    print(f"  t daily {s['t']:+.2f} (GONFLE : funding tres autocorrele, ne pas citer)")
    print(f"  t mensuel non-chevauchant {t_m:+.2f} (significativite honnete)")
    print(f"  >>> (A) {'PASS' if gate_A else 'FAIL'}")
    print("\n  Tendance annuelle (gross_ann -> COMPRESSION) :")
    for y, g in btc.groupby(btc.index.year)["carry"]:
        print(f"    {y}: {float(np.mean(g)) * 365:+.1%}")

    # ---------- (B) ----------
    section("(B) WORTH-IT NET ROBUSTE REGIME  [net>5%, net>0 chaque régime, drop-best>5%]")
    above = s["net"] > HURDLE
    all_pos = all(v > 0 for v in s["reg"].values())
    best = max(s["reg"], key=s["reg"].get)
    rest = btc[btc["regime"] != best]["carry"]
    net_drop = ann(rest) - FEE_ANN
    drop_ok = net_drop > HURDLE
    print(f"  net_ann {s['net']:+.1%} > {HURDLE:.0%}? {above}")
    print(f"  net>0 chaque régime? {all_pos}  (régimes neg: "
          f"{[k for k, v in s['reg'].items() if v <= 0] or 'aucun'})")
    print(f"  drop meilleur régime ({best}) -> net_ann {net_drop:+.1%} > {HURDLE:.0%}? {drop_ok}")
    gate_B = above and all_pos and drop_ok
    print(f"  >>> (B) {'PASS' if gate_B else 'FAIL'}")

    # ---------- VERDICT ----------
    section("VERDICT PRE-ENREGISTRE (piste 6 carry)")
    if gate_A and gate_B:
        print("  (A) ^ (B) => GO  : protocole complet (exécution réelle, liquidation, WF).")
        print("              PREMIER non-kill du programme.")
    elif gate_A and not gate_B:
        print("  (A) ^ -(B) => DOWNGRADE : carry réel mais fair-weather / compressé / sous")
        print("                le hurdle. Pas worth le risque exchange pour un solo.")
    else:
        print("  -(A) => KILL : funding non positif/significatif.")


if __name__ == "__main__":
    main()

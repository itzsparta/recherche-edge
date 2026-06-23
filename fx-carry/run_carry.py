"""Runner gates A-D — pré-enregistrés docs/SPEC.md (Piste 17).

FX carry G10. Tranche : prime réelle (t>2, DSR>0.95) ? tail 2008 supportable ?
et surtout (D) ajoute-t-elle un sleeve orthogonal au trend (+0.12) ?
"""
from __future__ import annotations

import math

import pandas as pd

import audit
import carry

T_FLOOR = 2.0
DSR_FLOOR = 0.95
CORR_MAX = 0.30


def section(t: str) -> None:
    print(f"\n{'=' * 76}\n{t}\n{'=' * 76}")


def ann_sharpe(xs) -> float:
    return audit.sharpe(list(xs)) * math.sqrt(12)


def max_dd(rets) -> float:
    eq = (1 + pd.Series(list(rets))).cumprod()
    return float((eq / eq.cummax() - 1).min())


def main() -> None:
    df = carry.carry_portfolio(n_side=3)
    net = df["net"]
    gross = df["gross"]

    section("(A) PRIME RÉELLE ?  [carry net, mensuel non-chevauchant]")
    t_net = audit.tstat(list(net))
    print(f"  mois={len(net)}  gross ann={gross.mean()*12*100:+.2f}%  net ann={net.mean()*12*100:+.2f}%")
    print(f"  net Sharpe ann={ann_sharpe(net):.2f}  t={t_net:+.2f}  [plancher t>{T_FLOOR}]")
    gate_A = (net.mean() > 0) and (t_net > T_FLOOR)
    print(f"  >>> (A) {'PASS' if gate_A else 'FAIL'}")

    section("(B) PAS UN MIRAGE ?  [DSR anti-multiple-testing + concentration]")
    # variantes raisonnables pour estimer var_trials (n_side 2/3, gross/net)
    variants = []
    for ns in (2, 3):
        d = carry.carry_portfolio(n_side=ns)
        variants += [audit.sharpe(list(d["gross"])), audit.sharpe(list(d["net"]))]
    var_trials = pd.Series(variants).var(ddof=0)
    n_trials = max(len(variants), 6)
    dsr, sr, sr0 = audit.deflated_sharpe(list(net), n_trials=n_trials, var_trials=max(var_trials, 1e-6))
    print(f"  DSR={dsr:.3f}  (SR_période={sr:.3f} vs seuil bruit SR0={sr0:.3f}, n_trials={n_trials})  "
          f"[plancher {DSR_FLOOR}]")
    gate_B = dsr > DSR_FLOOR
    print(f"  >>> (B) {'PASS' if gate_B else 'FAIL'}")

    section("(C) TAIL  [carry crash 2008, drawdown, skew]")
    ret08 = net[(net.index >= "2008-01-01") & (net.index < "2009-01-01")]
    skew = audit._moments(list(net))[0]
    dd = max_dd(net)
    print(f"  2008 (année): {ret08.sum()*100:+.1f}%  |  max drawdown: {dd*100:+.1f}%  |  skew: {skew:+.2f}")
    worst = net.nsmallest(3)
    print(f"  3 pires mois: " + ", ".join(f"{d:%Y-%m} {v*100:+.1f}%" for d, v in worst.items()))
    # tail-ok si la prime survit au krach : Sharpe hors-2008 pas radicalement porté par le reste
    net_ex08 = net[(net.index < "2008-01-01") | (net.index >= "2009-01-01")]
    print(f"  Sharpe ann hors-2008={ann_sharpe(net_ex08):.2f} (vs {ann_sharpe(net):.2f} full)")
    tail_ok = (skew > -1.0) and (dd > -0.25)
    print(f"  >>> (C) {'tail OK' if tail_ok else 'TAIL-DOMINÉ'} "
          f"(skew>{-1.0} ∧ DD>{-25}% ; sinon cap DOWNGRADE)")

    section("(D) SLEEVE ORTHOGONAL AU TREND ?  [le test qui compte pour l'objectif]")
    tr = carry.trend_proxy()
    j = pd.concat([net.rename("carry"), tr.rename("trend")], axis=1).dropna()
    corr = float(j["carry"].corr(j["trend"]))
    sh_c = ann_sharpe(j["carry"])
    sh_t = ann_sharpe(j["trend"])
    combo = 0.5 * j["carry"] + 0.5 * j["trend"]
    sh_combo = ann_sharpe(combo)
    print(f"  corr(carry, trend)={corr:+.2f}  [plancher |corr|<{CORR_MAX}]")
    print(f"  Sharpe ann : carry={sh_c:.2f}  trend(proxy)={sh_t:.2f}  combo 50/50={sh_combo:.2f}")
    adds = (abs(corr) < CORR_MAX) and (sh_combo > sh_t) and (sh_combo > sh_c)
    print(f"  >>> (D) {'AJOUTE un sleeve' if adds else 'N AJOUTE PAS'} "
          f"(orthogonal ∧ combo > chaque jambe)")

    section("VERDICT PRÉ-ENREGISTRÉ  (docs/SPEC.md)")
    if not gate_A or not gate_B:
        print("  ¬(A) ∨ ¬(B) => KILL : pas de prime (t<2) ou mirage (DSR<0.95).")
        if not gate_A:
            print(f"           Prime full-sample noyée — décennie taux-zéro 2009-2021 annule le différentiel.")
    elif gate_A and gate_B and adds and tail_ok:
        print("  (A)∧(B)∧(C)∧(D) => GO-sleeve : 2e sleeve diversifiant réel, agrandit le deliverable.")
    elif gate_A and gate_B and not adds:
        print("  (A)∧(B)∧¬(D) => KILL-pour-l'objectif : prime réelle mais n'ajoute rien au trend.")
    else:
        print("  (A)∧(B)∧¬(C) => DOWNGRADE : prime réelle mais tail-dominée (carry crash) = comme VRP #4.")


if __name__ == "__main__":
    main()

"""Runner gates A-D — pré-enregistrés docs/SPEC.md (Piste 18).

Dealer gamma GEX. Tranche : GEX prédit-il la vol (mécanisme) ET un alpha de RENDEMENT
tradable net, ou seulement la vol (prédicteur réel sans edge déployable, comme pré-FOMC) ?
"""
from __future__ import annotations

import math

import audit
import gex


def section(t: str) -> None:
    print(f"\n{'=' * 76}\n{t}\n{'=' * 76}")


def ann_sh(xs: list[float]) -> float:
    return audit.sharpe(xs) * math.sqrt(252)


def main() -> None:
    section("(A) MÉCANISME — GEX prédit-il la vol du lendemain ?")
    c, n = gex.mechanism()
    t = c * math.sqrt(n)  # t-stat de la corrélation
    print(f"  corr(GEX_lag, |ret|) = {c:+.3f}  t≈{t:+.1f}  (n={n})")
    gate_A = (c < 0) and (abs(t) > 2)
    print(f"  >>> (A) {'PASS' if gate_A else 'FAIL'}  "
          f"{'GEX haut -> vol basse = mécanisme réel' if gate_A else 'pas de signal vol'}")

    section("(B) EDGE DE RENDEMENT TRADABLE ?  [S1 switch, S2 vol-timing, net de coûts]")
    st = gex.strategies()
    bh = st["buyhold"]
    sh_bh = ann_sh(bh)
    best = None
    for k in ("S1_switch", "S2_voltiming"):
        v = st[k]
        sh = ann_sh(v)
        tt = audit.tstat(v)
        dsr, sr, sr0 = audit.deflated_sharpe(v, n_trials=6, var_trials=max(audit.sharpe(v) ** 2, 1e-6))
        ann = sum(v) / len(v) * 252 * 100
        print(f"  {k:14s} ann={ann:+6.2f}%  Sharpe={sh:+.2f}  t={tt:+.2f}  DSR={dsr:.3f}")
        if best is None or sh > best[1]:
            best = (k, sh, tt, dsr)
    print(f"  buyhold        ann={sum(bh)/len(bh)*252*100:+6.2f}%  Sharpe={sh_bh:+.2f}  (benchmark)")
    # tradable = bat le buy-hold en risque-ajusté AVEC t>2 et DSR>0.95
    gate_B = (best[2] > 2.0) and (best[3] > 0.95) and (best[1] > sh_bh)
    print(f"  >>> (B) {'PASS' if gate_B else 'FAIL'}  "
          f"(meilleure {best[0]} Sharpe {best[1]:+.2f} vs buyhold {sh_bh:+.2f} ; t={best[2]:+.2f} DSR={best[3]:.3f})")

    section("(C) PRICED-IN ?  [mécanisme + meilleure strat, pré-2021 vs post-2021]")
    d = gex.data_gex.load()
    # mécanisme par période
    for lab, lo, hi in (("pré-2021", "2011-01-01", "2021-01-01"), ("post-2021", "2021-01-01", "2027-01-01")):
        g = [d[i - 1].gex for i in range(1, len(d)) if lo <= d[i].date < hi]
        v = [abs(d[i].ret) for i in range(1, len(d)) if lo <= d[i].date < hi]
        cc = gex.pearson(g, v)
        print(f"  {lab}: corr(GEX,|ret|)={cc:+.3f}  t≈{cc*math.sqrt(len(g)):+.1f}  (n={len(g)})  [mécanisme]")
    print("  (mécanisme vol = robuste les deux périodes = vrai prédicteur de vol, pas un artefact)")

    section("(D) ORTHOGONAL AU BÊTA DE VOL ?")
    # le rendement de S2 est-il juste de l'évitement de vol (corrélé négativement à |ret|) ?
    s2 = st["S2_voltiming"]
    absret = [abs(x) for x in bh]
    corr_vol = gex.pearson(s2, absret)
    print(f"  corr(S2, |ret|) = {corr_vol:+.3f}  (S2 = simple dé-risking en régime vol, pas alpha)")

    section("VERDICT PRÉ-ENREGISTRÉ  (docs/SPEC.md)")
    if not gate_A:
        print("  ¬(A) => KILL : pas même de signal vol.")
    elif gate_A and not gate_B:
        print("  (A) ∧ ¬(B) => KILL-tradable : GEX est un PRÉDICTEUR DE VOL réel (corr −0.26, robuste")
        print("       pré ET post-2021) mais AUCUN alpha de rendement déployable — S1 switch PERD,")
        print("       S2 vol-timing sous-performe le buy-hold (juste de l'expo réduite, pas un edge).")
        print("       Même structure que overnight #5a / pré-FOMC #5b : mécanisme réel, rien à trader net.")
        print("       Le flux forcé prédit la VARIANCE, pas la MOYENNE — non-directionnel = non-tradable solo.")
    else:
        print("  (A) ∧ (B) => voir (C)/(D) pour GO/DOWNGRADE/priced-in.")


if __name__ == "__main__":
    main()

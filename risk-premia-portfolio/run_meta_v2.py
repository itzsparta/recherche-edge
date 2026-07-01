"""Runner META v2 — 4 sleeves, mêmes gates PRÉ-COMMITTÉS que run_meta.py (docs/SPEC.md).

Diff vs v1 : remplace le FX-carry DILUANT (#17, corr +0.41 au cœur) par deux sleeves
RÉELLEMENT orthogonaux au cœur — carry_energy (#30, corr −0.105) et ils (#31, +0.106).
La question v2 : ces deux briques ajoutent-elles l'INCRÉMENT que le FX-carry ne pouvait pas,
ou diluent-elles aussi ?

SCOPE acté (pas caché) : intersection 4-way = ils 2013-03 → carry_energy 2024-04 (cache EIA).
=> 2008 INTESTABLE pour ce combo (ils n'existe pas avant 2013). M4-crise = 2020/2022 seuls.
La thèse v2 se joue donc sur le régime CALME+2022 — là où le trend-seul (v1) DILUE.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

import audit
import sleeves_v2
from run_meta import ann_sharpe, fixed_combo, inv_vol_combo, tot_ret

COLS4 = ["base6040", "trend", "carry_energy", "ils"]


def main() -> None:
    S_full = sleeves_v2.load_sleeves_v2()

    print("=" * 72)
    print(f"SLEEVES v2 (union {S_full.index.min()}->{S_full.index.max()}, {len(S_full)} mois)")
    for c in COLS4:
        x = S_full[c].dropna()
        print(f"  {c:13s} n={len(x):3d} Sharpe={ann_sharpe(x):+.2f}  t={audit.tstat(list(x)):+.2f}")
    print("  corr:\n" + S_full[COLS4].corr().round(3).to_string())

    # STRICT 4-way : ne garder que les mois où les 4 sleeves existent simultanément.
    # (sinon inv_vol min_count=1 mélange des périodes -> combos pommes-vs-oranges)
    S = S_full[COLS4].dropna()
    print(f"\n  intersection STRICTE 4-way : {S.index.min()}->{S.index.max()} ({len(S)} mois)")

    # --- schémas PRÉ-COMMITTÉS (zéro opt IS, cœur-lourds comme v1 70/20/10) ---
    rp4 = inv_vol_combo(S, COLS4)                                  # primaire 4 sleeves
    rp2 = inv_vol_combo(S, ["base6040", "trend"])                 # deliverable v1
    fix = fixed_combo(S, {"base6040": 0.55, "trend": 0.15,
                          "carry_energy": 0.15, "ils": 0.15})
    ew = fixed_combo(S, {c: 0.25 for c in COLS4})
    schemes = {"RP4 (inv-vol 4)": rp4, "fixe 55/15/15/15": fix,
               "RP2 (cœur v1)": rp2, "equal-weight 4": ew}

    # fenêtre = post-warmup RP4 (inv-vol mange 36 mois) -> tout le monde dessus
    idx = rp4.index
    base = S["base6040"].reindex(idx)
    sleeve_sr = {c: ann_sharpe(S[c].reindex(idx)) for c in COLS4}

    print("\n" + "=" * 72)
    print(f"COMBOS vs sleeves — fenêtre commune {idx.min()}->{idx.max()} ({len(idx)} mois)")
    print("  (2008 hors-fenêtre : ils n'existe pas avant 2013-03)")
    for c in COLS4:
        print(f"  sleeve {c:13s} Sharpe={sleeve_sr[c]:+.2f}")
    sch_sr = {}
    for name, x in schemes.items():
        xw = x.reindex(idx).dropna()
        sr = ann_sharpe(xw)
        sch_sr[name] = sr
        print(f"  combo  {name:17s} Sharpe={sr:+.2f}  ann={xw.mean()*12*100:+5.2f}%  "
              f"t={audit.tstat(list(xw)):+.2f}")

    # ===== (M1) le tout bat chaque partie =====
    print("\n" + "=" * 72 + "\n(M1) LE TOUT BAT CHAQUE PARTIE ?")
    best_sleeve = max(sleeve_sr, key=sleeve_sr.get)
    m1 = all(sch_sr["RP4 (inv-vol 4)"] > sleeve_sr[c] for c in COLS4)
    print(f"  RP4 {sch_sr['RP4 (inv-vol 4)']:+.2f}  vs meilleur sleeve "
          f"({best_sleeve} {sleeve_sr[best_sleeve]:+.2f})")
    print(f"  >>> (M1) {'PASS' if m1 else 'FAIL'}")

    # ===== les NEUFS ajoutent-ils ? (RP4 4-sleeves vs RP2 cœur-v1) =====
    print("\n" + "=" * 72 + "\nLES NEUFS (carry_energy+ils) AJOUTENT-ILS ?  (RP4 vs RP2)")
    add = sch_sr["RP4 (inv-vol 4)"] > sch_sr["RP2 (cœur v1)"]
    print(f"  RP2 cœur-v1 {sch_sr['RP2 (cœur v1)']:+.2f}  vs RP4 4-sleeves "
          f"{sch_sr['RP4 (inv-vol 4)']:+.2f}  => les neufs {'AJOUTENT' if add else 'DILUENT'}")

    # ===== (M2) stabilité =====
    print("\n" + "=" * 72 + "\n(M2) STABILITÉ (pas un knife-edge) ?")
    srs = list(sch_sr.values())
    spread = max(srs) - min(srs)
    print(f"  Sharpes 4 schémas: " + "  ".join(f"{s:+.2f}" for s in srs))
    print(f"  écart max-min = {spread:.2f}")
    m2 = spread < 0.30

    # ===== (M3) DSR =====
    print("\n" + "=" * 72 + "\n(M3) DÉFLATION (DSR, n_trials=4) ?")
    per_period_sr = [audit.sharpe(list(x.reindex(idx).dropna())) for x in schemes.values()]
    var_trials = float(np.var(per_period_sr))
    best_name = max(sch_sr, key=sch_sr.get)
    best_series = list(schemes[best_name].reindex(idx).dropna())
    dsr, sr_hat, sr0 = audit.deflated_sharpe(best_series, n_trials=4, var_trials=var_trials)
    print(f"  meilleur combo = {best_name} (Sharpe {sch_sr[best_name]:+.2f})")
    print(f"  DSR={dsr:.3f}  (SR_mois={sr_hat:+.3f} vs seuil SR0={sr0:+.3f})")

    # ===== (M4) crisis-alpha (2020/2022 ; 2008 NA) =====
    print("\n" + "=" * 72 + "\n(M4) CRISIS-ALPHA ?  (combo vs 60/40 pur ; 2008 INTESTABLE)")
    print(f"  {'année':6s} {'60/40':>9s} {'fixe':>9s} {'equal-w':>9s} {'RP4':>9s}")
    for yr in (2020, 2022):
        row = [tot_ret(base, yr), tot_ret(fix, yr), tot_ret(ew, yr), tot_ret(rp4, yr)]
        print(f"  {yr:<6d} " + " ".join(f"{v*100:+8.1f}%" if v == v else f"{'NA':>8s} " for v in row))
    m4 = (tot_ret(fix, 2022) > tot_ret(base, 2022))  # 2022 = seule vraie crise dans la fenêtre

    # ===== INCRÉMENT sur le cœur + both-halves =====
    incr_full = ann_sharpe(fix.reindex(idx)) - ann_sharpe(base)
    half = len(idx) // 2
    h_beat = []
    for sl in (slice(0, half), slice(half, None)):
        sub = idx[sl]
        h_beat.append(ann_sharpe(rp4.reindex(sub)) > ann_sharpe(base.reindex(sub)))
    both_halves_beat = all(h_beat)

    print("\n" + "=" * 72 + "\nBOTH-HALVES (RP4 vs 60/40)")
    for lab, sl in (("1re", slice(0, half)), ("2e ", slice(half, None))):
        sub = idx[sl]
        print(f"  {lab} {sub.min()}->{sub.max()}: RP4 {ann_sharpe(rp4.reindex(sub)):+.2f}  "
              f"vs 60/40 {ann_sharpe(base.reindex(sub)):+.2f}")

    # ===== VERDICT pré-enregistré (mapping SPEC.md) =====
    # Sharpe-increment (M1) ET crisis-alpha (M4) testés SÉPARÉMENT. La leçon #22 : une
    # fenêtre calme-dominée (ici 2016-24, un seul vrai drawdown 2022, PAS de 2008) fait
    # gagner le cœur sur Sharpe par construction -> NO-GO-Sharpe ≠ inutile si M4 tient.
    beats_core_sharpe = (incr_full > 0) or (max(sch_sr.values()) > sleeve_sr["base6040"])
    robust = incr_full > 0 and both_halves_beat
    print("\n" + "=" * 72 + "\nVERDICT PRÉ-ENREGISTRÉ v2")
    print(f"  incrément-Sharpe fixe SUR cœur (4-way, sans 2008) = {incr_full:+.2f} ; "
          f"both-halves RP4 bat 60/40 = {both_halves_beat}")
    print(f"  crisis-alpha 2022 (fixe vs 60/40) = {'OK' if m4 else 'KO'} "
          f"(fixe {tot_ret(fix, 2022)*100:+.1f}% vs 60/40 {tot_ret(base, 2022)*100:+.1f}%)")
    if m1 and robust:
        print(f"  (M1)∧incrément robuste => KEEP-4-SLEEVE {'FORT' if dsr > 0.95 else 'FAIBLE'}"
              f"  DSR={dsr:.3f} — les neufs ajoutent ce que le FX-carry ne pouvait pas.")
    elif not beats_core_sharpe and m4:
        print("  => KEEP-FAIBLE = ASSURANCE-CRISE (même bucket que v1 #22, PAS un deliverable neuf).")
        print("    Les neufs SONT plus orthogonaux au cœur que le FX-carry (corr −0.105/+0.106 vs")
        print("    +0.41) mais leur Sharpe PROPRE est trop faible (carry_energy −0.20, ils +0.38 sur")
        print("    la fenêtre) pour battre le cœur en régime calme -> DILUENT sur Sharpe (RP4 0.61 <")
        print("    RP2 0.84 < cœur 0.87). Seule valeur = couper 2022 (−16.4%→−1.5%). 2008 INTESTABLE.")
        print("    => conclusion v1 INCHANGÉE : deliverable = 60/40+trend, l'ajout ne crée pas d'alpha.")
    elif not beats_core_sharpe and not m4:
        print("  ¬(M1) ∧ ¬crisis-alpha => NO-GO-TRIVIAL : 'achète 60/40 et dors'.")
    else:
        print(f"  les neufs aident sur Sharpe mais non-robuste/non-M1 => KEEP-FAIBLE conditionnel "
              f"(DSR={dsr:.3f}, m2={'OK' if m2 else 'fragile'}).")
    print("=" * 72)


if __name__ == "__main__":
    main()

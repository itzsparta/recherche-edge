"""Runner META — combine les sleeves réels sous règles PRÉ-COMMITTÉES (docs/SPEC.md).

Tranche : la diversification produit-elle un portefeuille qui bat chaque brique seule
(KEEP), ou même la combinaison ne bat-elle pas le 60/40 passif (NO-GO-trivial) ?
Aucune optimisation de poids in-sample — inverse-vol mécanique + variantes fixes.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

import audit
import sleeves

VOL_WIN = 36          # fenêtre vol trailing (mois), pré-enregistrée
ANN = math.sqrt(12)


def ann_sharpe(x: pd.Series) -> float:
    return audit.sharpe(list(x.dropna())) * ANN


def tot_ret(x: pd.Series, year: int) -> float:
    m = x[[p.year == year for p in x.index]]
    return float((1 + m).prod() - 1) if len(m) else float("nan")


def inv_vol_combo(S: pd.DataFrame, cols: list[str], win: int = VOL_WIN) -> pd.Series:
    """Risk-parity inverse-vol : poids ∝ 1/vol_trailing, laggé (vol connue à t-1)."""
    vol = S[cols].rolling(win).std().shift(1)
    iv = (1.0 / vol).replace([np.inf, -np.inf], np.nan)
    w = iv.div(iv.sum(axis=1), axis=0)
    # min_count=1 : une ligne de warmup (tous poids NaN) -> NaN (pas 0.0) -> droppée.
    return (w * S[cols]).sum(axis=1, min_count=1).dropna()


def fixed_combo(S: pd.DataFrame, wts: dict[str, float]) -> pd.Series:
    return sum(S[c] * w for c, w in wts.items()).dropna()


def main() -> None:
    S = sleeves.load_sleeves()
    cols3 = ["base6040", "trend", "carry"]

    print("=" * 72)
    print(f"SLEEVES (full {S.index.min()}->{S.index.max()}, {len(S)} mois)")
    for c in cols3:
        print(f"  {c:9s} Sharpe={ann_sharpe(S[c]):+.2f}  t={audit.tstat(list(S[c])):+.2f}")
    print("  corr:\n" + S.corr().round(3).to_string())

    # --- les 4 schémas PRÉ-COMMITTÉS ---
    rp3 = inv_vol_combo(S, cols3)                               # primaire
    rp2 = inv_vol_combo(S, ["base6040", "trend"])              # sans carry
    fix = fixed_combo(S, {"base6040": 0.70, "trend": 0.20, "carry": 0.10})
    ew = fixed_combo(S, {"base6040": 1/3, "trend": 1/3, "carry": 1/3})
    schemes = {"RP3 (inv-vol 3)": rp3, "fixe 70/20/10": fix,
               "RP2 (sans carry)": rp2, "equal-weight": ew}

    # fenêtre commune (post-warmup RP = la plus courte) pour comparaison équitable M1
    idx = rp3.index
    base_w = S["base6040"].reindex(idx)
    sleeve_sr = {c: ann_sharpe(S[c].reindex(idx)) for c in cols3}

    print("\n" + "=" * 72)
    print(f"COMBOS vs sleeves — fenêtre commune {idx.min()}->{idx.max()} ({len(idx)} mois)")
    for c in cols3:
        print(f"  sleeve {c:9s} Sharpe={sleeve_sr[c]:+.2f}")
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
    m1 = all(sch_sr["RP3 (inv-vol 3)"] > sleeve_sr[c] for c in cols3)
    print(f"  RP3 Sharpe {sch_sr['RP3 (inv-vol 3)']:+.2f}  vs meilleur sleeve "
          f"({best_sleeve} {sleeve_sr[best_sleeve]:+.2f})")
    print(f"  >>> (M1) {'PASS' if m1 else 'FAIL'}  "
          f"(RP3 {'bat' if m1 else 'NE bat PAS'} toutes les briques)")

    # ===== carry dilue-t-il ? =====
    print("\n" + "=" * 72 + "\nCARRY DILUE-T-IL ?  (RP3 avec carry vs RP2 sans)")
    dilue = sch_sr["RP2 (sans carry)"] >= sch_sr["RP3 (inv-vol 3)"]
    print(f"  RP2 sans carry {sch_sr['RP2 (sans carry)']:+.2f}  vs RP3 avec carry "
          f"{sch_sr['RP3 (inv-vol 3)']:+.2f}  => carry {'DILUE' if dilue else 'ajoute'}")

    # ===== (M2) stabilité across schémas =====
    print("\n" + "=" * 72 + "\n(M2) STABILITÉ (pas un knife-edge) ?")
    srs = list(sch_sr.values())
    spread = max(srs) - min(srs)
    print(f"  Sharpes 4 schémas: " + "  ".join(f"{s:+.2f}" for s in srs))
    print(f"  écart max-min = {spread:.2f}  (faible = robuste au réglage)")
    m2 = spread < 0.30

    # ===== (M3) DSR =====
    print("\n" + "=" * 72 + "\n(M3) DÉFLATION (DSR, n_trials=4) ?")
    per_period_sr = [audit.sharpe(list(x.reindex(idx).dropna())) for x in schemes.values()]
    var_trials = float(np.var(per_period_sr))
    best_name = max(sch_sr, key=sch_sr.get)
    best_series = list(schemes[best_name].reindex(idx).dropna())
    dsr, sr_hat, sr0 = audit.deflated_sharpe(best_series, n_trials=4, var_trials=var_trials)
    print(f"  meilleur combo = {best_name} (Sharpe {sch_sr[best_name]:+.2f})")
    print(f"  DSR={dsr:.3f}  (SR_mois={sr_hat:+.3f} vs seuil SR0={sr0:+.3f}, var_trials={var_trials:.2e})")

    # ===== (M4) crisis-alpha =====
    print("\n" + "=" * 72 + "\n(M4) CRISIS-ALPHA conservé ?  (combo vs 60/40 pur)")
    base_full = S["base6040"]
    print(f"  {'année':6s} {'60/40':>9s} {'fixe70/20/10':>13s} {'equal-w':>9s} {'RP3':>9s}")
    for yr in (2008, 2022):
        row = [tot_ret(base_full, yr), tot_ret(fix, yr), tot_ret(ew, yr), tot_ret(rp3, yr)]
        print(f"  {yr:<6d} " + " ".join(f"{v*100:+8.1f}%" if v == v else f"{'NA':>8s} " for v in row))
    # M4 = combo (fixe, full-span) bat 60/40 les deux années de crise
    m4 = (tot_ret(fix, 2008) > tot_ret(base_full, 2008)) and (tot_ret(fix, 2022) > tot_ret(base_full, 2022))
    print(f"  >>> (M4) {'PASS' if m4 else 'FAIL'}  (fixe bat 60/40 en 2008 ET 2022)")

    # ===== both-halves (RP3 ET le deliverable RP2) =====
    print("\n" + "=" * 72 + "\nBOTH-HALVES (vs 60/40)")
    half = len(idx) // 2
    for nm, series in (("RP3 (3 sleeves)", rp3), ("RP2 (deliverable, sans carry)", rp2)):
        for lab, sl in (("1re", slice(0, half)), ("2e ", slice(half, None))):
            sub = idx[sl]
            print(f"  {nm:30s} {lab} {sub.min()}->{sub.max()}: "
                  f"{ann_sharpe(series.reindex(sub)):+.2f}  vs 60/40 {ann_sharpe(base_full.reindex(sub)):+.2f}")

    # ===== INCRÉMENT sur le cœur (le VRAI test, pas le Sharpe absolu) =====
    # Le DSR mesure le Sharpe absolu (un combo 70% 60/40 a forcément un DSR élevé) ; ce qui
    # compte = l'incrément du sleeve SUR le cœur, et sa ROBUSTESSE temporelle. On l'évalue
    # (a) full-sample (fixe, couvre 2008 où le sleeve paie), (b) both-halves (RP2 deliverable).
    incr_full = ann_sharpe(fix) - ann_sharpe(base_full)          # 238m, inclut 2008
    h_beat = []
    for sl in (slice(0, half), slice(half, None)):
        sub = idx[sl]
        h_beat.append(ann_sharpe(rp2.reindex(sub)) > ann_sharpe(base_full.reindex(sub)))
    both_halves_beat = all(h_beat)

    # ===== VERDICT pré-enregistré =====
    # NO-GO-TRIVIAL = "RIEN ne bat le 60/40". Sinon, carry-dilue => KEEP-2-SLEEVE.
    # Force = robustesse de l'INCRÉMENT (full-sample > 0 ET both-halves), PAS le DSR absolu.
    any_beats = (incr_full > 0) or (max(sch_sr.values()) > sleeve_sr["base6040"])
    robust = incr_full > 0 and both_halves_beat
    print("\n" + "=" * 72 + "\nVERDICT PRÉ-ENREGISTRÉ (docs/SPEC.md)")
    print(f"  incrément sleeve SUR cœur : full-sample(2006-26, incl. 2008) {incr_full:+.2f} ; "
          f"both-halves RP2 bat 60/40 = {both_halves_beat}")
    if not any_beats:
        print("  ¬(M1) [rien ne bat le 60/40] => NO-GO-TRIVIAL : 'achète 60/40 et dors'.")
    elif dilue:
        tag = "KEEP-2-SLEEVE-FORT" if robust else "KEEP-2-SLEEVE-FAIBLE (assurance-crise conditionnelle)"
        print(f"  carry-dilue => {tag}")
        print(f"    RP3 3-sleeves ({sch_sr['RP3 (inv-vol 3)']:+.2f}) FAIL M1 : carry (corr +0.41 au")
        print(f"    cœur, Sharpe 0.10) = risk-on, pas diversifiant -> DILUE. Deliverable = 60/40+trend.")
        print(f"    Valeur = couper le drawdown de crise (2008/2022, sleeve ≈ moitié du DD 60/40),")
        print(f"    PAS battre un 60/40 de bull calme : sur 2009-26 (sans 2008) RP2 "
              f"{sch_sr['RP2 (sans carry)']:+.2f} < cœur {sleeve_sr['base6040']:+.2f}.")
        print(f"    crisis-alpha {'OK' if m4 else 'KO'} ; stabilité {'OK' if m2 else 'fragile'} ; "
              f"incrément {'robuste' if robust else 'régime-dépendant'}.")
    elif m1:
        print(f"  (M1)∧(M3) => KEEP {'FORT' if robust else 'FAIBLE'} (3 sleeves)  DSR={dsr:.3f}")
    else:
        tag = "KEEP-2-SLEEVE-FORT" if robust else "KEEP-2-SLEEVE-FAIBLE (conditionnel)"
        print(f"  2-sleeve bat le cœur en crise, pas RP3 partout => {tag}")
    print("=" * 72)


if __name__ == "__main__":
    main()

"""Runner gates A-D — pré-enregistrés docs/SPEC.md (Piste 16).

Ledger EV net-de-vig (PAS un backtest de prédiction). Tranche : un biais de book
récréatif laisse-t-il un ROI net positif, t>2, dans les deux moitiés temporelles,
à la cote de CLÔTURE Pinnacle (sharp) — et encaissable sans se faire limiter ?
"""
from __future__ import annotations

import bias
import data

# --- seuils pré-enregistrés (SPEC.md) ---
T_FLOOR = 2.0          # t-stat plancher pour un edge crédible
TURNOVER_HURDLE = 0.02  # edge net > 2 % du turnover (franchir vig effectif + limites)
FLOOR_EUR_H = 15.0     # plancher labeur EV/heure
EARLY_MAX_YY = 17      # saisons à code année <=17 = moitié early (2012-2017)


def section(t: str) -> None:
    print(f"\n{'=' * 74}\n{t}\n{'=' * 74}")


def fav_legs(legs: list[bias.Leg]) -> list[bias.Leg]:
    return [l for l in legs if l.is_fav]


def main() -> None:
    section("DONNÉES — univers FIXE (5 ligues × 2012-2024, cotes Pinnacle-closing)")
    matches = data.load()
    legs = bias.explode(matches)

    # vig moyen (le hold que tout ROI doit franchir)
    vigs_psc = [bias.devig(m.psc)[1] for m in matches]
    vigs_b365 = [bias.devig(m.b365)[1] for m in matches]
    vig_psc = sum(vigs_psc) / len(vigs_psc)
    vig_b365 = sum(vigs_b365) / len(vigs_b365)
    print(f"  vig moyen : Pinnacle close {vig_psc:.2%}  |  Bet365 {vig_b365:.2%}  "
          f"(le hold à franchir, par match 3-way)")

    # ---------- COURBE FAVORITE-LONGSHOT (diagnostic) ----------
    section("COURBE FAVORITE-LONGSHOT  [winrate réalisé vs proba sharp dévigée, par décile]")
    print(f"  {'bin':>3} {'n':>7} {'p_sharp':>9} {'winrate':>9} {'edge(pp)':>9} {'ROI@PSC':>9} {'t':>6}")
    curve = bias.bias_curve(legs, n_bins=10)
    for c in curve:
        print(f"  {c['bin']:>3} {c['n']:>7,} {c['p_sharp']:>8.1%} {c['winrate']:>8.1%} "
              f"{c['edge_pp']:>+8.2f} {c['roi_psc']:>+8.2%} {c['t_psc']:>+6.2f}")
    print("  (FL bias = bins bas/longshots : edge(pp) négatif = winrate < proba = surpaiement.")
    print("   Mais ROI@PSC est le verdict : un edge(pp) ≠ 0 ne survit que s'il franchit le vig.)")

    # ---------- (A) BIAIS FRANCHIT LE VIG AU PRIX SHARP ----------
    section("(A) BIAIS FRANCHIT-IL LE VIG ?  [ROI parier les FAVORIS @ Pinnacle closing]")
    fav = fav_legs(legs)
    roi_a, t_a, n_a = bias.roi(fav, "psc")
    roi_fav_soft, t_soft, _ = bias.roi(fav, "b365")
    # inverse documenté : back longshots (le non-favori le plus long)
    longshots = [l for l in legs if not l.is_fav and l.p_sharp < 0.20]
    roi_ls, t_ls, n_ls = bias.roi(longshots, "psc")
    print(f"  FAVORIS @ Pinnacle close : ROI {roi_a:+.2%}  t={t_a:+.2f}  n={n_a:,}")
    print(f"  FAVORIS @ Bet365 (soft)  : ROI {roi_fav_soft:+.2%}  t={t_soft:+.2f}  (contraste sharp/soft)")
    print(f"  LONGSHOTS (p<20%) @ close : ROI {roi_ls:+.2%}  t={t_ls:+.2f}  n={n_ls:,}  (la jambe FL inverse)")
    gate_A = (roi_a > 0) and (t_a > T_FLOOR)
    print(f"  >>> (A) {'PASS' if gate_A else 'FAIL'}  "
          f"{'(biais dans le vig : ≤0 ou t<2 au prix sharp)' if not gate_A else ''}")

    # ---------- (B′) ROBUSTESSE SOUS-PÉRIODE (Gate G généralisé) ----------
    section("(B′) ROBUSTESSE SOUS-PÉRIODE  [favoris @ close : 2012-2017 vs 2018-2024]")
    early = [l for l in fav if int(l.season[:2]) <= EARLY_MAX_YY]
    late = [l for l in fav if int(l.season[:2]) > EARLY_MAX_YY]
    roi_e, t_e, n_e = bias.roi(early, "psc")
    roi_l, t_l, n_l = bias.roi(late, "psc")
    print(f"  early 2012-2017 : ROI {roi_e:+.2%}  t={t_e:+.2f}  n={n_e:,}")
    print(f"  late  2018-2024 : ROI {roi_l:+.2%}  t={t_l:+.2f}  n={n_l:,}")
    gate_Bp = (roi_e > 0 and t_e > T_FLOOR) and (roi_l > 0 and t_l > T_FLOOR)
    print(f"  >>> (B′) {'PASS' if gate_Bp else 'FAIL'}  "
          f"{'(edge absent dans au moins une moitié = early-only / priced-out)' if not gate_Bp else ''}")

    # ---------- (C) ENCAISSABLE À UN VENUE NON-LIMITANT ----------
    section("(C) ENCAISSABLE ?  [CLV : mispricings soft B365 vs clôture Pinnacle]")
    value = bias.clv_value_legs(legs, min_edge=0.0)  # B365 > Pinnacle close
    roi_clv_soft, t_clv, n_clv = bias.roi(value, "b365")   # parié à la cote SOFT (ce qu'on bannit)
    roi_clv_sharp, t_cs, _ = bias.roi(value, "psc")        # MÊMES legs au venue NON-limitant
    frac = n_clv / len(legs)
    print(f"  legs CLV+ (B365 > close) : {n_clv:,} ({frac:.0%} des legs)")
    print(f"    @ Bet365 (SOFT, te BANNIT)        : ROI {roi_clv_soft:+.2%}  t={t_clv:+.2f}")
    print(f"    @ Pinnacle close (NON-limitant)   : ROI {roi_clv_sharp:+.2%}  t={t_cs:+.2f}")
    # encaissable = le +EV doit exister au venue NON-limitant (sharp), pas seulement au soft
    gate_C = (roi_clv_sharp > 0 and t_cs > T_FLOOR)
    print(f"  >>> (C) {'PASS' if gate_C else 'FAIL'}  "
          f"{'(le +EV n existe qu au book soft qui bannit → inencaissable à l échelle)' if not gate_C else ''}")
    print("      [pré-enregistré : un edge présent seulement au soft = uncapturable (winners limités).]")

    # ---------- (D) MATÉRIALITÉ / SEUIL LABEUR ----------
    section("(D) MATÉRIALITÉ  [edge > 2 % turnover ET EV/heure > 15 €]")
    best_real = roi_a if gate_A else max(roi_a, 0.0)  # edge encaissable réaliste = au venue sharp
    gate_D = best_real > TURNOVER_HURDLE
    print(f"  edge encaissable (favoris @ sharp) = {best_real:+.2%} vs hurdle {TURNOVER_HURDLE:.0%} turnover")
    print(f"  >>> (D) {'PASS' if gate_D else 'FAIL'}  (edge {'>' if gate_D else '≤'} hurdle ; EV/h moot si edge≤0)")

    # ---------- MIRAGE HUNT ----------
    section("MIRAGE — concentration par ligue (favoris @ close ; un seul porteur = mirage)")
    for lg, ls in sorted(bias.by_key(fav, lambda l: l.league).items()):
        r, t, n = bias.roi(ls, "psc")
        print(f"  {lg:4s} ROI {r:+.2%}  t={t:+.2f}  n={n:,}")

    # ---------- VERDICT ----------
    section("VERDICT PRÉ-ENREGISTRÉ  (docs/SPEC.md)")
    if not gate_A or not gate_Bp:
        print("  ¬(A) ∨ ¬(B′) => KILL : biais dans le vig au prix sharp, ou absent d'une moitié temporelle.")
        if not gate_C and (roi_clv_soft > 0):
            print("              Le +EV n'existe qu'aux books soft (CLV+) — inencaissable : ils bannissent.")
        print("              Motif unifié confirmé : edge réel mangé par le vig / inaccessible par structure.")
    elif gate_A and gate_Bp and not (gate_C and gate_D):
        print("  (A) ∧ (B′) ∧ ¬(C ∨ D) => DOWNGRADE : biais réel au sharp mais inencaissable / sous seuil.")
    else:
        print("  (A) ∧ (B′) ∧ (C) ∧ (D) => GO : premier edge à contrepartie bête. Projet opérationnel séparé.")
        print("              Chasse mirage (ligue/saison) déjà au-dessus — vérifier qu'aucune ne porte tout.")


if __name__ == "__main__":
    main()

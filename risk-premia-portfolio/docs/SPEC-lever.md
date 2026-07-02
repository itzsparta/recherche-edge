# SPEC — Étude #34 : le deliverable #22 levé — pré-enregistré

> Écrit AVANT tout chiffre (2026-07-02). Suite directe de la question « pourquoi le #22
> plafonne bas ? » : réponse structurelle = on ne monte pas le Sharpe (META v1/v2 : empiler
> dilue), on monte la **vol** jusqu'au maximum tenable. Ceci n'est PAS une chasse à l'edge —
> c'est l'**ingénierie du deliverable existant** : le levier ajoute-t-il du rendement net de
> financement RÉEL sans franchir la ruine ? Aucun nouveau test d'hypothèse de marché : le RP2
> est déjà validé (#22) ; les gates ici sont arithmétiques et conditionnels.

## Portefeuille de base (pré-committé)

- **fixe 80/20** : 0.80 × `base6040` + 0.20 × `trend` (sleeves de `sleeves.load_sleeves()`,
  moteurs déjà validés). 80/20 = milieu de la fourchette deliverable « 15-35 % de sleeve »,
  choisi a priori, PAS optimisé.
- Poids **fixes** (pas d'inverse-vol) → pas de warmup → **2008 dans l'échantillon** (le test
  de ruine l'exige). Fenêtre = full sample commun (~2006-04 → 2026-02, 238 mois).

## Mécanique du levier (pré-committée)

- Levier **constant** L, rebalancé mensuellement : `r_L = L·r_p − (L−1)·c_m`.
- `c_m` = (T-bill 3M + spread)/12, T-bill = ^IRX (fallback FRED TB3MS), moyenne mensuelle.
- Spreads de financement :
  - **+0.40 %/an** (futures/box-spread — le meilleur accessible) → **GATING**.
  - +1.50 %/an (marge broker retail type IBKR) → diagnostic NON-gating.
- **Grille pré-committée : L ∈ {1.0, 1.25, 1.5, 2.0, 3.0}.** Pas d'interpolation, pas
  d'optimisation continue. Levier constant (pas de vol-target dynamique = pas de paramètre de
  fenêtre = pas de forking paths) ; vol-target 10 % en diagnostic non-gating seulement.

## Sélection et gates (figés avant run)

**Contrainte de ruine (sélection de L\*)** : maxDD (équité composée mensuelle, full sample)
**> −35 %**. L\* = le plus grand L de la grille qui respecte la contrainte. Seuil −35 % =
au-delà, abandon comportemental et/ou contraintes de marge réelles ; déclaré arbitraire mais
conservateur, figé avant run.

| Gate | PASS | KILL |
|------|------|------|
| **(A) le levier paie** | net_ann(L\*) ≥ net_ann(1.0) **+ 1.0 point/an** @ spread 0.40 % | sinon — le financement mange l'excès |
| **(B) un levier tenable existe** | L\* > 1.0 | L\*=1 → aucun levier ne respecte la ruine |
| **(C) robustesse temporelle** | net(L\*) > net(1.0) dans **les deux moitiés** de l'échantillon (attrape le régime taux : ZIRP 2009-21 vs 4-5 % 2023+) | une moitié échoue → incrément = artefact de régime de taux |
| **(D) sanity mécanique** | Sharpe_net(L\*) ≥ Sharpe(1.0) − 0.10 | dégradation > coût → erreur de construction |

Verdict : A∧B∧C∧D → **EXTENSION-LEVIER** (deliverable levé à L\*, caveats ci-dessous).
Tout FAIL → **KILL** de l'extension (le deliverable reste non-levé), cause documentée.

## Diagnostics non-gating

- Scénario broker +1.5 % (si seul +0.4 % passe → le deliverable exige futures, à dire).
- Vol-target 10 % (fenêtre 36 m, comme VOL_WIN méta) pour comparaison.
- Années de crise (2008, 2022) à L\* : rendement + DD.
- Check margin-call grossier à L=3.

## Caveats déclarés d'avance (non simulables proprement)

1. **Gap intra-mois** : levier rebalancé mensuellement → le DD mensuel sous-estime le pire
   intra-mois (path-dependency, appels de marge en cours de mois).
2. **Granularité petit compte** : la mise en œuvre futures (MES ~33 k$, micro-treasury)
   impose des paliers grossiers sous ~50 k€ — L réalisé ≠ L cible.
3. Le levier n'est **pas un edge** : même bêta, même Sharpe (moins le financement), plus de
   vol. L'étude chiffre le plafond, elle ne le perce pas.

## Prior honnête (écrit avant run)

Excès du RP2 au-dessus du cash ~6-8 %/an full-sample → A devrait passer à +0.4 %. Ruine :
DD 60/40 peak-trough ~−30 %, le sleeve le coupe → RP2 ~−20-25 % ; L=1.5 → ~−30-37 % : L\*
probable ∈ {1.25, 1.5}. C est le gate le plus incertain (financement 2023+ à ~5 % vs ZIRP).
Issue la plus probable : EXTENSION modeste (+1.5-3 pts/an) à L\* 1.25-1.5, avec le caveat
« futures obligatoires, paliers petit compte ». Ce serait la réponse chiffrée à « plafonne
bas » : plafond levé ≈ 9-11 %/an net, pas plus, DD ~−30 %.

## Sortie

`run_lever.py`, `docs/FINDINGS-lever.md`. Commit spec avant code, commit findings après run.
Data taux : cache `data/irx.csv` (^IRX yfinance, fallback FRED TB3MS).

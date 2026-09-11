# FINDINGS — Étude #36 : vol-target du deliverable levé — **KILL artefact**

**Verdict (2026-09-11) : KILL artefact (¬G1 ∧ ¬G3).** La « domination sur les trois axes » du
diagnostic #34 était **entièrement un artefact de fenêtre** : le warmup 36 m retirait 2008 de la
série vol-target, pas du levier constant. À fenêtre égale et à volatilité égale, le vol-target ne
fait **pas mieux** qu'un levier constant — et **pire** dès que 2008 est dans l'échantillon. Le
deliverable reste **#22 levé à L=1,5 constant (#34)**.

Pré-enregistré : [`SPEC-voltarget.md`](SPEC-voltarget.md) (commit `298450c` avant tout code).
Reproduire : `python run_voltarget.py`.

## 1. Le confound fenêtre, chiffré

Sanity : diagnostic #34 reproduit **à l'identique** (+11,48 %, Sharpe 1,16, maxDD −17,2 %, début 2009-04).

| Levier constant 1,5 | Sharpe | maxDD |
|---|---|---|
| fenêtre FULL 2006-04→ (celle du tableau #34) | 0,91 | −29,0 % |
| **même fenêtre que le VT (2009-04→)** | **1,16** | −21,5 % |

Le Sharpe 1,16 du vol-target = **exactement** celui du levier constant sur la même fenêtre. Les
+0,25 de Sharpe « gagnés » = 2008 retiré d'un seul côté de la comparaison.

## 2. À volatilité égale (C\*), coût |ΔL| inclus

| W | début | VT net / Sharpe / DD | C\* (L_c) net / Sharpe / DD | ΔSharpe |
|---|---|---|---|---|
| 12 | 2007-04 | +9,46 % / 0,83 / −31,6 % | (1,52) +10,27 % / 0,90 / −29,3 % | **−0,072** |
| 24 | 2008-04 | +9,24 % / 0,83 / −32,3 % | (1,46) +10,20 % / 0,92 / −26,7 % | **−0,086** |
| **36** | 2009-04 | +11,46 % / 1,16 / −17,2 % | (1,41) +11,63 % / 1,18 / −20,2 % | **−0,017** |
| 48 | 2010-04 | +10,98 % / 1,09 / −17,7 % | (1,44) +11,09 % / 1,10 / −20,6 % | **−0,011** |

## Gates

| Gate | Résultat | |
|---|---|---|
| R ruine | maxDD −17,2 % > −35 % | PASS |
| **G1** ΔSharpe ≥ +0,10 | **−0,017** | **FAIL** |
| G2 DD ≤ C\* | −17,2 % vs −20,2 % | PASS |
| **G3** ΔSharpe > 0 ∀W | **négatif sur les 4** | **FAIL** |
| G4 both-halves | H1 −0,007 / H2 −0,034 | FAIL |
| G5 DSR(n=4) | **0,253** (t=−0,24, écart −0,17 %/an) | FAIL |

## Ce qui se passe dans les crises (le prior écrit avant run se vérifie)

| | 2008 VT vs C\* | 2020 VT vs C\* | 2022 VT vs C\* |
|---|---|---|---|
| W12 | **−22,8 % vs −16,0 %** | +7,6 vs +16,9 | −14,7 vs −18,8 |
| W24 | **−20,8 % vs −12,7 %** | +12,5 vs +16,3 | −13,9 vs −18,0 |
| W36 | — (hors fenêtre) | +13,9 vs +15,7 | −14,7 vs −17,3 |

- **Krach rapide (2008, 2020)** : la vol laggée est basse juste avant → le vol-target arrive
  **sur-levé** (L jusqu'à 3,0 en W12) et prend le choc en plein ; puis il est dé-levé pendant le
  rebond. Pire des deux côtés.
- **Crise lente (2022)** : la vol monte progressivement → dé-levage à temps, −3 à −4 pts de perte
  en moins. C'est le seul endroit où il aide, et c'est ce qui fait passer G2 sur W36/W48 (fenêtres
  sans 2008).
- Le gain de drawdown n'est donc pas une propriété générale : il dépend du **type** de crise, et
  s'inverse sur le krach le plus sévère de l'échantillon.

## Diagnostics

- Levier constant à L̄ égal ≈ même Sharpe que le VT sur chaque fenêtre (W36 : 1,17 vs 1,16).
- Cap 2× (W36) : ΔSharpe +0,003 → zéro, pas de sauvetage par le cap.
- Coût de rotation total 0,30 pt sur 17 ans : ce n'est pas le coût qui tue, c'est l'absence de gain.
- Pire mois VT : 2018-10, −9,1 % à L=2,31 (vol laggée basse après 2017 → levier max au mauvais
  moment, même mécanique en petit).

## Place dans le programme

Conforme à Cederburg et al. (2020) et Liu-Tang-Zhou (2019) : le gain du vol-management s'évapore
sans look-ahead, et plus encore sur un portefeuille déjà diversifié dont le sleeve trend est
lui-même vol-targeté. **Erratum #34** : le diagnostic « vol-target domine sur les trois axes »
était un artefact de fenêtre (note ajoutée dans `FINDINGS-lever.md`). Leçon méthodo : **toute
comparaison entre variantes à warmup différent se fait sur la fenêtre commune** — le piège était
déjà connu (warmup inverse-vol du META v1) et a quand même passé dans un diagnostic.

**Bilan : 36 études, 0 edge déployable.** Deliverable inchangé : 60/40 + trend (80/20) levé
**1,5× constant**, net ~+10 %/an, maxDD −29 % (2008 inclus). Il n'y a plus de multiplicateur
identifié dans le marché : le reste est **capital × temps** (conclusion #34, confirmée).

# SPEC — Étude #36 : vol-target du deliverable levé — pré-enregistré

> Écrit le 2026-09-11, AVANT le run #36. **Pas un test à l'aveugle** : le diagnostic non-gating
> de #34 a déjà été vu (vol-target 10 %, fenêtre 36 m, cap 3× : net +11,48 %, Sharpe 1,16,
> maxDD −17,2 %, L moyen 1,46, vs levier constant 1,5 : +10,04 %, 0,91, −29,0 %). Cette spec ne
> « redécouvre » donc pas l'effet : elle teste s'il **survit** aux trois confounds qui peuvent
> l'avoir fabriqué. Discipline 2 sens [[feedback-gate-override]].

## Les trois confounds du diagnostic #34 (identifiés avant run)

1. **Fenêtre (le plus grave).** Vol glissante 36 m laggée ⇒ warmup 37 mois ⇒ la série vol-target
   démarre ~2009-05 et **exclut 2008**, alors que le levier constant (−29 %, 2008 −15,8 %) l'inclut.
   « Domine sur les 3 axes » compare deux échantillons différents. Même piège que le warmup
   inverse-vol du META v1 (#22 : « RP exclut 2008, exactement la crise où le trend paie »).
2. **Quantité de levier ≠ timing.** Un Sharpe plus haut peut venir du niveau moyen de risque, pas
   du fait de dé-lever quand la vol monte. Il faut comparer à **risque égal**.
3. **Coût du rebalancement.** Le diagnostic ne facturait pas la rotation du levier (|ΔL|).

## Construction (pré-committée)

- Portefeuille `r_p` = **identique #34** : 0,80 × `base6040` + 0,20 × `trend` (`sleeves.load_sleeves()`),
  2006-04 → 2026-02.
- Vol-target : `σ_t = std(r_p sur W mois jusqu'à t−1)·√12` ; `L_t = min(0,10 / σ_t, 3,0)`.
  **Cible 10 % et cap 3× = ceux du diagnostic** (pas re-choisis).
- Rendement : `r_VT = L_t·r_p − (L_t−1)·c_t − k·|L_t − L_{t−1}|`, avec `c_t` = (T-bill 3M +
  0,40 %)/12 si `L_t > 1` (emprunt), T-bill/12 si `L_t < 1` (cash placé, pas de spread) ;
  **k = 5 bps** de notionnel par unité de ΔL (futures, conservateur).
- **Comparateur gating = levier constant à VOLATILITÉ ÉGALE** (`C*`) : `L_c` tel que
  vol(r_C*) = vol(r_VT) sur la **même fenêtre** (appariement ex-post standard Moreira-Muir). À
  risque égal, un Sharpe supérieur = timing, pas quantité de levier. **Aucun coût facturé à C*** →
  biais contre le vol-target (conservateur).
- Diagnostics : constant à levier moyen égal (`L̄`), constant 1,5 (deliverable actuel), cap 2×.

## Fenêtres (pré-committées)

**W ∈ {12, 24, 36, 48} mois**, chacune comparée à son C* sur **sa propre fenêtre commune**. W=36 =
primaire (celle du diagnostic). W=12 démarre 2007-05 → **contient 2008** ; W=24 démarre 2008-05 →
contient le krach sept-nov 2008. n_trials = **4** pour la DSR.

## Gates (figés avant run)

| Gate | PASS si |
|---|---|
| **R ruine** | maxDD(VT, W=36) > −35 % |
| **G1 timing paie** | Sharpe(VT) − Sharpe(C\*) **≥ +0,10** (W=36) |
| **G2 drawdown** | maxDD(VT) ≥ maxDD(C\*) (pas pire à risque égal, W=36) |
| **G3 robuste à W** | Sharpe(VT_W) > Sharpe(C\*_W) pour **les 4** fenêtres (dont W=12/24 avec 2008) |
| **G4 both-halves** | ΔSharpe > 0 sur chaque moitié de la fenêtre W=36 |
| **G5 anti-overfit** | DSR(série `r_VT − r_C*`, W=36, n_trials=4) > 0,95 |

## Verdict (mapping pré-enregistré)

| Cas | Verdict |
|---|---|
| R ∧ G1 ∧ G2 ∧ G3 ∧ G4 ∧ G5 | **PROMOTION** : vol-target remplace le levier constant 1,5 comme règle du deliverable. |
| R ∧ G1 ∧ G2 ∧ G3 ∧ G4 ∧ ¬G5 | **DOWNGRADE** : timing réel et robuste mais non significatif → deliverable reste L=1,5 constant ; vol-target = option de confort (DD) sans preuve statistique. |
| ¬G1 ∨ ¬G3 | **KILL artefact** : la domination du diagnostic venait de la fenêtre sans 2008 et/ou de la quantité de levier, pas du timing. |
| autre (¬R, ¬G2, ¬G4) | **KILL** : cause documentée (ruine / DD / régime). |

## Prior honnête (écrit avant run)

Littérature partagée : Moreira-Muir (2017) trouvent un gain du vol-management sur actions et
facteurs ; Cederburg et al. (2020) et Liu-Tang-Zhou (2019) montrent qu'il s'évapore largement en
out-of-sample / sans look-ahead de l'échelle. Sur un portefeuille déjà diversifié et en partie
vol-targeté (le sleeve trend l'est), le gain de timing doit être **modeste**. Une vol laggée sur
36 m réagit **lentement** aux krachs rapides (sept. 2008, mars 2020) : W=12/24 peuvent arriver
**sur-levés** dans 2008 (vol pré-crise basse). Attendu : ΔSharpe à risque égal ≈ +0,00 à +0,10,
la majeure partie du « +0,25 » du diagnostic = confound fenêtre. **Issue la plus probable : KILL
artefact ou DOWNGRADE.** Une PROMOTION serait une surprise.

## Caveats déclarés

1. C\* apparié ex-post (standard de comparaison, pas une stratégie tradable).
2. Gap intra-mois non simulé ; à L=3 le pire mois compte (rapporté).
3. Granularité petit compte (MES ~33 k$) : L_t continu non réalisable sous ~50 k€ (hérité #34).

## Sortie

`run_voltarget.py`, `docs/FINDINGS-voltarget.md`. Commit spec avant code, findings après run.

# Piste 6 — Carry (crypto perp funding) : pré-test (PRÉ-ENREGISTRÉ)

> Écrit **avant** de voir le moindre résultat. Tout changement après avoir vu un chiffre =
> overfit, interdit. (Leçon FINDINGS orderflow.)

Sous-piste testée : **cash-and-carry sur le funding des perpetuals crypto**. (FX / commodités =
autres sous-pistes carry, non traitées ici.)

## Hypothèse
Les perpetual futures sont tethered au spot par un **funding** (Binance : toutes les 8 h). Quand
les longs dominent (demande de levier haussier), ils **paient** les shorts. Une position
**delta-neutre long spot + short perp** encaisse le funding. Historiquement positif en moyenne
(le levier crypto penche long). Deux conditions :
1. le funding est **positif et significatif** (le carry existe), ET
2. il est **worth-harvesting net** pour un solo — au-dessus d'un hurdle risk-free+, **et
   positif dans chaque régime** (pas seulement le bull 2021).

**Market-neutral par construction** : le spot et le perp annulent le mouvement de prix → le
drift directionnel **ne peut pas** fabriquer le P&L (la structure relative-value de la piste 7
est ici intrinsèque). C'est le seul *kind* différent du programme : on **porte**, on ne *time* pas.

## Univers & données (FIXE)
- **BTCUSDT** perp (primaire), **ETHUSDT** (robustesse). Funding 8 h via
  `fapi.binance.com/fapi/v1/fundingRate` (urllib, paginé), depuis le lancement (~2019-09).
- `markPrice` du flux funding = proxy prix (sert au test bull-beta, pas de fetch séparé).
- Régimes : 2019-20 (lancement/COVID), **2021 bull**, **2022 bear**, 2023-24 (reprise/hausses
  taux), 2025-26. Multi-régime par construction.

## Stratégie & coût (FIXE)
- Long spot + short perp. `carry_jour = Σ funding 8 h du jour` (collecté par le short perp).
- **Coût = rééquilibrage mensuel** (gestion du risque de liquidation du perp), **0.1 %
  round-trip / rebal × 12 = 1.2 %/an**. Le funding est collecté **passivement** → le coût n'est
  PAS un turnover quotidien (contraste avec l'overnight 5a). `net_ann = gross_ann − 0.012`.

## Métriques + critères PRÉ-ENREGISTRÉS
**(A) le carry existe — requis**
- `mean(carry_jour) > 0` ET **t-stat > 2** sur l'historique complet.

**(B) worth-it net, robuste régime — TOUT requis**
- `net_ann > 5 %` (hurdle : proxy risk-free 2020-26 + prime pour le risque exchange/liquidation),
- `net_ann > 0` dans **chaque** régime (test **fair-weather** : le carry paie-t-il aussi en bear
  2022, ou s'éteint-il quand le levier long disparaît ?),
- **drop-régime** : `net_ann` full reste **> 5 %** en retirant le meilleur régime (pas un
  artefact mono-bull).

Diagnostics (non-gating) : `corr(carry_jour, rendement BTC)` (concentration bull) ; ETHUSDT.

## Décision pré-enregistrée
- **(A) ∧ (B) ⇒ GO** vers le protocole complet (exécution réelle, modélisation liquidation,
  walk-forward). **Premier non-kill possible du programme.**
- **(A) ∧ ¬(B) ⇒ DOWNGRADE** : carry réel mais **fair-weather / compressé / sous le hurdle** —
  pas worth le risque exchange pour un solo. **Verdict plausible.**
- **¬(A) ⇒ KILL** : funding non positif/significatif (implausible — sanity).

## Caveat (pré-enregistré)
- Un seul exchange (risque FTX), capacité $ modeste, **risque de liquidation du short perp**
  sur un squeeze non modélisé finement (le rééq. mensuel + la marge le bornent, mais c'est un
  vrai risque de queue). markPrice ≈ spot (le vrai cash-and-carry porterait le spot réel).

## Implémentation
- `data_funding.py` (urllib paginé, cache `data/`), `carry.py`, `run_carry.py`. Audit :
  `deflated_sharpe`/`tstat` portés depuis factor-harvest. Sortie : `docs/FINDINGS-funding.md`.

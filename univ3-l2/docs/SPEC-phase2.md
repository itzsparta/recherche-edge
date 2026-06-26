# SPEC Phase-2 — #29 : backtest LP-V3 delta-hedgé discret (resserrer le résidu)

**Pré-enregistré 2026-06-26, AVANT le sim.** Gates figés ici ([[feedback-gate-override]]).

## But

Phase-1 (#29) a rendu **GO/WIN** sur les axes mesurés (frais>LVR, JIT<4 %, net APR ~30 %, robuste-régime),
résidu unique = **fuite d'exécution du hedge**. Discipline #26 = **épuiser le simulable avant le live**.
La fuite a deux parts :
- **simulable** (ce sim) : (a) **funding** du short ETH perp, (b) **slippage du hedge discret** (gamma
  non-couvert entre 2 rebalancements), (c) **temps hors-range** d'un LP à range fini (zéro frais quand
  le prix sort) ;
- **live-only** (Phase-3, hors sim) : qualité de fill réelle, **part de frais réelle** de TA position,
  MEV sur tes propres rebalancements.

Ce sim **resserre** le réalisé ; il ne le **clôt** pas. Honnêteté : un PASS ici ne prouve pas le GO,
il retire seulement les tueurs simulables ; un FAIL le tue sans dépenser de capital.

## Mesure (sur vrai chemin ETH 2024, horaire)

LP V3 concentré, demi-largeur `w`, recentré quand le prix sort de `[P0(1−w), P0(1+w)]`. Maths V3
closed-form (amount0/amount1 par tick-range). Delta-hedge = short `amount0` ETH en perp, **rebalancé
toutes les H heures** (discret). Sur le chemin réel :
- **slippage discret** = P&L(hedge discret H-heures) − P&L(hedge continu pas-à-pas) ≤ 0 (coût de gamma).
- **funding** = somme du funding 8h Binance ETHUSDT payé/reçu sur le notional short (short ⇒ reçoit si
  funding>0).
- **frac_in_range** = part du temps où le prix est dans la bande (= part du temps à toucher des frais).
- **réalisé_net_APR** = `frac_in_range · net_contLVR_APR(#29)` − `gas_L2` − `|slippage discret|` − `drag funding`.
  (`net_contLVR_APR` = le net-de-LVR-continue mesuré en #29, conservativement plafonné à 30 %.)

Données : Binance klines ETHUSDT 1h + fundingRate 8h (free), 2024. Réutilise l'esprit infra carry #6.

## Gates (figés AVANT le sim)

| Gate | Test | Seuil |
|---|---|---|
| **P1** survie discrétisation | réalisé_net_APR, hedge **horaire**, meilleur `w∈{2,5,10 %}` | > **10 %** |
| **P2** stress | réalisé_net du **pire mois** ETH 2024 (plus gros move) | **> 0** (pas wipé par un spike) |
| **P3** funding | drag funding annualisé du short hedge | **≤ 15 %/an** (sinon mange l'edge) |

**KILL Phase-2 si P1 échoue** (discrétisation+funding font passer sous le hurdle) → le GO Phase-1 tombe
avant tout capital. PASS P1∧P2∧P3 → le résidu se réduit au **live-only**, et on passe au protocole live.

## Prior honnête

P1 passe (funding ETH 2024 majoritairement positif → short **reçoit**, slippage horaire modéré), **P2 =
le vrai risque** (un mois à gap violent peut être net−). Si P2 échoue, le verdict devient « prime réelle
mais à variance mensuelle négative » = DOWNGRADE vers risk-premium-saisonnier, pas KILL.

## Caveats

- `net_contLVR_APR` repris de Phase-1 (mesuré agrégé) ; le sim ajoute la discrétisation/funding/hors-range
  par-dessus, il ne re-dérive pas les frais (la part-de-frais réelle reste live-only).
- Hedge sur perp = base/funding ≠ spot ; tail de liquidation non modélisé (hedge petit vs notional LP).

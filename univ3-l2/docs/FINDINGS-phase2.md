# FINDINGS Phase-2 — #29 : backtest hedge-discret (resserrer le résidu simulable)

**Verdict : aucun tueur SIMULABLE trouvé ; funding = tailwind ; le GO-pending-live de Phase-1 TIENT.**
Phase-2 ne **valide pas la magnitude** (elle reste la mesure agrégée de Phase-1 + le test live) ; elle
retire les tueurs simulables un par un et trouve même un vent porteur (funding crédit).

Pré-enregistré : [`SPEC-phase2.md`](SPEC-phase2.md). Code : [`../hedge_sim.py`](../hedge_sim.py)
(klines+funding Binance free, cache `../data/`).

## Ce que Phase-2 PROUVE (composantes robustes, valides géométriquement / mesurées)

| Composante | Mesure 2024 | Lecture |
|---|---|---|
| **Funding** du short ETH perp | **+17,15 %/an** sur notional plein → **~+8 %** sur LP ~48 %-hedgé | **CRÉDIT, pas drag** (P3 PASS). Le hedge est *payé* en 2024. |
| **Temps hors-range** (frac_in_range) | w=2 %→94 % ; w=5 %→**98,7 %** ; w=10 %→99,7 % | drag hors-range **petit** pour range modéré. |
| **Recentrages / an** | 543 / 117 / **30** | gas L2 **trivial** (×$0,05). |
| **Hedge tx** (rebalance journalier) | ~0,5-1,4 %/an | petit. |
| **Stress pire mois** (Nov 2024, **+47 %** ETH) | net mensuel **+2,6 %**, frac 98 % | **non wipé par un spike** (P2 PASS). Le hedge neutralise la direction. |

→ **Aucun tueur simulable** : funding aide, hors-range petit, gas trivial, et même le plus gros move
mensuel de 2024 reste net-positif.

## Ce que Phase-2 NE prouve PAS (honnêteté — le piège évité)

Le cross-check **`pnl_h`** (P&L d'un LP hedgé en continu, sans frais = la LVR réalisée) sort à **−105 %
(w=10 %) à −458 % (w=2 %)** par an — **bien au-delà** de la LVR-agrégée du pool (31 %, #29). Raison : un
range **serré** est bien plus **concentré** que la distribution moyenne du pool → sa LVR/\$ (et ses frais/\$)
explosent ensemble. **Conséquence** : ma colonne `REALISE` (~25-36 %) **combine le net-AGRÉGÉ 30 % de
Phase-1 avec les coûts d'un LP CONCENTRÉ = SEMI-CIRCULAIRE** — elle ressort *≈ l'input + funding* et **ne
valide pas indépendamment** la magnitude. Je ne la présente donc PAS comme une validation
[[feedback-gate-override]] (ne pas fabriquer une fausse précision pour conforter le GO).

**Ce qu'il faut en retenir, correctement** : la forme déployable est un LP **modéré / pro-rata** (range
large ou mimant la distribution du pool), où le **net-agrégé mesuré (#29, 30 %) s'applique directement** à
un petit LP au prorata, hedgé pour retirer la direction. Un range **serré** n'est PAS gratuit (LVR de
concentration) — il faut alors capturer les frais de concentration correspondants, ce que seul le **live**
mesure (part-de-frais réelle).

## Le résidu restant = strictement LIVE-ONLY

Phase-2 a vidé le simulable. Restent les inconnues que **seul un déploiement live** mesure :
1. **part-de-frais réelle** de TA position (vs le net-agrégé du pool) — la grande inconnue ;
2. **qualité de fill** des rebalancements (range + hedge) ;
3. **MEV** sur tes propres transactions.

C'est le pendant de #26 — mais ici le résidu est **résoluble par un test cheap et réversible** (et le prior
est favorable : produits ALM Arrakis/Gamma nettent double-digit), pas par une clause contractuelle mortelle.

## Verdict

**GO-pending-live, INCHANGÉ.** Phase-2 confirme : (a) funding = vent porteur 2024, (b) coûts simulables
(hors-range, gas, tx) petits pour un range modéré, (c) résistance au pire mois — **aucun tueur simulable**.
La magnitude (~15-30 % réalisé selon la part-de-frais réelle) et le résidu live-only se tranchent par le
**protocole live** ([`RUNBOOK-live.md`](RUNBOOK-live.md)). Caveat majeur honnête : **chemin unique 2024
haussier** (ETH +41 %) ; le funding-crédit et le stress-test ne couvrent qu'un régime — un marché à funding
négatif (bear prolongé) retournerait le tailwind funding en drag (mais l'edge LP de base — frais>LVR — a
tenu en 2022 crash, Phase-1).

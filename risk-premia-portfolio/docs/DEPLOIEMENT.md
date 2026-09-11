# DÉPLOIEMENT — le deliverable 60/40 + trend levé 1,5× (#22 / #34)

**Statut (2026-09-11) : plan opérationnel, PAS une étude.** Aucun edge testé, aucun gate, aucun
verdict. Le deliverable est déjà validé (#22 construction, #34 levier constant 1,5, #36 vol-target
KILL). Ce document répond à « comment le détenir concrètement », avec un contrôle chiffré que les
véhicules achetables reproduisent le backtest : `python deploy_check.py` (descriptif, poids fixés
par arithmétique avant run, cache `data/deploy_px.csv`).

## Ce qu'on déploie

Deliverable = 1,5 × (0,80 × 60/40 + 0,20 × trend), financé ≈ T3M + 0,40 %
= **1,2 × 60/40 + 0,3 × trend**. Backtest 2006-04 → 2026-02 : **+10,0 %/an net, maxDD −29 %**
(USD, 2008 inclus). Rappel : ce n'est pas un edge, c'est du bêta bien construit (primes réelles +
assurance trend) avec un levier modéré (FINDINGS-lever, caveat 4).

## Véhicules retenus (UCITS, achetables depuis la France)

| Rôle | ETF | ISIN | Place / ticker | TER | Encours |
|---|---|---|---|---|---|
| **Cœur = 1,5× un 60/40** | WisdomTree US Efficient Core UCITS ETF — 90 % actions US + 60 % futures Treasury | IE000KF370H3 | Xetra `WTEF` (EUR), Borsa Italiana `NTSX` (EUR) | 0,20 % | ~18 M€ |
| **Trend** | iMGP DBi Managed Futures Fund R EUR UCITS ETF | LU2951555403 | Euronext Paris `DBMFE` | 0,75 % | ~151 M€ (+115 M€ classe USD) |
| Trend (secours) | BNP Paribas Easy Managed Futures UCITS ETF | LU3307218399 | Euronext Paris `FOLOW`, Xetra `EEAU` | 0,60 % | ~28 M€, lancé 2026-05-29 |

**Allocation : 80 % WTEF + 20 % DBMFE.**
- 0,80 × 1,5 = **1,2 × 60/40** : exactement le cœur du deliverable (arithmétique, pas un fit).
- 20 % DBMFE ≈ **0,30 sleeve trend à volatilité égale** (mesuré : 0,19 — vol DBMF 11,4 % vs
  sleeve 7,1 %). Le reste du capital tombe naturellement au bon niveau.
- **Le levier est DANS les fonds** (futures) : aucun emprunt personnel, aucun appel de marge,
  perte maximale = capital investi. Aucun seuil de capital (pas de contrat à 33 k€).

**Enveloppe : compte-titres.** Le PEA ne peut porter ni l'un ni l'autre (fonds irlandais/
luxembourgeois, actions US, futures). Courtier : accès Xetra ou Borsa Italiana pour WTEF
(Interactive Brokers : oui), Euronext Paris pour DBMFE (tout courtier français).

## Contrôle : les véhicules reproduisent-ils le backtest ?

Versions US (historique plus long ; les UCITS en sont les clones) :

| Comparaison | Fenêtre | corr | β | TE/an | écart/an |
|---|---|---|---|---|---|
| NTSX vs 1,5 × 60/40 financé T3M+0,40 % | 2018-09→2026-02 (89 m) | **+1,00** | 0,99 | 1,6 % | −0,33 % |
| DBMF vs sleeve trend | 2019-06→2026-02 (80 m) | +0,63 | 1,01 | 8,8 % | +6,61 % |
| **80 NTSX / 20 DBMF vs deliverable #34** | 2019-06→2026-02 (80 m) | **+0,98** | 0,98 | 2,5 % | +0,99 % |

| Année | implémentable 80/20 | deliverable backtest |
|---|---|---|
| 2020 | +16,3 % | +16,7 % |
| 2021 | +20,1 % | +19,1 % |
| 2022 | −17,1 % | −18,5 % |
| 2023 | +16,3 % | +15,3 % |
| 2024 | +17,7 % | +14,3 % |
| 2025 | +17,9 % | +18,2 % |

Clones UCITS vs US (en EUR, historique court) : WTEF vs NTSX corr **+0,96** sur 34 m (TE 3,9 %,
en partie décalage d'heures de clôture EU/US) ; DBMFE vs DBMF corr **+0,87** sur 16 m seulement
(TE 5,3 %).

**Lecture :**
- **NTSX = réplique quasi parfaite du cœur levé.** Il coûte −0,33 %/an de plus que le backtest,
  qui intégrait déjà le financement à T3M + 0,40 % : le levier via ce fonds coûte ce que #34
  supposait. Pas d'avantage à le refaire soi-même en futures.
- **DBMF n'est PAS notre sleeve trend** (corr 0,63) : il réplique l'indice des CTA (univers plus
  large, devises incluses), pas notre TSMOM 12 m sur 9 ETF. Il a battu le sleeve de +6,6 %/an sur
  2019-26 : **chance d'échantillon (2022), pas une attente.** Hypothèse de travail : Sharpe trend
  ~0,4-0,5 (backtest + littérature CTA), comme pour le sleeve.
- **L'ensemble colle** : même vol (12,7 %), corr 0,98, drawdown −20,1 % vs −21,5 % sur la fenêtre.

## Vu en euros (non couvert)

Les deux lignes portent du dollar ; WTEF n'a pas de classe couverte EUR. Deliverable backtesté
converti en EUR (EURUSD mensuel) :

| | ann | vol | Sharpe | maxDD | 2008 | 2020 | 2022 |
|---|---|---|---|---|---|---|---|
| USD | +10,04 % | 11,0 % | 0,91 | −29,0 % | −15,8 % | +16,7 % | −18,5 % |
| EUR non couvert | +10,24 % | 10,8 % | 0,95 | **−20,6 %** | −12,0 % | +8,2 % | −13,4 % |

Le dollar a historiquement monté pendant les crises (corr −0,44 avec le portefeuille), ce qui a
coupé le drawdown EUR. **Ne pas compter dessus** : le change a coûté 8,5 pts en 2020, et en avril
2025 le dollar et les actions US ont baissé ensemble. Planifier pour **−30 %**, pas −20 %.

## Règles d'exploitation

1. **Achat initial** : 80 % WTEF / 20 % DBMFE.
2. **Apports** : chaque versement va sur la ligne sous-pondérée (rééquilibrage sans vente).
3. **Rééquilibrage forcé** seulement si WTEF sort de la bande **75-85 %** ; sinon rien. (Le
   backtest rééquilibre mensuellement ; la bande est une simplification déclarée, non testée —
   effet attendu négligeable sur deux lignes.)
4. **Aucune vente en drawdown.** −29 % est dans l'historique (2008). Il n'y a pas de règle de
   sortie : le plan se tient à travers une baisse de −30 %, ou il ne se commence pas.
5. **Hors portefeuille** : ne pas y mettre l'argent nécessaire à moins de ~5 ans.
6. **Contrôle annuel** (~15 min) : encours de WTEF (risque de fermeture, voir plan B) ; tracking
   DBMFE (relancer `deploy_check.py` après avoir supprimé le cache `data/deploy_px.csv`).

## Plans B

- **WTEF ferme** (18 M€ d'encours = risque réel ; une liquidation rend le cash, ce n'est pas une
  perte mais une sortie forcée) : WisdomTree Global Efficient Core UCITS (IE00077IIPQ8, actions
  mondiales au lieu de US — ≠ backtest, mécanique à vérifier au moment du remplacement), ou la
  route futures ci-dessous.
- **DBMFE ferme ou dérive** : BNP Easy Managed Futures (`FOLOW`) — trop jeune (2026-05) pour être
  validé aujourd'hui.
- **Route futures** (seulement si capital ≳ 100 k€ ET envie d'opérer) : ETF non levés (S&P 500 +
  Treasury 7-10 ans) + surcouche 0,5× via MES (≈ 5 $ × S&P ≈ 37,9 k$ ≈ 32,7 k€ de notionnel par
  contrat) et micro 10Y Yield (DV01 10 $, à vendre pour être long obligations). À 100 k€ la
  surcouche actions (0,30 × K = 30 k€) = 1 contrat ; en dessous, le levier réel ne colle plus à la
  cible. Coût pas meilleur que NTSX, plus rolls trimestriels, marge et risque d'appel.
  **Non recommandé.**

## Attente réaliste : capital × temps

Le +10 %/an du backtest contient le bull US post-2009 (FINDINGS-lever, caveat 3 : si l'excès futur
du 60/40 n'est que de 4 %, le levier 1,5 rend ~5,5 % net). Fourchette de planification :
**~5,5 % à 10 %/an**, drawdowns de −30 % possibles.

| Versement | 10 ans @5,5 % / @10 % | 20 ans @5,5 % / @10 % | 30 ans @5,5 % / @10 % |
|---|---|---|---|
| 200 €/mois | 32 k€ / 40 k€ | 86 k€ / 144 k€ | 178 k€ / 413 k€ |
| 500 €/mois | 79 k€ / 100 k€ | 214 k€ / 359 k€ | 445 k€ / 1 031 k€ |

(Nominal, avant impôts, sans capital initial.) Sur 10 ans, le montant versé pèse plus que le
rendement ; sur 30 ans, c'est la durée. Aucun levier de marché identifié ne bat ces deux-là (36
études, 0 edge déployable).

# FINDINGS — Étude #37 : stress séculaire du deliverable levé — **CONFIRMÉ + 2 caveats**

**Verdict (2026-09-11) : CONFIRMÉ** — G0, A, C, D, E PASS ; B et R FAIL (non tueurs par
construction, pré-enregistré). Le levier 1,5× **n'est pas un artefact de 2006-2026** : il ajoute
**+1,76 pt/an composé** sur 1926-2006, et reste positif dans 86 % des fenêtres de 15 ans. Mais deux
chiffres de risque du déploiement étaient **mono-régime** :
- **stagflation 1966-81** : le levier coûte −0,87 pt/an, et le portefeuille reste **sous le cash
  pendant 16 ans** (réel −1,65 %/an à L = 1,5) ;
- **la règle de ruine −35 % n'est vraie que sur 2006-26** : −38 % nominal / −48 % réel en 1973-74,
  −71 % dans un 1929 (L = 1 lui-même : −54 %).

Côté trend, le premium est **prouvé** (t = 5,4 sur 41 ans, net de coûts : le KILL #1 était un
défaut de puissance) mais **en déclin significatif** (Welch t = 3,2 ; Sharpe net 0,00 depuis 2016).

Test contre [`SPEC-secular.md`](SPEC-secular.md) (commit `2a19aad`, avant tout pull). Reproduire :
`python run_secular.py` (caches `data/` : Ken French, FRED LTGOVTBD/GS10/DGS10/CPIAUCNS, AQR).

## Construction (rappel de la spec)

- 6040 proxy = 0,6 × marché US Ken French + 0,4 × obligation 10 ans au pair reconstruite (FRED
  `LTGOVTBD` jusqu'en 1953-04, `GS10` ensuite), rebalancé mensuellement. Cash et financement = RF
  Ken French (+0,40 %/an).
- Trend = RF + k × TSMOM AQR − 1 %/an, k = 0,579 (vol sleeve #22 7,23 % / vol TSMOM 12,49 %) ;
  **à plat (= RF) avant 1985**.
- Deliverable = 0,80 × 6040 + 0,20 × trend, levier constant L, comme #34.

## G0 — fidélité des proxys (W0 = 2006-04 → 2026-02) : PASS

| Comparaison | corr | Niveau |
|---|---|---|
| **6040 proxy vs `base6040` #22** | **+0,973** | CAGR 7,93 % vs 8,32 % (−0,39 pt) |
| Marché Ken French vs SPY | +0,995 | |
| Oblig. 10 ans vs IEF | +0,724 → **+0,991** en taux de fin de mois (post-hoc) | |
| Deliverable proxy L = 1,5 vs #34 | +0,963 | CAGR 9,70 % vs 9,85 % |
| RF Ken French vs TB3MS | | 1,59 vs 1,62 %/an |

La corrélation obligataire de 0,72 vient des taux FRED **mensuels = moyennes du mois** (rendement
reconstruit en retard sur IEF). Refait avec le taux de fin de mois (DGS10 quotidien, 1962+) : 0,991,
et G0 passe à 0,995. Aucun gate ne bouge (B : −0,88 au lieu de −0,87). Avant 1962 il n'existe pas de
taux quotidien : le timing obligataire reste lissé (sans effet sur les rendements cumulés).

## Grilles (financement RF + 0,40 %)

**W1 — hors fenêtre séculaire, 1926-07 → 2006-03 (957 mois)**

| L | CAGR | arith | vol | Sharpe excès | maxDD | pire mois |
|---|---|---|---|---|---|---|
| 1,00 | +8,29 % | +8,44 % | 9,6 % | +0,50 | −53,5 % | −13,9 % |
| 1,25 | +9,20 % | +9,54 % | 11,9 % | +0,49 | −62,9 % | −17,4 % |
| **1,50** | **+10,05 %** | +10,64 % | 14,3 % | +0,49 | **−70,6 %** | −20,8 % |
| 2,00 | +11,59 % | +12,83 % | 19,1 % | +0,48 | −81,9 % | −27,8 % |

**W2 — stagflation, 1966-01 → 1981-12 (192 mois)** — cash : +6,84 %/an

| L | CAGR | réel | Sharpe excès | maxDD |
|---|---|---|---|---|
| 1,00 | +6,12 % | −0,83 %/an | −0,03 | −23,3 % |
| **1,50** | **+5,24 %** | **−1,65 %/an** | −0,05 | **−37,6 %** |
| 2,00 | +4,17 % | | −0,06 | −49,5 % |

**W3 — deliverable complet (trend AQR), 1985-01 → 2006-03 (255 mois)**

| L | CAGR | vol | Sharpe excès | maxDD |
|---|---|---|---|---|
| 1,00 | +12,37 % | 8,2 % | +0,91 | −14,5 % |
| **1,50** | **+15,86 %** | 12,3 % | +0,89 | **−22,1 %** |
| 2,00 | +19,24 % | 16,3 % | +0,89 | −29,5 % |

W0 (proxys) : L = 1,5 → CAGR +9,83 %, maxDD −30,5 % (#34 : −29,0 %). W4 (1985-01 → 2026-05) :
L = 1,5 → +13,02 %, maxDD −30,5 %.

## Gates

| Gate | Fenêtre | Résultat | Verdict |
|---|---|---|---|
| **G0** fidélité | W0 | corr 0,973, écart CAGR −0,39 pt | **PASS** |
| **A** levier paie hors fenêtre | W1 | CAGR(1,5) − CAGR(1) = **+1,76 pt/an** (hurdle +1,00) | **PASS** |
| **B** stagflation | W2 | **−0,87 pt/an** | **FAIL** (non tueur) |
| **C** ruine avec trend | W3 | maxDD(1,5) = −22,1 % ; L\*_W3 = 2,0 | **PASS** |
| **R** ruine séculaire | W1 | maxDD(1,5) = **−70,6 %** ; L = 1 : −53,5 % ; L\*_W1 = aucun | **FAIL** (non tueur) |
| **D** puissance du trend | W4 | t = **+5,42** ; Sharpe net 0,84 [IC95 0,53 ; 1,15] ; W3 +1,43 ; 2006 → +0,31 | **PASS** |
| **E** sleeve hors fenêtre | W3 | Sharpe 0,91 vs 6040 0,70 = **+0,21** | **PASS** |

Mapping de la spec → **CONFIRMÉ** (A ∧ C ∧ D ∧ E), plus deux caveats chiffrés :
- ¬B : coût du levier en stagflation → `DEPLOIEMENT.md` ;
- ¬R avec L = 1 aussi sous −35 % → la règle de ruine est une propriété de 2006-26 ; le DD de
  planification (« −30 % ») est remplacé par le chiffre séculaire.

## Diagnostics (non-gating)

**Épisodes** (L = 1 / L = 1,5 nominal ; L = 1,5 réel ; maxDD à 1,5 dans l'épisode) :

| Épisode | L = 1 | L = 1,5 | L = 1,5 réel | DD |
|---|---|---|---|---|
| 1929-09 → 1932-06 | −53,5 % | −70,6 % | −62,6 % | −69,5 % |
| 1940-1951 (répression) | +118,2 % | +196,5 % | +56,7 % | −19,6 % |
| 1973-74 | −17,9 % | −31,8 % | −44,1 % | −36,1 % |
| oct. 1987 | −11,9 % | −18,2 % | −18,4 % | — |
| 2000-02 | −2,4 % | −10,0 % | −16,2 % | −21,0 % |
| 2008 | −11,5 % | −18,0 % | −18,1 % | −22,9 % |
| 2022 | −11,5 % | −18,0 % | −23,0 % | −18,0 % |

- **Fenêtres glissantes de 15 ans** (1926-2026, 1 017 fenêtres) : CAGR(1,5) < CAGR(1) dans
  **14,1 %** ; < +1 pt dans 25,6 % ; médiane **+2,38 pt** ; pire −1,25 pt (fenêtre finissant en 1982-07).
- **Financement broker** RF + 1,5 % : W1 +1,17 pt, W2 −1,45 pt, W3 +2,86 pt.
- **Sous-facteurs AQR** (brut, 1985-2026) : TSMOM Sharpe 0,98 (t 6,3) ; matières premières 0,65 ;
  actions 0,55 ; taux 0,61 ; devises 0,55 — tous t > 3,5. Le premium n'est pas porté par une classe.
- **corr(sleeve AQR, trend #22)** = 0,741 (W0) ; **corr(sleeve AQR, DBMF)** = 0,607 (2019-06 →,
  84 mois) — même ordre que DBMF vs #22 (0,63) : trois implémentations du même premium.
- W3 avec trend à plat : incrément du levier +2,38 pt au lieu de +3,49, maxDD −26,6 % au lieu de
  −22,1 % → le trend porte ~1/3 de l'incrément et ~4 pts de DD.

## Post-hoc (non pré-enregistré — ne change aucun gate)

1. **Taux de fin de mois** : voir G0 (corr IEF 0,72 → 0,99 ; B −0,88).
2. **Drawdown d'après-guerre** (1945 → 2026, creux 1974-09) : L = 1 : −23,3 % nominal / −35,6 %
   réel ; **L = 1,5 : −37,6 % nominal / −48,3 % réel**. Même chiffre depuis 1950.
3. **Déclin du trend, testé comme différence** (critique 2 : pas deux t lus séparément) : net
   **+9,61 %/an** sur 1985-2006 contre **+2,38 %/an** depuis 2006-04, **Welch t = 3,24**. Par
   sous-période : Sharpe net 0,63 (2006-2015), **0,00 (2016-2026, 125 mois)**.

## Lecture

1. **Le levier est une propriété du siècle, pas de la fenêtre.** +1,76 pt/an sur 80 ans avant
   #34, positif dans 86 % des fenêtres de 15 ans, médiane +2,4 pt. Le prior (« pile ou face à
   +0,8-0,9 ») sous-estimait l'excès du 60/40 sur le cash au XXe siècle.
2. **Ce qui le tue : un régime où le portefeuille ne bat pas le cash.** 1966-81 : les obligations
   font moins que les T-bills, les actions à peine plus → Sharpe excès ≈ 0 pendant 16 ans, et le
   levier multiplie une prime nulle moins son coût. La pire fenêtre de 15 ans finit en 1982.
   Aucun ajustement de L n'y change rien : c'est le cœur qui manque d'un actif réel.
3. **Les chiffres de risque du déploiement étaient ceux d'un seul régime.** « Planifier pour
   −30 % » : un 1973-74 à ce levier = −38 % nominal, **−48 % en pouvoir d'achat** ; un 1929 =
   −71 %. La règle de ruine −35 % de #34 n'est satisfaite par aucun L, même 1, dès que 1929 est
   dans l'échantillon : elle décrivait la fenêtre, pas la stratégie.
4. **Trend : réel, et en déclin.** Le KILL #1 (t = 1,87) était un défaut de puissance : sur 41 ans,
   net d'1 %/an de coûts, t = 5,4. Mais la baisse de rendement est elle-même significative
   (t = 3,2), et la dernière décennie est nulle. Le gate E (+0,21) a été mesuré dans l'ère forte
   (1985-2006). Verdict pré-enregistré inchangé (D passe tel qu'écrit) ; l'hypothèse de travail
   « Sharpe trend 0,4-0,5 » de `DEPLOIEMENT.md` est ramenée à **~0,3, rôle principal = assurance**
   (post-hoc, étiqueté).

## Errata de méthode (portée programme)

1. **`audit.sharpe` = Sharpe de rendement TOTAL, pas d'excès.** Sans effet sur les stratégies
   long/short (le cash n'y entre pas), il **surestime tout Sharpe long-only ou levé de ~RF/σ**.
   #34 : L = 1 **1,01 → 0,78** en excès ; L = 1,5 **0,91 → 0,76**. Le gate D de #34 (« 0,91 vs
   0,91, limite exacte ») était un artefact de la métrique : en excès, 0,76 vs 0,68, passage net.
   **Aucun verdict ne change**, mais les Sharpe du deliverable affichés (0,91 ; 0,95 en EUR) sont
   à lire −0,15 à −0,2.
2. **Taux FRED mensuels = moyennes du mois** : toute reconstruction obligataire future doit
   partir d'un taux de fin de mois (DGS10) quand il existe.

## Caveats

1. **Trend à plat avant 1985** : 1929-32 et 1973-74 sont des bornes **pessimistes** (Hurst-Ooi-
   Pedersen 2017 : trend positif dans les deux). Le −71 % surestime probablement le pire cas.
2. **Financement anachronique** : futures/box n'existaient pas avant 1982 — on teste la stratégie
   avec la technologie d'aujourd'hui.
3. **Biais du survivant US** : le XXe siècle américain est le meilleur marché connu ; le test est
   optimiste sur les actions.
4. Proxys sans frais ; nominal USD ; hors fiscalité ; gap intra-mois non simulé.

## Conséquences appliquées

- `DEPLOIEMENT.md` : section « Stress séculaire (#37) », règle 4 réécrite (DD de planification
  −40 % après-guerre, −70 % type 1929), coût stagflation, hypothèse trend ~0,3, note Sharpe excès.
- `FINDINGS-lever.md` : erratum Sharpe + renvoi ici.
- Déploiement (80 WTEF / 20 DBMFE) **inchangé**.

## Place dans le programme

Premier test du deliverable hors de son régime (critique 1 de la revue du 2026-09-11). Il confirme
la **construction** (levier et sleeve paient hors fenêtre) et réécrit le **risque** : ce que #34
présentait comme la ruine (−35 %) était la météo de 2006-26. Il tranche aussi la critique 2 sur
son cas le plus important : le trend « non prouvé » de #1 était prouvable, il fallait 41 ans — et
ces 41 ans montrent un premium qui s'érode. **Bilan : 37 études, 0 edge déployable** ; deliverable
confirmé, son risque réel écrit. Suites possibles (non lancées) : actif réel dans le cœur contre la
stagflation (nouvelle spec), vol-target rapide P2 (#38), dividende PEA P3 (#39).

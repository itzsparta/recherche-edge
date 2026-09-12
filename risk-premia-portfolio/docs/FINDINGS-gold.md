# FINDINGS — Étude #41 : l'or dans le cœur du deliverable — ASSURANCE 1970s SEULEMENT

**Verdict (2026-09-12) : ASSURANCE 1970s SEULEMENT**, mapping pré-enregistré appliqué sans override.
G0, A, B, D PASS ; **C FAIL**.

- Dans les années 1970, 10 % d'or comble réellement le trou stagflation (+1,51 pt/an réel).
- Mais après 1982, dans chaque choc d'inflation (1982, 1989-91, 2021-23), l'or fait **moins bien que la
  même part laissée en cash** : −2,61 pts cumulés sur 47 mois.
- La protection mesurée est donc la réévaluation post-Bretton Woods (n = 1), pas une couverture
  répétable.
- **L'or n'est pas ajouté.** Le déploiement reste 80 WTEF / 20 DBMFE et le caveat stagflation reste dans
  [`DEPLOIEMENT.md`](DEPLOIEMENT.md).

Test contre [`SPEC-gold.md`](SPEC-gold.md) (commit `463fdd4`, avant tout pull de l'or). Reproduire :
`python run_gold.py` (sortie dans `data/run_gold_output.txt`, gitignoré).

## Données

- **Or** : Banque mondiale, Pink Sheet mensuel, colonne `Gold`, 1960-01 → 2026-08.
  - **Amendement de version** : l'URL d'origine servait un fichier gelé au 2025-01-03 (fin 2024-12). Elle
    est remplacée par la version du 2026-09-02, même source et même fichier (le document 2026 du portail
    Banque mondiale).
  - Garder l'ancien fichier aurait coupé le rallye 2025-26 : un biais contre l'or. L'ancienne version est
    gardée en cache.
- **Contrôle datahub** : corrélation mensuelle +1,000 avec la Banque mondiale, c'est la même série.
- **P0** = deliverable proxy #37 (levier 1,5), avec une obligation reconstruite sur le DGS10 de fin de
  mois. Fin commune : 2026-07.

## G0 — fidélité

Sur 2004-12 → 2026-06 (259 mois), face à GLD :
- corrélation des rendements 12 mois glissants **+0,975** ;
- écart de CAGR +0,59 pt (les frais de GLD sont de 0,40 %) ;
- → **PASS**.

La corrélation mensuelle n'est que de +0,622 : c'est l'effet de la moyenne mensuelle, déclaré en caveat 1
de la SPEC. C'est ce qui justifiait un gate en 12 mois.

## Gates (g = 10 %)

| Gate | Résultat | Verdict |
|---|---|---|
| **A** protection, 1968-04 → 1981-12, réel | CAGR réel Pg −0,31 % vs P0 −1,83 % : **+1,51 pt/an** | PASS |
| **B** coût, 1982-01 → 2026-07 | Pg +12,56 % vs P0 +13,25 % : **−0,69 pt/an** (limite −0,75) | PASS, de justesse |
| **C** mieux que le cash dans les chocs modernes | 47 mois d'inflation > 5 % : Σ(Pg − Pc) = **−2,61 pts** | **FAIL** |
| **D** efficacité face au cash, 1982+ | Sharpe excès Pg 0,819 vs Pc 0,804 | PASS, de justesse |

## Le gate qui décide : C, épisode par épisode

| Choc d'inflation (après 1982) | Mois | Σ(Pg − Pc) |
|---|---|---|
| 1982 (fin de la désinflation Volcker) | 10 | −0,23 pt |
| 1989-91 | 13 | −1,70 pt |
| 2008 | 3 | −0,55 pt (reste du total) |
| 2021-23 | 21 | −0,13 pt |

L'or fait moins bien que le cash dans **chacun** des épisodes. En 2022, Pg et Pc finissent à égalité à
−16,8 % : le gain du « 10 % d'or » y est entièrement celui du dé-risquage (piège 2 de la SPEC).

## Deux PASS fragiles, et c'est le récent qui les porte

- **B sans 2024-26** (1982-01 → 2023-12) : −0,83 pt/an, **sous la limite**. Seul le rallye 2024-2026
  (achats des banques centrales) fait passer B.
- **Par sous-période**, B et D changent de signe :

  | Sous-période | B | Sharpe Pg vs Pc | Lecture |
  |---|---|---|---|
  | 1982-2001 | −1,93 pt/an | 0,772 < 0,837 | D échoue |
  | 2002-2026 | +0,27 pt/an | 0,872 > 0,778 | D passe |

  L'or n'est pas un diversifieur stable : il dépend d'un régime (baissier sur 20 ans, puis haussier sur 24).
- Glissant 15 ans : Pg > P0 dans **32 %** des fenêtres seulement. La pire fait −1,97 pt/an (fin 1999-06).

## Ce que l'or fait bien : le drawdown des années 1970

| Épisode | P0 / Pg / Pc nominal | P0 / Pg réel |
|---|---|---|
| 1973-74 | −31,5 / **−19,9** / −27,6 % | −43,9 / **−34,4** % |
| 1979-80 | +38,4 / +49,6 / +37,0 % | +8,5 / +17,4 % |
| Krach de l'or 1980-82 | +7,9 / **+0,0** / +10,6 % | −13,4 / −19,8 % |
| 2008 | −17,5 / −15,5 / −15,7 % | −17,6 / −15,6 % |
| 2013 | +22,2 / +16,2 / +19,9 % | +20,4 / +14,5 % |
| 2022 | −18,7 / −16,8 / −16,8 % | −23,6 / −21,9 % |

MaxDD réel sur 1968-2026 : P0 −47,9 %, **Pg −39,0 %**, Pc −44,2 %. Ce gain vient de 1973-74, soit
exactement l'épisode de la réévaluation.

**Or seul** :

| Période | CAGR (réel) | Sharpe excès | Corr P0 |
|---|---|---|---|
| 1968-1981 | +18,8 % (+10,4 %) | 0,53 | −0,04 |
| 1982-2026 | +5,0 % (+1,85 %) | 0,16 | −0,01 |

Toujours décorrélé de P0, mais sa prime après la réévaluation est faible.

## Grille de poids (diagnostic)

| g | A réel | B | C Σ S | Sharpe Pg / Pc |
|---|---|---|---|---|
| 5 % | +0,76 | −0,34 | −1,31 | 0,813 / 0,804 |
| **10 %** | +1,51 | −0,69 | −2,61 | 0,819 / 0,804 |
| 15 % | +2,25 | −1,04 | −3,92 | 0,822 / 0,804 |
| 20 % | +2,97 | −1,41 | −5,22 | 0,821 / 0,804 |

C est négatif **à tous les poids** : aucun g ne sauve le verdict. Au-delà de 10 %, B échoue aussi.

## Lecture

1. **Le trou stagflation reste ouvert, et l'or ne le ferme pas de façon répétable.** Sa protection de
   1973-74 est réelle, mais elle vient d'un prix libéré après 37 ans de parité. Dans les chocs
   d'inflation d'un monde à monnaie flottante (1990, 2022), il n'a pas fait mieux que du cash.
2. **Le vrai substitut testé est le cash.** Si l'on veut moins de risque stagflation, dé-lever (Pc) fait
   aussi bien dans les chocs modernes, sans pari sur le régime de l'or.
3. **Piège déjoué.** Sans le contrefactuel cash (gate C) et sans l'arrêt à 2023-12, l'étude aurait
   conclu « AJOUTER » : A, B et D passent, et 2024-26 flatte l'or.

## Conséquences

- **Déploiement inchangé** : 80 % WTEF / 20 % DBMFE. Le caveat stagflation de `DEPLOIEMENT.md` reste,
  avec une note sur #41.
- **Actif réel suivant ?** Les obligations indexées sur l'inflation (TIPS, OATi) sont l'actif
  stagflation par construction, mais leurs séries ne commencent qu'en 1997-1998, sans stagflation dans
  l'échantillon : non testable proprement en gratuit. Les matières premières en futures (rendement
  total) exigent des données payantes (P4). **Rien à lancer ici.**

## Caveats

1. Moyennes mensuelles (vol et maxDD de l'or adoucis) ; USD nominal ; ETC d'aujourd'hui appliqué au
   passé ; hors fiscalité.
2. S ne compte que 47 mois en 3,5 épisodes : C est un test de direction, pas de significativité. Mais
   son signe est le même dans chaque épisode.

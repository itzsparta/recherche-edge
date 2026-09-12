# FINDINGS — Étude #40 : capture de dividende PEA sur les exonérés de TTF — UNTESTABLE (sous-puissant)

**Verdict (2026-09-12) : UNTESTABLE**, mapping pré-enregistré appliqué sans override.
- Les données petites valeurs sont **fiables** : G0 par période PASS sur les trois périodes.
- Mais le segment déployable (y ≥ 3 %, turnover ≥ 200 k€, 2015+) ne compte que **85 événements**, sous
  le seuil de puissance de 100 fixé d'avance.
- Les gates A à D n'ont **pas été lus** (règle de la SPEC). Pas question d'abaisser N ni le filtre de
  liquidité pour rendre le test lisible : ce serait un override dans le sens favorable.

Test contre [`SPEC-smallcap.md`](SPEC-smallcap.md) (commit `9dd1675`, avant tout pull). Reproduire :
`python data.py small` puis `python run_small.py` (sortie dans `data/run_small_output.txt`, gitignoré).

## Données

- **Univers** : 575 ISIN FR sur Euronext Paris (réglementé) et Euronext Growth.
  - 120 exclus : liste TTF officielle du [BOFiP au 1er décembre 2025](https://bofip.impots.gouv.fr/bofip/9789-PGP.html/identifiant=BOI-ANNX-000467-20251217),
    121 noms sans ISIN, appariés aux noms Euronext (103 à l'identique, 17 par alias saisi à la main).
    Tarkett est sur la liste mais plus coté.
  - Reste **455 titres** (188 réglementé, 267 Growth), dont 438 ont des prix et **218 versent un
    dividende** depuis 2009.
- **Événements** :
  - 2 522 ex-dates ≥ 2009 ;
  - −247 nuits invalides, dont beaucoup d'ouvertures sans volume ou égales à la veille, typiques des
    titres cotés au fixing ;
  - −73 à y > 10 % ;
  - −1 à |AR| > 15 % ;
  - soit **2 201 événements** sur 212 noms (1 447 réglementé, 754 Growth).

## G0 par période (prérequis)

| Période | n | ρ̂ nuit J | ρ̂ placebos J−3 … J−1 / J+1 … J+3 | Verdict |
|---|---|---|---|---|
| P1 2009-2014 | 739 | 0,865 | +0,02 +0,02 +0,13 / −0,03 +0,00 +0,08 | PASS |
| P2 2015-2020 | 719 | 0,888 | −0,01 +0,03 −0,02 / +0,03 +0,10 −0,00 | PASS |
| P3 2021 → | 743 | 0,923 | +0,01 −0,08 +0,03 / +0,09 +0,03 +0,04 | PASS |

Les dates sont alignées sur toutes les périodes, contrairement au SBF 120 avant 2009 (#39).

## Prérequis N : l'entonnoir (comptages seulement, aucun rendement lu)

| Étape (2015+) | Événements |
|---|---|
| Tous | 1 462 |
| y ≥ 3 % | 664 |
| dont turnover médian [J−60, J−2] ≥ 200 k€ | **85** (27 noms) |
| dont turnover < 200 k€ | 579 (87 %) |

Le turnover médian des événements à y ≥ 3 % est de **25 k€ par jour**. Le segment déployable compte 3 à 11
événements par an (7, 8, 3, 7, 6, 5, 3, 11, 9, 10, 9, 7 de 2015 à 2026), et 130 toutes périodes
confondues.

## Lecture (limitée à ce que le verdict autorise)

1. **Le jour ex des petites valeurs ressemble à celui des grandes.** ρ̂ = 0,87-0,92, contre 0,89 pour le
   SBF 120 sur 2013-2026 (#39). La thèse capacité prédisait un ρ nettement plus bas là où les
   arbitragistes ne vont pas : rien de tel au niveau agrégé. C'est cohérent avec la borne d'arbitrage
   ou avec un price-setter domestique, sans que cette mesure permette de les départager.
2. **L'ensemble d'opportunités est minuscule.** Le rendement élevé vit dans des titres à 25 k€ de volume
   quotidien, où un ordre de particulier fait le prix du fixing : c'est le mur de capacité de #3. Là où
   l'on peut exécuter, il reste ~7 trades par an.
3. **Même un PASS pèserait peu.** Arithmétique indicative, non mesurée : 7 trades × une capture nette de
   quelques dixièmes de point ≈ 1-3 % par an sur un capital immobilisé quelques nuits seulement.

## Conséquences

- **Rien à déployer.** Re-test possible à **SPEC inchangée** quand le segment atteindra 100 événements,
  soit environ 2028 au rythme de 7-10 par an. C'est un rendez-vous, pas une piste active.
- **Axe « statut fiscal » quasi clos.** L'avantage du PEA le jour ex existe (ρ ≈ 0,9) ; la TTF le reprend
  là où il y a du volume (#39), et il est trop rare pour compter là où il n'y en a pas (#40).
- **Leçon méthode.** Le seuil N pré-enregistré a fait son travail : il empêche de lire un t sur 85
  événements concentrés sur 27 noms. Le G0 par période, ajouté après #39, passe proprement ici.

## Caveats

1. Survivorship plus fort qu'en #39 : univers = cotés aujourd'hui.
2. Profondeur réelle des fixings non observée ; le turnover quotidien n'est qu'un proxy.
3. Exonération TTF de 2025 appliquée à toute la période.

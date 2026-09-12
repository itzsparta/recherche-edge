# FINDINGS — Étude #39 : capture de dividende sous statut PEA — KILL friction (TTF)

**Verdict (2026-09-12).**
- Mapping pré-enregistré : **DOWNGRADE** (G0, A, B, D PASS ; C FAIL).
- Verdict retenu : **KILL friction** (override défavorable, section « Pourquoi l'override »).

Le jour ex, le cours ne baisse pas de tout le dividende : ρ ≈ 0,85-0,90 sur 2013-2026, t > 3. Le
détenteur exonéré capte donc réellement quelque chose. Mais sur les données fiables (2009+), le segment
tradable (y ≥ 3 %) rapporte +0,07 % net par événement (t = 0,60), et **−0,08 % depuis 2015**. La TTF
seule (0,40 % à l'achat) mange la capture. Hors TTF, le même segment ferait +0,32 % (t = 4,55) :
c'est le seul obstacle.

Test contre [`SPEC.md`](SPEC.md) (commit `880db7b`, avant tout pull). Reproduire : `python data.py`
puis `python run.py` (sortie complète dans `data/run_output.txt`, gitignoré).

## Données

- Univers : 120 constituants actuels du SBF 120, dont **110 à ISIN FR**, 109 avec prix (Neoen retiré de
  la cote). 2 250 ex-dates ≥ 2005 → **2 173 événements retenus**, 103 noms.
- Filtres : nuit invalide −44 ; y > 10 % −33 ; |AR| > 15 % −0 (le filtre ne mord pas).
- **Amendements de source (règles inchangées).**
  - Wikipedia FR n'a pas de table de composants et la page Euronext est derrière un antibot → table
    Wikipedia DE (nom + ISIN), appariée à la liste publique des actions Euronext Paris.
  - Atos et Worldline appariés par nom (ISIN changé après opération sur capital).
- **Choix d'implémentation.** La « moyenne » des gates est celle de la série des cohortes mensuelles, qui
  porte aussi le t. La moyenne par événement est rapportée à côté.

## Gates (mapping pré-enregistré)

| Gate | Résultat | Verdict |
|---|---|---|
| **G0** fidélité | ρ̂ nuit J = 0,702 ; placebos J−1 = −0,12, J+1 = −0,03 | PASS (poolé, voir post-hoc) |
| **A** existence | AR +0,645 %, t = 8,84 (242 mois) ; croissant en y : +0,29 / +0,61 / +1,15 % | PASS |
| **B** déployable | y ≥ 3 %, net de 0,60 % : +0,550 %, t = 3,76 (143 mois, 735 évts) | PASS |
| **C** maturité | < 2015 : +1,372 % (62 m) ; 2015+ : **−0,079 %** (81 m) ; Welch t = 4,79 | **FAIL** |
| **D** concentration | hors top-5 (GFC, VIV, ORA, SW, ACA) : +0,382 %, t = 2,49 | PASS |

Par segment de rendement :

| Segment | n | y médian | AR (cohortes) | ρ̂ |
|---|---|---|---|---|
| y < 1,5 % | 659 | 0,98 % | +0,291 %, t = 5,09 | 0,790 |
| 1,5-3 % | 779 | 2,17 % | +0,606 %, t = 8,79 | 0,608 |
| y ≥ 3 % | 735 | 4,31 % | +1,150 %, t = 7,86 | 0,771 |

## Post-hoc : le sous-échantillon 2005-2008 est inexploitable

Signal d'alerte : ρ̂ = 0,33 sur 2005-2012/07, contre 0,93 sur 2017-2025. Le ρ̂ en clôture-clôture est
même **négatif** en 2005 et 2006 (−0,08 et −0,05) : le cours *monterait* le jour ex, ce qui est
impossible économiquement. Scan d'alignement, ρ̂ nuit par nuit autour de la date yfinance :

| Période | n | J−5 … J−1 | **J** | J+1 … J+5 |
|---|---|---|---|---|
| 2005-2008 | 390 | +0,02 −0,36 +0,20 +0,06 −0,37 | **+0,16** | −0,10 +0,09 −0,05 −0,16 +0,04 |
| 2009-2012 | 368 | −0,05 +0,06 +0,11 +0,01 −0,04 | **+0,68** | +0,05 −0,13 −0,01 +0,02 −0,06 |
| 2013-2026 | 1 415 | −0,01 −0,01 −0,02 −0,04 −0,05 | **+0,89** | −0,02 +0,04 +0,04 −0,03 +0,05 |

Avant 2009, la baisse du dividende n'apparaît sur **aucune** nuit de J−5 à J+5 : dates ou montants
yfinance inexploitables. Sur ces événements, AR ≈ y par construction, ce qui gonfle le segment à haut
rendement (2005-2008 : +3,33 % net par événement, un chiffre sans rapport avec un marché réel). À partir
de 2009, l'alignement est net.

Par période :

| Période | n | ρ̂ overnight | ρ̂ clôt.-clôt. | Segment B net (0,60 %) |
|---|---|---|---|---|
| 2005-2008 | 390 | 0,155 | 0,730 | +3,330 %, t = 11,45 (artefact) |
| 2009-2012/07 | 356 | 0,720 | 0,934 | +0,659 %, t = 1,49 |
| 2012/08-2014 | 204 | 0,750 | 0,834 | −0,332 %, t = −2,12 |
| 2015-2016 | 204 | 0,807 | 0,748 | −0,342 %, t = −2,12 |
| 2017-2020 | 387 | 0,862 | 0,657 | +0,197 %, t = 1,27 |
| 2021-2025/03 | 430 | 1,019 | 1,121 | −0,175 %, t = −2,12 |
| 2025/04 → | 202 | 0,875 | 0,845 | −0,185 %, t = −1,35 |

Segment y ≥ 3 % sur la partie propre, selon le coût :

| Échantillon | Brut | Hors TTF (0,20 %) | Optimiste (0,44 %) | **SPEC (0,60 %)** |
|---|---|---|---|---|
| 2009+ (640 évts) | +0,671 %, t = 5,65 | +0,471 %, t = 3,96 | +0,231 %, t = 1,95 | **+0,071 %, t = 0,60** |
| 2015+ (430 évts) | +0,521 %, t = 7,38 | +0,321 %, t = 4,55 | +0,081 %, t = 1,14 | **−0,079 %, t = −1,12** |

Net 2015+ par an : négatif 10 années sur 12 (seules 2018 +0,09 % et 2020 +0,68 % sont positives).

## Pourquoi l'override (sens défavorable)

- G0 existait pour garantir l'alignement des dates. Poolé, il passe parce que 2009+ domine
  l'échantillon ; appliqué par période, il échoue en 2005-2008.
- Or le mapping « DOWNGRADE = réel mais décru » repose entièrement sur ce sous-échantillon : le
  « déclin » mesuré par C, c'est la disparition de l'artefact.
- Sur la partie fiable, **B échoue** (t = 0,60), ce qui correspond au cas **A ∧ ¬B = KILL friction**.
- L'override va contre la thèse, pas pour elle ([[feedback-gate-override]]). Le mapping mécanique est
  conservé en tête de fichier pour traçabilité.

## Diagnostics (non-gating, sur tout l'échantillon, donc contaminés avant 2009)

- **Mécanisme.**
  - Pente AR ~ y = +0,167 (t = 10,4), soit ρ marginal 0,83, avec une ordonnée de +0,16 %.
  - Période 2025-04+ (retenue à la source étendue au cum-cum) : ρ̂ 0,875, AR +0,26 %, t = 3,39 sur 18
    mois. Pas de rupture visible.
- **Robustesse du signe.** Toutes les variantes gardent le même signe :
  - clôture-clôture : +0,622 % ;
  - marché = `^FCHI` : +0,729 % ;
  - benchmark médian : +0,683 %.

  L'intraday du jour ex après 2015 est ≈ 0 (+0,03 à +0,08 %) : pas de retour du prix à l'ouverture.
- **Hartzmark-Solomon.** Run-up [J−21, J−1] : −0,50 %, t = −0,94, non significatif. [J, J+5] : +0,81 %,
  mais la fenêtre contient la capture elle-même. Rien à promouvoir.
- **CAGR du segment B** : +10,6 %/an sur 10 % des nuits. Chiffre **non interprétable**, porté par
  l'artefact 2005-2008.

## Lecture

1. **L'arme fiscale existe.** Le prix n'est pas fixé par un investisseur neutre : ρ ≈ 0,85-0,90 depuis
   2013, significativement < 1. Un détenteur exonéré (PEA) récupère ~10-15 % du dividende brut le jour
   ex. C'est la première fois que le programme mesure un avantage propre au statut de résident FR.
2. **L'État reprend exactement cet avantage.** Sur un dividende de 4 %, 0,85 × 4 % laisse 0,6 % de
   capture brute, soit le montant de la TTF (0,40 %) plus le courtage. Même motif que le sous-type 2
   (friction), sauf que la friction est ici fiscale, pas microstructurelle.
3. **Aucune dérive dans le temps sur la partie propre.** ρ̂ oscille entre 0,75 et 1,0 depuis 2009, sans
   tendance nette. Le « déclin » du mapping mécanique était l'artefact des données.

## Conséquences

- **Rien à déployer.** Le PEA reste l'enveloppe des ETF (diversification fiscale du deliverable), pas un
  outil de capture.
- **Porte ouverte par la branche pré-enregistrée.** Hors TTF, la capture tient (+0,32 %, t = 4,55 sur
  2015+). Les sociétés < 1 Md€ de capitalisation sont exonérées de TTF, mais c'est un autre univers
  (étude #40, nouvelle SPEC), avec trois tueurs a priori :
  1. **ρ plus proche de 1** : moins de non-résidents au capital, donc un price-setter domestique pour
     qui dividende et plus-value sont taxés pareil (PFU 30 %) ;
  2. **fixings minces**, où l'ordre d'un particulier bouge le prix ;
  3. **données yfinance plus fragiles** sur les petites valeurs, alors qu'ici même le SBF 120 est
     inexploitable avant 2009.

  La liste officielle des sociétés soumises à la TTF (publiée chaque décembre) délimite l'univers
  exonéré sans données payantes.
- **Leçon méthode.** Un gate de fidélité **poolé** peut masquer une sous-période corrompue qui porte le
  résultat. Il faut appliquer G0 par période dès qu'un verdict lit une différence entre périodes.

## Caveats

1. Survivorship : constituants actuels du SBF 120.
2. TTF appliquée uniformément (conservateur pour les quelques noms < 1 Md€).
3. Exécution supposée au prix des fixings ; l'écart est compris dans les 0,10 % par jambe.
4. Taux TTF et courtage 2025-2026 non revérifiés sur BOFiP : sans effet sur un KILL.

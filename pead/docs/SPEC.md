# SPEC — Étude #28 : PEAD (post-earnings-announcement drift)

**Pré-enregistré le 2026-06-26, AVANT toute data.** Gates numériques figés ici ; je ne les bouge pas
pour fabriquer un PASS ([[feedback-gate-override]]).

## Thèse

Après une publication de résultats, le prix **dérive dans le sens de la surprise** pendant des semaines
(Bernard-Thomas 1989, l'anomalie publiée la plus robuste du factor-zoo). Test de l'anomalie canonique
**dans l'univers liquide déployable**, **net de friction**, avec **contrôle de décroissance post-publication**.

C'est, dans la taxonomie du programme, l'attaque côté **prédiction-de-prix** la plus haut-prior qui
restait jamais testée. Prior honnête = **KILL sous-type #2** (réel historiquement, décru depuis qu'il est
connu, et mangé par la friction / concentré dans les microcaps non-tradables).

## Mécanisme testé (identité, pré-enregistrée)

- **Surprise** (proxy free, pas d'estimés analystes payants) = rendement anormal de fenêtre d'annonce
  **standardisé** :
  ```
  z = CAR[-1,+1]_mkt-adj  /  (σ_pré × √3)
  ```
  où `σ_pré` = vol quotidienne du titre sur `[-60,-11]`. `z` = un SUE-like construit sur le PRIX
  (la réaction du marché EST la mesure de la surprise), comparable entre noms et dans le temps.
- **Dérive** = rendement anormal **post-annonce** : `CAR[+2,+21]_mkt-adj` (≈1 mois, **primaire**) et
  `CAR[+2,+63]` (≈3 mois, le PEAD classique 60-jours, secondaire). `mkt-adj` = moins le rendement SPY
  sur la même fenêtre (retire le beta ; un rendement = marché n'est pas un alpha).
- **Stratégie** = long tercile haut `z` (T3), short tercile bas (T1). Terciles par **cutoffs fixes** de la
  distribution `z` plein-échantillon (33/67 pct).
- **t honnête = calendar-time inter-mois** : on groupe les événements par **mois d'annonce**, on calcule
  `LS_cohorte = moy(dérive|T3) − moy(dérive|T1)` par mois, puis `t` sur la série des cohortes mensuelles.
  Robuste au chevauchement des fenêtres de détention (leçon carry #6 : l'inter-événement intra-jour
  gonfle le t par autocorrélation). L'inter-événement brut est reporté en diagnostic, **pas** gating.

## Gates (numériques, figés AVANT data)

| Gate | Test | Seuil PASS |
|---|---|---|
| **A** existence (plein échantillon) | LS tercile `CAR[+2,+21]` mkt-adj | spread > 0 **ET** t(inter-mois) > **3** **ET** monotone T1<T2<T3 |
| **B** maturité (annonces 2015+) | idem restreint 2015-01+ | spread > 0 **ET** t > **2** |
| **C** déployable / net | univers liquide (px≥$5), net du round-trip | net = brut − **40 bps** > **60 bps** **ET** t > 2 |
| **D** large-cap (pas microcap-only) | sous-ensemble S&P 500 | spread > 0 |

**KILL si B, C, ou D échoue.** (A seul ne suffit pas — l'anomalie est réelle historiquement ; la question
déployable est B∧C∧D.) Discipline : **t>3 sur A** parce que c'est un test grand-N (t>2 trop facile).

## Données (free-data, par design)

- **Univers** : constituants **S&P 500 + S&P 400 (midcap)** (Wikipedia, ~900 noms). Liquide par
  construction → teste directement la **déployabilité** (les microcaps, où le PEAD est le plus fort, sont
  exclues exprès ; voir caveat). D = sous-ensemble S&P 500.
- **Ticker↔CIK** : `company_tickers.json` (SEC, free).
- **Dates d'annonce** : **8-K Item 2.02** ("Results of Operations") via le flux `submissions` EDGAR
  (`filings.recent`, champ `items` contient "2.02"). Free, propre, même tuyau que SPAC #27.
- **Prix** : yfinance (caché). **SPY** pour le market-adjust.

## Prior honnête & ce qui tuerait / sauverait

- **Prior = KILL.** A passe (PEAD réel), **B faiblit** (décru post-publication), **C/D tuent** (friction +
  concentration microcap). Sous-type #2, forme canonique.
- **Sauverait la thèse** (GO improbable) : B ∧ C ∧ D tous PASS — i.e. spread net > 60 bps/mois persistant
  2015+ ET présent en large-cap. Ce serait le 2e GO du programme.
- **Faux-GO à chasser** si A/B passent : (i) le spread vient-il d'une poignée de noms / d'une saison
  (regarder la dispersion des cohortes) ; (ii) survit-il au lag d'entrée +1 jour (bounce, leçon CEF #8) —
  ajouté en sortie si pertinent.

## Caveats (déclarés d'avance)

- **Survivorship** : constituants **actuels** → dérive mesurée sur les survivants. Direction du biais pour
  le PEAD ambiguë (un nom delisté pour faillite a pu sur- ou sous-dériver) → documenté, pas corrigé en
  Phase-1. Un re-test lirait l'appartenance historique.
- **Profondeur d'historique** : `submissions.recent` plafonne ~1000 filings/nom → pour les filers actifs,
  l'historique 8-K peut ne remonter que ~10 ans. Aligné avec le focus maturité (gate B). Caveat noté.
- **Variante prix vs SUE fondamental** : on teste la version **price-based** (earnings-momentum), la PLUS
  arbitragée. Si A passe mais C échoue, Phase-2 testerait le SUE seasonal-random-walk (EPS XBRL EDGAR) —
  moins arbitragé. Mais si A échoue déjà, sans objet.
- **Trust/coût** : round-trip 40 bps (long-short, noms liquides) est une borne basse réaliste ; net réel
  ≤ mesuré → KILL conservateur.

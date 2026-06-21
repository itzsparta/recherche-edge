# Piste 1 — Primes de risque, basse fréquence : pré-test (PRÉ-ENREGISTRÉ)

> Écrit **avant** de voir le moindre résultat. Tout changement de cette spec après
> avoir vu un chiffre = overfit, interdit. (Leçon FINDINGS orderflow.)

## Hypothèse

Une stratégie de **time-series momentum (trend-following)** unique et pré-spécifiée,
sur un panier **cross-asset diversifié**, vol-targetée et rééquilibrée mensuellement,
**nette de frais** :

1. récolte un premium **positif et significatif** (edge existe), ET
2. le fait de manière **worth-harvesting** vs un 60/40 passif (l'edge vaut le coup).

Les deux conditions sont requises. Une seule ⇒ pas un go.

## Univers (FIXE — aucun cherry-pick)

Un proxy ETF par grande classe d'actifs. La diversification **cross-classe** est le
mécanisme qui sépare l'edge-de-trend du **drift mono-marché** (leçon étage-1).

| Classe | Ticker | Depuis |
|--------|--------|--------|
| Actions US | SPY | 1993 |
| Actions dév. ex-US | EFA | 2001 |
| Actions émergents | EEM | 2003 |
| Oblig. UST 20 ans | TLT | 2002 |
| Oblig. UST 7-10 ans | IEF | 2002 |
| Or | GLD | 2004 |
| Matières premières larges | DBC | 2006 |
| Énergie (pétrole) | USO | 2006 |
| Immobilier (REIT) | VNQ | 2004 |

Échantillon = du démarrage commun (~2006, quand DBC/USO existent) à aujourd'hui.
Couvre **GFC 2008, COVID 2020, krach inflation 2022** = multi-régime par construction.

## Signal (FIXE — un seul hyperparamètre)

- **Time-series momentum**, lookback **12 mois**, évalué en fin de mois.
- Position = **signe du rendement total trailing 12 mois** : long si > 0, short si < 0.
- Lookback = **pré-spécifié à 12m**. Pas de tuning pour trouver le « meilleur ».
- Robustesse {6, 9, 12, 15} mois lancée en **diagnostic seulement** (jamais pour
  sélectionner) ; DSR déflate par le nombre de lookbacks essayés.

## Sizing (FIXE)

- **Vol-targeting** : chaque jambe dimensionnée à une vol cible égale (vol réalisée
  trailing 60j → poids ∝ 1/σ), puis equal-risk entre les jambes.
- Portefeuille mis à l'échelle d'une **vol cible ~10 %/an**.
- But : retirer l'artefact « un marché volatil domine le P&L ».

## Frais (FIXE)

- **10 bps round-trip** par unité de turnover, appliqués au turnover mensuel
  (conservateur pour des ETF liquides). Net d'office, jamais de brut en décision.

## Métriques + critères PRÉ-ENREGISTRÉS

### (A) L'edge existe — TOUT requis
- Sharpe net **> 0**, **t-stat > 2** sur l'échantillon complet.
- Rendement net **positif dans la majorité** des sous-périodes régime
  (pré-GFC / GFC 2008 / reprise 2010s / COVID 2020 / 2022+).
- **Drop-one-instrument** : le Sharpe reste positif en retirant n'importe quel marché
  (pas porté par un seul).
- **Stabilité lookback** : signe/positivité stable sur {6,9,12,15}m (sinon = fragile).
- **DSR(best) > 0.95** sur les lookbacks essayés (sanity anti-overfit).

### (B) L'edge vaut le coup — au moins UN requis
- Sharpe net **> Sharpe du 60/40 passif** (60 % SPY / 40 % IEF, rebal mensuel), OU
- **Diversification de crise réelle** : rendement net **positif en 2008 ET 2022** et
  corrélation faible/négative aux actions (le « crisis alpha » du trend).

## Décision pré-enregistrée

- **(A) ∧ (B) ⇒ GO** vers le protocole complet (walk-forward, MC, paper).
- **(A) ∧ ¬(B) ⇒ DOWNGRADE** : premium réel mais le passif fait pareil en
  risk-adjusted → pas worth l'effort solo. Documenter, ne pas builder plus loin.
- **¬(A) ⇒ KILL** : pas robuste cross-régime / porté par un marché / t<2. Geler +
  FINDINGS.

## Données & implémentation

- **Source** : CSV daily stooq (`stooq.com/q/d/l/?s=<ticker>.us&i=d`) — gratuit, pur
  `urllib`, plus robuste que yfinance. Cache local `data/`.
- **Analyse** : pandas + numpy. Audit : `deflated_sharpe` / `pbo_cscv` portés depuis
  `orderflow-bot/scripts/overfit_audit.py` (pur stdlib).
- **Sortie** : verdict console + `docs/FINDINGS.md` au format orderflow/meme.

# Piste 4 — Volatility Risk Premium : FINDINGS

**Verdict (2026-06-22) : DOWNGRADE.** Le premium est **réel** (la vol implicite excède la
réalisée, t=4.03 sur 436 mois) — mais c'est la **juste compensation d'un risque de queue
catastrophique** (SVXY, le vrai véhicule short-vol, fait **−95 % de drawdown**), pas un edge
récoltable par un solo. (A) PASS, (B) FAIL. Conforme au null pré-enregistré.

> Reproduire : `python run.py` (verdict + gates) puis `python stress.py` (tail réel).
> Données : `^VIX`, `^GSPC`, `SPY`, `SVXY` via yfinance, gratuit, cache `data/`.

## Ce qui a été testé

Vente systématique de variance sur le S&P 500, pré-enregistrée dans [`SPEC.md`](SPEC.md).
Phase 0 = mesure du premium (`VIX²` implicite vs variance réalisée forward 21 j, mensuel
**non-chevauchant**, 1990→2026, multi-régime sans exclure aucun krach). Phase 1 = rendement
net d'un short-variance synthétique (points de vol, vega-flat 1×, coût 0.5 pt/mois).

## (A) Le premium existe — PASS

- `mean(VRP_var) = +0.0104` décimal², **t = 4.03** (n=436) ; `+4.07 points de vol` en moyenne.
- **4/6 régimes positifs.** Les deux négatifs sont **les krachs** : GFC −0.0136, COVID −0.0236
  — la réalisée dépasse l'implicite exactement quand le sinistre frappe. C'est la signature
  d'une **prime d'assurance**, pas d'un edge prédictif.
- **DSR(best, n_trials=3 sur h∈{15,21,30}) = 0.977 > 0.95.** Pas un artefact de multiple-testing.

Le premium est aussi robuste que la littérature le dit (Bollerslev-Tauchen-Zhou, Carr-Wu).
Aucune surprise : la question n'a jamais été « existe-t-il ? » mais « est-il récoltable net
du tail par ce profil ? ».

## (B) Worth-it tail-inclus — FAIL

Les métriques **naïves** crient GO — et c'est précisément le mirage :

- Récolte nette : **Sharpe annualisé 1.86**, t=11.19, vs SPY 0.77. Miroir (long vol) = −2.38
  (perd, donc le premium **est** bien la source du P&L).
- **Mais skew −3.30, kurtosis 24.9.** Sharpe pénalise la variance, pas le skew : une stratégie
  qui gagne régulier puis perd −8.79σ en un mois affiche un Sharpe somptueux et reste ruineuse.

Tail **honnête** (vrai véhicule short-vol, marqué au quotidien) :

| | maxDD | pire jour |
|---|---|---|
| **SVXY** (short VIX futures, le harvest réel) | **−95.2 %** | **−83.0 %** (6 fév 2018) |
| SPY buy-hold (même fenêtre 2011+) | −33.7 % | — |

Le VIX a **gappé +116 % en une séance** (5 fév 2018). COVID : SVXY −52 %. Le drawdown du
short-vol est **~3× celui de l'équité** → tail catastrophique → (B) FAIL.

## Le faux GO, et pourquoi le pipeline l'a attrapé

Le `run.py` initial rendait **GO**. Deux trous, tous deux corrigés **dans le sens dur**
(resserrage, jamais relâche — donc pas de l'overfit, cf. leçon override-de-gate) :

1. **Tail σ-normalisé ment.** La première opérationnalisation comparait le maxDD en *unités
   de σ*. Le σ du short-vol est gonflé par la queue elle-même → −14σ « paraît » meilleur que
   SPY −15.7σ. Métrique aveugle au skew = exactement ce que FINDINGS orderflow avertit. Corrigé
   → drawdown **absolu** sur le vrai véhicule (SVXY).
2. **L'échantillon mensuel LISSE le krach intramois.** Le régime 2018-2019 reste +0.004 et le
   mois de **février 2018 = −0.4 pt de vol** dans le harvest mensuel : le **−83 % du 5-6 fév
   est invisible** en close-to-close. Or un book short-vol est margin-call au quotidien.

Le critère (B) pré-enregistré disait « survie au tail, **non catastrophique** ». L'opérationnalisation
honnête (SVXY, quotidien, absolu) le fait **échouer**. Le pipeline a donc transformé un Sharpe
1.86 / t=11.19 (que la plupart des retail auraient tradé) en un DOWNGRADE motivé.

## Leçon

- **Pour le short-vol, le tail EST le produit.** Sharpe et t-stat sont structurellement
  trompeurs (aveugles au moment 3/4). Toujours trancher sur skew/kurtosis + drawdown absolu
  d'un véhicule réel, jamais sur un ratio variance-only.
- **L'échantillonnage basse fréquence masque le risque haute fréquence.** Un premium mesuré
  mensuellement peut cacher la séance qui tue la position.
- Le VRP rejoint le motif du programme sous un angle neuf : non pas « priced-in », mais
  **« correctement prix »** — la prime *est* le loyer du risque de queue. Pas un free lunch.

## Ce qui resterait (non poursuivi par défaut)

La **seule forme solo-viable** = short-vol à **risque défini** (spreads d'options, ou short-vol
couvert par une aile long-vol) qui plafonne le −95 %. Mais le hedge **mange aussi la prime** →
EV résiduelle vraisemblablement mince, même profil que le sleeve trend (piste 1). Candidat
Phase-2 *seulement* si Rémi veut explorer le defined-risk ; sinon piste 4 close pour l'objectif edge.

## Caveat données

SVXY a été **dé-levé à −0.5× après février 2018** : le −95 % est donc, si quelque chose,
**optimiste** pour un short-vol −1× naïf d'avant 2018 (XIV, lui, a terminé à zéro le 6 fév 2018).
Le tail réel d'un short-vol non-couvert est au moins aussi mauvais que mesuré ici.

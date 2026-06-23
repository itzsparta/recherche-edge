# Piste 18 — Dealer gamma (GEX), flux forcé : FINDINGS

**Verdict (2026-06-23) : KILL-tradable.** Le GEX est un **vrai prédicteur de vol** — corr(GEX_veille,
|ret|) = **−0.262** (t≈−16), robuste **pré-2021 (−0.31) ET post-2021 (−0.32)**. Le mécanisme
gamma→vol est réel et **pas arbitré**. **Mais aucun alpha de rendement déployable** : la stratégie
switch mean-rev/momentum **perd** (−6.66 %/an, Sharpe −0.50), le vol-timing sous-performe le buy-hold
(Sharpe 0.38 vs 0.79). Le flux forcé prédit la **VARIANCE, pas la MOYENNE** → non-directionnel,
non-tradable pour un solo. (A) PASS, (B) FAIL.

> Reproduire : `python run_gex.py`. Data = SqueezeMetrics DIX.csv (gratuit, 3807 jours 2011-2026,
> GEX + close SPX). Stdlib pur.

## Ce qui a été testé

Pré-enregistré dans [`SPEC.md`](SPEC.md). Pari sur un **flux FORCÉ** (les dealers **doivent** hedger leur
gamma, price-insensitive = catégorie théoriquement la moins arbitrée). Hypothèse : GEX haut → dealers
longs gamma → vol supprimée + mean-reversion ; GEX négatif → vol amplifiée + momentum. Testé en **daily**
(close SPX), signal GEX laggé, régimes par médiane **trailing 252j** (pas de look-ahead), coûts 1 bp.

## Gates

| Gate | Résultat | |
|---|---|---|
| **(A) mécanisme GEX→vol** | corr **−0.262** (t≈−16), robuste pré+post-2021 | **PASS** — vrai prédicteur de vol |
| **(B) alpha de rendement** | S1 switch −6.66 % (Sh −0.50, t−1.88) ; S2 vol-timing Sh 0.38 < buyhold 0.79 | **FAIL** — aucun edge net |
| (C) priced-in | mécanisme robuste les **deux** périodes (pas arbitré) | NA — pas d'alpha à pricer-in |
| (D) bêta de vol | corr(S2, \|ret\|) −0.075 = simple dé-risking | le maigre gain S2 = évitement de vol, pas alpha |

## Le kill est NEUF — variance ≠ moyenne

Contrairement à **pré-FOMC #5b** (mécanisme réel mais **mort à la publication**, McLean-Pontiff), le
mécanisme GEX **survit** : il prédit la vol aussi bien post-2021 (mainstream, mème retail) que pré-2021.
**Ce n'est pas un edge priced-out — c'est un edge qui n'a jamais été directionnel.**

- Le flux forcé de gamma-hedging agit sur l'**amplitude** des moves (il les amortit ou les amplifie),
  **pas sur leur signe**. Donc GEX prédit `|ret|` (variance) fortement, mais `ret` (moyenne) **pas du
  tout** → aucun signal directionnel à trader.
- Les deux seules façons de monétiser un prédicteur de vol :
  1. **Vendre/acheter de la vol** (options) selon le régime → on retombe dans **VRP #4** (DOWNGRADE,
     tail catastrophique SVXY −95 %). Le solo n'a pas l'instrument defined-risk rentable.
  2. **Timing d'exposition** (S2) → ce n'est pas de l'alpha, c'est du **bêta de vol** (réduire l'expo
     quand la vol monte) — qui sous-performe le buy-hold en rendement (Sharpe 0.38 < 0.79) et que
     gate (D) démasque (corr au |ret| −0.075).

## Leçon

- **Un flux forcé authentique et non-arbitré peut être réel sans être tradable** — s'il prédit le
  **second moment** (variance) et pas le **premier** (rendement). GEX est le cas d'école : prédicteur
  de vol robuste 15 ans, **zéro** alpha directionnel.
- **Rejoint overnight #5a / pré-FOMC #5b** dans la famille « mécanisme réel, rien à trader net » — mais
  par une route différente : overnight = mangé par le turnover, pré-FOMC = priced-in, **GEX = mauvais
  moment prédit (variance)**. Trois façons qu'un effet réel ne devienne pas un edge.
- **La porte vol mène à VRP** : tout edge de prédiction de vol pour un solo se heurte au même mur que
  la piste 4 (le tail du short-vol). Cohérent avec le bilan.

## Caveat

Daily-only : le pinning **intraday** (le plus cité pour le GEX) n'est pas testable ici (close SPX seul)
— possible qu'un edge intraday existe, mais il exigerait des données tick + exécution intraday, hors
du périmètre solo/free-data, et serait le terrain des market-makers (cf. le motif #15/#16 : l'edge
intraday appartient au participant sophistiqué). Le verdict porte sur le **daily tradable solo**, où le
mécanisme est réel (vol) mais l'alpha de rendement absent. GEX = `gex` SqueezeMetrics (convention
dealers longs calls/courts puts) ; la robustesse pré/post-2021 du signe rend le verdict insensible à
la convention exacte.

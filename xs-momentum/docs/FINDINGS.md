# Piste 13 — Momentum cross-sectionnel crypto : FINDINGS

**Verdict (2026-06-23) : KILL.** Le brut momentum transversal n'est **même pas significatif**
(gross hebdo +0.27 %, ann ≈ +14 %, mais **t=0.84**), et le peu qui existe est un **artefact
early-market 2021** : en marché mûr (2023+) le net est **−19.4 %/an** (t=−1.47). DSR(best, L∈{1,2,4,8 sem})
= **0.660**. (A) FAIL → KILL. La market-neutralité est propre (corr BTC −0.01) : c'est une **vraie
absence d'edge**, pas un backtest cassé.

> Reproduire : `python run_xs_mom.py`. Data : klines daily perp Binance (75 perps), gratuit, cache `data/`.

## Ce qui a été testé

Pré-enregistré dans [`SPEC.md`](SPEC.md). L/S transversal **dollar-neutral** (long tercile fort /
short tercile faible) sur **univers fixe de 75 perps USDT** (onboard < 2021-06, TRADING), rebal
**hebdomadaire**, formation **trailing 4 semaines**, **gap 1 j** formation→entrée (anti-bounce, leçon
CEF), coût pré-enregistré 10 bps/côté × turnover + funding 6 bps/sem. 330 rebals, 2020-02 → 2026-06.

## Gates — un seul PASS structurel, zéro edge

| Gate | Résultat | |
|---|---|---|
| **(A) brut t>2** | gross +14 %/an mais **t=0.84** | **FAIL** — pas de signal significatif |
| (B) net t>2 | net +3.9 %/an, **t=0.24** | FAIL — turnover achève le peu de brut |
| (C) deux jambes | long_exc +0.14 % (t=0.80), short_exc +0.12 % (t=0.78) | PASS de signe, ns individuellement |
| (D) market-neutral | corr(net, BTC) = **−0.01** | PASS — construction propre |
| (E) robustesse | drop-top-3 OK, miroir OK, **mais 3/6 régimes net+** | **FAIL** sur le split régime |
| (F) DSR | **0.660** | FAIL — aucun lookback ne sauve |
| (G) marché mûr 2023+ | net **−19.4 %/an** (t=−1.47) | **FAIL** — négatif hors 2021 |

Le verdict pré-enregistré tranche dès (A) — mais **chaque gate indépendant confirme le KILL**.

## Le motif : un artefact 2021, mort en marché mûr (dos à dos avec la Piste 12)

Net par régime, hebdo :

| régime | net/sem | n |
|---|---|---|
| 2021 H1 bull | **+2.25 %** | 17 |
| 2021 crash | −1.43 % | 13 |
| 2021 H2 | **+1.88 %** | 22 |
| 2022 bear | −0.69 % | 52 |
| 2023 | −0.55 % | 52 |
| 2024+ | +0.16 % | 174 |

Tout le P&L vit en **2021** (marché crypto immature : dispersion énorme, alts qui trendent fort,
peu d'arbitragistes). Dès 2022 le signal est **négatif ou nul**. C'est **exactement le motif de la
Piste 12 (VRP crypto)** rendue le même jour : une prime/edge crypto réel·le en 2021 est **arbitré·e
jusqu'à disparition à mesure que le marché mûrit**. Deux pistes crypto consécutives, même cause de mort.

## Pourquoi c'est un KILL robuste (et non un artefact de méthode)

- **La construction est saine** : market-neutralité réelle (corr −0.01), les deux jambes ont le même
  signe positif (pas de long-bêta déguisé), le signe survit au drop-top-3 (DOGE/AXS/AVAX) → le KILL
  ne vient pas d'un bug ni d'un seul nom.
- **Le brut lui-même est ns** (t=0.84) : on ne tue pas un edge que le turnover aurait mangé (ça,
  c'était funding-XS) — ici il n'y a **pas de brut significatif** au départ. Type de mort plus sec.
- **Survivorship pré-enregistré = optimiste** : l'univers exclut les alts delistés (morts). Le réel,
  alts-morts inclus, serait **pire** → le KILL est conservateur.

## Leçon

- **Les edges crypto documentés sur échantillons 2017-2021 peuvent être de purs artefacts
  d'immaturité de marché.** Le test du sous-échantillon mûr (Gate G, 2023+) est désormais
  indispensable sur tout signal crypto — il a tué la Piste 12 ET la 13 le même jour.
- **La market-neutralité a fait son travail** (annuler le drift, le confound qui a contaminé les
  pistes directionnelles) — mais annuler le drift ne crée pas un edge là où il n'y en a pas.
- Rejoint le motif unifié : *là où le prix est public, un solo n'a pas d'edge récoltable* — ici même
  pas de brut, et le résidu 2021 est arbitré dès que le marché se densifie.

## Caveat données

Klines perp Binance, 75 noms, gap 1 j anti-bounce appliqué. Univers survivant (optimiste, pré-enregistré).
Formation 4 semaines / hold 1 semaine pré-spécifiés ; les variantes L∈{1,2,4,8} sont en DSR (0.660),
aucune ne franchit le seuil — pas de lookback magique non-testé qui sauverait la thèse.

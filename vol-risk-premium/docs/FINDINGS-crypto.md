# Piste 12 — Crypto VRP (defined-risk) : FINDINGS

**Verdict (2026-06-23) : KILL.** Le VRP crypto **existe** mais n'est **pas matériellement plus gros
que l'actions** une fois le marché mûri : la prime fat est un **artefact early-market non-répétable**.
Full-sample BTC = +7.88 pts de vol (**sous la barre pré-enregistrée 8.0**) — et cette moyenne est
**gonflée par 2021-2022** (marché d'options crypto immature, peu de vendeurs). Dans le marché **mûr
(2023+)** la prime est compressée à +5.23 pts (BTC, **t=1.88 ns**) / +1.35 (ETH, **t=−0.29**) = niveau
actions, non-significatif. (A) FAIL. La porte « defined-risk » que la piste voulait ouvrir n'a même
pas eu besoin de la Phase 2 : le premium censé payer l'aile **n'est plus là** dans le régime répétable.

> Reproduire : `python run_crypto.py` (gates + verdict). Data : DVOL + perp Deribit, gratuit, cache `data/`.

## Pourquoi cette piste existait

Enfant direct de la **Piste 4 (VRP actions, DOWNGRADE)**, qui a laissé **une seule porte ouverte** :
le short-vol à **risque défini** (ailes OTM longues qui plafonnent le −95 % de SVXY), viable *si* le
premium est assez gros pour rester positif **après** le coût de l'aile. L'actions disait non (4 pts de
prime, l'aile mange tout). Hypothèse Piste 12 : la **crypto**, où le gap DVOL−réalisée est réputé
3-5× plus gros, est le seul endroit où ce defined-risk pourrait dégager une EV nette. Pré-enregistré
dans [`SPEC-crypto.md`](SPEC-crypto.md), gate de magnitude `mean(VRP_vol) > 8 pts` fixé **avant** tout chiffre.

## (A) Le premium existe ET est fat — FAIL

DVOL Deribit (implicite 30 j) vs variance réalisée forward 30 j daily, mensuel non-chevauchant,
62 mois (2021-03 → 2026-04), BTC + ETH, **aucune exclusion de krach**.

| | full-sample (n=62) | early ≤2022 (n=22) | **mûr ≥2023 (n=40)** |
|---|---|---|---|
| **BTC** mean VRP_vol | +7.88 pts | **+12.68** | **+5.23** (t=1.88 ns) |
| **ETH** mean VRP_vol | +4.71 pts (t=1.16 ns) | +10.83 | **+1.35** (t=−0.29) |

- **BTC rate la barre de magnitude** (7.88 < 8.0) — et le détail régime montre que ce n'est **pas**
  un knife-edge : la décroissance est **monotone** (crash-2021 +25 → 2021H2 +18 → bear-2022 +10 →
  2023 +7 → **2024+ +4.5**, n=28). Le marché d'options crypto **mûrit** (vendeurs de vol, produits
  structurés, ETF covered-call) → la prime se **comprime vers le niveau actions**, en temps réel.
- **ETH ne réplique même pas** : premium full-sample non-significatif (t=1.16), et **négatif** en
  tendance dans le marché mûr.
- DSR diagnostic BTC 0.998 (la prime *existe* hors multiple-testing) — mais le DSR ne juge pas la
  **répétabilité** : il valide le full-sample, pas le fait que tout le signal vit dans 2021-2022.

Discipline pré-enregistrement : la barre 8.0 a été fixée avant les données. 7.88 < 8.0 = FAIL.
**Aucun déplacement de barre post-hoc** (leçon override : on serre, on ne relâche jamais). Et la
décomposition régime *confirme* le FAIL au lieu de le contredire.

## (pré-B) Le faux PASS qui révèle le tueur

Le `run_crypto.py` rend pré-B **PASS pour BTC en full-sample** : net +4.88 pts/mois @ coût 3.0,
Sharpe 1.08, t=2.45, bat le buy-hold (0.38), miroir perd (−2.40). Trade-able à première vue.

C'est le **même piège que LST (piste 9) et les faux GO VRP/CEF** : le t flatteur est porté par un
**régime unique non-reproductible**. Restreint au marché mûr (2023+), le net @3 tombe à **+2.23
pts/mois, t=1.07 (ns)** pour BTC et **−1.65 pts (négatif)** pour ETH. Le PASS full-sample = 100 %
l'early-market 2021-2022. Il n'y a **rien à trader en avant**.

## La porte defined-risk ne s'est jamais ouverte

La Phase 2 (iron-condor sur surface d'options réelle, net des spreads d'ailes) était censée trancher
le **null central** : la peur du krach qui gonfle le premium gonfle aussi la put-wing → wash. On n'y
arrive même pas : **dans le marché mûr le premium est déjà revenu au niveau actions (~5 pts) avant de
payer la moindre aile.** L'actions a été DOWNGRADE parce que 4 pts ne paient pas l'aile ; la crypto
mûre est à ~5 pts → **même conclusion, un cran plus sec** (KILL sur la magnitude/répétabilité, sans
même avoir à mesurer l'aile). La seule fenêtre où la crypto avait +12 pts (2021-2022) est révolue et
ne reviendra pas — le marché s'est densifié.

## Leçon

- **Une prime crypto « fat » mesurée full-sample peut être un artefact d'immaturité de marché.** Le
  bon test n'est pas « la prime existe-t-elle ? » (DSR 0.998 dit oui) mais « **persiste-t-elle dans le
  régime récent ?** ». La décomposition early/mature est obligatoire sur les marchés jeunes.
- **Le defined-risk ne sauve rien si le sous-jacent premium n'est pas là.** La porte ouverte par la
  Piste 4 supposait un premium durablement gros ; la crypto ne le fournit que transitoirement.
- Rejoint le motif unifié sous l'angle le plus net du programme : **un edge structurel arbitré jusqu'au
  niveau actions, observé EN TEMPS RÉEL** via la décroissance régime (12.7 → 5.2 pts en 4 ans). La
  densification du marché *est* l'arbitrage.

## Caveat données

DVOL BTC/ETH démarre 2021-03 (inception Deribit) → pas de COVID mars-2020 ni de marché pré-2021. Le
perp sert de proxy spot pour la réalisée (basis négligeable sur la vol). 62 mois = échantillon court
(caveat puissance pré-enregistré) — mais la conclusion ne repose pas sur la puissance : elle repose
sur la **décroissance monotone** de la prime, robuste BTC **et** ETH, vers le niveau actions.

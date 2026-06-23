# Piste 14 — Airdrop farming (EV-ledger opérationnel) : FINDINGS

**Verdict (2026-06-23) : KILL.** Même en **garantissant** la qualification au basket entier des
airdrops majors 2020-2025 (jackpots inclus, allocations valorisées **au TGE** = best-case généreux),
le net est **8.4 €/h** sur 2 250 h de farming — **sous le plancher de labeur (15 €/h)**. Et **53 % du
$ total dépend de 2 jackpots non-répétables** (dYdX, Hyperliquid). En base-case honnête (sans
jackpots, qualif partielle, gas payé sur les zéros farmés) l'EV est **négative (−1 050 $)**. (A) FAIL,
(B) FAIL. La seule arme structurelle inédite du programme — le moat sybil — **coupe dans les deux sens**.

> Reproduire : `python run_airdrop.py`. Décroissance = prix spot CoinGecko (gratuit), reste = arithmétique transparente.

## Ce qui a été testé

Pré-enregistré dans [`SPEC.md`](SPEC.md). **Ledger d'EV opérationnel**, pas un backtest : le $ net par
**heure** de farming bat-il un seuil de labeur, après les zéros-farmés, la décroissance, le clawback ?
Basket FIXE = 15 airdrops majors (les **payeurs**, survivants sur 5 ans), allocation médiane par wallet
valorisée au prix TGE (généreux). Paramètres pré-enregistrés : 500 h/an × 4.5 ans, 40 protocoles farmés
(zéros inclus, gas 150 $ chacun), plancher 15 €/h.

## Gates

| Gate | Résultat | |
|---|---|---|
| **(A) plafond best-case** | qualifié pour TOUT : net 20 500 $ / 2 250 h = **8.4 €/h** | **FAIL** — le plafond ne paie pas le labeur |
| **survivorship** | jackpots dYdX+Hyperliquid = **53 %** du $ total | **MIRAGE** — leçon meme-coin |
| **(B) EV base-rate** | sans jackpots, qualif 50 %, gas sur 40 farms : **−1 050 $** | **FAIL** — EV négative |
| (C) décroissance | médiane hold-to-now **−93 %** | la valo TGE EST le best-case |
| (E) seuil labeur | base-case **−0.4 €/h**, −54 €/trimestre | FAIL |

## Le moat coupe dans les deux sens (le null central, confirmé)

L'argument d'entrée : les institutions **ne peuvent pas** sybil-farmer → seul étang du programme où le
gros acteur est **structurellement absent**. Vrai. Mais le ledger révèle la symétrie pré-enregistrée :

- **Le solo organique (1 wallet) est plafonné au petit $** — et même tout cumulé, best-case 8.4 €/h.
- **Scaler (multi-wallets) pour rendre ça matériel = exactement ce que le clawback sybil détruit**
  (LayerZero, zkSync, Hop ont exclu des centaines de milliers d'adresses). L'absence de l'institution
  est **compensée par la défense sybil du protocole** : le farmer hérite d'un plafond, pas d'un edge.
- **L'upside matériel est une loterie** : 53 % du $ vient de 2 jackpots (dYdX, Hyperliquid). On ne
  planifie pas un jackpot. HYPE **+1689 %** (le seul token qui n'a pas dumpé) est la preuve vivante du
  survivorship : tout le rendement-queue de l'airdrop farming tient à des HYPE qu'on ne peut prévoir.

## La décroissance — data réelle, vivide

Hold-to-now médian **−93 %**. dYdX −99 %, Wormhole −99 %, Starknet −98 %, Blur −98 %, OP −94 %,
ARB −93 %, zkSync −94 %, EigenLayer −93 %. **Une** exception : HYPE +1689 %. Valoriser au TGE (ce qu'on
a fait, généreusement) suppose déjà une vente parfaite au TGE+7 j ; quiconque a **gardé** s'est fait
laminer. Le best-case du ledger est donc déjà optimiste, et il échoue quand même.

## Leçon

- **L'airdrop farming est un edge RÉEL mais immatériel et non-scalable pour un solo.** C'est une
  subvention (donc pas mangée par l'efficience, contrairement aux 13 pistes de prix/info) — mais
  bornée au mono-wallet par le clawback, diluée par la décroissance, et son upside est une loterie.
- **Même structure de kill que le meme-coin** : un mirage survivorship (les jackpots mémorables
  cachent la traîne de zéros). Ici 53 % sur 2 noms ; là +0.223 sur n=4.
- **Le seuil de labeur est la bonne métrique** pour l'opérationnel (≠ Sharpe pour le trading) : 8.4 €/h
  au mieux, négatif en réalité. Pour l'objectif « cash / temps bien employé », c'est un mauvais boulot.
- Clôt le dernier fil ouvert du programme : **même l'étang où l'institution est absente ne produit pas
  d'edge solo matériel** — l'absence est compensée par la défense anti-sybil. *Changer l'étang* reste 0/N.

## Caveat

Allocations = figures publiques approximatives, valorisées au TGE (généreux pour la thèse). Le verdict
ne repose pas sur leur précision mais sur (a) le **dénominateur labeur** (best-case 8.4 €/h) et (b) la
**concentration jackpots** (53 %) — robustes à toute variation raisonnable. Un farmer plus casual change
les heures mais pas la dépendance-loterie ni le plafond sybil. Décroissance = data CoinGecko réelle.

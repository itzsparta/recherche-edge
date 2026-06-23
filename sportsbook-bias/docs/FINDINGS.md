# Piste 16 — Biais des books sportifs récréatifs (EV-ledger net-de-vig) : FINDINGS

**Verdict (2026-06-23) : KILL.** Le biais favorite-longshot est **réel** (la courbe winrate-vs-proba
le confirme, 50 ans de littérature : les longshots gagnent **moins** que leur proba dévigée, t jusqu'à
−3.3 ; les favoris **plus**, +1.8 pp). Mais il **vit à l'intérieur du vig** : parier les favoris à la
cote de **clôture Pinnacle** (sharp) rend **−1.09 % (t=−1.65)**, négatif dans les **deux** moitiés
temporelles. Le **seul +EV** du jeu de données — parier les mispricings du book soft (Bet365 > clôture
Pinnacle, 32 % des legs) — rapporte **+2.37 % (t=2.00)** *à la cote soft*, mais les **mêmes paris au
venue non-limitant** (Pinnacle close) rendent **−3.18 % (t=−2.90)**. L'edge n'existe **qu'au book qui
bannit les gagnants**. (A) FAIL, (B′) FAIL, (C) FAIL.

> Reproduire : `python run_sportsbook.py`. Data = football-data.co.uk (CSV gratuits, cotes
> Pinnacle-closing + Bet365 + résultats), 21 727 matchs / 65 181 legs, 5 ligues, 2012-2024.

## Ce qui a été testé

Pré-enregistré dans [`SPEC.md`](SPEC.md). **Ledger d'EV net-de-vig**, pas un backtest de prédiction :
un biais de book *récréatif* laisse-t-il un ROI net positif, t>2, dans les deux moitiés temporelles,
à la cote de **clôture Pinnacle (sharp)** — et **encaissable** sans se faire limiter ? Univers FIXE =
tous les matchs des 5 grandes ligues européennes (E0/SP1/I1/D1/F1) 2012/13→2023/24, aucune sélection
sur le résultat. C'est le **premier marché du programme à contrepartie PROUVÉE bête** (argent récréatif),
pas sophistiquée — le seul test qui attaque l'hypothèse partagée par les 15 kills au lieu de la re-tester.

## Gates

| Gate | Résultat | |
|---|---|---|
| **(A) biais franchit le vig** | favoris @ Pinnacle close : ROI **−1.09 %**, t=−1.65, n=21 727 | **FAIL** — biais dans le vig (2.37 %) |
| **(B′) robustesse sous-période** | early 2012-17 **−0.56 %** (t=−0.61) ∧ late 2018-24 **−1.62 %** (t=−1.73) | **FAIL** — négatif dans les deux moitiés |
| **(C) encaissable au venue non-limitant** | CLV+ @ Bet365 **+2.37 %** (t=2.00) ; mêmes legs @ Pinnacle close **−3.18 %** (t=−2.90) | **FAIL** — +EV seulement au book qui bannit |
| (D) matérialité | edge encaissable au sharp ≤ 0 < hurdle 2 % | FAIL (moot) |

## Le biais est réel — mais dans le vig (le null central #1, confirmé)

La courbe winrate-vs-proba dévigée **reproduit le favorite-longshot bias** proprement :

| décile | proba sharp | winrate | edge (pp) | ROI @ close | t |
|---|---|---|---|---|---|
| 0 (longshots) | 10.1 % | 9.7 % | **−0.39** | −7.84 % | −2.10 |
| 2 | 22.5 % | 21.4 % | **−1.10** | −7.31 % | −3.31 |
| 9 (favoris) | 70.5 % | 72.3 % | **+1.82** | +0.15 % | +0.19 |

Les longshots gagnent **moins** que leur proba implicite (surpaiement = ticket loterie), les favoris
**plus** (sous-pariés). C'est exactement le biais documenté. **Mais le ROI à la cote offerte est le
verdict** : même le décile favori — le côté le mieux valorisé — rend **+0.15 % (t=0.19)**, du bruit.
Le vig Pinnacle de **2.37 %** mange entièrement un biais qui culmine à 1.8 pp. **Exister dans la courbe
winrate ≠ franchir le prix offert** — l'analogue exact du *spread fantôme* (capacity-niche #3 : le
spread existait t=+7 mais sans profondeur derrière) et du *bounce CEF* (#8).

## Le seul +EV est inencaissable (le THÉORÈME du programme, prouvé numériquement)

C'est le résultat le plus net. On peut **fabriquer du +EV** : parier les 32 % de legs où Bet365 offre
une cote **supérieure** à la clôture Pinnacle (CLV positif) rend **+2.37 % (t=2.00)** — battre la ligne
de clôture efficiente **est** +EV, comme la théorie le dit. **Mais** :

- Ce +EV n'existe **qu'à la cote soft**. Les **mêmes paris** au venue non-limitant (Pinnacle close)
  rendent **−3.18 % (t=−2.90)**. L'edge **est** le mispricing soft, rien d'autre.
- Or les books soft qui laissent ces prix sont **exactement** ceux qui **limitent/bannissent** les
  comptes gagnants en quelques semaines ; les books qui ne bannissent pas (Pinnacle, Betfair) tarifent
  efficacement (pas d'edge). L'intersection **réel ∧ encaissable est vide**.

C'est « ce qui te laisse entrer est ce qui tue l'edge », en version sportive et **chiffrée** : +2.37 %
au book bannable, −3.18 % au book scalable. Le même théorème que le bounce CEF (#8) et la niche
illiquide (#3).

## Leçon — « changer l'étang » vers une contrepartie bête échoue aussi (0/3)

- **La contrepartie bête EXISTE** (le récréatif surpaie les longshots, mesurable, t=−3.3). C'était
  l'hypothèse neuve : attaquer un marché où le gros acteur n'est pas sophistiqué. **Elle ne suffit pas.**
- **Le book sharp (Pinnacle) a déjà absorbé la bêtise** dans une clôture efficiente (vig 2.37 %, biais
  dans le vig). Le résidu qui dépasse le vig n'existe qu'aux books soft — **et ceux-là bannissent**.
  La dumb money est intermédiée par un market-maker sharp + une défense par limitation ; le parieur
  hérite d'un **plafond**, pas d'un edge. Symétrie exacte de l'airdrop #14 (le moat sybil compense
  l'absence de l'institution).
- **« Changer l'étang » est désormais 0/3** : CEF inarbitrable (#8, bounce), Polymarket récréatif mais
  arbitré (#10, biais inversé), books sportifs récréatifs mais sharp-intermédiés (#16, biais dans le
  vig + limitation). Trois mécanismes différents, **même issue** : changer la contrepartie ne produit
  pas plus d'edge que changer l'instrument. L'efficience n'est pas portée par « qui parie » mais par
  **l'existence d'un market-maker sharp qui price le close** — présent même face à une foule bête.

## Caveat

Le verdict ne dépend d'aucun chiffre fragile : il repose sur (a) le ROI favoris **négatif** à la
clôture sharp dans **les deux** moitiés (biais < vig), et (b) le **renversement +2.37 % → −3.18 %**
entre book soft et venue non-limitant (inencaissable). Tous deux sont des effets gros et significatifs
sur 65 k legs. La limitation des comptes gagnants par les books soft est un fait opérationnel documenté,
pas une hypothèse. Un univers élargi (autres sports, autres ligues) changerait l'amplitude du biais
mais pas sa position **sous** le vig sharp ni la bannabilité du résidu soft.

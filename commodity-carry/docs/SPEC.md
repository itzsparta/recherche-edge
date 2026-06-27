# SPEC #30 — Carry commodités (énergie) : prime de hedging-pressure

**Pré-enregistré AVANT de voir la data.** Gates fixés ici ; le run ne les bouge pas.
Discipline 2 sens : un Sharpe>0 porté par le beta énergie (et non le carry) = DOWNGRADE/KILL,
pas un GO. [[feedback-gate-override]]

## Thèse

Le **carry commodité** (backwardation normale, Keynes / Gorton-Rouwenhorst) paie une prime de
risque au spéculateur qui porte le risque des **hedgers forcés**. Mécanisme = flux forcé
STRUCTUREL et CONTINU (≠ flux daté public absorbé du LETF #25, ≠ différentiel de taux sans hedger
de FX carry #17, ≠ demande de levier de crypto-funding #6). Les **producteurs d'énergie** shortent
des futures pour hedger leur production physique → pression vendeuse → courbe en backwardation en
moyenne → le long touche un roll yield positif. En contango (glut, storage) le carry s'inverse.

C'est le cas hedging-pressure le plus FORT (producteurs pétrole/gaz = hedgers canoniques) et
l'actif est **orthogonal aux actions** → valeur potentielle de **sleeve** pour le méta-portefeuille
(qui manque d'orthogonalité au CŒUR : carry crypto/FX corrélé +0.41, cf. méta risk-premia).

## Limitation data PRÉ-ENREGISTRÉE (honnêteté)

Le carry commodité FAIT FAITHFULLY = cross-section large ~25 marchés (grains/métaux/softs/énergie).
**La term structure (front/next) pour cet univers sur 20 ans n'existe PAS en data libre** (yfinance
= front continu seul ; échéances datées vides ; quandl/nasdaqdatalink absents ; FRED no-key = spot
seul ; EIA = clé requise). Seul sous-ensemble propre = **énergie via EIA** (contrat 1-4).

→ Univers ≈ {WTI, NatGas, Heating oil, RBOB gasoline}, soit **~2 paris indépendants** (produits
pétroliers corrélés au brut ; NatGas seul indépendant). **t>2 est une barre HAUTE à ce breadth.**
Conséquence pré-enregistrée : ce test est **NARROW**. Un GO ici ne vaut que « directionnellement
réel, à confirmer sur univers large (non-free) ». On ne sur-vend PAS un GO narrow.

## Data

- Source : **EIA Open Data API** (clé gratuite). Séries futures contrat 1 & 2 (front, 2e échéance),
  daily, ~1994+ : WTI (`PET.RCLC1.D`/`RCLC2`), NatGas Henry Hub (`NG.RNGC1.D`/`RNGC2`), Heating oil
  & RBOB gasoline (séries `PET.EER_*` contrat 1/2 — IDs vérifiés au pull). Brent si EIA sert une
  série futures contrat (sinon exclu — Brent EIA = spot seul).
- Cache local `data/` (gitignored). Clé dans `.eia_key` (gitignored, jamais commitée).

## Construction (clean, 100% EIA, zéro splice)

Pour chaque marché, mensuel (fin de mois) :
- **Signal carry** : `carry_t = C1_t / C2_t − 1`. Backwardation (C1>C2) → carry>0 → long.
- **Rendement de détention** (sans contamination roll) : `ret_{t→t+1} = C1_{t+1} / C2_t − 1`
  (= acheter la 2e échéance à t au prix C2_t ; à t+1 elle est devenue le front, prix ≈ C1_{t+1}).
  Pas de splice de continu, pas de roll-jump spurious.
- carry_t **prédit** ret_{t→t+1} : c'est exactement le test de la prime (de Roon / Koijen-Carry).

Stratégies :
1. **TS-carry** (principal, vu le breadth bas) : `pos_t = sign(carry_t)` par marché ; P&L mensuel =
   `pos_t × ret_{t→t+1}` ; vol-scalé equal-risk entre marchés, gross=1x (pas de levier empilé).
2. **XS-carry** (secondaire) : rank les marchés par carry, long moitié haute / short moitié basse.

## Gates pré-enregistrés

### (A) L'EDGE EXISTE
- **A1 significance** : TS-carry full-sample Sharpe>0 ∧ t>2. *(DSR reporté ; voir caveat breadth.)*
- **A2 LES DEUX CÔTÉS PAIENT** *(le vrai test prime-vs-beta)* : moyenne des rendements quand
  long-backwardation (carry>0) **>0** ∧ moyenne quand short-contango (carry<0) **>0**. Si seul le
  long paie (= beta long pétrole en bull) → **DOWNGRADE/KILL**. Miroir du brut_long ∧ brut_short.
- **A3 régimes** : rendement net positif dans **≥3/5** sous-périodes (pré-GFC / GFC08 / 2010s /
  COVID20 / 2021+). L'énergie a des régimes violents (glut 2014-16, oil négatif 2020, backw. 2022).
- **A4 pas un seul marché** : drop-one (retirer WTI, NG, HO, ou RB) → TS-carry reste Sharpe>0.
- **A5 DSR** : DSR(best, N=4 essais) > 0.95.

### (B) L'EDGE VAUT LE COUP (sleeve / orthogonalité)
- **B1 orthogonalité** : |corr(rendements carry, SPY mensuel)| < 0.30.
- **B2 sleeve** : ajouter le carry à 60/40+trend améliore le Sharpe (test sleeve 10-25 %).

## Verdict (mapping pré-enregistré)

| Cas | Verdict |
|---|---|
| A1∧A2∧A3∧A4∧A5 ∧ B | **GO-narrow** : prime carry énergie réelle + orthogonale + sleeve+. Flag « confirmer univers large non-free ». |
| A2 FAIL (seul long paie) | **DOWNGRADE** : beta énergie, pas prime carry. |
| A1 FAIL (t<2) mais A2∧A3∧B1 OK | **DOWNGRADE-to-watch** : directionnellement réel mais sous-puissant au breadth free (PAS un KILL propre — le breadth, pas l'absence de prime, plombe le t). |
| A2 FAIL ∧ A3 mixte | **KILL** : pas de prime. |

Le caveat breadth est pré-enregistré pour qu'un t<2 ne soit pas sur-interprété en KILL si la prime
est par ailleurs présente (2 côtés + régimes + orthogonale). Inversement, A2 (les 2 côtés) est le
gate dur : sans lui, c'est du beta, point.

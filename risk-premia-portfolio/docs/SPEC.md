# META — Portefeuille risk-premia diversifié (post-21-kills)

**Pré-enregistré le 2026-06-23, AVANT tout chiffre de combinaison.** Aucun critère
ci-dessous ne sera modifié après avoir vu les résultats. C'est une **construction**,
pas une chasse à l'edge — mais soumise à la **même** discipline anti-overfit que les 21
études : les règles de poids et les seuils de succès sont fixés ici, en amont.

## Contexte

21 études, 0 edge déployable solo. Le programme a prouvé qu'à information/prix public,
liquide, compété, un solo sans latence/infra/capital n'extrait rien. **Une seule chose a
survécu à la rigueur** : le premium **trend-following** (piste 1) — réel (DSR 0.988),
crisis-alpha 2008/2022, mais trop faible en standalone (Sharpe 0.42 < 60/40 0.93). Son
seul usage honnête = **sleeve diversifiant** (+0.12 Sharpe sur un cœur passif).

Hypothèse meta : après 21 kills, **le deliverable n'est pas un edge mais un portefeuille
diversifié** où le seul « edge » est la **diversification + la discipline**. On teste si
combiner les briques RÉELLES survivantes, sous une règle de poids pré-committée (pas
d'optimisation in-sample = l'overfit que tout le programme refuse), produit un profil
risque-ajusté **meilleur que chaque brique seule** — ou si même ça ne bat pas le passif.

## Ingrédients (seulement les survivants RÉELS)

| Sleeve | Statut programme | Inclus ? | Justification |
|---|---|---|---|
| **60/40 passif** (SPY/IEF) | premium equity+terme, connu | OUI (cœur) | base que tout investisseur a déjà ; le benchmark à battre |
| **Trend 12m** (TSMOM ETF) | piste 1, réel DSR 0.988, crisis-alpha | OUI (sleeve) | le SEUL survivant rigueur ; corr actions −0.12 = vrai diversifiant |
| **FX carry G10** (piste 17) | KILL standalone (t=0.99) mais **orthogonal** (corr trend +0.01), signe économiquement fondé (UIP) | OUI (petit) | candidat-diversification : faible mais réel-de-signe et décorrélé. **Test = ajoute-t-il ou dilue-t-il ?** |
| VRP / GEX / carry-crypto / autres | KILL/DOWNGRADE tail ou friction | NON | tail-catastrophe (VRP), non-directionnel (GEX), risque exchange (crypto). Pas des briques de portefeuille sain |

Tous les sleeves sont ramenés en **rendements mensuels** (alignement propre ; FRED carry
est mensuel). Le moteur trend = `factor-harvest/backtest.run_strategy` (vol-targeté,
no-look-ahead, déjà validé). Carry = `fx-carry/carry.carry_portfolio` (net de coûts).

## Règles de construction — PRÉ-COMMITTÉES (zéro optimisation in-sample)

**Règle primaire — risk-parity inverse-vol, vol-targetée :**
- Poids de chaque sleeve ∝ **1 / vol trailing 36 mois** (fenêtre glissante, **laggée** :
  vol connue à t−1, poids appliqués au rendement de t). Égalise la contribution au risque.
- Portefeuille global **vol-targeté à 10 %/an** (scalaire sur la vol trailing 36m du combo,
  laggé). Cosmétique pour le Sharpe (scale-invariant) mais rend les niveaux comparables.
- **Aucun poids n'est choisi pour maximiser un résultat passé.** L'inverse-vol est une
  règle mécanique fixée ici.

**Variantes de robustesse (fixées AUSSI en amont, pour tester la stabilité, pas pour
cherry-pick) :**
1. **Fixe core-satellite** : 70 % 60/40 + 20 % trend + 10 % carry (poids « raisonnables »
   pré-committés, pas optimisés).
2. **Sans carry** : risk-parity sur {60/40, trend} seuls — isole la contribution carry.
3. **Equal-weight** : ⅓ / ⅓ / ⅓ des trois sleeves.

Le nombre de schémas essayés (**4**) alimente la déflation DSR (n_trials).

## Critères de succès — PRÉ-ENREGISTRÉS

Le meta est un **deliverable réel** (KEEP) si et seulement si :

- **(M1) Le tout bat chaque partie.** Sharpe(combo risk-parity, net) **>** Sharpe de
  CHAQUE sleeve seul, **dont le 60/40**. C'est la définition d'un gain de diversification :
  si le combo ne bat pas le meilleur composant, la combinaison n'apporte rien.
- **(M2) Le gain vient de la diversification, pas du fit.** Le Sharpe du combo est
  **stable** sur les 4 schémas (pas un knife-edge sur un réglage). Écart-type des 4
  Sharpes faible ; l'inverse-vol n'est pas significativement battu par un fixe arbitraire.
- **(M3) Survit à la déflation.** DSR(combo, n_trials=4) calculé. **DSR > 0.95** = KEEP-fort.
  0.5 < DSR < 0.95 = KEEP-faible (diversification réelle mais modeste, conforme littérature
  « managed futures = diversifiant »). DSR < 0.5 = le gain est du bruit → NO-GO.
- **(M4) Le bénéfice économique tient.** Le combo conserve le **crisis-alpha** du trend :
  rendement 2008 ET 2022 **meilleur que le 60/40 pur** (la vraie raison économique de
  porter le sleeve, pas juste un Sharpe in-sample).

## Mapping verdict

- **(M1)∧(M3 fort)∧(M4) ⟹ KEEP-FORT** : portefeuille diversifié = deliverable, gain robuste
  et significatif. Préciser la composition retenue.
- **(M1)∧(M3 faible)∧(M4) ⟹ KEEP-FAIBLE** : diversification réelle mais modeste (+0.1–0.2
  Sharpe), honnête « tiens 60/40 + sleeves », pas un money-machine.
- **Carry dilue** (combo-sans-carry ≥ combo-avec-carry) ⟹ **KEEP-2-SLEEVE** : drop carry,
  deliverable = 60/40 + trend seul. (Résultat attendu plausible vu t=0.99 du carry.)
- **¬(M1)** (rien ne bat le 60/40) ⟹ **NO-GO-TRIVIAL** : même la combinaison ne sert à
  rien ; le deliverable honnête se réduit à « achète 60/40 et dors » — clôture sèche du
  programme côté trading.

## Falsifiabilité (ce qui ferait échouer, pré-listé)

- Le carry (t=0.99) peut **drainer** le Sharpe malgré l'orthogonalité → M1 échoue à 3
  sleeves, KEEP-2-SLEEVE.
- L'inverse-vol peut **sous-performer** un fixe naïf → M2 échoue, signe que le gain est
  fragile/réglage-dépendant.
- Sur 2009-2021 (managed-futures winter), le trend traîne → le combo pourrait ne PAS
  battre le 60/40 sur la 2ᵉ moitié → on **rapporte les deux moitiés** (both-halves), pas
  seulement le full-sample.
- Sharpe du combo > 60/40 mais **DSR < 0.5** ⟹ NO-GO (le gain ne survit pas à la déflation).

## Data & reproduction

`python run_meta.py`. Sleeves régénérés depuis les caches existants : trend/60-40 =
`factor-harvest/data/` (ETF total-return yfinance), carry = `fx-carry/data/` (FRED 3m).
Échantillon = intersection mensuelle des trois (~2006–2026). Stdlib + numpy/pandas.
`audit.py` = DSR (Bailey–López de Prado), porté verbatim.

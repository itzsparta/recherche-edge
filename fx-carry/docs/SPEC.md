# SPEC — Piste 17 : FX carry G10 (pré-enregistré)

> Écrit **avant** tout chiffre. Retour à un **edge de prime de risque** (≠ payoff opérationnel #14
> ou cashflow #15). La question : le **carry FX** (long devises à haut taux / short bas taux) dégage-t-il
> une prime réelle, et surtout **AJOUTE-t-il un sleeve orthogonal** au seul deliverable du programme
> (trend +0.12 Sharpe, piste 1) — ou est-il, comme le trend, réel-mais-faible + dominé par le tail ?

## Hypothèse d'edge

Le portefeuille **long devises à haut taux court / short devises à bas taux** (G10 vs USD,
dollar-neutral) encaisse une **prime de carry positive** (Lustig-Verdelhan), distincte du trend, et
**diversifiante** — donc un **2e sleeve** potentiel sur le trend.

## Pourquoi ça pourrait persister — prime structurelle, pas edge prédictif

Le carry n'est pas un pari directionnel sur le prix : c'est une **prime de risque** = compensation
pour le **risque de krach** (les devises à haut taux s'effondrent en risk-off — 2008). UIP échoue
empiriquement (le différentiel de taux ne prédit PAS la dépréciation compensatrice) → la prime survit
car elle **rémunère un risque réel**, pas une inefficience d'information. Famille piste 1 (trend) /
piste 4 (VRP) : prime réelle dont le **tail EST le produit**.

## Le null honnête (= verdict attendu a priori)

Prior : prime **réelle mais faible** (Sharpe historique ~0.4-0.5, érodé post-2008), **dominée par le
krach** (carry crash 2008 −30 %+, skew négatif comme le short-vol). Morts pré-enregistrées :
1. **Faible standalone** (comme trend #1) — Sharpe < hurdle, dominé par 60/40 → **KILL-standalone**.
2. **Tail = le produit** (comme VRP #4) — Sharpe trompeur si aveugle au skew ; le carry crash 2008
   peut effacer des années → **DOWNGRADE** si la prime ≈ le risque de queue.
3. **N'ajoute rien au trend** — si corr(carry, trend) élevée ou Sharpe combiné ≤ trend seul → pas de
   sleeve → **KILL pour l'objectif deliverable**.
4. **Mirage data** — 6 devises, peu de cross-section ; DSR doit survivre (anti-multiple-testing).

## Univers / data (FIXE — déterministe)

6 devises G10 vs USD depuis les **futures FX existants** (`factor-harvest/data/` : 6A AUD, 6B GBP,
6C CAD, 6E EUR, 6J JPY, 6S CHF) pour les **mouvements spot**. **Taux courts 3 mois interbancaires** =
FRED `IR3TIB01{US,EZ,GB,JP,CH,CA,AU}M156N` (mensuel, gratuit) pour le **signal de ranking + l'accrual
de carry**. Fenêtre = depuis 2003 (début data futures) → 2024. Mensuel.

## Mesure (FIXE)

- **Rendement excédentaire** de détenir la devise i (long foreign, funding USD) sur le mois :
  `r_i = spot_return_i + (rate_i − rate_usd)/12` où `spot_return_i` = variation du future FX
  (USD par unité foreign), `rate_i` = taux 3m de i.
- **Signal de carry** = `rate_i − rate_usd` (≈ forward discount par CIP). Ranking mensuel.
- **Portefeuille** dollar-neutral : long les 3 plus hauts différentiels, short les 3 plus bas,
  équipondéré, rebalance mensuel. `R_carry = mean(r_long) − mean(r_short)`.
- **Coûts** : ~2 bps/jambe au rebalance (FX liquide). **Sleeve** : Sharpe de R_carry, corrélation à
  un proxy trend (time-series momentum 12 m sur les mêmes futures) et à SPY ; Sharpe du combo 50/50.

## Gates de décision (pré-enregistrés)

- **(A) Prime réelle** : `mean(R_carry) > 0` avec **t > 2** (mensuel non-chevauchant).
- **(B) Pas un mirage** : **DSR > 0.95** (audit.py, anti-multiple-testing) ∧ pas porté par 1 devise/1 an.
- **(C) Tail** : drawdown max et perte 2008 reportés ; **Sharpe net** crédible *malgré* le krach
  (skew < 0 attendu). Si la prime ≈ le risque de queue (un krach efface l'essentiel) → cap DOWNGRADE.
- **(D) Sleeve orthogonal** : `|corr(carry, trend)| < 0.3` ∧ **Sharpe(50/50 carry+trend) > Sharpe(trend)**.
  C'est le test qui compte pour l'objectif : ajoute-t-il au deliverable ?

## Décision pré-enregistrée

- **(A) ∧ (B) ∧ (C-ok) ∧ (D) ⇒ GO-sleeve** : 2e sleeve diversifiant réel → agrandit le deliverable
  (trend+carry). Pas un edge standalone, mais un **ajout** mesurable et honnête.
- **(A) ∧ (B) ∧ ¬(C-ok) ⇒ DOWNGRADE** : prime réelle mais tail-dominée (carry crash) = comme VRP #4.
- **(A) ∧ ¬(D) ⇒ KILL-pour-l'objectif** : réel mais n'ajoute rien au trend (redondant ou trop faible).
- **¬(A) ∨ ¬(B) ⇒ KILL** : pas de prime, ou mirage DSR.

## Falsifiabilité (comment ça meurt)

1. t < 2 → KILL (A). 2. DSR < 0.95 ou 1 devise porte tout → KILL (B). 3. Sharpe net effacé par 2008,
prime ≈ tail → DOWNGRADE (C). 4. corr(carry,trend) élevée OU Sharpe combo ≤ trend → KILL-objectif (D).

## Données & implémentation

- **Spot FX** : `factor-harvest/data/6{A,B,C,E,J,S}=F.csv` (yfinance front-month, réutilisé).
- **Taux** : FRED `IR3TIB01*M156N` via urllib (CSV gratuit). **DSR** : `factor-harvest/audit.py` copié.
- **Sortie** : `data_fx.py` (FX + taux alignés mensuels), `carry.py` (portefeuille), `run_carry.py`
  (gates A-D + sleeve + verdict), `docs/FINDINGS.md`. Interpréteur = venv factor-harvest (pandas/numpy).

## Verdict attendu a priori

Le carry est une **vraie prime de risque** (UIP échoue, compensation de krach) — donc il devrait
**exister** (gate A plausible PASS, contrairement aux edges prédictifs morts). La question discriminante
est **(D)** : ajoute-t-il un sleeve orthogonal au trend ? Le programme prédit soit un **GO-sleeve modeste**
(carry et trend = les deux primes macro canoniques, corrélation basse → +0.x Sharpe au combo, le 2e
deliverable réel du programme), soit un **DOWNGRADE** si le tail 2008 mange la prime (comme VRP). Une
mort standalone seule (A faible) est possible mais le test utile reste le sleeve : c'est la seule piste
dont le **succès attendu n'est pas un edge mais un ajout diversifiant** au deliverable existant.

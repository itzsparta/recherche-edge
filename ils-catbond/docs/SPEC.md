# SPEC #31 — Prime ILS / cat-bond : le diversificateur vraiment décorrélé

**Pré-enregistré AVANT le run complet.** Probe data déjà vu (rendements annuels grossiers des funds) —
le hurdle ci-dessous est fixé sur PRINCIPE (compensation tail + illiquidité + fees), PAS pour matcher
la data. Discipline 2 sens. [[feedback-gate-override]]

## Thèse

Les **ILS** (insurance-linked securities : cat bonds, quota-shares de réassurance) paient une **prime
de risque** pour porter le risque de catastrophe naturelle. Cette prime est **génuinement décorrélée**
des marchés financiers (un ouragan ≠ une récession) et **persiste par RÉTICENCE de capital** (peu
d'acteurs veulent le risque de queue physique) — PAS par inefficience arbitrable. C'est le sous-type
de mort qu'aucune piste n'a encore esquivé : « arbitré jusqu'au coût » ne s'applique pas, le mur est
l'ACCÈS, pas l'arbitrage.

**Pourquoi maintenant** : le méta-portefeuille (60/40+trend) manque d'orthogonalité au **CŒUR** (carry
crypto/FX corrélé +0.41 ; trend −0.07). L'ILS est le diversificateur canonique. **Rare** : le véhicule
déployable EXISTE en retail (interval funds SRRIX/XILSX/SHRIX) → on teste la prime ET la déployabilité
dans le MÊME instrument (NAV total-return net de fees), pas un indice théorique inaccessible.

## Data (free, yfinance, total-return NAV)

- ILS funds : **SRRIX** (Stone Ridge Reins. Risk Premium, flagship, 2013+), **SHRIX** (2013+),
  **XILSX** (Pioneer/Amundi ILS, 2014+). EMPIX (2021+) en secondaire (trop court pour gating).
- Hurdle / risk-free : **BIL** (T-bill ETF) = T-bill contemporain (rendement varie 0%→5% sur l'échant.).
- Corrélation : **SPY**. Sleeve : 60/40 (SPY/IEF) + trend (32 futures, infra factor-harvest).
- Rendements mensuels = NAV resamplé fin-de-mois. **Fees déjà DANS le NAV** (net retail).

## Construction

- Pour chaque fund : `excess_t = ret_fund_t − ret_BIL_t` (excès sur T-bill contemporain).
- Portefeuille ILS = **equal-weight** des funds disponibles ce mois (union). Report aussi par-fund
  (la divergence SRRIX vs XILSX est un finding).

## Gates pré-enregistrés

### (A) LA PRIME EXISTE ET CLEAR LE HURDLE (net du tail)
- **A1 magnitude** : excès annualisé sur T-bill du portefeuille ILS **> 3 %** ∧ t>2.
  *Rationale hurdle 3 %* : l'ILS a une queue gauche sévère (ouragan → −10 à −20 %/an possible) +
  illiquidité interval-fund (rachats trimestriels ~5 %, lock-up) + fees ~1.5-2.5 %. Sous 3 % d'excès,
  le T-bill (liquide, sans tail) domine. **Pré-enregistré sur principe, pas sur la data.**
- **A2 survit au TAIL** : l'excès reste **>0 en INCLUANT** les années cat (2017 Harvey/Irma/Maria,
  2022 Ian). Pas un artefact de période calme (peso problem = ramasser des pennies avant l'ouragan).
  Report des pires années + skew. HARD : aucune année cat exclue.

### (B) VRAIMENT DÉCORRÉLÉ (la valeur de diversification)
- **B1 orthogonalité** : |corr(ILS, SPY mensuel)| **< 0.20** (la propriété cardinale). Test aussi en
  STRESS (corr pendant les drawdowns actions — l'ILS doit rester ~0, sinon le free-lunch est faux).
- **B2 sleeve** : ajouter l'ILS à 60/40+trend améliore le Sharpe (orthogonal+prime>0 ⇒ devrait).

### (C) DÉPLOYABLE (souvent le mur — ici partiellement résolu)
- **C1** : véhicule retail accessible = OUI (SRRIX/XILSX). Contrainte RÉELLE = liquidité interval-fund
  (rachat trimestriel gaté ~5 %, pas de sortie rapide en crise) + minimums. Notée, pas simulable.

## Verdict (mapping pré-enregistré)

| Cas | Verdict |
|---|---|
| A1∧A2 ∧ B1∧B2 | **GO** : prime ILS réelle, décorrélée, clear le hurdle net-du-tail, déployable retail → **vrai nouveau sleeve orthogonal** (1er du programme à esquiver le mur d'accès). |
| A2∧B1 OK mais A1 FAIL (excès <3 %) | **DOWNGRADE** : prime réelle + décorrélée mais **mangée par fees+tail** dans le wrapper retail → diversificateur réel mais trop mince net, dominé par T-bill. NOUVEAU sous-type : *prime réelle consommée par le wrapper accessible*. |
| B1 FAIL (corrélé) ∨ A2 FAIL (négatif tail inclus) | **KILL** : pas le diversificateur annoncé / peso problem. |

Discipline : le hurdle 3 % ne sera PAS baissé pour sauver un GO. La divergence inter-funds (SRRIX
flagship ~breakeven vs XILSX +5 %) sera traitée honnêtement (sélection de fund ≠ prime structurelle ;
risque survivorship = yfinance n'a que les funds SURVIVANTS).

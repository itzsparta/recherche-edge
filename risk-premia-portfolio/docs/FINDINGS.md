# META — Portefeuille risk-premia diversifié : FINDINGS

**Verdict (2026-06-23) : KEEP-2-SLEEVE-FAIBLE — assurance-crise conditionnelle.**
Première **construction** (pas une chasse) du programme, après 21 kills. On combine les
briques RÉELLES survivantes sous règles de poids **pré-committées** (docs/SPEC.md, aucun
poids optimisé in-sample). Résultat net : le deliverable honnête = **60/40 + sleeve trend**
(le carry, 3ᵉ sleeve candidat, **dilue** et est rejeté). Mais sa valeur est **conditionnelle
à la présence d'une crise dans l'échantillon** — c'est de l'**assurance**, pas une
domination de Sharpe. Le 3-sleeves « tout dedans » **FAIL**.

> Reproduire : `python run_meta.py`. Sleeves régénérés via les moteurs déjà validés
> (`factor-harvest/backtest.py` trend+60/40, `fx-carry/carry.py` carry), caches locaux.

## Les briques (mensuel, 2006-04 → 2026-02, 238 mois)

| Sleeve | Sharpe | t | corr/cœur | Statut |
|---|---|---|---|---|
| 60/40 passif (SPY/IEF) | **+0.92** | +4.11 | — | cœur (benchmark à battre) |
| Trend 12m (piste 1) | +0.43 | +1.92 | **−0.094** | seul survivant rigueur, vrai diversifiant |
| FX carry G10 (piste 17) | +0.10 | +0.45 | **+0.408** | faible ET corrélé au cœur = risk-on |

corr(carry, trend) = −0.071 (orthogonaux entre eux) **mais** corr(carry, 60/40) = **+0.41**.
C'est le nœud : le carry est orthogonal au trend mais **pas au cœur actions** → il importe
de la bêta risk-on, pas de la diversification.

## Le test, deux fenêtres (la clé de l'honnêteté)

Le RP inverse-vol exige 36 mois de warmup → sa fenêtre **exclut 2008**, exactement la crise
où le trend paie. Il faut donc lire **les deux** :

| | full 2006-26 (238m, **incl. 2008**) | post-warmup 2009-26 (202m, **sans 2008**) |
|---|---|---|
| 60/40 cœur | +0.92 | **+1.20** (bull post-GFC exceptionnel) |
| fixe 70/20/10 | **+0.98** (+0.06 vs cœur) | +1.22 (+0.02) |
| RP2 (60/40+trend) | — | +1.10 (**−0.10 vs cœur**) |
| RP3 (3 sleeves) | — | +0.89 (dilué par carry) |

- **Avec 2008 en échantillon** : le sleeve **aide** (fixe 0.98 > 0.92 ; piste 1 montrait
  jusqu'à +0.12 à poids sleeve plus élevé).
- **Sans 2008** (bull calme 2009+) : le 60/40 seul était si bon (1.20) que le sleeve
  **dilue** (RP2 1.10 < 1.20). Both-halves le confirme : 1ʳᵉ moitié 2009-2017 RP2 **+1.12 vs
  60/40 +1.71** (perd lourd, bull pur) ; 2ᵉ moitié 2017-2026 RP2 **+1.07 vs +0.91** (gagne,
  contient 2022). **Incrément régime-dépendant, pas robuste.**

## Pourquoi c'est de l'ASSURANCE (la vraie valeur économique)

Le sleeve ne sert pas à battre un 60/40 de bull calme — il sert à **couper le drawdown de
crise** :

| Année crise | 60/40 pur | fixe 70/20/10 | equal-weight |
|---|---|---|---|
| 2008 | **−16.7 %** | −9.9 % | −4.9 % |
| 2022 | **−16.4 %** | −10.1 % | −3.3 % |

Le sleeve trend ≈ **divise par deux** la perte de crise (corr actions −0.094, crisis-alpha
2008/2022 conservé dans le blend). C'est la thèse « managed futures = diversifiant » de la
littérature, chiffrée : on porte le trend POUR la crise, en acceptant un **drag** en bull
prolongé. Le Sharpe full-sample dépend donc de si une crise est dans ta fenêtre.

## Carry : rejeté (dilue)

RP3 (avec carry) 0.89 < RP2 (sans) 1.10 → le carry **dilue**. Cause : orthogonal au trend
mais **corrélé +0.41 au cœur** + Sharpe 0.10. **Leçon générale** : la diversification n'est
un free-lunch que si le sleeve ajouté est orthogonal au **CŒUR**, pas seulement aux autres
sleeves. Empiler une prime faible qui partage la bêta du cœur (carry risk-on) **n'ajoute
rien**. Confirme le KILL standalone de la piste 17 sous un autre angle (portefeuille).

## Verdict & deliverable

- **KEEP-2-SLEEVE-FAIBLE** : le portefeuille déployable = **60/40 + sleeve trend** (poids
  ~15-35 %, cf. courbe piste 1 : 60/40 0.92 → ~1.00-1.05). Réel, robuste **quand une crise
  est en échantillon**, conserve le crisis-alpha. Mais incrément modeste (+0.06 à +0.12
  Sharpe) et **régime-dépendant** (dilue en bull calme) → FAIBLE, pas FORT.
- **3-sleeve = FAIL** : carry dilue, drop.
- **DSR(best, n=4) = 1.000** mais NON décisif ici : le DSR mesure le Sharpe **absolu** (un
  combo 70 % obligs/actions a forcément un DSR élevé) ; le vrai test = l'**incrément** sur
  le cœur, qui est +0.06 (full) / régime-dépendant (halves). Piège évité : ne pas confondre
  « Sharpe absolu significatif » et « le sleeve bat le cœur ».

## Place dans le programme

C'est l'**aboutissement honnête** après 21 kills, pas un 22ᵉ edge. Le seul survivant de la
rigueur (trend) se comprend, en portefeuille, comme **assurance-crise sur un cœur passif** —
valeur réelle mais conditionnelle, modeste, et qui ne se cumule PAS avec d'autres primes
faibles (carry) dès qu'elles partagent la bêta du cœur. Le deliverable trading du programme
reste **mono-sleeve trend sur 60/40**, désormais cadré comme assurance, pas comme alpha. Le
vrai capital demeure le **pipeline de verdicts pré-enregistrés** (22 études).

---

## META v2 (2026-06-30) — remplacer le FX-carry diluant par 2 sleeves vraiment orthogonaux

**Verdict : KEEP-FAIBLE = ASSURANCE-CRISE — conclusion v1 INCHANGÉE.** L'objection de fond
au v1 était que le FX-carry diluait *parce que* corrélé +0.41 au cœur. Test direct : le
remplacer par les deux primes survivantes les plus orthogonales au cœur — **carry_energy**
(#30, TS-carry énergie, corr cœur **−0.105**) et **ils** (#31, cat-bonds, corr cœur
**+0.106**). Hypothèse : des briques *réellement* orthogonales au cœur ajouteraient
l'incrément que le FX-carry ne pouvait pas. **Réfutée.**

> Reproduire : `python run_meta_v2.py`. Sleeves via les moteurs déjà validés
> (`commodity-carry/run_carry.py`, `ils-catbond/run_ils.py`, caches locaux).

### Scope acté (pas caché)
Intersection STRICTE 4-way = ils 2013-03 → carry_energy 2024-04 (cache EIA) = **134 mois**,
post-warmup inv-vol **2016-03→2024-04 (98 mois)**. ⇒ **2008 INTESTABLE** (ils n'existe pas
avant 2013) ; M4-crise = **2022 seul**. La thèse v2 se joue donc sur le régime calme+2022 —
là où le trend-seul (v1) dilue déjà.

### Résultats (fenêtre 2016-2024, sans 2008)
| Sleeve / combo | Sharpe |
|---|---|
| 60/40 cœur | **+0.87** (domine) |
| trend | +0.00 (managed-futures winter) |
| carry_energy | **−0.20** (perd sur cette fenêtre) |
| ils | +0.38 |
| RP2 (cœur v1, 60/40+trend) | +0.84 |
| fixe 55/15/15/15 | +0.74 |
| RP4 (4 sleeves inv-vol) | +0.61 |

- **(M1) FAIL** : RP4 +0.61 < cœur +0.87. Rien ne bat le 60/40 sur Sharpe.
- **Les neufs DILUENT** : RP4 +0.61 < RP2 +0.84. Plus de sleeves = pire, *malgré*
  l'orthogonalité au cœur.
- **incrément-Sharpe sur cœur = −0.14** ; both-halves RP4 bat 60/40 = **False**
  (1ʳᵉ moitié 2016-20 RP4 +0.18 vs 60/40 +1.11, écrasé en bull).
- **(M4) crisis-alpha 2022 = OK et FORT** : fixe **−1.5 %** vs 60/40 **−16.4 %** ;
  equal-weight **+9.4 %** ; RP4 +2.0 %. Les sleeves coupent (voire annulent) la perte 2022.

### Pourquoi l'orthogonalité n'a PAS suffi
Le FX-carry diluait par **corrélation** au cœur (+0.41 = bêta risk-on importée). Les neufs
sont vraiment décorrélés du cœur (−0.105 / +0.106) — donc **autre cause** : leur Sharpe
**propre** est trop faible sur la fenêtre (carry_energy −0.20, ils +0.38) pour soulever
l'incrément. Orthogonalité = **nécessaire mais non suffisante** ; il faut aussi une **prime
propre positive**. Empiler des décorrélés faibles sur un cœur fort (60/40 +0.87 en bull) =
drag, pas free-lunch. C'est la même structure que v1 vue sous un 2ᵉ angle : la valeur des
sleeves est l'**assurance-crise** (2022 chiffré ici), pas un incrément de Sharpe en régime
calme — et une fenêtre sans 2008 fait gagner le cœur **par construction**.

### Deliverable inchangé
**60/40 + trend** reste le seul deliverable trading, cadré assurance-crise. Le v2 ferme la
question « et si on remplaçait le carry par mieux ? » : non — aucune combinaison de primes
publiques faibles ne crée d'alpha sur le cœur ; elles ne font que (bien) couper les crises.
Limite honnête : 2008 hors-fenêtre pour ce combo, donc le crisis-alpha v2 n'est démontré que
sur 2022 (cohérent avec le 2008 du v1 mono-sleeve).

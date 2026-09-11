# SPEC #35 — Prime fallen angels : le flux forcé par MANDAT (pas par info)

**Pré-enregistré le 2026-09-11, AVANT tout rendement.** Seul probe fait : les **dates de début** des
tickers (ANGL 2012-04, FALN 2016-06, WING.L 2016-06, HYG 2007-04, LQD 2002-07) — aucun rendement,
aucun écart, aucune régression vus. Prior externe connu et déclaré : VanEck (émetteur d'ANGL, donc
source intéressée) revendique une surperformance vs HY 15 années sur 22 et une prime de spread ~120 bps.
Aucun seuil ci-dessous n'est calé sur ce prior ; discipline 2 sens [[feedback-gate-override]].

## Thèse

Quand une obligation passe d'investment grade à high yield, les détenteurs IG (assureurs, fonds à mandat
IG, fonds indiciels IG) sont **contraints de vendre** — par mandat/réglementation, pas par information.
Ces ventes forcées, concentrées autour de la dégradation, font **surcorriger** le prix ; le détenteur non
contraint est payé pour absorber le flux. C'est la famille « flux forcé », mais avec une différence
cardinale vs les morts du programme :

- l'effet d'indexation S&P 500 (flux public, daté, prévisible) est mort : 7,4 % (1990s) → <1 % (2010s)
  (Greenwood-Sammon) ; le rebalancement LETF (#25) est absorbé par la liquidité ;
- ici la contrainte est **juridique** (interdiction de détenir), l'arbitragiste naturel (fonds HY) a sa
  propre capacité limitée, et l'événement n'est pas daté à l'avance. Si un flux forcé survit quelque
  part, c'est là.

Sample = ETF 2012+ → **entièrement post-documentation académique** du phénomène : pas de biais
McLean-Pontiff à corriger, l'échantillon est déjà out-of-sample vis-à-vis de la publication.

## Le confound à tuer d'abord : le bêta déguisé

ANGL ≠ HYG sur deux axes de BÊTA, pas d'edge : (1) **duration plus longue** (anciennes IG = maturités
longues) → gagne mécaniquement quand les taux baissent (2012-2020), perd en 2022 ; (2) **qualité plus
haute** (majorité BB) → moins de défauts, spread plus bas. Un écart brut ANGL − HYG > 0 ne prouve
**rien**. Le gating porte sur l'**alpha de régression** après contrôle crédit HY + terme.

## Data (free, yfinance, total-return prix `auto_adjust`)

- Fallen angels : **ANGL** (VanEck, gating principal, 2012-05→dernier mois complet), **FALN** (iShares
  US, 2016+, réplication), **WING.L** (iShares UCITS, USD, 2016+, **le véhicule achetable par un
  résident FR** — ANGL/FALN sont US sans KID).
- Facteurs : **HYG** (crédit HY), **IEF** (terme 7-10 ans), **LQD** (crédit IG), **BIL** (T-bill).
- Portefeuille : **SPY/IEF** 60/40 + trend (moteur `factor-harvest`, identique #31/#22).
- Rendements mensuels = prix ajusté fin de mois. Frais TER **déjà dans** les prix. Prix de marché (pas
  NAV) : les décotes d'ETF obligataires (mars 2020) sont incluses = réalité déployable.

## Modèles (pré-committés)

`ex_X = r_X − r_BIL`.

- **2F (primaire, gating)** : `ex_FA = α + β_HY·ex_HYG + β_T·ex_IEF + ε`
- **3F (robustesse)** : 2F + `(r_LQD − r_IEF)` (prime de crédit IG → contrôle la qualité BB)
- t-stat de α = **Newey-West HAC, lag 3** (rendements obligataires autocorrélés / prix stale).
- Série couverte `h = ex_FA − β̂·facteurs` (= α + ε) pour DSR et sous-échantillons.
- Variantes = {2F ANGL, 3F ANGL, 2F drop-2020, 2F FALN, 2F WING} → **n_trials = 5** pour la DSR.

## Gates pré-enregistrés

### (A) LA PRIME EXISTE, NETTE DE BÊTA
- **A1** : α_2F(ANGL) **≥ +1,0 %/an ∧ t_NW ≥ 2,0**.
  *Rationale 1 %* : sous 1 %/an, l'alpha est dans le bruit d'estimation d'un panier concentré
  (secteurs énergie/auto, quelques centaines d'émetteurs) et ne justifie pas un sleeve de plus. Fixé
  sous le prior VanEck (~1,2 %) mais au-dessus du différentiel de TER vs HYG (~0,2 %, qui gonfle
  mécaniquement α et n'est pas une prime de flux).
- **A2** : α_3F(ANGL) **> 0 ∧ t_NW ≥ 1,5** (la prime survit au contrôle qualité IG).
- **A3** : **DSR(h_2F ANGL, n_trials=5) > 0,95**.

### (B) PAS UN MIRAGE DE RÉGIME / DE VÉHICULE
- **B1 both-halves** : α_2F > 0 sur **chaque moitié** (coupe au mois médian).
- **B2 drop-2020** : α_2F ≥ +0,5 %/an **en excluant 2020-02→2020-12** (vague record de dégradations
  Ford/Oxy/Kraft + rachats de la Fed via SMCCF, qui achetait des fallen angels = régime n=1 non
  répétable, cf. leçon LST).
- **B3 drop-best-year** : α_2F > 0 sans la meilleure année calendaire de `h`.
- **B4 réplication** : α_2F(FALN) > 0 (autre émetteur, autre index, 2016+).

### (C) UTILE ET DÉPLOYABLE
- **C1 déployable FR** : α_2F(**WING.L**) > 0 (le seul véhicule UCITS achetable, TER 0,50 %).
- **C2 sleeve** : sur (60/40 + trend 20 %), ajouter FA à 15 % (risk-scaled comme #31) améliore le
  Sharpe **ET plus que HYG ajouté de la même façon** : `incr(FA) > 0 ∧ incr(FA) > incr(HYG)`.
  Sinon FA n'est que du crédit HY mieux emballé, pas un sleeve.

## Verdict (mapping pré-enregistré, évalué dans cet ordre)

| Cas | Verdict |
|---|---|
| ¬A et écart brut ANGL−HYG > 0 | **KILL bêta déguisé** : la surperformance marketing = duration/qualité. |
| ¬A et écart brut ≤ 0 | **KILL sec** : pas même de surperformance brute. |
| A ∧ ¬B | **KILL mirage** : prime portée par 2020 / une moitié / une année / un seul véhicule. |
| A ∧ B ∧ ¬C1 | **DOWNGRADE non-déployable** : prime réelle US, pas dans le véhicule UCITS. |
| A ∧ B ∧ C1 ∧ ¬C2 | **DOWNGRADE meilleur-HY** : prime réelle, déployable, mais n'aide le portefeuille que via un remplacement HYG→FA pour qui détient déjà du HY. |
| A ∧ B ∧ C | **GO** : 1er flux forcé survivant du programme → candidat sleeve ; intégration au deliverable #22/#34 = étude séparée pré-enregistrée (pas de promotion directe). |

## Diagnostics (non-gating, rapportés quoi qu'il arrive)

Écart brut ANGL−HYG et ANGL−BIL annualisés ; β̂ ; corr SPY normale + stress (décile bas SPY) ;
années calendaires ; skew ; maxDD ANGL vs HYG ; 2015-16 (choc énergie) et 2022 (choc taux) isolés.

## Discipline

Le hurdle 1 % ne sera pas baissé, la fenêtre drop-2020 ne sera pas déplacée, le lag NW ne sera pas
changé après le run. Survivorship : faible (ETF vivants, les 3 gros du segment). Caveat déclaré : β̂
estimés in-sample (la série `h` a un léger look-ahead de bêta, sans effet sur α_OLS).

Reproduire : `python run_fa.py` (après commit de cette spec).

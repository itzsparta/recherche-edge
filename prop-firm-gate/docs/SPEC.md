# SPEC — Méta-gate prop firm : ledger d'EV + simulation de franchissement de barrière

**Pré-enregistré le 2026-06-25, AVANT tout chiffre.** Étude **#24** du programme, **1re sous
l'objectif révisé** « valider un compte prop firm » (cf. `RESEARCH-ROADMAP.md`, section *Objectif
opérant*). C'est la **piste A** du plan prop = le *méta-gate* qui décide s'il existe quoi que ce
soit à bâtir avant de payer la moindre fee.

## Question

Acheter une évaluation de prop firm est-il **+EV** ? Et sinon, sous l'a priori **no-edge** du
programme, **combien** d'edge directionnel (Sharpe annualisé) faut-il pour basculer `EV > 0` ?

Le challenge n'est **pas** une source d'edge : c'est un **wrapper de payoff**. On le traite comme
un **ledger d'EV** (méthodologie airdrop #14), pas un backtest de prix. La sortie décisive = un
**nombre** — l'EV en $ sous no-edge, et le **Sharpe de break-even** — comparé au seul signal
directionnel réel du programme : le **sleeve trend, Sharpe 0.42** (#1, DSR 0.988).

## Hypothèse & null central

- **Hypothèse pro-challenge** : la **convexité** (frais remboursés au 1ᵉʳ payout + extraction du
  compte financé + scaling) suffit à rendre `EV > 0` **même sans edge** ; OU le Sharpe de
  break-even est **≤ 0.42** (donc atteignable par le trend sur instruments prop).
- **Null central (attendu)** : la firme fixe la fee `F` pour que `EV(no-edge) ≤ 0` — c'est son
  modèle d'affaires (≈ books sportifs #16 : produit à marge maison ; *« ce qui te laisse entrer
  tue l'edge »*). On **s'attend à un KILL** ; la simulation est le test falsifiable.

## Modèle (Monte Carlo, pur-sim, zéro data marché)

Compte virtuel, equity en **unités de compte** (E0 = 1.0 ; les limites des firmes sont définies vs
la balance initiale → modèle **additif** en fraction de compte, fidèle aux règles réelles).

**Dynamique par jour.** Le trader fait `k` trades/jour ; chaque trade rend `r = mu_t + sigma_t·z`,
`z~N(0,1)`, ajouté à l'equity. `mu_t = edge_par_trade − cout_par_trade` (drift). Sous le null,
`edge = 0` → `mu_t = −cout`. On suit le **chemin intraday** (cumul des `k` trades) pour tester la
limite *daily* — c'est la « fuite » qui distingue ce modèle d'un simple gambler's ruin.

**Barrières (paramétrées ; valeurs de firmes réelles citées plus bas).**
- **Cible** : equity ≥ `1 + target` (atteinte intraday) → phase passée (si `min_trading_days` atteint).
- **Max drawdown** : *statique* (FTMO « max loss ») plancher fixe `1 − maxDD` ; *trailing*
  (Topstep/Apex) plancher `peak − maxDD` qui monte avec le high-water mark.
- **Daily drawdown** : intraday, equity < `day_start − dailyDD` → échec.
- **Min trading days**, **time limit**, **règle de consistance** (aucun jour > X % du profit total) :
  paramétrés.
- **Ordre des chemins honnête** : si la cible est touchée à un trade *antérieur* à la 1ʳᵉ breach
  intraday → pass ; sinon, si breach → fail.

**Deux phases** (FTMO) : P1 `target=+10 %`, P2 `target=+5 %`, même DD, **une seule fee** couvre les
deux. `P(both) = P1·P2` (comptes séparés, mêmes paramètres → indépendants). Passer les deux → financé.

**Compte financé** : pas de cible ; à chaque date de payout (`payout_days`) on retire le profit
au-dessus de 1.0, on garde `split`, l'equity revient à 1.0 ; le compte **meurt** à la 1ʳᵉ breach DD.
`E[extraction]` = somme des retraits sur la vie du compte (horizon borné `funded_horizon_days`).

**Ledger d'EV** (unité = un achat de challenge) :
```
EV = P(both) · E[extraction $ | financé]
   + P(both) · P(payout | financé) · refund · F        (remboursement de la fee)
   − F
```
Retries non modélisés : un seul achat est l'unité de décision (si `EV_single ≤ 0`, racheter est
aussi ≤ 0 ; si > 0, on répète — le **signe** tranche).

## Paramètres pré-enregistrés (2 firmes-archétypes, cités)

**BASE — FTMO-like (statique ; le plus favorable à une stratégie de barrière, et l'archétype que le
toolkit trend-sur-FX/futures vise).** Account $100k ; **F = $540** ; **refund = 100 %** au 1ᵉʳ
payout ; P1 +10 % / P2 +5 % ; **max loss 10 % statique** ; **daily 5 %** ; `min_trading_days = 0`
(FTMO l'a retiré) ; **pas de time-limit** ; pas de consistance ; **split 80 %** ; payout / 14 j ;
scaling **ignoré** en base (ne peut qu'améliorer → KILL conservateur).

**STRESS — Topstep-like (trailing ; futures).** F mensuel ~$165 (proxy coût-jusqu'au-pass) ; **pas
de refund** ; target +6 % ; **trailing maxDD ~4 %** ; daily ; consistance 50 % ; split 90 %.

**Coûts & sizing.** `cout_par_trade` = fraction de compte, base **5 bp = 0.00005** (futures liquides
type MES : ~$3 round-trip sur $100k), **balayé** [0.00002, 0.0002] (CFD/FX plus large). `sigma_t`
et `k` **balayés** ; on rapporte `P(pass)` à la **sizing qui la MAXIMISE** = best-case **donné à la
thèse** (un KILL est donc conservateur).

## Gates (pré-enregistrés — coupent dans les DEUX sens)

- **PASS (prop poursuivable)** ssi **l'une** :
  - (i) `EV(no-edge) > 0` après fee (la convexité seule suffit — résultat surprenant), **ou**
  - (ii) **Sharpe de break-even ≤ 0.42** (le trend réel le clear) **et** réalisable sur instruments prop.
- **KILL (produit à marge maison)** ssi `EV(no-edge) ≤ 0` **et** **Sharpe de break-even > 0.42**.
- **Robustesse** : la conclusion doit tenir sur les **deux** archétypes (statique ET trailing). Si
  elle bascule, nommer la règle de firme responsable (variable décisive identifiée d'avance :
  statique > trailing, time-limit, consistance, refund).

## Sorties bonus (pont vers piste B = overlay GEX)

- **Optimum de sizing** : `P(pass)` vs risque/trade — vérifie l'**invariance gambler's-ruin** (sous
  null symétrique statique, `P(pass)` indépendante de la taille de mise *sauf* via la fuite
  daily-DD) et **localise la fuite**.
- **Canal daily-DD** : `P(pass)` vs `sigma_t` — si réduire la vol monte `P(pass)`, alors un overlay
  qui coupe la vol des mauvais jours (proxy **GEX-survie**, sans data GEX) a de la valeur → décide
  si la **piste B** vaut le coup. Sinon, B est mort-né.

## Falsifiabilité / honnêteté

- Sizing **best-case donné à la thèse** + refund 100 % + scaling ignoré + coût borné bas =
  **généreux envers le challenge** → un KILL est conservateur, un GO crédible.
- Le **coût/trade** est le levier sensible : borné bas, sensibilité rapportée.
- Sanity-checks d'ingénierie obligatoires AVANT lecture : sous `mu=0` sans fuite daily, P1
  (10/10 symétrique) doit ≈ **0.50** ; P2 (target 5 / maxloss 10) doit ≈ **0.667** (gambler's ruin).
  Si le moteur rate ça, on débogue avant tout verdict.
- [[feedback-gate-override]] : la barre **0.42** (Sharpe du trend réel) est fixée AVANT les chiffres
  et ne bouge pas si le break-even tombe juste au-dessus/dessous.

## Note de correction (run #1 → run #2, 2026-06-25)

Le 1ᵉʳ run a utilisé un **coût/trade placeholder de 0.00005** (0.5 bp de compte) et n'a lu que la
**moyenne** → il a rendu un **faux-GO** (`EV(no-edge) > 0` sur les deux archétypes). Diagnostic : le
coût était **20-30× trop bas** pour du futures actif (réel ≈ 5-15 bp) et la moyenne est trompeuse.

Corrections du run #2, **pré-déclarées ici comme réparation d'erreur d'input vers la réalité
documentée — PAS un tuning vers le KILL** :
1. **Coût réaliste** `COST_BASE = 0.0005` (~5 bp) **+ slippage proportionnel** `SLIP·sigma_t`
   (impact de taille), avec **sweep complet `EV(coût)`** rapporté + coût de break-even — la décision
   ne repose donc pas sur un point estimate.
2. **Distribution** : on lit désormais EV (moyenne) **ET médiane + P(net>0)** (lecon airdrop #14).
3. **Gate durci** : un PASS exige la **déployabilité réelle** = avec l'edge trend (0.42), `EV > 0`
   **ET médiane > 0** (pas une loterie). Le break-even sur la *moyenne* est insuffisant car contaminé
   par la queue chanceuse. Durcir un gate qui donnait un PASS favorable = la direction crédible
   [[feedback-gate-override]].

**Le verdict est robuste au coût** : la médiane vaut −fee à *tous* les niveaux de coût du sweep, donc
la correction de coût ne porte pas la conclusion (elle ne touchait que le signe de la moyenne).

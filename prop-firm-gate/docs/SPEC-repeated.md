# SPEC — Prop firm en JEU RÉPÉTÉ : EV par achat (pas médiane), récolte de buffer + bankroll

**Pré-enregistré le 2026-06-25, AVANT tout chiffre.** Étude **#26**, ré-ouverture de #24 sous le
**bon critère de succès** (objection de Rémi : *« un payout suffit, pas besoin de battre le marché »*).
#24 a tué sur la **médiane** (`P(net>0)<50%`). Mais en **jeu répété avec bankroll**, la médiane ne
gouverne pas — c'est la **MOYENNE (EV) par achat** qui gouverne. Cette étude lit l'EV, la décompose,
y injecte les **vraies règles** du compte financé, et calcule la **faisabilité bankroll** (ruine/Kelly).

## Le mécanisme « trop propre » à stresser : martingale d'extraction du buffer

Compte financé static-maxDD : equity démarre à 1.0, plancher de mort fixe `b = 1 − m` (m = max loss,
ex. 10%), on **skim** (retire l'excès au-dessus de 1.0, reset à 1.0) tous les `payout_days`. Sous
**drift nul** (zéro coût), l'equity + skim cumulé est une **martingale** → par arrêt optionnel,

```
E[skim total]  =  E0 − b  =  m          (le buffer entier, QUELLE QUE SOIT la politique de skim)
```

Donc il existe un **+EV structurel réel** sous no-edge = **le buffer `m` que la firme t'offre** sur un
plancher *statique*. Ce n'est PAS battre le marché : c'est encaisser les excursions positives pendant
que le plancher fixe et lointain attend. **C'est pourquoi #24 sortait EV(no-edge) > 0 sur FTMO-static
(+$416).** L'ennemi de ce +EV n'est donc PAS l'absence d'edge — c'est :
1. **le COÛT** (drift négatif qui érode `m`),
2. **le TRAILING** (plancher qui suit le high-water → le buffer ne se reconstitue plus → martingale cassée),
3. les **règles funded** (min trading days = plus de coût ; consistance = skim plafonné),
4. la **VARIANCE / bankroll** (EV>0 mais P(funded) faible → faut survivre la série perdante),
5. le **voiding discrétionnaire** (clause anti-« non-real-trading » ; ne peut que NUIRE).

## Question

Sous **no-edge marché**, acheter des challenges **de façon répétée** est-il **+EV par achat** une
fois les vraies règles funded modélisées ? Et un **bankroll modeste** réalise-t-il ce +EV (P(profit
de campagne) > 50 %, ruine acceptable) ?

## Null central

#16 : la firme fixe ses règles pour que `EV(no-edge) ≤ 0`. Killers attendus : le coût mange `m`, OU
le trailing tue le buffer, OU min-trading/consistance l'érodent, OU la variance exige un bankroll
déraisonnable. **Prior = KILL.** MAIS mes propres chiffres #24 (+$416 static) penchent positif →
**genuinely ouvert**. Le coût réaliste futures est BAS (~1-4 bp/jour pour σ 1-2%/j) vs buffer 10 % →
le coût pourrait NE PAS suffire à tuer. Le gate tranche.

## Modèle (Monte Carlo daily, vectorisé)

Equity en unités de compte, pas daily `r = μ_day + σ_day·z`. `μ_day = −cost_day` sous no-edge.
`cost_day = c_fixe + slip·σ_day` (coût croît avec la taille). Daily-DD testée sur **sous-étapes
intraday** (low du jour). Plancher static (`1−m`) ou trailing (`peak−m`).

- **Éval** : phase(s) cible(s) `+target` avant breach ; static/trailing ; daily-DD ; `P(both)`.
- **Funded** : pas de cible ; skim/`payout_days` (excès>1 → keep `split`, reset 1.0) ; **min trading
  days/cycle** (force des jours actifs = coût) ; **consistance** (skim d'un cycle plafonné) ; meurt à
  la 1ʳᵉ breach ; horizon borné.
- **Ledger d'EV** (unité = un achat) avec **économie d'advantage-play** :
  ```
  EV = P(both)·E[skim$|funded]  +  P(both)·P(payout)·refund·F_nominal  −  F_payé
  ```
  `F_payé = F_nominal·(1 − discount)` (codes promo chroniques) ; **refund sur F_nominal** (asymétrie
  réelle exploitable). Décomposition rapportée : skim / refund / −fee.

## Paramètres pré-enregistrés (firmes-archétypes, vraies règles)

- **STATIC — FTMO-like** : $100k ; F_nominal $540 ; **discount 30%** (codes promo courants, borné
  conservateur) → F_payé $378 ; refund 100% de $540 ; P1 +10% / P2 +5% ; **max loss 10% STATIQUE** ;
  daily 5% ; funded min_trading_days/cycle = 4 ; consistance 0 (FTMO funded n'en a pas) ; split 80% ;
  payout/14j ; horizon 504j.
- **TRAILING — Topstep/Apex-like** : $50k ; coût-jusqu'au-pass proxy ; **trailing maxDD ~4%** ;
  consistance funded ; split 90% ; sinon idem. (Devrait tuer le buffer-harvest → contraste décisif.)
- **Coûts** : `c_fixe` balayé [très bas → élevé], `slip` fixe ; **coût de break-even rapporté** (la
  décision ne repose pas sur un point). `σ_day` balayé → **sizing harvest-optimale** (maximise EV).

## Gates (pré-enregistrés — coupent dans les DEUX sens)

- **G1 (cœur +EV)** : `EV(no-edge) > 0` par achat sur l'archétype **static** après coût **réaliste**
  (≤ ~5 bp/jour), avec `E[skim|funded] > 0` substantiel. Rapporter le **coût de break-even**.
- **G2 (vraies règles)** : `EV > 0` tient après injection min-trading-days + consistance + (vérif)
  static = la vraie règle FTMO funded. Le **trailing** doit, lui, faire passer `EV ≤ 0` (cohérence du
  mécanisme buffer).
- **G3 (faisabilité bankroll)** : avec la distribution réelle du net$/achat, un bankroll **modeste
  (≤ ~20 achats)** donne **P(profit de campagne) > 50 %** ET **P(ruine) < 25 %**. Rapporter Kelly +
  nb d'achats médian avant 1er compte financé.
- **GO** ssi **G1 ∧ G2 ∧ G3**. **KILL** sinon, en **nommant le killer** (coût / trailing / règles /
  bankroll).

## Sanity-checks obligatoires (avant tout verdict)

- **Martingale** : à `cost_day = 0`, static → `E[skim|funded] ≈ m` (le buffer). Si le moteur rate
  ça, bug → debug avant lecture.
- Éval gambler's ruin : `P(+10%|maxloss10%) ≈ 0.5`, `P(+5%|10%) ≈ 0.667` (daily-DD off).

## Falsifiabilité / honnêteté — discipline INVERSÉE

- **Je suis désormais biaisé VERS le GO** (Rémi le veut, #24 penche positif). Donc je **fige G1/G2/G3
  AVANT de lancer** et je ne bouge pas les seuils [[feedback-gate-override]]. La discipline qui a tué
  les faux-GO (VRP 1.86, CEF t=7.13) doit aussi **protéger un vrai GO** : si la martingale survit au
  coût réel ET au bankroll, je **ne KILL pas par prior #16**.
- **Chasse au faux-GO** : la martingale `E[skim]=m` est le « trop propre » → stresser coût, trailing,
  voiding. Le **voiding discrétionnaire** (non modélisable) ne peut que NUIRE → si GO, l'énoncer comme
  le risque résiduel n°1.
- **Best-case borné honnête** : discount 30% (pas 50%), coût borné mais balayé, refund 100%. Un GO
  doit survivre au **coût de break-even** rapporté, pas à un point choisi.

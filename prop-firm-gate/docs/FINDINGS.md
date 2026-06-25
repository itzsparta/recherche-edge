# FINDINGS — Étude #24 : méta-gate prop firm (ledger d'EV + franchissement de barrière)

**Verdict : KILL — acheter une évaluation de prop firm est, pour un solo one-shot, une
LOTERIE (médiane = −fee), pas un edge.** Sans edge directionnel, l'EV moyen est ≈ 0 ou
négatif et **porté par une queue chanceuse** (~10 % des achats) ; **même avec le seul signal
directionnel réel du programme (sleeve trend, Sharpe 0.42), la médiane reste à −fee** sur les
deux archétypes de firme. C'est le motif **airdrop #14** (moyenne portée par des jackpots)
croisé avec le théorème **#16** (la convexité exploitable = exactement les règles que les firmes
retirent). Spec + gates pré-enregistrés 2026-06-25 : [`SPEC.md`](SPEC.md) (+ note de correction
du coût). Code : [`../challenge.py`](../challenge.py), [`../run_gate.py`](../run_gate.py).
Données : `../data/gate_results.json`.

## Ce qui a été testé

1re étude sous l'**objectif révisé** (« valider un compte prop firm »). Le challenge n'est pas une
source d'edge : c'est un **wrapper de payoff**. On le traite en **ledger d'EV** (méthodo airdrop
#14), par **simulation Monte Carlo** (pur-sim, zéro data marché, parallélisée 16 cœurs) du pipeline
complet *par trader* : phase 1 → phase 2 → compte financé, sous barrières réelles (max DD
statique/trailing, daily DD, cible, min trading days, consistance) et coûts réalistes. Sortie
décisive = **la distribution du net $ par achat** (moyenne = EV, **mais aussi médiane + P(net>0)**),
plus le **Sharpe de break-even** comparé au sleeve trend (0.42, le seul signal directionnel réel,
#1).

**Moteur validé** avant tout verdict (sanity gambler's ruin) : P(+10 % | maxloss 10 %, symétrique)
= **0.501** (attendu 0.50) ; P(+5 % | maxloss 10 %) = **0.656** (attendu 0.667).

## Le faux-GO du run #1, et sa cause

Le 1ᵉʳ run rendait `EV(no-edge) > 0` sur les **deux** archétypes (+$2 110 FTMO) = drapeau rouge
(une firme ne donne pas d'argent à un lanceur de pièce). Diagnostic : **coût/trade 20-30× trop bas**
(placeholder 0.5 bp de compte ; réel ≈ 5-15 bp pour du futures actif) **et** lecture de la seule
**moyenne**. Corrigés : coût réaliste (5 bp + slippage proportionnel à la taille) **et** lecture de
la **distribution**. Le faux-GO disparaît. Voir la note de correction dans la SPEC : la correction
est une réparation d'erreur d'input, **pas** un tuning vers le KILL — et le **verdict est robuste au
coût** (cf. infra).

## Résultats (best sizing = celle qui maximise P(pass), best-case donné à la thèse)

| Archétype | scénario | EV (moyenne) | **médiane** | P(net>0) | P(financé) |
|---|---|--:|--:|--:|--:|
| **FTMO statique** (fee $540, refund 100 %) | no-edge | +$416 | **−$540** | 9.7 % | 18.3 % |
| FTMO statique | + trend 0.42 | +$3 000 | **−$540** | 23.3 % | 34.9 % |
| **Topstep trailing** (fee $330, no refund, consist. 50 %) | no-edge | −$196 | **−$330** | 4.2 % | 16.5 % |
| Topstep trailing | + trend 0.42 | +$13 | **−$330** | 8.6 % | 24.3 % |

**Sensibilité au coût (FTMO, no-edge)** : EV moyen +$864 (coût 1 bp) → −$342 (coût 20 bp),
break-even du *moyen* à ~11 bp. **Mais la médiane vaut −$540 à TOUS les niveaux de coût** → le
verdict ne dépend pas du coût.

## Le mécanisme du kill — une loterie, pas un edge

1. **Sans edge = loterie pure.** La médiane d'un achat = **−fee** : on perd la totalité du fee dans
   ~90 % des cas. La moyenne (faiblement +$416 sur FTMO) est **entièrement portée par une queue
   chanceuse** de ~10 % d'achats (comptes financés qui « skiment » longtemps avant de sauter). C'est
   le **motif airdrop #14** : une moyenne séduisante adossée à des jackpots non-répétables — un solo
   one-shot **n'encaisse pas une moyenne**, il encaisse une médiane, et elle est négative.

2. **Même le seul edge réel ne sauve pas la médiane.** Injecter le sleeve trend (Sharpe 0.42) fait
   bondir la **moyenne** FTMO à +$3 000 (P(financé) 18 %→35 %, P(net>0) 10 %→23 %), mais la
   **médiane reste −$540**. Pour une médiane > 0 il faudrait **P(net>0) > 50 %** ; le meilleur cas
   atteint **23 %**. Aucune sizing ne franchit ce seuil (P(net>0) < 0.5 sur toute la grille). La
   distribution reste brutalement asymétrique : un solo perd toujours la fee plus d'une fois sur deux.

3. **Gradient #16 chiffré.** FTMO (statique + refund 100 % + pas de consistance) = la convexité la
   plus généreuse (+$3 000 moyen avec edge) ; Topstep (trailing + consistance + zéro refund) =
   écrasé à ≈ $0 (break-even du moyen à Sharpe 0.38, juste sous 0.42, donc ~nul à 0.42). **La
   convexité exploitable vit exactement dans les règles que les firmes suppriment** (passage massif
   au trailing-DD et aux règles de consistance) — *« ce qui te laisse exploiter est ce qu'ils
   retirent »*, théorème #16 sous forme quantifiée.

## Robustesse / honnêteté

- **Best-case donné à la thèse** : sizing maximisant P(pass), refund 100 %, scaling ignoré, coût
  borné bas, edge injecté = le Sharpe du sleeve **diversifié** (0.42). Or un **seul instrument prop
  n'a aucune diversification** → le Sharpe mono-compte réel est **bien sous 0.42** → le +$3 000 est
  **optimiste**, et le cas réaliste mono-compte se rapproche de la loterie no-edge. Le KILL est donc
  conservateur des deux côtés.
- **Verdict cost-robuste** : la médiane = −fee à tous les coûts testés → la correction de coût
  (run #1 → run #2) ne porte pas la conclusion (elle ne touchait que le signe de la *moyenne*).
- **Piste B (overlay GEX-survie) tombe aussi** : un overlay qui réduit les breaches daily-DD ne peut
  monter P(pass) que marginalement ; or il faudrait **doubler** P(net>0) (23 %→>50 %) pour flipper la
  médiane → hors de portée d'un gain marginal de survie. Piste C (exécution trend) idem : l'edge est
  déjà injecté à 0.42 et la médiane reste négative.
- **Caveats modèle** : extraction du compte financé = skim-and-reset (retrait du profit / 14 j,
  plancher statique) — fidèle à FTMO ; le trailing post-payout est approximé. Daily-DD testée au
  chemin intraday. Sanity gambler's ruin passé.

## Place dans le programme

**Étude #24, 1re sous l'objectif prop, KILL.** Sous-type de mort = **loterie / jackpot** (airdrop
#14) appliqué à un **produit à fee** (#16) : la convexité (refund + skim du compte financé) est
**réelle dans la moyenne mais lottery-shaped** (médiane = −fee), et le seul edge réel disponible ne
pousse pas la médiane positive. **Le prop firm ne change pas le constat no-edge** : il le
re-emballe en loterie à marge maison. Pour qu'un achat soit déployable il faudrait soit un edge
mono-compte **très au-dessus de 0.42** (qu'on n'a pas), soit du **capital pour répéter** et lisser
la variance (= un grind à forte variance, pas un edge — et la réplication multi-comptes = piste D,
bannie). 

**Bilan programme : 24 études, 0 edge déployable.** Le méta-gate aura au moins répondu *cheap* à
« faut-il payer $540 ? » → **non, on s'attend à le perdre**.

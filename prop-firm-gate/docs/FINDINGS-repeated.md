# FINDINGS — Étude #26 : prop firm en JEU RÉPÉTÉ (EV par achat + bankroll)

**Verdict : GO — le PREMIER du programme.** Sous no-edge marché, acheter de façon **répétée**
des évaluations FTMO-static **2-Step** et y jouer la **martingale d'extraction du buffer** est
**+EV par achat** (+$668 à coût réaliste et monitoring fin), et un **bankroll modeste** (~20 achats)
réalise ce +EV de façon fiable (**P(profit de campagne) = 76 %**). Le GO **survit à la chasse au
faux-GO** sur les trois axes qui ont tué les faux-GO précédents (monitoring / friction / coût) et
reste robuste à un voiding de la firme **jusqu'à 64 %**. **Seul résidu non-simulable : le voiding
discrétionnaire.** Pré-enregistré, discipline **inversée** (biais assumé vers le GO, seuils figés
avant run) : [`SPEC-repeated.md`](SPEC-repeated.md). Code : [`../repeated_ev.py`](../repeated_ev.py)
(GO) + [`../repeated_ev_stress.py`](../repeated_ev_stress.py) (chasse au faux-GO). Données :
`../data/repeated_ev_results.json`, `../data/repeated_ev_stress.json`.

## Pourquoi #26 ne contredit pas #24 (il le corrige)

#24 a tué le prop firm sur la **médiane** d'un achat unique (`médiane = −fee`, loterie). Mais #24
**voyait déjà** `EV(no-edge) > 0` sur FTMO-static (+$416). Objection de Rémi : *« un payout suffit,
pas besoin de battre le marché »*. En **jeu répété avec bankroll**, ce n'est plus la médiane qui
gouverne — c'est la **MOYENNE (EV) par achat**. #26 prend l'EV>0 de #24 au sérieux et demande : ce
+EV est-il **réel** (survit au coût/monitoring/friction réalistes) et **réalisable** (un bankroll
modeste le convertit en profit fiable) ? C'est un pari à **skew positif** : médiane single-shot
négative (on perd souvent son fee), mais moyenne positive (la queue financée paie), et K≈20 achats
indépendants convertissent le +EV en P(profit) = 76 %.

#24 avait pré-écarté « répéter » sur deux fronts ; #26 y répond :
- *« grind à forte variance, pas un edge »* — vrai, mais l'**objectif révisé** du programme est
  *valider un compte prop firm*, pas *trouver un edge*. Un grind +EV répétable qui passe fiablement
  **EST** le deliverable de cet objectif.
- *« réplication multi-comptes = piste D, bannie »* — #26 n'est PAS piste D. La campagne tire K
  achats **séquentiels-indépendants** (pas de comptes corrélés/copy-tradés simultanés). C'est jouer
  un pari +EV plusieurs fois, pas manufacturer un gagnant par corrélation.

## Le mécanisme : martingale d'extraction du buffer (réel sous no-edge)

Compte financé à plancher **statique** `b = 1 − m` (m = max loss 10 %). On skim l'excès au-dessus
de 1.0 (reset à 1.0) tous les `payout_days`. Sous drift nul, `equity + skim cumulé` est une
**martingale** → par arrêt optionnel, `E[skim total] = E0 − b = m`. **Le buffer entier est
extractible en espérance, quelle que soit la politique de skim.** Ce n'est pas battre le marché :
c'est encaisser les excursions positives pendant qu'un plancher **fixe et lointain** attend. C'est
un **+EV structurel que la firme DONNE** (son coût marketing : elle parie que la masse des acheteurs
est −EV, ce qui est vrai, et finance les rares harvesters disciplinés).

**Sanity moteur (avant tout verdict)** : à coût 0, static, daily-DD off → `E[skim|funded] = 0.1018`
(attendu m = 0.10) ✓ ; gambler's ruin `P(+10%|10%) = 0.498` (~0.5), `P(+5%|10%) = 0.662` (~0.667) ✓.

## Le fait porteur — VÉRIFIÉ, pas assumé

Tout repose sur un plancher **statique** sur le compte financé (s'il **trail**, la martingale casse
→ EV négatif, cas Topstep). Vérifié sur les règles **FTMO 2026** : le **2-Step Challenge → financé**
porte un **max loss 10 % STATIQUE** (ne monte jamais) + daily 5 %. Le **1-Step** est trailing (EOD)
— c'est le cas KILL, non utilisé. L'archétype `base()` (2 phases 10 %/5 %, static, daily 5 %) =
**exactement** FTMO 2-Step financé. La martingale buffer-harvest est donc structurellement activée
sur un produit réel et courant. (Sources : FTMO Academy / Trading Objectives, vérif. juin 2026.)

## Les chiffres (gates pré-enregistrés, tous PASS)

À **coût réaliste 5 bp/j** (~7 bp avec slip à σ 2 %), sizing-optimale σ\* = 0.020 :

| | valeur |
|---|---|
| **G1 cœur +EV** (static FTMO) | EV = **+$668**/achat = funded $1 046 + refund $61 − fee $378 ; **break-even coût = 16.5 bp/j** (≈ 3× le réaliste) |
| **G2 vraies règles** (trailing tue le buffer) | Topstep-trailing EV = **−$200** (tous coûts, tous σ) → le trailing casse bien la martingale ✓ cohérence |
| **G3 bankroll** | K=20 (budget $7 560) → **P(profit) = 76.4 %**, médiane +$11 221, moyenne +$15 285 ; K=10 → 60.7 % ; K=50 → 91.9 % |

Pboth (passe les 2 phases) = 0.21 ; E[skim|funded] = 0.06 (le buffer m=0.10 minoré par horizon
fini + daily-DD + coût) ; P(payout|funded) = 0.52.

## La chasse au faux-GO (post-GO mirage hunt) — OBLIGATOIRE après un GO

Le programme a produit 2 faux-GO (VRP t=1.86 mort sur artefact early-market ; CEF t=7.13 mort sur
bounce au lag d'entrée) qui passaient les gates et mouraient en post-GO. Un GO **déclenche** une
attaque adverse avant verdict. On a frappé les 3 axes mêmes :

1. **Monitoring (discrétisation, type-VRP).** SUB=6 sous-détecte les breach intraday → sur-estime la
   survie. En raffinant SUB 6→96 (16× plus fin) : EV **$769 → $659** (−14 %), **converge** (pas de
   falaise), et σ\* **reste 0.020** au re-sizing. Le +EV n'est **pas** un artefact de discrétisation.
2. **Friction de payout (lag, type-CEF).** Le skim « tous les 14 j, reset 1.0 » suppose une
   extraction frictionless. On injecte un **délai 1er payout** et des **cycles plus longs** (le réel) :
   EV reste **positif partout** — cycle 14 j/délai 30 j = $445 ; cycle 30 j = $463 ; cycle 60 j/délai
   60 j (au-delà des termes FTMO) = $207. Le coût-drift érode 30–70 % mais ne **tue jamais**.
3. **Coût.** Break-even **16.5 bp/j** à monitoring réaliste vs ~5 bp/j réaliste (futures, turnover
   bas car le harvest tient une position et banke par cycle) → marge **3×**.
4. **Voiding (résiduel non-simulable).** Gross extractible $1 046 vs fee $378 → **EV=0 ssi la firme
   void 64 % des payouts-harvest**. L'EV reste positif tant que `p_void < 64 %`. Robuste, mais c'est
   le seul tueur restant.

**Aucune des trois sondes simulables ne tue le GO.** Par la discipline inversée pré-enregistrée, on
ne KILL **pas** par prior #16.

## Verdict honnête, sans surévaluer

**GO = « mérite une validation LIVE à capital minime », PAS « edge déployable à taille ».** Le seul
résidu est non-simulable : la clause de **voiding discrétionnaire** (« non-real-trading » / martingale
/ variance-farming) que les firmes ont précisément pour annuler ce mécanisme. La sim montre que le
+EV survit à tout ce qu'on peut modéliser **et** à un voiding jusqu'à 64 % ; elle ne peut **pas**
trancher le taux de voiding réel contre un harvest discipliné et discret. La seule façon de lever ce
résidu : **acheter 1–3 challenges FTMO 2-Step et observer si les payouts d'un pattern à turnover bas
clearent**. Risque opérationnel : le harvest (tenir une position, banker l'excès, reset) ressemble à
du variance-farming → le faire ressembler à du trading discrétionnaire normal réduit le risque de void.

## Place dans le programme

**Étude #26, 1er GO en 26 études.** C'est le premier candidat à **survivre tous les tueurs
simulables** ; les 25 précédents mouraient sur un mécanisme modélisable (info publique mangée,
structurel arbitré, tail/friction/bounce, edge capté par le sophistiqué). Ici le résidu est une
**inconnue de comportement de contrepartie** — exactement ce qu'un test live à petit capital résout
et qu'une sim ne peut pas. Cohérent avec l'objectif révisé (*valider un compte prop firm*) : la voie
+EV pour le faire est le **buffer-harvest répété sur une firme à plancher STATIQUE** (FTMO 2-Step),
et non le single-shot (loterie #24) ni le trailing (Topstep, buffer cassé). Le deliverable trading
du programme passe de « mono-sleeve trend » à « **mono-sleeve trend + GO-pending-live prop
buffer-harvest** ».

## Revue technique du Brief #26 — sim v2 coût scalé-levier (`repeated_ev_v2.py`)

Une revue externe a soulevé 5 vulnérabilités. Tri honnête après vérification :

1. **« Daily-DD = 2ᵉ barrière absorbante mobile non modélisée »** → **FAUX**. Déjà dans le moteur :
   `floor = np.maximum(static, s − daily_dd)` (`challenge.py:77`, `repeated_ev.py:62`), barrière
   mobile sur `s` = équité day-start, exactement le `0.95·S_t` de la revue. Double barrière
   {10 % statique, 5 % daily} testée jusqu'à SUB=48. Pas un gap.
2. **+5. « σ haute coûteuse + swap/spread-minuit/slippage »** → **LE vrai gap simulable.** Ces
   frictions scalent en **levier** `L = σ_day / σ_actif`. Le coût v1 (`c_fixe + slip·σ`) est linéaire
   en σ mais ne divise pas par σ_actif → sous-estime le coût de sizer haut. v2 ajoute un terme
   `(swap+widen)·L` (mode *hold*) ou `reentry·L` (mode *flat*, le harvester prend le moins cher),
   params bornés conservateur (swap 1.5 bp/L, widen 0.5, reentry 1.0). Slippage-au-stop **écarté avec
   raison** : au-delà de la barrière la firme absorbe la perte, ce n'est pas un coût trader.
3. **« Voiding/résiliation ciblée sur signature buffer-skim »** → seul **résidu vivant**, non-simulable,
   déjà porté en risque n°1 (break-even p_void < 64 %).
4. **« K achats séquentiels indépendants »** → légal sous règles actuelles ; la LLN ne sauve que si
   l'EV/achat reste > 0 — ce que v2 teste.

**Résultat (15 workers, SUB=24, friction levier-aware, seuils figés) :**

| Gate | v2 | Statut |
|------|----|--------|
| G1 EV @5bp+levier (σ_actif 0.007) | **$453**, break-even **14.9 bp** (≥5) | PASS |
| G2 trailing | **−$240** (≤0) | PASS |
| G3 bankroll K=20 | P(net>0) = **0.664** | PASS |

- **EV v1 $693 → v2 $453 = −35 %.** Le coût-levier mord franchement mais **ne tue pas** ; break-even
  reste ≈ **3×** le coût réaliste 5 bp.
- Sensibilité σ_actif : 0.005 → $389 / 0.007 → $453 / 0.010 → $539 (tous > 0 ; moins de levier
  requis = EV plus haute).
- Mécanique : l'optimum bascule en mode **flat** (flatter avant minuit < payer le swap overnight) —
  confirme que le swap EST le coût dominant, mais esquivable au prix d'une ré-entrée.
- **Caveat de bord fermé** : grille σ étendue à 0.040, l'optimum **reste à σ* = 0.020** (intérieur,
  pas un artefact de bord) — le coût-levier linéaire contre-balance exactement le gain de skim-speed
  au-delà de 0.02.

**La revue ne flippe pas le GO.** « Survit aux tueurs simulables » passe de *provisoire* à
**re-validé sous coût-levier** (haircut 35 %). Verdict inchangé : **GO-pending-live**, résidu unique =
point 3 (comportement de contrepartie), que seul un test live à capital minime résout.

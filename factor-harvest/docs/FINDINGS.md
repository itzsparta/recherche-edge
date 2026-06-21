# FINDINGS — Piste 1 : trend-following cross-asset (ETF)

Verdict rendu le 2026-06-21. Test exécuté contre la spec **pré-enregistrée**
([`SPEC.md`](SPEC.md)) — aucun critère modifié après avoir vu les résultats.

## Verdict

**STANDALONE : KILL** — mais un KILL *catégoriquement différent* des thèses mortes
précédentes. Le premium trend est **réel** ; il est simplement **trop faible** pour
franchir la barre pré-enregistrée sur cet univers, et **inférieur au 60/40 passif**
en standalone.

| | Trend 12m (pré-enreg.) | 60/40 passif |
|---|---|---|
| Sharpe (ann, net) | **+0.42** | +0.93 |
| t-stat | **+1.87** (< 2 → FAIL) | — |
| CAGR net | +2.8 % | — |
| Vol réalisée | 8.4 % | 11.1 % |
| Levier moyen | 0.95x (gross=1) | 1x |

Échantillon : 9 ETF cross-asset, 2006-04 → 2026-06 (~20 ans, GFC + COVID + 2022).

## Pourquoi ce n'est PAS un mirage (≠ orderflow t=−7, meme t=−35)

L'edge **existe**, il survit à tout sauf au seuil de significativité :

- **4/5 régimes positifs** : pré-GFC +8.9 %, GFC 2008 +6.9 %, reprise +21.4 %,
  COVID −0.0 % (seul raté), 2021+ +23.4 %.
- **Tous lookbacks positifs**, gradient lisse : 6m +0.62, 9m +0.47, 12m +0.42,
  15m +0.27. Pas de spike sur une valeur = pas d'artefact.
- **Drop-one robuste** : pire cas (sans SPY) Sharpe reste +0.32.
- **Anti-overfit franchi** : DSR(best=6m, N=4) = **0.988** (> 0.95), même N=20 = 0.962.
  Le meilleur lookback survit à la déflation multi-essais.
- **Crisis-alpha fort** : 2008 **+21.1 %**, 2022 **+6.8 %**, corrélation actions
  **−0.12** — exactement la thèse « le trend paie quand le reste saigne ».

C'est le premium documenté depuis 40 ans (Moskowitz-Ooi-Pedersen ; AQR). Il est là.
Il est juste **mince**.

## Ce qui tue le standalone

1. **t = 1.87 < 2** sur la config pré-enregistrée (12m). Marginal, mais la
   pré-enregistration interdit de switcher sur 6m post-hoc pour sauver le résultat
   (= overfit, la faute que tout ce projet refuse).
2. **Standalone strictement dominé** : Sharpe 0.42 vs 0.93 du 60/40. Un trader qui
   veut *un* edge à trader seul fait mieux en achetant 60/40 et en dormant.

## Diagnostic (hors verdict) — valeur comme SLEEVE

(B)-crisis ayant passé (corr −0.12), question légitime distincte : un sleeve trend
améliore-t-il un cœur passif ? Oui, **modestement** :

| Sleeve trend | Sharpe portefeuille |
|---|---|
| 0 % (60/40 seul) | +0.93 |
| 15 % | +1.00 |
| 25 % | +1.04 |
| 35 % | +1.05 |
| blend optimal (théorique) | +1.05 |

Gain ~**+0.12 Sharpe (+13 %)**. Réel, conforme à la littérature « managed futures =
diversifiant ». Mais ce n'est **pas un edge** : c'est de l'optimisation de
portefeuille qui *suppose* qu'on tourne déjà un cœur passif.

## Limites honnêtes (pourraient relever le verdict — chantier séparé)

- **Univers maigre** : 9 ETF / 5 classes, lourdement corrélés actions. Les vrais CTA
  tournent 50-100+ marchés (sucre, bétail, taux courts, FX croisés…) → diversification
  supérieure → Sharpe publié 0.5-0.8. Mon 0.42 est au bas de la fourchette **en partie**
  à cause de l'univers étroit. **Correction 2026-06-21 : un univers futures riche est
  GRATUIT** — 32 futures continus tous secteurs via yfinance `=F` (~25 ans depuis 2000),
  et le pipeline les gère déjà (swap de liste, pas de build). Le "data payante IBKR"
  était un report erroné de l'orderflow (vrai pour l'**intraday tick/L2**, pas pour le
  **daily** trend). Vrai caveat = **roll-adjustment** : les continus front-month gratuits
  ont des gaps de roll (contango/backwardation) qui ajoutent du **bruit** (Norgate/CSI
  back-adjustés = payant). Le bruit de roll *baisse* le Sharpe → un PASS sur data
  gratuite serait conservateur/crédible. Test = **décision pré-enregistrée séparée**.
- **Pas de short réel modélisé** : les ETF se shortent imparfaitement ; le test est
  un proxy futures. Marginal pour le signe du momentum, réel pour l'exécution.
- **Dividendes** : réglé (yfinance `auto_adjust` = rendement total).

## Décision

- Pour l'objectif « trouver un **edge** à trader » → **KILL**. Trend standalone sur
  ETF liquides est réel mais sub-seuil et dominé par le passif. Un diversifiant
  +0.12 Sharpe sur un cœur passif n'est pas l'edge cherché.
- **Capital conservé** : pipeline factor (data yfinance + moteur vol-targeté +
  audit DSR porté) réutilisable tel quel pour pistes 2/3 et pour un éventuel rerun
  univers-futures.
- **Thread futures TESTÉ (2026-06-21) → ne sauve pas** (cf. section dédiée). La largeur
  gratuite est plombée par le bruit de roll ; settle propre = data payante (Norgate), mais
  même un succès = sleeve, pas un edge standalone. Branche refermée pour l'objectif edge.

## Re-run univers FUTURES riche (2026-06-21) — la largeur ne sauve pas

Hypothèse testée (pré-enreg. [`SPEC-futures.md`](SPEC-futures.md)) : un univers de **32
futures continus / 8 secteurs** (~2003-2026, gratuit yfinance `=F`) franchirait t>2 là
où l'ETF maigre ratait. **Résultat : plus FAIBLE, pas plus fort.**

| | Trend 12m FUTURES | Trend 12m ETF | 60/40 |
|---|---|---|---|
| Sharpe | **+0.25** | +0.42 | +1.01 |
| t-stat | **+1.22** | +1.87 | — |
| DSR(best, N=4) | **0.62 (FAIL)** | 0.99 | — |
| Lookbacks 6/9/12/15m | **−0.07 / −0.21 / +0.25 / +0.14** | tous + | — |

Régimes 5/5 positifs, drop-one OK (pire sans Copper +0.14), crisis-alpha OK (2008
+12.2 %, 2022 +4.1 %, corr −0.04). Mais **(A) FAIL** : t<2, DSR<0.95, lookbacks courts
**négatifs**.

**Pourquoi plus faible alors que plus large** (2 causes, la 1re pré-enregistrée) :
1. **Bruit de roll** : les continus front-month gratuits ne sont pas back-adjustés →
   gaps de roll = bruit. Signature : les momentum **courts** (6/9m) captent le bruit →
   négatifs ; seuls les longs survivent. La data ETF était propre (total-return), la
   futures sale. Le caveat SPEC disait : *FAIL sur data sale ≠ trend mort.*
2. **Faiblesse réelle post-2009** : reprise 2010s **+0.4 % sur une décennie** = le
   « managed futures winter » documenté. Pas que du bruit.

**Trouvaille solide (robuste sur les DEUX univers)** : comme **sleeve** sur 60/40, le
trend ajoute **~+0.12 Sharpe** (ETF 0.93→1.05 ; futures 1.01→1.05). *Identique.* C'est le
seul deliverable réel : un diversifiant modeste, pas un edge.

**Conclusion piste 1** : trend standalone = KILL, robuste sur clean-thin ET dirty-rich.
Settle propre de la largeur = data back-adjustée payante (Norgate ~$), mais même un
succès plafonnerait ~0.5-0.6 (Sharpe CTA publié) = **toujours un sleeve, jamais un edge**
qui bat le 60/40. Non worth pour l'objectif edge. Cross-check gratuit possible (facteur
TSMOM publié AQR) si besoin de clôture académique — sinon piste 1 close.

## Méthode validée au passage

Le **sizing honnête a renversé le verdict** : en per-leg vol-target naïf, levier
empilé 6.31x → vol 47.5 %, Sharpe 0.46, t=2.05 → faux GO. La normalisation gross=1x
(risk-parity, finance ≈ 0) a ramené à la réalité : t=1.87 → KILL. Leçon : **un
backtest non-levé ment ; toujours ramener au levier réellement tenable + coût de
financement avant de lire le Sharpe.** (Analogue du mur d'exécution orderflow, côté
financement.)

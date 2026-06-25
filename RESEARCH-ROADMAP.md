# Research roadmap — chasse à l'edge (post-mortem orderflow / meme / rebate)

## Objectif opérant (révisé 2026-06-25) — valider un compte prop firm

**Nouveau but des bots : passer une évaluation de prop firm (FTMO / Topstep / Apex / …)
et obtenir un compte financé.** Cet objectif **remplace la « chasse à l'edge déployable »**
comme cible opérante. Les 23 études ci-dessous restent la base de connaissance, désormais
relue à travers cette grille.

**Pourquoi c'est un jeu différent — et pourquoi l'écart initial (cf. Diagnostic) ne le ferme
pas.** Le prop firm avait été écarté tôt (« profil rendement ⊥ challenge ») mais l'écart était
*asserté*, jamais chiffré, et confondait deux choses : (1) le carry delta-neutre est bien
impossible sur un compte CFD unique — vrai et définitif ; (2) le *profil* de nos signaux ne
collerait pas — jamais calculé. Le challenge n'est **pas** un problème de récolte d'edge : c'est
un problème de **franchissement de barrière** (atteindre +cible avant −maxDD sur une fenêtre
courte) **avec convexité** (frais souvent remboursés au 1ᵉʳ payout, scaling plan, split 80-90 %).
La bonne analyse est un **ledger d'EV** (méthodo airdrop #14), **pas** un Sharpe.

**Gate pré-enregistré.** `EV(challenge) = P(pass)·E[extraction | financé] − frais·(1 − remb·P(pass))`
doit être **> 0** net de frais, spread/commission, et **fuite daily-DD**. Kill : si, sous l'a
priori **no-edge** du programme (P(directionnel) ≈ 0.5/phase), l'EV reste ≤ 0 → le challenge est
un produit à marge maison comme un autre (cf. books sportifs #16, *« ce qui te laisse entrer tue
l'edge »*). Variable décisive = **règles de la firme** : maxDD **statique** (barrières ≈ symétriques,
P(pass/phase) ≈ 0.5 hors coûts) vs **trailing** (la barrière basse monte avec le pic → P(pass) < 0.5
*avant* coûts) ; **limite de temps** (tue le trend lent) ; **règle de consistance** (tue le
variance-farming).

**Ce qui survit de la base, relu prop :**
- **GEX dealer-gamma (#18)** — seul prédicteur **robuste de variance** (corr −0.262, t≈−16). Nul en
  alpha de rendement, mais **la variance EST la contrainte qui tue les challenges** (breach
  daily/maxDD) → candidat **overlay de survie**, pas d'alpha.
- **Trend / TS-momentum (#1)** — seul signal **directionnel réel** (DSR 0.988), tradable sur
  instruments prop (futures/FX). Lent → exige firme **maxDD statique + sans limite de temps**.
- Carry (#6), LP V3 (#15), CEF (#8), funding-XS (#11) : **hors-jeu** (multi-venue, on-chain, ou
  non-directionnel — incompatibles compte unique directionnel).

**Piste A — méta-gate prop (#24) = KILL (2026-06-25).** Simulation Monte Carlo (pur-sim,
parallélisée) du pipeline complet par trader (phase 1 → phase 2 → compte financé) sous barrières
réelles (max DD statique/trailing, daily DD, consistance) et coûts réalistes ; sortie = la
**distribution** du net $ par achat. **Sans edge = loterie** : médiane = −fee (on perd tout le fee
~90 % du temps), la moyenne (FTMO +$416) est portée par une **queue chanceuse de 10 %** = motif
airdrop #14. **Même avec le seul edge réel (sleeve trend 0.42)** la moyenne FTMO monte à +$3 000
mais la **médiane reste −$540** (P(net>0) 23 % < 50 %) → pas déployable en solo one-shot. Topstep
(trailing + consistance) écrasé à ≈ $0. **Verdict robuste au coût** (médiane = −fee à tous les
coûts). Gradient #16 chiffré : la convexité exploitable vit dans les règles que les firmes
retirent (trailing/consistance). Le 0.42 injecté est le Sharpe **diversifié** → mono-compte réel
< 0.42 → KILL conservateur. Pistes B (overlay GEX-survie) et C (trend) tombent aussi : flipper la
médiane exigerait P(net>0) > 50 %, hors de portée. [`prop-firm-gate/docs/FINDINGS.md`](prop-firm-gate/docs/FINDINGS.md).

---

## Diagnostic : l'étang, pas la canne

Trois thèses tuées proprement — **orderflow** (level-edge fade+continuation mort,
DSR(N=50)=0.008), **meme-coin** (no-edge Dune réelle, t=−35, −28 %/trade),
**rebate-crypto** (mort) — plus **delta-neutral / prop firm** écarté (mismatch
structurel : carry impossible sur un compte CFD unique, profil rendement ⊥ profil
challenge). Voir les `FINDINGS.md` respectifs.

Point commun de **tous** ces échecs : ils chassaient un **edge prédictif** (deviner
le prix mieux que le marché) dans les **étangs les plus efficients et crowdés** qui
existent — intraday majors, meme pump.fun, funding arb. C'est là que se battent
chaque fonds quant, bot HFT, desk prop. Un solo sans edge latence / infra / data /
capital y perd **par construction**. La méthode était honnête ; le terrain de chasse
était condamné d'avance.

**La méthodologie n'est pas en cause** (DSR, López de Prado, multi-régime, miroir,
pré-enregistrement). Elle a fait son travail : elle a tué des mirages que la plupart
des retail auraient tradés. Le capital conservé = **l'infra + la méthode**, pas les
signaux.

## Le reframe : edge STRUCTUREL ≠ edge PRÉDICTIF

On arrête de chercher à être plus malin que le marché. On cherche où la **structure**
d'un petit acteur solo gagne — ce que les fonds **ne peuvent pas** répliquer :

- **Capacité** — déployer $5k là où un fonds *doit* placer des millions. Marchés
  illiquides = le seul monopole d'un solo.
- **Patience** — pas de LP, pas de benchmark, pas de redemption. Porter un drawdown
  qu'un fonds ne peut pas se permettre.
- **Pivot** — pas de comité, pas de mandat.

Les pistes ci-dessous sont classées par espérance **pour ce profil précis** (solo,
capital modeste, fort en build/data/méthode, zéro edge latence).

---

## Piste 1 — Primes de risque documentées, basse fréquence ★ top EV

**Thèse.** Récolter les premia *compensés* (pas de l'alpha) : trend-following
(time-series momentum), carry, momentum cross-sectionnel, sur un panier **cross-asset
diversifié**. Long/short selon le signe du momentum, vol-targeting, rééquilibrage
mensuel.

**Pourquoi ça persiste.** Ce sont des **risques rémunérés**, pas une inefficience à
arbitrer. Trend-following, carry et momentum sont documentés et robustes OOS depuis
40 ans (Moskowitz-Ooi-Pedersen 2012 ; AQR « A Century of Evidence »). Ils ne
disparaissent pas quand on les publie parce qu'ils paient pour porter un risque que
d'autres veulent fuir (le trend = « crisis alpha », positif en 2008 et 2022).

**Pourquoi toi.** Zéro besoin de latence / infra / capital. Scalable à n'importe
quelle taille. Et surtout : la **leçon étage-1** (*un smoke mono-régime / mono-marché
ne sépare pas l'edge du drift*) s'applique pile — un test trend honnête **exige** le
multi-marché multi-régime, exactement le harness anti-overfit déjà construit. Les
kills passés ont bâti le muscle requis.

**Tueur probable.** Pas « no-edge ever » (le premium est réel) — mais **« edge réel
mais pas worth it »** : trend a connu un hiver post-2009 (une décennie sous le
buy-and-hold). Le vrai risque = trop mince / lent / régime-dépendant pour battre un
simple 60/40 passif après coûts. → Le critère de kill doit être *bat le passif en
risk-adjusted*, pas juste *Sharpe > 0*.

**Pré-test cheap.** Panier ETF cross-asset (free data), TS momentum 12-1 pré-spécifié,
vol-targeting, ~2006-2024 (couvre GFC / COVID / 2022). Réutilise `deflated_sharpe`
+ `pbo_cscv` de l'orderflow tel quel. Spec pré-enregistrée → `factor-harvest/docs/SPEC.md`.

**Statut : KILL standalone (2026-06-21)** — premium **réel** mais **trop faible** sur
univers ETF : Sharpe 0.42, **t=1.87 < 2** (config pré-enreg. 12m), dominé par le 60/40
(0.93). ≠ mirage : 4/5 régimes positifs, drop-one robuste, **DSR(best,N=4)=0.988**,
crisis-alpha fort (2008 +21 %, 2022 +7 %, corr −0.12). Comme **sleeve** sur cœur passif
→ Sharpe 0.93→1.05 (+0.12, modeste, pas un edge). Leçon clé : le **sizing honnête
(gross=1x vs levier empilé 6.3x) a renversé un faux GO** (t=2.05→1.87). **Re-run univers
futures riche (32 marchés, 2026-06-21) = ne sauve PAS** : plus faible (Sharpe 0.25, t=1.22,
DSR 0.62 FAIL, lookbacks courts négatifs) — plombé par le **bruit de roll** (continus
gratuits non back-adjustés, caveat pré-enregistré) + faiblesse réelle post-2009 (reprise
+0.4 %/décennie). Sleeve **+0.12 Sharpe robuste sur les DEUX univers** = seul deliverable.
Settle propre = data payante Norgate, mais même un succès = sleeve, pas un edge → **piste 1
close pour l'objectif edge**. Détail : [`factor-harvest/docs/FINDINGS.md`](factor-harvest/docs/FINDINGS.md).

---

## Piste 2 — Flux forcés mécaniques ★ bon EV

**Thèse.** Se mettre du côté **non-contraint** d'un participant *forcé* : token
unlocks (vesting qui doit vendre), roll de futures, rebalancement d'indices (le fonds
indiciel *doit* acheter au close de reconstitution), pinning à l'expiration d'options.

**Pourquoi ça persiste.** L'edge n'est pas prédictif — c'est une **contrainte
structurelle** d'un autre acteur. Un unlock *doit* libérer de l'offre à date connue ;
un tracker *doit* répliquer l'indice. Tu fournis la liquidité qu'ils paient cher.

**Pourquoi toi.** Méthodo event-study = déjà maîtrisée. Pré-test très cheap
(rendement fenêtré [-Nj, +Nj] autour de l'événement, net de frais).

**Tueur probable.** Crowdé (tout le monde voit le calendrier d'unlock / la date de
rebal). Le edge peut être déjà arbitré dans le prix avant l'événement. Timing +
slippage. → Tester si un résidu net survit *après* le front-running connu.

**Pré-test cheap.** Event-study sur N unlocks / rebals historiques. Données :
unlocks via Dune/token vesting trackers ; rebals indices via dates publiques.

**Statut : KILL unlocks (2026-06-21)** — sous-piste **token unlocks** attaquée
(`forced-flows/`, 24 804 cliff events DefiLlama, 10 642 exploitables / 78 tokens, prix
Binance, tout gratuit). Shorter l'unlock = **≈ zéro** market-adjusted (post +1,+10 :
−0.22 %/token, t=−0.16). **Priced-in net** : toute la dérive est AVANT la date (pré
[−10,−1] +1.28 %), rien après — dates publiques anticipées. Dose-réponse non-monotone,
drop-top-5 t=−1.21, DSR 0.53 : (A) et (B) FAIL. Caveat pré-enregistré : univers
Binance-listed = large caps arbitrés ; small-caps (capacité) non testés faute de prix
gratuit, **mais** non-shortables de toute façon → thèse faible aux deux bouts. **Le risque
priced-in frappe aussi rebal/roll** (dates connues) → pondérer avant d'attaquer ces
sous-pistes. Détail : [`forced-flows/docs/FINDINGS-unlocks.md`](forced-flows/docs/FINDINGS-unlocks.md).

---

## Piste 3 — Niche capacity-constrained — EV moyen

**Thèse.** Marchés trop petits pour les fonds : petites paires cross-exchange,
inefficiences de chaînes récentes, spreads sur actifs sub-$1M ADV.

**Pourquoi ça persiste.** Les fonds **ne peuvent pas entrer** (leur taille bouge le
marché). Monopole pur du petit acteur.

**Pourquoi toi.** C'est littéralement la définition de l'avantage solo (capacité).

**Tueur probable.** Complexité opérationnelle (multi-exchange, custody), risque
exchange (le vrai tueur, cf. FTX), et surtout **capital petit ⇒ $ minuscules même si
% bon** : 30 % APR sur $5k = $1 500/an. Le ratio temps/EV peut ne pas valoir le coup.

**Pré-test cheap.** Mesurer les spreads cross-exchange réels nets de frais/retrait sur
un échantillon de petites paires ; estimer la capacité $ avant d'écrire une ligne.

**Statut : KILL — spread fantôme (2026-06-22)** — scan cross-exchange 3 venues gratuites
(Binance/MEXC/Gate, `capacity-niche/`, 25 snapshots × 60 s, régime minutes solo-capturable,
modèle inventaire pré-positionné = meilleur cas). Le spread **existe et persiste** (79 paires
net>0 sur ≥60 % des snaps, t cross-paires=+7.07 → **pas du flicker**, tueur « quote périmée »
réfuté) **mais** : (A) **dose-réponse plate/inversée** (basse-liq +0.30 % vs haute-liq +0.41 %)
→ **pas** de signature structurelle « trop petit pour un fonds » ; (B) **capacité fantôme** —
profondeur réelle marchée (`/depth`) = **1 253 $ agrégés** (borne haute), 5 paires seulement, et
les gros spreads (MEMEFI +2.52 %, EDGEN +2.30 %) ont **0-1 $** derrière le top-of-book. Le spread
vit au sommet d'un carnet vide. Sanity mega-caps (BTC −0.19 %) valide le pipe. Aller plus obscur =
même ~1 k$ payé en risque opérationnel (retraits haltés, exit-scams). La **capacité — dernière
arme structurelle d'un solo — est ici un mirage**. Détail :
[`capacity-niche/docs/FINDINGS-niche.md`](capacity-niche/docs/FINDINGS-niche.md).

---

## Protocole partagé (tout pré-test doit le franchir)

Repris de `orderflow-bot/docs/ROADMAP.md` — la partie réutilisable telle quelle :

1. **Pré-enregistrement.** Écrire l'hypothèse, la règle, le critère de **succès** ET
   de **kill** *avant* de voir le moindre résultat, à bornes spécifiques à la piste.
   (Leçon FINDINGS : les métriques brutes mentent ; DSR(N=50)=0.008 a tranché.)
2. **Multi-régime obligatoire.** Le test doit séparer l'edge du drift — jamais un
   total flatteur tiré par un seul sous-échantillon / marché. (Leçon étage-1.)
3. **Net de frais + slippage d'office.** Jamais de brut en input de décision.
4. **Audit anti-overfit dès le jour 1.** `deflated_sharpe` (déflate par le nombre
   d'essais) + `pbo_cscv`. Le meilleur Sharpe après k variantes doit battre le seuil
   de bruit SR0.
5. **Miroir / drop-one.** Le résultat survit-il en inversant le signe / en retirant
   le marché qui porte tout le P&L ?
6. **Kill franc.** Une espérance ≤ 0 ne se sauve par aucun sizing (Kelly d'un edge
   négatif = 0). On gèle et on documente, on ne version-hop pas sur un espoir.

## Bilan (2026-06-22) — 3/3 pistes structurelles traitées

Le reframe edge-structurel ≠ prédictif a produit **3 verdicts propres, 3 raisons différentes** :

| Piste | Arme structurelle | Verdict | Raison |
|---|---|---|---|
| 1 — primes de risque | aucune (premium réel) | KILL standalone | réel mais trop faible (t=1.87) ; sleeve +0.12 seulement |
| 2 — flux forcés | non-contraint vs forcé | KILL | **priced-in** : dérive avant la date publique, ≈0 après |
| 3 — niche capacité | capacité (taille fonds) | KILL | spread **fantôme** : persistant mais ~1 $ de profondeur |

**Le motif unifié.** Tout edge à **déclencheur ou prix public** est mangé : signal trend
(piste 1, premium compressé), date d'unlock (piste 2, priced-in), quote cross-venue (piste 3,
arbitrée jusqu'au top-of-book vide). Les 3 confirment la même loi : **là où l'info/le prix est
public, un solo sans latence/infra n'a pas d'edge récoltable** — y compris quand l'avantage
théorique est la capacité (le spread existe, mais il n'y a rien derrière à prendre).

**Ce qui reste vivant** : un seul deliverable trading = le **sleeve trend +0.12 Sharpe** (piste 1,
robuste 2 univers) — modeste, pas un edge. Le vrai capital conservé = **le pipeline lui-même**
(pré-enregistrement, DSR/PBO, multi-régime, event-study, scan cross-exchange) : 5+ études de kill
honnêtes et reproductibles.

**Pistes non-explorées** (même risque que les mortes, EV faible *a priori*) : sous-mécanismes
piste 2 (rebal/roll = dates publiques = priced-in), venues plus obscures piste 3 (= risque
opérationnel pour le même ~1 k$). Aucune ne change la conclusion sans nouvelle arme structurelle.

## Note méta — quel est le but ? (devenue la décision opérante)

Les 3 pistes mortes **répondent empiriquement** à « un solo retail peut-il récolter un edge ? » :
pas sur les terrains accessibles, pas avec une info publique. La reco dépend maintenant de
l'objectif réel :

- **Cash maintenant** → il n'y en a pas ici. Le moins mauvais = sleeve trend (+0.12, lent, borné),
  pas un edge autonome.
- **Apprendre / portfolio alternance** → le *pipeline de recherche EST le produit*, et il est
  **fini et solide**. La méthodo anti-overfit (5 kills pré-enregistrés, data engineering propre)
  vaut plus sur un CV ingénieur que n'importe quel P&L. **C'est le deliverable à packager.**
- **Battre le marché pour le frisson** → réfuté par 5 kills. Mauvais ratio temps/EV pour un solo.

## Suite — V2 (2026-06-22) : l'axe non-testé

Les 3 pistes V1 cherchaient toutes le **même type d'edge** (deviner une direction). Une
catégorie est restée non testée : l'edge **non-prédictif et non-arbitrage** = la **prime
d'assurance**. Ouvert dans [`EDGE-PISTES-V2.md`](EDGE-PISTES-V2.md) (pistes 4 VRP, 5 calendrier
FOMC/overnight, 6 carry, 7 relative-value transverse).

**Piste 4 — VRP : DOWNGRADE.** Premium réel (t=4.03, DSR 0.977) mais = compensation d'un tail
catastrophique (SVXY −95 % de drawdown, −83 % en un jour). Le pipeline a attrapé son propre **faux
GO** (Sharpe 1.86 = mirage aveugle au skew). [`vol-risk-premium/docs/FINDINGS.md`](vol-risk-premium/docs/FINDINGS.md).

**Piste 5 — calendrier : DOWNGRADE + KILL.** 5a overnight = prime réelle (+10-14 %/an) mangée par
le turnover quotidien (DOWNGRADE). 5b pré-FOMC = drift réel 1994-2014 mais **priced-in** post-2015
(+2.3 bps, t=0.20, −93 %). [`calendar-premium/docs/`](calendar-premium/docs/).

**Piste 6 — carry crypto-funding : GO Phase-1 → KILL-FORWARD Phase-2.** Phase-1 = net +10.5 %/an,
**market-neutral** (corr +0.09), positif chaque régime dont le bear 2022 → seul non-kill du
screening. **Phase-2 (exécution réelle + tail)** = le carry est **réel** (P&L delta-neutre vrai
reproduit avec legs spot/perp séparés, basis ≈ 0, frais réels 1.14 %) **mais pas déployable** : le
forward (OOS 24 mois) tombe à **+3.8 %** < hurdle 8 %, et le **break-even faillite exchange 3.6 %/an
< gate 5 %** (post-FTX → le tail mange l'EV). Liquidation **pas** le tueur (cross-margin offsete). Le
+10.5 % = chance de régime 2020-21. **(C) FAIL, (D) FAIL.** [`carry/docs/FINDINGS-phase2.md`](carry/docs/FINDINGS-phase2.md).

**Piste 7 — RV BTC/ETH cointegration daily : KILL Phase-1 (2026-06-23).** Spread `log(BTC/ETH)`
non-stationnaire IS (ADF p=0.38) **et** OOS (p=0.77) → marche aléatoire, pas de niveau d'équilibre.
Pas un artefact du ratio 1:1 : Engle-Granger à hedge ratio libre non-cointégré partout, ratio
instable 0.70→1.36 IS→OOS (rupture post-Merge). Half-life 305-572 j = intradable même dans le doute.
Tué à la **stationnarité en ~30 min**, sans backtest — le gate falsifiable cheap a fait son travail.
[`relative-value/docs/FINDINGS-rv.md`](relative-value/docs/FINDINGS-rv.md).

**Piste 8 — CEF discount mean-reversion : KILL faux GO microstructure (2026-06-23).** Premier étang
*structurellement différent* attaqué (contrepartie retail, discount inarbitrable car pas d'AP — l'inverse
de la piste B ETF). Gate A stationnarité PASS net (62 % fonds, pooled ADF p≈0) et Phase-2 brut **tout-vert
= premier GO provisoire du programme** (net +8.41 %/an, t=7.13, DSR 1.000). **Tué en robustesse** : lag
d'entrée +1 mois → alpha **s'inverse** (survie −48 %) = la « convergence » était du **bid-ask bounce**
non-capturable (CEF illiquides : on achète le print au bid, rebond au mid). Forme déployable (intra-cat +
lag + long-only, borrow réaliste) = **zéro** (−0.64 %, t=−0.64). Survivorship non corrigé (univers = fonds
vivants) = pire encore. Même structure que le faux GO VRP (Sharpe aveugle au tail) : ici t=7.13 aveugle au
bounce. [`cef-discount/docs/FINDINGS-cef.md`](cef-discount/docs/FINDINGS-cef.md).

**Le bilan, V1+V2 (9 pistes, 0 edge déployable).** Tout edge à **information/prix public** est mort
(trend, unlocks, niche, VRP, overnight, pré-FOMC). Le carry **structurel market-neutral** a survécu
le screening (réel) mais **échoué le déploiement** : la prime est **arbitrée jusqu'au coût** (tail
exchange). La RV BTC/ETH (piste 7) ajoute un kill d'un autre type : **pas même de relation
stationnaire** à exploiter (le ratio des deux actifs est lui-même une marche aléatoire). La piste 8
(CEF) ajoute un troisième type de mort : prime structurelle **réelle** mais récolte mangée par la
**friction de microstructure** (bid-ask bounce) — cousine du tail qui a mangé le carry. Conclusion en
deux temps : *edge structurel ≠ prédictif* **tient** (le carry est réel là où tout le reste est mort)
**mais structurel ≠ gratuit** (compressé sous le seuil où il paie son risque : tail, friction, ou
bounce). Le vrai capital du programme = le **pipeline de 10 verdicts pré-enregistrés** — dont un faux
GO (t=7.13) démasqué avant déploiement — pas un P&L.

**Piste 10 — favorite-longshot bias (Polymarket) : KILL Gate A, hypothèse INVERSÉE (2026-06-23).**
Deuxième et dernier étang « structurellement différent » du reframe (contrepartie récréative, CLOB sans
vig). 3082 marchés binaires résolus, prix ex-ante au midpoint temporel, 5586 legs. Résultat : **pas de
biais favorite-longshot, mais le pattern INVERSE** — longshots (<0.10) **sous-cotés** (gap réalisé−
implicite +0.011, t=+2.26), favoris **surcotés** (gap −0.08). Fader les longshots (l'hypothèse) aurait
**perdu**. Aucune catégorie ne sauve (Gate E). Polymarket = foule crypto-native + arbitragistes, pas
parieurs récréatifs naïfs → efficient. Le pattern inverse n'est PAS exploité : post-hoc + même tueur de
friction que le bounce CEF (gap 5-8 % mangé par le spread du côté cheap). [`prediction-markets/docs/FINDINGS-pm.md`](prediction-markets/docs/FINDINGS-pm.md).

**Bilan du reframe « changer l'étang » : 0/2.** Les deux étangs à contrepartie non-optimisatrice sont
morts — CEF (inarbitrable par structure, mais récolte mangée par la microstructure) et Polymarket
(supposé récréatif, en fait arbitré/efficient). **Changer l'étang n'a pas plus produit d'edge que
changer la canne.** Le motif unifié se renforce : *là où le prix est public, un solo n'a pas d'edge
récoltable* — que la contrepartie soit un fonds (étangs V1/V2) OU supposément naïve (CEF/Polymarket).

**Piste 11 — funding cross-sectionnel : KILL (brut réel, mangé par le turnover 8h).** Bolt-on direct du
carry (piste 6). Gate A **PASS** : la dispersion de funding paie *brut* (+51.9 %/an, t=3.43, sharpe
1.35) — décomposé en +3.45 % spread de funding (mécanique) + 7.19 % spread de prix (cross-sectionnel
réel). Mais B/C/D/E tous **KILL** : le turnover 8h (1.32 du book/période, ≈72 %/an de frais) transforme
+52 % brut en **−20.6 % net** ; 51 % du P&L sur 2 alts (ETC, BNB) ; jambe short −4.4 % en standalone ;
seul le bull 2020-21 ≥0 (t=0.15 ns). Forme la plus nette du motif unifié : *un brut réel et significatif,
exactement neutralisé par la friction structurelle requise pour le capter*. [`funding-xs/docs/FINDINGS-xs.md`](funding-xs/docs/FINDINGS-xs.md).

**Piste 9 — LST convergence (stETH/ETH) : KILL (edge one-off pré-redemption, n=1 régime).** Étang ≠ :
convergence *garantie protocolairement* (redemption 1:1). Gates B/C **PASS en apparence** (brut +82 %,
net +76.8 %, t=3.14) — mais c'est un **artefact in-sample** : les 26 épisodes de stress sont **tous
pré-Shapella** (2021-2022, LST jeune sans marché de retrait). Post-Shapella (169 j présents) le discount
est **pinné** (min −0.40 %, jamais < seuil −1.5 %) → l'arbitrage de redemption a écrasé l'edge → KILL
Gate E. Plus : ADF p=0.058 (pas de niveau stable hors stress, KILL A) et breakeven au creux −7.5 %
n'exige que P(perte 50 %)=13 % (prime ≈ risque de queue réel, priced-in plausible, KILL D). **La piste a
prédit sa propre obsolescence** : le mécanisme qui garantit la convergence la détruit en s'activant.
Piège pédagogique : t=3.14 sur un **régime unique non-reproductible** ≠ edge — même leçon que les faux GO
VRP/CEF (t aveugle au tail/bounce). [`lst-convergence/docs/FINDINGS-lst.md`](lst-convergence/docs/FINDINGS-lst.md).

**BILAN FINAL — programme edge V1+V2 clos : 12 pistes, 0 edge déployable.** Toutes les pistes
opportunistes restantes sont tombées. Le motif unifié tient sans exception : *à information/prix public,
un solo n'a pas d'edge récoltable*. Trois sous-types de mort, tous convergents : **(1) no-edge brut**
(orderflow, meme-coin, RV BTC/ETH — pas même de signal) ; **(2) brut réel mangé par la friction**
(funding XS turnover 8h, niche capacity, CEF bounce — l'edge ≈ son coût d'extraction) ; **(3) brut réel
mangé par le tail/non-répétabilité** (carry exchange-default, LST pré-redemption, VRP — la prime ≈ le
risque, ou n=1 régime). Les deux étangs « structurellement différents » (CEF, Polymarket) sont morts =
*changer l'étang ≠ produit pas d'edge*. **Le seul deliverable trading = le sleeve trend +0.12 Sharpe.**
Le vrai capital = **le pipeline de 12 verdicts pré-enregistrés**, dont deux faux GO (VRP, CEF t=7.13) et
un troisième mirage in-sample (LST t=3.14) démasqués *avant* déploiement. La rigueur du kill ≫ le P&L.

## Réouverture ponctuelle — Piste 12 (2026-06-23) : VRP crypto defined-risk = KILL

Le programme « clos » a été rouvert une fois pour tester la **seule porte que la Piste 4 (VRP actions)
avait laissée ouverte** : un short-vol à **risque défini** est-il viable là où le premium est le plus
gros, la **crypto** ? Hypothèse : gap DVOL−réalisée 3-5× l'actions → assez pour payer l'aile et garder
une EV nette. Pré-enregistré dans [`vol-risk-premium/docs/SPEC-crypto.md`](vol-risk-premium/docs/SPEC-crypto.md),
barre de magnitude `mean(VRP_vol) > 8 pts` fixée avant les données.

**KILL.** Le premium **existe** (DSR BTC 0.998) mais full-sample BTC = +7.88 pts (**sous la barre**), et
surtout c'est un **artefact d'immaturité** : décroissance monotone 2021-crash +25 → 2024+ +4.5 pts. En
marché **mûr (2023+)** la prime est compressée à **+5.23 pts BTC (t=1.88 ns)** / +1.35 ETH (t=−0.29) =
niveau actions, non-significative. Le pré-B Phase-1 PASS de BTC (Sharpe 1.08, t=2.45) était **100 %
porté par l'early-market** (net mûr +2.23 pts, t=1.07 ns ; ETH négatif) — même piège que LST. La porte
defined-risk ne s'ouvre jamais : le premium censé payer l'aile est **déjà revenu au niveau actions**
avant qu'on mesure la moindre aile → DOWNGRADE actions, un cran plus sec. Tué en **un run free-data**
(DVOL Deribit), zéro Phase 2. La densification du marché d'options crypto **EST** l'arbitrage, observé
en temps réel. [`vol-risk-premium/docs/FINDINGS-crypto.md`](vol-risk-premium/docs/FINDINGS-crypto.md).

**Bilan inchangé : 13 pistes, 0 edge déployable.** Le motif tient — un edge structurel (la prime de vol)
arbitré jusqu'au niveau actions à mesure que le marché mûrit.

## Piste 13 (2026-06-23) : momentum cross-sectionnel crypto = KILL

Seul des deux candidats proposés en fin de programme qui rentre dans la machine gate-kill (l'autre,
alpha opérationnel/airdrop, est un AUTRE jeu = ledger EV, pas un backtest falsifiable). L/S transversal
**market-neutral** (long tercile fort / short tercile faible, rebal hebdo) sur univers fixe de 75 perps
Binance. Distinct des morts : ≠ trend TS (p1), ≠ funding-XS (p11), ≠ RV paire (p7) ; la market-neutralité
**annule le drift** qui avait contaminé les pistes directionnelles. Pré-enregistré dans
[`xs-momentum/docs/SPEC.md`](xs-momentum/docs/SPEC.md), gap 1 j anti-bounce (leçon CEF), Gate G mûr (leçon p12).

**KILL — type le plus sec : pas même de brut.** Gross hebdo +14 %/an mais **t=0.84 (ns)** ; net t=0.24 ;
DSR(L∈{1,2,4,8 sem}) **0.660**. Et **même motif que la Piste 12 dos à dos** : tout le P&L vit en **2021**
(marché immature : +2.25 %/sem bull-H1, +1.88 % H2) puis **négatif/nul dès 2022** ; en marché **mûr 2023+
le net est −19.4 %/an** (Gate G FAIL). La construction est saine (corr BTC −0.01, deux jambes même signe,
drop-top-3 préserve) → vraie absence d'edge, pas un bug. Survivorship pré-enregistré = univers optimiste
→ KILL conservateur. [`xs-momentum/docs/FINDINGS.md`](xs-momentum/docs/FINDINGS.md).

**Leçon transverse p12+p13 (même jour).** Le **test du sous-échantillon mûr (2023+) est désormais
obligatoire** sur tout signal crypto : les edges documentés sur 2017-2021 peuvent être de purs artefacts
d'immaturité. La densification du marché EST l'arbitrage. **Bilan : 14 pistes, 0 edge déployable.**

## Piste 14 (2026-06-23) : airdrop farming (EV-ledger opérationnel) = KILL

Le **second** candidat de fin de programme, attaqué comme l'AUTRE jeu qu'il est : pas un backtest de
prix mais un **ledger d'EV opérationnel** (le $ net par **heure** bat-il un seuil de labeur ?). Seule
arme structurelle inédite = subvention d'acquisition, **institutions absentes par structure** (sybil =
moat). Pré-enregistré dans [`airdrop-ev/docs/SPEC.md`](airdrop-ev/docs/SPEC.md), seuil 15 €/h.

**KILL.** Même en garantissant la qualif au basket entier (15 majors 2020-2025, jackpots inclus, alloc
valorisée au TGE = best-case généreux), net **8.4 €/h** < plancher (Gate A FAIL). **53 % du $ vient de 2
jackpots non-répétables** (dYdX, Hyperliquid) = MIRAGE survivorship (leçon meme-coin). Base-case honnête
(sans jackpots, qualif 50 %, gas payé sur 40 farms dont les zéros) = **EV négative −1 050 $** (Gate B
FAIL). Décroissance réelle (CoinGecko) médiane **−93 %** hold-to-now — la valo TGE était déjà le
best-case. **Le moat coupe dans les deux sens** (null central confirmé) : l'absence de l'institution est
compensée par la défense anti-sybil du protocole → le solo hérite d'un **plafond**, pas d'un edge ;
l'upside matériel est une **loterie** (HYPE +1689 %, le seul non-dumpé). [`airdrop-ev/docs/FINDINGS.md`](airdrop-ev/docs/FINDINGS.md).

**Leçon.** Même l'étang où le gros acteur est **structurellement absent** ne produit pas d'edge solo
matériel — l'absence est neutralisée par le clawback sybil, et l'upside est un survivorship de jackpots.
*Changer l'étang* reste **0/N**. **Bilan final : 15 pistes, 0 edge déployable.** Les deux candidats
proposés en clôture (XS-momentum, airdrop) sont tombés — l'un en backtest (no-edge brut), l'autre en
ledger (seuil labeur + mirage). Le vrai capital reste **le pipeline de 17 verdicts pré-enregistrés**.

---

## Suite — V3 (2026-06-23) : La "Prime de Saleté" (Messiness Premium)

Le constat post-Piste 15 est sans appel : **là où l'information ou le prix est public et normalisé, un solo sans latence n'a pas d'edge récoltable.** Changer d'étang vers des contreparties moins sophistiquées (CEF, Polymarket) n'a pas suffi (l'efficience cachée ou la friction a tout mangé).

Le seul monopole restant pour un solo ($ modeste, fort en code/data, zéro infra HFT) réside dans ce que les institutions **ne peuvent pas** ou **ne veulent pas** faire à cause de contraintes de compliance, de mandat, ou de coût de nettoyage des données. C'est l'étang de la saleté et de l'asynchronisme.

Voici les 4 pistes de la V3 pour exploiter la prime de complexité opérationnelle :

**Piste 16 — Alt-Data "Sale" et asynchrone (La prime de nettoyage)**
- **Thèse :** Exploiter des données dures à normaliser (commits GitHub, embauches LinkedIn locales, documents judiciaires obscurs). Les fonds rejettent ces pipelines car trop fragiles à maintenir à grande échelle.
- **Pourquoi ça résisterait :** C'est un monopole d'ingénierie "bricolée". L'information est publique mais illisible par les algos institutionnels.
- **Gate de Kill :** L'alpha généré survit-il au slippage et au coût de maintenance du pipeline sur une période d'essai ?

**Piste 17 — Value Betting sur Soft Bookmakers (L'arbitrage de lenteur)**
- **Thèse :** Les bookmakers "Soft" (Winamax, Unibet) sont structurellement lents vs les "Sharps" (Pinnacle) car ils extraient de la marge sur le public récréatif, pas sur la justesse absolue.
- **Pourquoi ça résisterait :** L'edge est garanti mais limité par le ban des comptes gagnants. L'institution ne peut pas "tourner" des comptes retail.
- **Gate de Kill :** L'EV opérationnelle (net de marge) justifie-t-elle le temps manuel passé avant le ban inévitable du compte ?

**Piste 18 — DeFi "Complex Yield" & Derivatives (Prime de Smart Contract)**
- **Thèse :** Arbitrage de rendements sur des protocoles complexes type Pendle Finance (Principal Tokens vs Yield Tokens) ou boucles de Money Markets sur des L2 de niche.
- **Pourquoi ça résisterait :** Prime de risque pur (Smart Contract hack risk) + KYC/Compliance institutionnelle qui bloque les gros fonds.
- **Gate de Kill :** Le rendement net (après gas, slippage, bridge) bat-il le risque de hack mesuré par les primes d'assurances on-chain (ex: Nexus Mutual) ?
- **Statut : KILL Gate B (2026-06-25, étude #23).** Dernier candidat pré-enregistré jamais run
  (gates datés 2026-06-24). Sur le marché Pendle **mûr** : Gate A **PASS** (prime brute réelle,
  spread PT stablecoin vs USDC AAVE médiane +3.7 %, 7/7 > 100 bps). Gate B **KILL** — le coût de
  couverture **live** lu sur Nexus Mutual tranche : là où le risque est **assurable** (PT Ethena),
  la prime (1.1-2.1 %) est < le cover (Pendle SC 1.15 % + depeg 2.25 % = 3.4 % floor) → **edge
  négatif** (−1.3 / −2.3 %) ; là où la prime est **grasse** (msUSD +6.5 %, USDai/USDat +3.7-4.4 %),
  le sous-jacent obscur n'a **aucun cover Nexus = inassurable** (+ 2/4 à TVL fantôme). **Zéro
  survivant** à la barre 200 bps pré-enreg. *Efficience actuarielle bipolaire : pas de quadrant
  grosse-prime-et-assurance-cheap.* La barrière compliance invoquée est réelle (fonds réglementés
  absents) mais le marché DeFi natif + l'assureur Nexus pricent le risque sans eux. Sous-type de
  mort #3 (prime ≈ risque), mécanisme neuf = prix du risque **lu** sur un marché d'assurance, pas
  estimé. [`pendle/docs/FINDINGS.md`](pendle/docs/FINDINGS.md).

**Piste 19 — Liquidity Provision active (DEX Toll-Booth)** *(traitée comme étude #15, V3 LP/LVR — DOWNGRADE)*
- **Thèse :** Fournir de la liquidité concentrée (Uniswap V3) gérée dynamiquement sur des paires trop volatiles pour les MM traditionnels mais à fort volume retail (memes/alts).
- **Pourquoi ça résisterait :** C'est l'inverse de l'arbitrage : on encaisse les frais. Trop complexe pour le retail (Impermanent Loss), trop petit pour un desk HFT.
- **Gate de Kill :** Les frais de transaction ("yield") dépassent-ils la somme de l'Impermanent Loss et des frais de gas nécessaires aux rééquilibrages fréquents ?
- **Statut : DOWNGRADE** (#15, frais > LVR au niveau pool mais capté par LP actifs/JIT ; solo passif tué par gas mainnet). [`univ3-lvr/docs/FINDINGS.md`](univ3-lvr/docs/FINDINGS.md).

## Bilan V3 + programme (2026-06-25) — 24 études, 0 edge déployable

**Objectif prop (révisé) — piste A méta-gate rendue = KILL (#24).** Le pivot vers « valider un
compte prop firm » a produit sa 1re étude : le challenge est un **wrapper de payoff lottery-shaped**
(médiane = −fee sans edge ; et la médiane reste négative même avec le sleeve trend 0.42). Il
**re-emballe le constat no-edge en loterie à marge maison** (#16), sans le lever. Pistes B/C/D du
plan prop tombent dans la foulée (flipper la médiane exigerait P(net>0) > 50 %, hors de portée du
seul edge réel). Détail dans la section *Objectif opérant* ci-dessus + `prop-firm-gate/`.

### (Clôture edge-hunting, pré-pivot)

Les 4 pistes V3 "Prime de Saleté" sont **toutes rendues** : alt-data sale (rejet filtre,
commoditisée), books sportifs (#16 KILL), Uniswap V3 LP (#15 DOWNGRADE), Pendle complex yield
(#23 KILL). Avec la construction META (#22, KEEP-2-SLEEVE-FAIBLE) le programme atteint **23 études**.
Le **dernier candidat pré-enregistré non-run** (Pendle) étant désormais clos, il **ne reste aucune
piste spécifiée en attente**. Le motif unifié tient sans exception sur les 23 : *à information/prix
public, un solo n'a pas d'edge récoltable* ; et quand l'edge structurel est réel (carry, LST, VRP,
LP V3, Pendle), il est **arbitré jusqu'à son coût** (tail, friction, bounce, gas, ou — cas Pendle —
le prix d'assurance actuariel lui-même). Seul deliverable trading = sleeve trend sur 60/40 (assurance-
crise, #22). Vrai capital = le pipeline de 23 verdicts pré-enregistrés. Toute reprise future exige
une **arme structurelle neuve**, pas une nouvelle canne dans l'eau morte.


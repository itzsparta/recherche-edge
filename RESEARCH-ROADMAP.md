# Research roadmap — chasse à l'edge (post-mortem orderflow / meme / rebate)

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
bounce). Le vrai capital du programme = le **pipeline de 9 kills pré-enregistrés** — dont un faux GO
(t=7.13) démasqué avant déploiement — pas un P&L.

**Pistes neuves restantes (`factor-harvest/EDGE-IDEAS-LOG.md`).** Le reframe « changer l'étang, pas la
canne » identifiait 2 étangs (contrepartie ≠ fonds optimisateur) : **piste 8 CEF discount = KILL**
(faux GO bounce, ci-dessus — l'inarbitrabilité par structure était réelle mais la récolte mangée par
la microstructure) ; reste **piste 10 contrepartie récréative** (favorite-longshot bias Polymarket/
Betfair = seul autre étang vraiment différent ; tueur probable = vig > biais). Plus 9 (LST
convergence, tail à la carry) et 11 (funding cross-sectionnel, bolt-on). Gates pré-enregistrés écrits.
La piste 8 prévient sur la 10 : un brut prometteur ne vaut rien sans le test net-de-friction réelle.

# Edge Ideas Log — proposition datée de nouvelles pistes

---

## 2026-06-23 — Session automatisée de scouting

### Contexte lu avant de proposer

- RESEARCH-ROADMAP.md et docs/FINDINGS.md relus.
- 7 pistes mortes (V1+V2) : trend, unlocks, niche-capacité, VRP, overnight, pré-FOMC, meme-coin.
- 1 survivante avec caveats : carry crypto-funding (piste 6, GO, net +10.5 %/an, market-neutral, mais compression forward ~2-5 %).
- Motif unifié : tout edge à **information/prix public** est mangé ; seul le carry structurel survit.
- Piste 7 "relative-value transverse" est mentionnée dans le ROADMAP (section Suite V2) mais jamais spécifiée ni testée.

---

### Pistes examinées + verdict filtre

#### Piste A — Seasonal commodity futures

- **Mécanisme candidat :** Cycles physiques réels (récolte maïs, pic chauffage gaz naturel) créent des saisonnalités documentées dans les futures.
- **Filtre 1 (info publique mangée ?)** : **OUI.** Les fonds CTA et les desks énergie/agri de Goldman, Glencore, Vitol connaissent et tradent ces saisonnalités depuis des décennies. Le "Goldman roll" calendrier est littéralement un produit standardisé. La prime est arbitrée dans les forward curves en temps réel par des acteurs avec des billions AUM.
- **REJET.** Pas d'arme structurelle "solo" : le solo arrive des années après les professionnels, sans avantage de taille ou d'info.

---

#### Piste B — ETF premium/discount vs NAV (arb mécanique)

- **Mécanisme candidat :** Un ETF s'échange temporairement au-dessus ou en dessous de la valeur de son panier sous-jacent → achat/short mécanique.
- **Filtre 1 :** Sur les grands ETFs (SPY, QQQ, BTC ETF…), les Authorized Participants corrigent l'écart en quelques secondes en créant/rachetant des parts — c'est leur métier rémunéré. Sur les petits ETFs, le premium/discount persiste mais : (a) volume trop bas pour sortir, (b) risque de closure du fonds, (c) même profil que piste 3 (spread existe, rien derrière).
- **REJET.** Même structure d'échec que piste 3 (fantôme de capacité + risque opérationnel disproportionné).

---

#### Piste C — Cross-sectional momentum sectoriel (rotation 11 secteurs SPDR)

- **Mécanisme candidat :** Long le secteur le plus fort sur 3-6m, short le plus faible, rééquilibrage mensuel.
- **Filtre 1 :** Variante directe de la piste 1 (trend-following cross-asset) déjà tuée. Le momentum cross-sectionnel sur indices sectoriels est étudié depuis Jegadeesh-Titman (1993), entièrement pricé par les smart-beta factor ETFs (iShares MSCI Momentum). Aucune arme structurelle nouvelle.
- **REJET.** Ne franchit pas le filtre "nouvelle arme non-arbitrée".

---

#### Piste D — Relative Value transverse : cointegration BTC/ETH daily ★ CANDIDAT

- **Filtre 1 :** AMBIGU — voir mini-spec ci-dessous.
- **Filtre 2 (data gratuite ?)** : OUI — Binance daily OHLCV, ~8 ans (2017-2026), API publique.
- **PASSE les deux filtres prudemment.** Gate strict requis dès le démarrage.

---

### Mini-spec piste D — RV BTC/ETH cointegration daily

#### Hypothèse d'edge

La série `log(BTC_price / ETH_price)` est I(0) (stationnaire, pas une marche aléatoire) : il existe un niveau d'équilibre économique entre les deux actifs. Chaque excursion > σ de cet équilibre se corrige → `P(mean-reversion dans les N barres suivantes) > 50 %`, exploitable via long-short du pair.

#### Source de l'inefficience structurelle — pourquoi NON entièrement arbitrée

1. **Non-prédictif** : on ne parie pas sur la direction BTC ou ETH mais sur leur RELATION. C'est une contrainte mécanique (loi des prix uniques intra-classe crypto), pas de l'alpha prédictif. Moins crowdé.
2. **Mandats séparés** : les grands ETFs institutionnels crypto (BlackRock IBIT = BTC only, Grayscale ETHE = ETH only) ne font PAS de pairs trading cross-actif. Leur tracking mandate interdit la jambe opposée. Un solo sans contrainte de mandat est l'acteur le plus libre ici.
3. **Leg-risk décourage les gros acteurs** : paire de positions simultanées sur deux actifs très volatils = risque de divergence temporaire à financer. $5k = 0 problème de marge. $500M = problème de VaR.
4. **Daily vs intraday** : les bots HFT arbitrent l'écart intraday en microsecondes. En daily, le turnover faible rend le carry de frais supportable — l'intraday est trop cher pour cette approche.

#### Falsifiabilité — pourquoi ça peut mourir

- Si `log(BTC/ETH)` est I(1) OOS (non-stationnaire après 2022 par exemple, car ETH post-Merge a changé son modèle économique) → thèse tombe immédiatement.
- Si la série est stationnaire mais le spread est trop lent à mean-reverter vs le coût de portage → net négatif.
- "Pairs trading crypto" est connu → possiblement crowdé au niveau daily par des bots semi-institutionnels.

#### Data source

Binance API : `GET /api/v3/klines?symbol=BTCUSDT&interval=1d` et `ETHUSDT`. Gratuit, ~2400 daily bars disponibles (2017→2026). Pipeline data déjà présent dans le projet (carry/ + forced-flows/).

#### Gate de décision — pré-enregistré ici avant tout run

| Gate | Critère PASS | Critère KILL |
|------|-------------|--------------|
| **(A) Stationnarité IS** | ADF p < 0.05 sur IS 2017-2021, `log(BTC/ETH)` | ADF non-significatif → KILL immédiat, thèse invalide |
| **(B) Stationnarité OOS** | ADF p < 0.05 sur OOS 2022-2026 (post-Merge) | Non-stationnaire OOS → KILL (rupture de régime structurel) |
| **(C) brut > 0, t > 2** | t-stat > 2 sur OOS, signal = z-score du spread > 1.0 (à pré-enregistrer avant run) | brut ≤ 0 ou t ≤ 2 → KILL |
| **(D) brut > miroir** | Long/short du spread bat long-only du spread | Miroir gagne → bruit directionnel, pas de l'edge symétrique |
| **(E) net > 0** | Net après frais 0.1 %/trade (Binance maker) + financement > 0 | Net ≤ 0 → KILL |
| **(F) split régime** | Positif dans ≥ 2/3 régimes (bull 2020-21, bear 2022, sideways 2023-24) | Positif dans 1 seul régime → drift, pas un edge |
| **(G) DSR** | DSR(best, N=3 variantes signal) > 0.95 | DSR < 0.95 → overfit |

Signal pré-enregistré : z-score = `(spread_t - μ_rolling_252) / σ_rolling_252`, threshold = ±1.0, exit = ±0.25. Un seul paramètre principal (threshold) à tester sur 3 valeurs (0.75 / 1.0 / 1.25) pour le DSR.

#### Coût d'implémentation

~150 lignes Python. Pipeline backtester + DSR + PBO déjà bâti dans le projet. Estimation 1-2 jours pour le harness complet + visualisation z-score.

#### Levier et coût honnête

Position : long 1 lot ETH / short 1 lot BTC simultané (ou inverse), sizing vol-parité. Levier cible ≤ 1x brut. Frais Binance : 0.1 % maker/taker par leg × 2 legs = 0.2 % aller-retour. Financement court : 0 % (spot vs spot, pas de futures). Si via futures : ajouter le funding rate moyen (~5-8 %/an côté short = coût à déduire).

#### Verdict (run effectué 2026-06-23) — KILL Phase-1

**KILL à la stationnarité.** ADF sur `log(BTC/ETH)` (3233 barres Binance 2017-2026) :
Gate (A) IS p=**0.3795** I(1), Gate (B) OOS p=**0.7700** I(1). Pas de niveau d'équilibre = marche
aléatoire. **Pas un artefact 1:1** : Engle-Granger à hedge ratio libre non-cointégré partout (IS
p=0.25 / OOS p=0.68), et le ratio flippe 0.70→1.36 IS→OOS = relation instable (rupture post-Merge
ETH, anticipée). Half-life 305-572 j = intradable même dans le doute. Tué en ~30 min, zéro backtest.
Détail : [`relative-value/docs/FINDINGS-rv.md`](../../relative-value/docs/FINDINGS-rv.md).

---

### Résumé 3 lignes

3 pistes rejetées en filtrage (seasonal = mangé par CTA, ETF arb = fantôme capacité, XS momentum = variante piste-1-tuée). **Piste 7 RV BTC/ETH cointegration daily** = seule candidate : mécanisme structurel non-prédictif (mandats séparés + leg-risk décourage les gros), data gratuite, gate falsifiable ADF IS+OOS prient avant tout run. Prochaine étape = valider Rémi OK pour lancer Phase-1 (stationnarité uniquement, ~30 min de code).

---

## 2026-06-23 (bis) — Reframe « l'étang, pas la canne » + pistes 8-11

### Le constat qui ré-oriente la chasse

Les 7 pistes mortes (V1+V2) partageaient un trait jamais nommé : **même type d'étang** — la
contrepartie est toujours un **fonds maximisateur de profit** (intraday majors, unlocks,
cross-venue, vol, funding, calendrier). Un solo sans latence/infra/capital y perd **par
construction**. Le ROADMAP dit « l'étang, pas la canne » mais les 7 pistes ont **changé la canne,
jamais l'étang**.

**Deux étangs structurellement différents, jamais testés**, où la contrepartie n'est PAS un
optimisateur :

1. **Inarbitrable par structure** — anomalie qui persiste *précisément parce qu'aucun mécanisme de
   redemption ne peut la fermer* (≠ piste B ETF, rejetée car les AP ferment l'écart).
2. **Contrepartie non-optimisatrice** — récréative, parie pour le frisson, pas pour l'EV.

Tout le reste = variante d'une piste morte. C'est le filtre de tri du neuf ci-dessous.

---

### Piste 8 — CEF discount mean-reversion ★ meilleure EV neuve

**Hypothèse d'edge.** Le `discount(t) = (price − NAV) / NAV` des closed-end funds est I(0)
(mean-reverting), pas une marche aléatoire. Acheter le quartile le plus décoté / shorter (ou hedger
via ETF sectoriel) le moins décoté → capter la convergence + le carry de distribution.

**Source de l'inefficience structurelle — pourquoi NON arbitrée.** Un CEF n'a **pas** de mécanisme
de création/rachat par AP (≠ ETF) → le discount ne **peut pas** être arbitré. C'est exactement ce
qui a tué la piste B (ETF : les AP ferment l'écart en secondes) qui, retourné, devient l'edge ici.
Énigme documentée et persistante depuis 30+ ans (Lee–Shleifer–Thaler 1991, « closed-end fund
puzzle »). Contrepartie = sentiment retail. Les activistes (Saba, Bulldog) attaquent les **gros** CEF
via tender offers → reste les **petits**, sous le radar institutionnel = terrain solo (capacité +
patience).

**Falsifiabilité — pourquoi ça peut mourir.**
- Si le discount est I(1) (pas de mean-rev) → KILL immédiat.
- Mean-rev réelle mais **trop lente** vs le drag (expense ratio CEF ~1-2 %/an + spread + coût hedge) → net négatif.
- Décile décoté = **value-trap** (sous-jacent pourri) → le discount est *justifié*, pas un edge à capter.

**Data.** CEFConnect / screeners gratuits ; prix via Stooq/yfinance ; NAV publié quotidiennement.

**Gate de décision — pré-enregistré.**

| Gate | PASS | KILL |
|------|------|------|
| (A) Stationnarité discount | ADF p<0.05 sur panel de discounts (pooled + par fonds) | I(1) → KILL |
| (B) brut>0, t>2 | L/S décoté-vs-peu-décoté, rebal mensuel, OOS, t>2 | brut≤0 ou t≤2 |
| (C) net>0 | après expense ratio + commissions + coût short/hedge | net≤0 |
| (D) brut>miroir | bat le long-only du sous-jacent | miroir gagne = beta sectoriel pur |
| (E) anti-value-trap | décile décoté ≠ simplement les pires actifs (contrôle secteur/style) | discount justifié → pas d'edge |
| (F) split régime | positif ≥2/3 régimes (2018 selloff, 2020 covid, 2022 bear) | 1 seul régime = drift |
| (G) DSR | DSR(best, N variantes) > 0.95 | <0.95 = overfit |

**Coût.** ~200 lignes, panel/event study. 1-2 j.

**Verdict (run 2026-06-23) — KILL, faux GO microstructure.** `code python/cef-discount/`. Gate A
PASS net (62 % fonds stationnaires, pooled ADF p≈0). Phase-2 brut **tout-vert = premier GO provisoire
du programme** (net +8.41 %/an t=7.13, DSR 1.000, 3/3 régimes). **Tué en robustesse** : lag d'entrée
+1 mois → alpha **s'inverse** (+8.41 % → −4.01 %, survie −48 %) = toute la « convergence » était du
**bid-ask bounce** non-capturable (CEF illiquides, on achète le print au bid, rebond au mid). Short =
CEF à premium = hard-to-borrow (borrow 15 % → net −2.59 %). Forme déployable (intra-cat + lag1 +
long-only) = **−0.64 % t=−0.64 = zéro**. Survivorship (univers = fonds vivants) non corrigé = pire
encore. Faux positif le plus convaincant du programme (un retail aurait tradé le t=7.13). Détail :
[`cef-discount/docs/FINDINGS-cef.md`](../../cef-discount/docs/FINDINGS-cef.md).

---

### Piste 9 — LST convergence (stETH/ETH) — EV moyen, tail à surveiller

**Hypothèse d'edge.** Les liquid-staking tokens (stETH, rETH…) tradent à **discount** vs le
sous-jacent en stress (file de retrait engorgée) ; la convergence est **garantie par le mécanisme de
redemption du protocole** (1 stETH → 1 ETH une fois la queue purgée). Acheter le LST décoté / hedger
ETH → capter la reconvergence.

**Source de l'inefficience structurelle.** Convergence garantie protocolairement = **non-prédictif**
(on ne devine pas un prix, on attend une égalité mécanique). Le discount = prix d'une **illiquidité
de queue**, payée à celui qui peut attendre. Les gros acteurs sous contrainte de redemption ne
peuvent pas porter la queue ; le solo patient, si.

**Falsifiabilité — RIME AVEC LE KILL CARRY (piste 6).** Si le discount price **juste** le risque
slashing / smart-contract / dépeg permanent → net ≈ zéro (priced-in, exactement le tail exchange qui
a tué le carry). Condition de survie : `discount moyen capté > coût-queue annualisé + prime de tail`.
Si non → KILL.

**Data.** Prix de pool Curve/Uniswap (stETH/ETH), DeFiLlama. Gratuit. ~2021→2026 (post-Merge).

**Gate de décision — pré-enregistré.**

| Gate | PASS | KILL |
|------|------|------|
| (A) reconvergence historique | après excursion >σ, retour à ~0 en N jours, taux de succès mesuré | ne reconverge pas |
| (B) brut>0, t>2 | stratégie buy-discount/hedge | brut≤0 ou t≤2 |
| (C) net>0 | après frais swap + gas + coût hedge | net≤0 |
| (D) tail explicite | break-even P(slashing/dépeg permanent) > seuil (méthode carry phase-2) | break-even < seuil → priced-in |
| (E) split régime | **2022 (Luna/3AC/FTX) DOIT être inclus = LE test** | survit pas le stress |

**Coût.** ~150 lignes, 1 j. ⚠ Petit échantillon d'événements de stress → puissance statistique faible.

---

### Piste 10 — Contrepartie récréative (favorite-longshot bias) — le seul étang vraiment différent

**Hypothèse d'edge.** Dans les marchés dominés par des participants **récréatifs** (Polymarket
longshots, Betfair exchange), les prix sont biaisés : les longshots (faibles probabilités) sont
**surcotés**. Fade systématique des longshots = EV>0 avant commission.

**Source de l'inefficience structurelle.** **Seul étang vraiment différent** de tout ce qui précède :
la contrepartie n'est PAS un profit-max, elle parie pour le frisson. Le biais persiste car le
participant marginal **ne maximise pas l'EV**. Aucun fonds quant ne concurrence (barrières
régul/réputation/capacité). Capacité minuscule = terrain solo par définition.

**Falsifiabilité.**
- EV après commission ≤ 0 → KILL (la vig/commission mange le biais — tueur le plus probable).
- Capacité exploitable < seuil $ → ratio temps/EV nul.
- Bannissement systématique des comptes gagnants → non-déployable (books classiques) ; seul espoir = venues peer-to-peer (commission, pas vig).

**Data.** Polymarket (API publique on-chain, gratuit) + résolutions historiques ; Betfair historical si accessible.

**Gate de décision — pré-enregistré.**

| Gate | PASS | KILL |
|------|------|------|
| (A) biais existe | calibration P_marché vs fréquence réalisée, N>500 marchés résolus : longshots (<10 %) réalisent < prix implicite | calibré = pas de biais |
| (B) net>0 | EV fade-longshot APRÈS commission + slippage AMM/CLOB + gas | net≤0 = vig mange tout |
| (C) dose-réponse | biais croît avec l'extrémité de la cote (monotone) | plat/inversé = bruit (cf. piste 3) |
| (D) capacité $ | profondeur réelle /depth aux cotes ciblées (≠ fantôme piste 3) | <seuil = pas worth it |
| (E) split catégories | biais sur ≥2 catégories (politique/crypto/sport) | 1 seule = artefact |

**Coût.** ~150 lignes + ingestion résolutions. 1-2 j.

**Verdict (run 2026-06-23) — KILL Gate A, hypothèse inversée.** `code python/prediction-markets/`.
3082 marchés binaires résolus (Gamma + CLOB, pagination fenêtres de date, prix ex-ante au midpoint
temporel), 5586 legs. Longshots (<0.10) : gap réalisé−implicite **+0.0109, t=+2.26** = **sous-cotés**,
PAS surcotés → favorite-longshot **inversé** (favoris surcotés gap −0.08). Fader les longshots
perdrait. Aucune catégorie ne montre le biais (Gate E). Polymarket = foule crypto-native + arbs, pas
récréative naïve = efficient. Pattern inverse NON exploité (post-hoc + même tueur friction que le
bounce CEF : gap 5-8% mangé par le spread du côté cheap). Détail :
[`prediction-markets/docs/FINDINGS-pm.md`](../../prediction-markets/docs/FINDINGS-pm.md).

---

### Piste 11 — Funding cross-sectionnel (≠ niveau) — bolt-on cheap, novelty faible

**Hypothèse d'edge.** Après avoir hedgé le **niveau** du funding (que la piste 6 a tué en
directionnel), la **dispersion cross-sectionnelle** paie : long le perp au funding le plus négatif /
short le plus positif, dollar-neutral, rebal 8h.

**Source de l'inefficience structurelle.** Extension de la piste 6 ; **faible novelty** — risque
d'être arbitré-jusqu'au-coût à l'identique. Justification du test : coût marginal quasi-nul (infra
`carry/` existe).

**Falsifiabilité.**
- Net ≤ 0 après frais (turnover 8h élevé) → KILL (tueur le plus probable).
- P&L dominé par 1-2 alts illiquides → capacité fantôme (cf. piste 3).

**Data.** Funding rates Binance/Bybit — `carry/data_funding.py` existe déjà.

**Gate de décision — pré-enregistré.**

| Gate | PASS | KILL |
|------|------|------|
| (A) dispersion paie | brut>0, t>2 sur portefeuille L/S funding-ranked | brut≤0 ou t≤2 |
| (B) net>0 | après frais réels (turnover 8h × spread) | net≤0 |
| (C) market-neutral | corr≈0 avec BTC ; brut_long ET brut_short >0 | un seul côté porte |
| (D) drop-top | retirer les 2 alts extrêmes → survit | meurt = capacité fantôme |
| (E) split régime | positif ≥2/3 régimes | 1 seul = drift |

**Coût.** Bolt-on sur `carry/`, ~0.5 j.

---

### Ordre d'attaque recommandé

1. ~~**Piste 7** (RV BTC/ETH)~~ — **KILL 2026-06-23** : spread I(1) IS+OOS, non-cointégré à ratio libre, half-life 305-572 j. Mort à la stationnarité (~30 min). Cf. `relative-value/docs/FINDINGS-rv.md`.
2. ~~**Piste 8** (CEF)~~ — **KILL 2026-06-23** : faux GO microstructure. Gate A + Phase-2 brut tout-vert (1er GO du programme), tué en robustesse par le bid-ask bounce (lag 1 mois → alpha s'inverse) ; forme déployable = zéro. Cf. `cef-discount/docs/FINDINGS-cef.md`.
3. ~~**Piste 10** (récréatif)~~ — **KILL 2026-06-23** : pas de vig sur Polymarket, mais le biais est **inversé** (favoris surcotés, longshots sous-cotés) → fader les longshots perd. Étang « différent » en fait efficient. Cf. `prediction-markets/docs/FINDINGS-pm.md`.
4. **Pistes 9, 11** — opportunistes (9 = tail à la carry ; 11 = bolt-on cheap).

**Prior honnête.** Après 7 kills à motif serré, proba qu'une piste neuve donne un edge déployable =
basse. Mais 8 et 10 attaquent un étang *structurellement différent*, pas une nouvelle canne dans
l'eau morte. C'est la seule façon de ne pas refaire les 7 mêmes kills.

---

## 2026-06-24 — Session automatisée de scouting

### Contexte lu avant de proposer

- RESEARCH-ROADMAP.md relu intégralement.
- **22 pistes testées, 0 edge déployable.** MEMORY mis à jour avec bilan complet.
- V1+V2 closes (pistes 1-14) : trend, unlocks, niche-cap, VRP, calendrier, carry, RV BTC/ETH,
  CEF, LST, Polymarket, funding-XS, XS-momentum, VRP-crypto, airdrop.
- V3 "Prime de Saleté" partiellement traitée : p16 sports books = KILL ; p15 Uniswap V3 LP =
  KILL déployabilité ; p17 FX carry G10 = KILL ; p18 GEX dealer-gamma = KILL-tradable.
- **Non testés dans le ROADMAP V3** : (A) Alt-Data "Sale" (commits GitHub/LinkedIn/judiciaire),
  (B) DeFi Complex Yield / Pendle Finance (piste 18 ROADMAP).

---

### Pistes examinées + verdict filtre

#### Piste A — Alt-Data "sale" : commits GitHub vs résultats logiciels

- **Mécanisme candidat :** Accélération des commits GitHub d'une software company avant ses
  earnings = indicateur leading de product readiness → bat le consensus EPS.
- **Filtre 1 (info publique mangée ?) :** **OUI, entièrement.** Les fournisseurs d'alt-data
  professionnels (Quandl, YipitData, Sentieo, Thinknum) vendent exactement ce signal depuis
  2017+. Two Sigma, Citadel et Acadian l'intègrent dans leurs features. Il n'y a aucun avantage
  informationnel qu'un solo sans licence peut extraire que ces acteurs n'ont pas déjà arbitré.
  La commodity-isation de l'alt-data GitHub/LinkedIn constitue le motif ici : le monopole
  d'ingénierie "bricolée" a une durée de vie de 12-24 mois avant que les vendors le packagisent.
  Pour les signaux datant de 2015+, la fenêtre est fermée.
- **REJET.** L'effort d'ingestion n'achetterait pas d'edge ; juste de la réplication d'un signal
  déjà institutionnalisé.

---

#### Piste B — NAV arb crypto ETF overnight (IBIT / FBTC)

- **Mécanisme candidat :** Les ETFs Bitcoin cotés sur NYSE Arca (IBIT, FBTC) closent à 16h EST.
  BTC trade 24/7. Un mouvement overnight de BTC >2% crée un "gap at open" prévisible le
  lendemain à 9h30. Acheter/shorter l'ETF en pré-marché dans la direction du mouvement nocturne.
- **Filtre 1 :** **OUI, instamment arbitré.** Les Authorized Participants (AP : Jane Street, Virtu,
  Citadel Securities) ont pour mandat explicite de fermer tout écart ETF/NAV en créant ou
  rachetant des parts. En pré-marché, le bid/ask de l'ETF reflète déjà le BTC spot à travers la
  prime/décote NAV que les APs surveillent en temps réel. L'arb se ferme en millisecondes à
  l'ouverture des marchés. Un solo en pré-marché face aux APs = même structure de mort que la
  piste 3 (niche capacité) mais 10x plus rapide.
- **REJET.** Structure d'échec identique aux pistes d'arb pur : APs institutionnels ferment
  l'écart par construction de leur mandat.

---

#### Piste C — Pendle Finance Principal Tokens : spread vs taux sans risque ★ CANDIDATE

- **Filtre 1 (info publique mangée ?) :** AMBIGU — voir mini-spec ci-dessous.
- **Filtre 2 (data accessible gratuitement ?)** : OUI — API Pendle v2 publique, DefiLlama
  yields API, Nexus Mutual cover cost public.
- **PASSE les deux filtres prudemment.** Le niveau de yield est public, mais la question
  n'est pas le niveau brut — c'est si le spread net (PT yield − USDC lending − SC insurance)
  est positif de façon persistante. Ce n'est pas directement lisible sans calcul.

---

### Mini-spec piste C — Pendle Finance Principal Token spread

#### Hypothèse d'edge

Un Principal Token (PT) Pendle sur un actif stablecoin (sUSDe, USDE, USDe+) offre un taux
fixe jusqu'à maturité = `(1 − PT_price) / T_years`. Ce taux implicite incorpore une prime pour
le smart contract risk (SC risk) du protocole Pendle + du protocole sous-jacent. Si cette prime
est systématiquement **supérieure à l'actuariel** (coût de couverture SC via Nexus Mutual), alors
acheter le PT + couvrir le SC risk = rendement net positif vs USDC lending sur AAVE, sans
exposition directionnelle crypto.

Formellement : `PT_yield_implied − USDC_AAVE_rate − SC_insurance_annual_cost > 0` de façon
persistante sur ≥12 mois (dont le sous-échantillon mûr 2025-2026, leçon p12+p13 Gate G).

#### Source de l'inefficience structurelle — pourquoi NON entièrement arbitrée

1. **Barrière compliance institutionnelle** : aucun fonds réglementé (UCITS, 40-Act, pension)
   ne peut positionner en DeFi non-KYC sur Ethereum mainnet. Les desks de taux fixes
   institutionnels qui pourraient comparer un PT de 6 mois à un T-bill sont
   structurellement absents. C'est la même barrière qui préservait le carry (p6) avant que
   le tail exchange ne le tue — ici pas de tail exchange, juste du SC risk.
2. **Complexité opérationnelle réelle** : le mécanisme PT/YT de Pendle + le risque oracle
   (Pendle utilise des price feeds pour les yield tokens) + la subtilité du pool AMM
   (Pendle SY = Standardized Yield wrapper) est une barrière d'entrée documentée. La
   documentation n'est pas un prospectus UCITS accessible à un analyste credit.
3. **Capacité** : TVL des pools Pendle stablecoin = $50M−$500M. Pour $5k−$50k : impact
   d'exécution négligeable. Un fonds qui voudrait y mettre $50M déplacerait le marché.
4. **SC insurance** : Nexus Mutual couvre Pendle Finance avec des cover costs typiquement de
   1−3%/an. Cette couverture est rarement achetée en pratique (la plupart des LP Pendle
   sont non-couverts) → la prime brute inclut SC risk payé, mais pas par des acteurs
   diversifiés qui pourraient compresser ce spread.

#### Falsifiabilité — pourquoi ça peut mourir

- **Gate A** : si PT yield ≤ USDC lending rate + 100 bps sur le panel récent → aucun spread
  à explorer ; KILL immédiat (< 30 min de code).
- **Gate B actuariel** : si prime brute = coût de couverture Nexus Mutual → entièrement
  priced-in, pas d'inefficience exploitable. C'est le kill le plus probable : le marché
  Pendle peut être "efficient" au sens où le spread brut = exactement la prime de SC risk.
- **Gate C OOS mûr** : si le spread existe en 2023−2024 mais pas en 2025−2026 (maturité du
  marché Pendle = densification des LP yield-hunters) → artefact early-market (même leçon
  p12+p13 crypto, Gate G obligatoire).
- **Hack matérialisé** : Penpie (protocole adjacent Pendle) hacké pour $27M en sept. 2024.
  Le tail SC risk a déjà été réalisé une fois. La prime peut être correctement calibrée.
- **Yield aggregators** : Pendle strategies sur Equilibria et Convex Pendle apportent du
  capital institutionnalisé dans les pools → compriment le spread.

#### Data sources (toutes gratuites)

| Source | Données | Accès |
|--------|---------|-------|
| `api-v2.pendle.finance/core/v1/` | Prix PT, yield implicite, pools actifs | REST public, no auth |
| `yields.llama.fi` (DefiLlama) | USDC lending rate AAVE/Compound, historical | REST public |
| `nexusmutual.io/api` / on-chain | Cover cost annuel par protocole | Web scrape ou GraphQL |
| The Graph (Pendle subgraph) | Historical PT prices, pool swaps | GraphQL public |

Pipeline data = ~100 lignes Python. Pas de backtest lourd : Gate A est un data-pull, Gate B
est un calcul simple (spread brut vs cover cost), Gate C est une comparaison is/oos.

#### Gates de décision — pré-enregistrés ici avant tout run

| Gate | Critère PASS | Critère KILL |
|------|-------------|--------------|
| **(A) Spread brut positif** | `PT_yield − USDC_AAVE_rate > 100 bps` sur ≥80% des obs récentes (pools stablecoins matures) | Médiane ≤100 bps → insuffisant pour couvrir gas + slippage |
| **(B) Actuariel** | `Spread_brut − SC_insurance_cost (Nexus) > 0` de façon persistante | Spread ≤ cover cost → entièrement priced-in, pas d'inefficience |
| **(C) Persistance OOS mûr** | Spread net positif sur 2025-06 → 2026-06 (12 mois récents) ; Gate G obligatoire leçon p12+p13 | Disparaît sur sous-échantillon mûr → artefact early-market |
| **(D) Dose-réponse** | Spread croît avec la durée à maturité (risque temporel SC = logique) | Plate ou inversée → structure incohérente |
| **(E) Liquidité réelle** | Exécution $10k sans impact > 25 bps sur pool cible | Impact > spread → capacité fantôme (leçon piste 3) |

Signal pré-enregistré : PT stablecoin uniquement (sUSDe, USDe, PT-USDC-*) — exclut les PT sur
actifs volatils (stETH, BTC) qui ajoutent exposition directionnelle non souhaitée. Durée cible :
1−6 mois à maturité (assez court pour que la comparaison AAVE soit valide, assez long pour absorber
gas).

#### Coût d'implémentation et levier

Aucun levier. Achat direct de PT sur mainnet Ethereum ou Arbitrum. Frais : Pendle swap fee
0.1% + gas ($3−$10 sur Arbitrum L2, << sur mainnet mainnet). Pour 3−6 mois à maturité, les frais
sont absorbables si le spread dépasse 200 bps.

**Honnêteté brutale.** Le tueur le plus probable est le Gate B : le spread brut visible sur
Pendle.finance **existe** (les pools stablecoin affichaient 6−12% APY fixe en 2023−2024 quand
AAVE USDC était à 3−8%), mais cette différence peut être exactement le SC risk correctement
pricé par le marché (Penpie hack = réalisation du tail). Le test dit si c'est un artefact ou
un edge. Sans run de données, on ne sait pas — c'est la définition d'une candidate non encore
tuée.

#### Verdict (run 2026-06-25, étude #23) — KILL Gate B, le tueur annoncé

**Gate A PASS, Gate B KILL — exactement le tueur le plus probable pré-dit.** Sur le marché
Pendle **mûr** (snapshot 2026-06-25, 63 PT actifs / 7 stablecoin) : la prime brute **existe**
(spread PT vs USDC AAVE médiane +3.7 %, 7/7 > 100 bps → A PASS). Mais le coût de couverture
**live** lu sur Nexus Mutual (`v2/capacity`) tranche en deux familles, sans quadrant exploitable :
**(1) assurable → priced-in** (PT Ethena : prime 1.1-2.1 % < cover Pendle SC 1.15 % + depeg 2.25 %
= 3.4 % floor → edge **−1.3 / −2.3 %**) ; **(2) prime grasse → inassurable** (msUSD +6.5 %,
USDai/USDat +3.7-4.4 %, sous-jacent obscur, **0 cover depeg Nexus** ; 2/4 à TVL fantôme $0.1-0.4M).
**Zéro survivant** à la barre 200 bps pré-enreg. Tué en <1h comme prévu, Gate C/D/E inutiles.
Mécanisme neuf : le prix du risque est **lu sur un marché d'assurance actuariel**, pas estimé →
forme la plus nette du motif *structurel ≠ gratuit*. Détail :
[`pendle/docs/FINDINGS.md`](../pendle/docs/FINDINGS.md).

---

### Résumé 3 lignes

2 pistes rejetées en filtrage : Alt-Data GitHub (signal déjà commoditisé par vendors institutionnels
depuis 2017) et NAV arb ETF crypto (APs ferment l'écart en millisecondes par construction). **Piste C
Pendle Finance PT spread** = seule candidate : barrière compliance institutionnelle réelle + capacité
solo avantageuse + data gratuite API. Gate A (spread brut >100 bps) et Gate B (spread > coût SC
assurance Nexus Mutual) doivent être vérifiés avant tout run — si Gate B KILL, thèse morte en <1h de
code. **→ Run 2026-06-25 : KILL Gate B confirmé** (Gate A PASS, prime priced-in là où
assurable / inassurable là où grasse, 0 survivant). Voir verdict ci-dessus + `pendle/docs/FINDINGS.md`.

---

## 2026-06-28 — #32 merger-arb : VERDICT = UNTESTABLE free-data

Pipeline bâti+validé (EDGAR EFTS + extraction prix cash 4-phrasings + fallback ticker depuis texte
8-K + yfinance). **UNTESTABLE**, pas par n trop petit mais par **biais de survie DIRECTIONNEL** : sur
l'échantillon 2015, `kept_map 5 / kept_text 0` ∧ `noprice_text 10 / noprice_map 0` = **yfinance sert
0/10 des cibles delistées**. Un deal qui CLÔTURE → cible rachetée → delistée → yfinance vide (exit ET
entry) ⇒ la jambe gagnante disparaît à 100 %, irrécupérable free (EDGAR n'a pas de prix, Stooq même
trou). Les 5 gardés = break-survivors (`closed 0/5`) + contaminés acquéreur (DHR=Danaher, ELV=Anthem)
+ misparses (PED/COR). Scaler ×15 = plus de break-survivors, pas un panel. Run complet NON lancé
(dropout 100 % directionnel non corrigeable). Sous-type = mur-de-données pire que #30 car *retire les
issues profitables*. Tester proprement exige une base M&A payante (termes + prix delistés + statut).
Détail : [`merger-arb/docs/FINDINGS.md`](merger-arb/docs/FINDINGS.md). **Bilan : 32 études, 0 edge.**

---

## 2026-06-27 — Session automatisée de scouting

### Contexte lu avant de proposer

- RESEARCH-ROADMAP.md + FINDINGS.md pistes #26-#31 relus intégralement.
- **31 études, 0 edge déployable.** Le seul GO du programme (#29 LP-V3-L2) renversé en Phase-2.5
  (LVR full-path > frais à toute concentration ; le net positif = funding-carry de #6, déjà KILL).
- Pistes récentes : #27 SPAC-trust KILL sub-hurdle (+145 bps < 200) ; #28 PEAD KILL (arbitré/décru,
  spread nul net de friction) ; #30 commodity-carry DOWNGRADE (long-backwardation asymétrique, DSR
  0.895 < 0.95) ; #31 ILS cat-bond DOWNGRADE (prime réelle, décorrélée, déployable, mais sub-hurdle
  EW t=1.51 et cyclique hard-market).
- Motif unifié inchangé : tout edge à déclencheur/prix public est mangé ; quand l'edge structurel
  est réel, il est compressé jusqu'à son coût (tail, friction, bounce, LVR, cycle, fees).
- **Dernier axe non testé identifié** : prime de risque pour incertitude binaire NON prédictible
  (≠ "info publique priceable") = une date est connue mais la RÉSOLUTION ne l'est pas.

---

### Pistes examinées + verdict filtre

#### Piste A — Buy-write systématique / covered calls (CBOE BXM-style)

- **Mécanisme candidat :** Vendre des calls couverts sur l'indice (roll mensuel ATM) → collecter la
  prime de volatilité implicite = CBOE BXM index. Documenté surperformer buy-and-hold risk-adjusted.
- **Filtre 1 (info/prix public mangé ?) :** **OUI, variant direct de la piste #4 (VRP).** Vendre un
  call couvert = short vol implicite cap + long equity → profil de payoff identique à VRP avec la
  queue gauche conservée (pas de naked short vol) mais upside capé. La prime capturée est la même
  prime de volatilité que le VRP equity qui a tué la piste #4 (t=4.03, DSR 0.977, mais Sharpe 1.86
  mirage aveugle au skew −4 et drawdown SVXY −95 %). La mécanique est moins explosive (position
  couverte) mais le P&L brut est inférieur et le mécanisme de compression est identique (les desks
  de vol institutionnels pricent l'implicite). Aucune arme structurelle nouvelle : l'edge est la
  prime VRP, déjà tuée piste #4 sous sa forme la plus favorable.
- **REJET.** Variant de la piste #4 tuée, mécanisme identique.

---

#### Piste B — Short-interest crowding : signal contrarian sur squeeze

- **Mécanisme candidat :** Les stocks avec borrow rate élevé (IEX free data) ou short interest
  >30 % du float (FINRA biweekly, gratuit) sont "crowdés short". Acheter ces noms anticipe le
  squeeze forcé si un catalyseur survient.
- **Filtre 1 (info/prix public mangé ?) :** **OUI.** Le short interest et le borrow rate sont
  PUBLICS (FINRA publie bi-hebdomadairement, IEX en temps réel pour les membres). Le signal est
  connu, documenté dans la littérature académique (D'Avolio 2002, Lamont-Thaler 2003), intégré
  dans les screeners retail (FINVIZ, Ortex). Les algorithmes retail + hedge funds long/short
  monitors précisément ces métriques. De plus, le SQUEEZE lui-même est imprévisible sans modèle
  du catalyseur — sans catalyseur, un stock surshourté peut rester surshourté des années (cf.
  "value traps"). Le timing non-modélisable = le signal sans timing = directional momentum
  aléatoire. Motif exact de la piste #28 PEAD : signal documenté, mais absent dans l'univers
  liquide net de friction, et la version exploitable (catalyseur = info non-publique) est
  structurellement impossible pour un solo.
- **REJET.** Info publique entièrement pricée dans les instruments liquides ; timing imprévisible
  sans info non-publique.

---

#### Piste C — Merger arbitrage cash deals, small-cap US (<$500M EV) ★ CANDIDATE

- **Filtre 1 (info/prix public mangé ?) :** **AMBIGU → PASS PARTIEL.** L'annonce est publique
  (8-K SEC), mais la RÉSOLUTION (le deal ferme-t-il ?) n'est PAS une information publique
  prédictible. Le spread = prime de risque pour une incertitude binaire réelle (clôture vs. échec).
  Ce n'est PAS "priced-in" comme les unlocks (date = résultat) ou la FOMC (récurrence = momentum) ;
  c'est une PRIME D'ASSURANCE que le détenteur touche en échange d'un risque de perte -30% sur
  breakage. La prime persiste tant que les deals échouent parfois, pour des raisons non-prévisibles
  ex-ante (régulateur imprévisible, financement qui tombe, MAC clause). Structural moat additionnel :
  les fonds merger-arb institutionnels (Elliott, Pentwater) ont des mandats de taille minimum (>$500M
  EV de deal), laissant le segment small-cap sous-couvert.
- **Filtre 2 (data accessible gratuitement ?) :** **OUI.** SEC EDGAR EFTS (full-text search API,
  gratuit) pour les annonces de fusion (8-K Item 8.01 "Completion of Acquisition"), prix cibles via
  Yahoo Finance. Deal outcome (closing ou termination) = 8-K Item 8.01 "Termination" ou form 8-K de
  closing — parseable du même feed EDGAR. Sans base de données institutionnelle (Bloomberg MA), mais
  suffisant pour construire un panel IS/OOS.
- **PASSE les deux filtres.** Voir mini-spec ci-dessous.
- **Prior honnête :** Stratégie connue depuis les années 1970 (Ivan Boesky). Des fonds dédiés existent
  (MERFX, ARBFX). L'ère FTC 2021-2024 a fortement augmenté les break rates. Le prior le plus
  probable = DOWNGRADE/KILL similaire à SPAC #27 (prime réelle mais sub-hurdle après ajustement
  tail). Mais STRUCTURELLEMENT DISTINCT de toutes les pistes mortes → vaut le gate-kill.

---

### Mini-spec piste C — Merger arbitrage small-cap cash deals

#### Hypothèse d'edge

Après l'annonce d'un deal M&A (tout-cash, cible cotée US, EV < $500M), le prix de la cible cote
**sous** le prix de deal annoncé. Ce spread = prime de risque pour l'incertitude de clôture. En
achetant la cible à l'annonce et en attendant la clôture (ou en sortant à perte si le deal brise),
le rendement annualisé net (= prime × P(close) − perte × P(break)) est **> 8 %** de façon robuste
dans le segment small-cap, là où la concurrence institutionnelle est réduite.

Formellement : `r_net = Σ_deals [P(close)·spread_ann + P(break)·loss_break] > 8 % ` net des frais,
où `loss_break ≈ −25 à −35 %` (retour au prix pré-annonce) et `P(break) ∈ [5–20 %]` selon l'univers.

#### Source de l'inefficience structurelle — pourquoi NON entièrement arbitrée

1. **Incertitude binaire non-prédictible.** La régulation antitrust, la clause MAC (Material Adverse
   Change), le vote actionnaire, le financement PE — ces issues sont RÉELLEMENT incertaines, pas des
   informations publiques ignorées. La prime compense un risque réel, pas un prix de marché erroné.
   Contraste net avec unlocks (#2 : date = résultat) et PEAD (#28 : surprise = info publique).

2. **Mandats de taille institutionnels.** Les fonds M&A arb de taille (Elliott $50Bn, Pentwater $5Bn)
   ne peuvent pas prendre de positions significatives sur une cible à $200M de market cap. La
   liquidité de la cible ne supporterait pas leur entrée/sortie. → Le segment <$500M EV est
   structurellement sous-couvert par les acteurs qui compriment les spreads dans les méga-deals.

3. **Durée de détention incertaine.** Capital bloqué 2–18 mois selon le scrutin réglementaire.
   Les gérants institutionnels contraints par les benchmarks ou les redemptions quarterly ne peuvent
   pas tenir. Un solo patient peut — exactement le même avantage que pour le SPAC (#27), sauf que
   le plancher ici est un deal price contractuel, pas un trust T-bill.

4. **Complexité opérationnelle du small-cap M&A.** Les small-cap deals ont moins de recherche
   sell-side, moins de couverture médiatique, moins d'attention des arb funds → le marché met plus
   de temps à "pricer" la probabilité de clôture = spread d'entrée plus large = rendement potentiel
   plus élevé.

#### Tueur le plus probable (honest kill prior)

Le programme a tué le SPAC (#27 sub-hurdle +145bps < 200bps) et l'ILS (#31 sub-hurdle t=1.51).
Le merger arb a le **même profil de mort probable** : prime réelle, comprimée par 50 ans de
concurrence institutionnelle, probablement **sous le hurdle ajusté du tail** (−30 % sur break).
Le hurdle doit couvrir : coût d'opportunité capital bloqué (T-bill 5 %) + prime de tail (-30 %
× P(break) ≈ 1.5–6 %) + illiquidité small-cap. Soit une barre ≈ 8–10 % annualisé. Les fonds
merger-arb institutionnels nettent historiquement 4–7 % annualisé (post-2010), **probablement
sous la barre** pour un solo avec coûts plus élevés. L'ère FTC 2021-2024 (break rate élevé) aggrave
le bilan récent.

#### Falsifiabilité — gates pré-enregistrés ici avant tout run

| Gate | Critère PASS | Critère KILL |
|------|-------------|--------------|
| **(A) Spread brut > hurdle** | Rendement annualisé médian IS (2010-2019) > 8 % sur univers cash+small-cap | ≤8 % → sub-hurdle, DOWNGRADE/KILL |
| **(B) t inter-deal > 2** | t-stat sur la série des rendements par deal, inter-deal (leçon carry #6 : PAS pooled-jours) | t ≤ 2 → bruit |
| **(C) OOS mûr — ère FTC (2020-2024)** | Rendement > 0 et t > 1.5 en OOS ; chute ≤30 % vs IS | Net négatif en OOS → arbitré, non-répétable |
| **(D) Drop-top-5 deals** | Retire les 5 meilleurs deals, rendement demeure positif | Meurt → 5 outliers portent tout = bruit |
| **(E) Miroir (short la cible)** | Short cible à l'annonce = rendement négatif (le côté positif est la prime de clôture, pas le momentum) | Miroir positif → le signal est du momentum, pas de l'arb |
| **(F) Ajustement tail (EV gate)** | EV explicite > 0 : `P(close)·spread − P(break)·loss_break`, P mesurés IS | EV ≤ 0 → prime mangée par la tail |
| **(G) DSR(best, N=3 filtres)** | DSR > 0.95 (N = 3 variantes : EV<200M / EV<500M / deal-type) | DSR < 0.95 → overfit |

Signal pré-enregistré : univers = annonces 8-K "entering into merger agreement" + cible US cotée +
deal all-cash (exclut stock + cash pour isoler l'arb pur) + EV < $500M (capco de la cible sur
yfinance J-30 avant annonce). Entry = prix à la clôture du jour d'annonce. Exit = deal price (close)
ou prix marché +5 jours post-annonce de termination (break).

#### Data source

| Source | Données | Accès |
|--------|---------|-------|
| SEC EDGAR EFTS | 8-K full-text search "merger agreement" / "definitive agreement" 2010-2025 | REST API gratuit (efts.sec.gov) |
| SEC EDGAR submissions | Ticker + CIK de la cible ; suivi des 8-K de closing/termination | REST API gratuit |
| Yahoo Finance / yfinance | Prix cible J-30 à J+deal, market cap pré-annonce | Python libre |

Pipeline estimé : ~250-300 lignes Python. EDGAR ingestion + classification deal type + price download
+ calcul spread IS/OOS. Durée estimée : 2-3 jours.

#### Coût d'implémentation (déploiement si GO)

Position long cible uniquement (pas de short acquéreur dans un cash deal). Levier = 0x. Rotation
lente (1-3 deals simultanés typiques, holding 2-12 mois). Frais de transaction : négligeables à
horizon deal. Risque tail : -25 à -35 % sur chaque break → sizing Kelly implicite = faible fraction
du capital (Kelly ≈ f*=(p·b-q)/b ; avec p=0.90, b=0.08, q=0.10, b_loss=0.30 → f* ≈ 0.27 brut).

---

### Résumé 3 lignes

2 pistes rejetées immédiatement en filtrage : buy-write (variant VRP piste #4, même mécanisme) et
short-interest squeeze (info publique, timing imprévisible, PEAD-adjacent). **Piste C merger arb
small-cap cash** = seule candidate qui passe les filtres : la prime de risque pour incertitude
binaire (clôture vs. breakage) n'est PAS "info publique priceable", et les mandats institutionnels
excluent le segment <$500M EV. Prior honnête = DOWNGRADE/KILL probable (sub-hurdle 8 % après
ajustement tail et ère FTC 2021-2024), mais mécanisme structurellement distinct des 31 pistes
testées — pipeline gate-kill vaut 2-3 jours de code. Prochaine étape = EDGAR EFTS ingestion.

---

### #25 — Flux forcé de fin de séance (rebalancement LETF) — Run 2026-06-25 : KILL

Première piste sous le critère **« arme structurelle neuve »** (contrepartie nommée, insensible au
prix, dont le flux mécanique pourrait dépasser le capital d'arbitrage). Thèse : un ETF à levier `L`
doit, au close, trader `Δ = AUM·r·L(L−1)` ; `L(L−1) > 0` pour tous les leviers → long et inverse
achètent du **même côté** → flux agrégé `≈ r·G` (`G = Σ AUM·L(L−1)`) qui frappe au close dans le sens
du jour → push late-day + reversal overnight, *plus fort là où `G/volume$` est grand*. Identification
= l'**interaction `G/volume$`**, pas `r` seul (momentum générique). Data gratuite (yfinance), 11
sous-jacents, 45 562 name-jours 2010-2026. **KILL net** : interaction insignifiante (t=−0.6 mûr
2023+), **dose-réponse INVERSÉE** (reversal max là où il y a le *moins* de LETF — opposé exact de la
thèse, comme le spread fantôme p3), fade overnight **net négatif** (t=−3.2) ; seul reste = rebond
post-baisse générique, sous-coût. Sous-type **#2 (arbitré/absorbé)** : sur QQQ/SOXX/SPY (G de
$100-300B = les plus liquides) le flux est entièrement absorbé. Conforme au prior textbook (Cheng-
Madhavan 2009). Détail : [`eod-flow/docs/FINDINGS.md`](../eod-flow/docs/FINDINGS.md).

---

## 2026-09-11 — Revue critique du programme (36 études) + pistes neuves

### Contexte lu avant de proposer

- RESEARCH-ROADMAP.md, FINDINGS.md, EDGE-PISTES-V2.md, ce log ; FINDINGS #1, #16, #18, #27, #28,
  #34, DEPLOIEMENT.md ; code `risk-premia-portfolio/run_voltarget.py`, `sleeves.py`.
- 36 études, 0 edge déployable ; deliverable = 1,5 × (60/40 + trend), déployé 80 WTEF / 20 DBMFE.

### Critique — 6 défauts de méthode, par enjeu décroissant

1. **Asymétrie de scrutin : l'objet qui reçoit l'argent est le moins testé en multi-régime.** Les
   kills exigent le multi-régime ; le deliverable levé (#34) n'est backtesté que sur 2006-2026 = **un
   seul régime macro** (corr actions/obligs négative sauf 2022, taux bas, surperformance US). Le
   gate C « both-halves » compare deux moitiés du même régime. Le levier 1,5× ne paie que si le 60/40
   bat son financement (T3M + 0,40) — faux sur 1966-1981 (obligs < T-bills). Jamais mesuré.

2. **Gates sous-puissants : « KILL » confond « absent » et « non prouvé ».** t = SR·√T. Sur 20 ans,
   t > 2 ⟺ SR > 0,45 ; détecter à 80 % le SR 0,42 du trend exige ~46 ans. Le gate #1 avait ~50 % de
   chances de tuer le premium que la littérature documente. Gate G « mûr 2023+ » (~3 ans) : t > 2
   exige SR > 1,15 → seul un edge extrême passe ; « ns en 2023+ » = absence de preuve, pas extinction
   (légitime quand le point estimate décroît de façon monotone, cf. #12 ; abusif quand seul le t est
   lu, cf. #35 H2 t=0,96). Test correct = différence IS/OOS significative, ou borne haute de l'IC
   sous le hurdle. Conséquence : #1, #17, #30, #31, #35 sont « premium plausible, non prouvé à cette
   taille d'échantillon » — pas le même objet qu'un no-edge (#13, orderflow), pas la même décision.

3. **#36 a tué le mauvais vol-target.** `run_voltarget.py:35` = `rp.rolling(W).std()` sur rendements
   **mensuels**, W ∈ {12..48} **mois** : une vol laggée de 1 à 4 ans est un régime de levier, pas du
   vol-targeting. La version publiée (Moreira-Muir 2017, Harvey et al. 2018) utilise la vol réalisée
   **quotidienne** sur 1-3 mois ou l'implicite. Le diagnostic de #36 lui-même (« vol laggée basse
   avant le krach → sur-levé ») désigne le correctif non testé. Le KILL ne vaut que pour le VT lent.

4. **Le « motif unifié » est devenu infalsifiable et filtre sans données.** Les 5 sous-types
   couvrent tout résultat possible (pas de signal / friction / tail / sophistiqué / clause). En
   filtrage, il rejette sans test (saisonnalité commodities, rotation sectorielle, alt-data,
   buy-write, short-interest : « les fonds le connaissent ») — asserté, pas chiffré, exactement le
   reproche fait à l'écart prop le 2026-06-25. Taux de faux négatifs du filtre jamais mesuré : le
   même raisonnement aurait rejeté SPAC (réel, t=11) et GEX (réel, t≈−16).

5. **Cadence largeur ≫ profondeur, incompatible avec la thèse V3.** ~36 études en ~80 jours,
   1-2 j chacune, données gratuites standard (yfinance, Binance, football-data). La « prime de
   saleté » postule un edge dans les pipelines trop fragiles à maintenir — aucune étude n'en a
   construit un. Données publiques + protocole court testent par construction « info publique avec
   data publique » : la conclusion « à info publique, pas d'edge » est en partie une propriété de la
   méthode.

6. **Fiscalité absente partout.** Backtests et deliverable pré-impôt. En CTO, chaque vente réalise la
   plus-value à 30 % (PFU) → pénalise tout ce qui tourne (VT, bande 75-85 %). L'enveloppe (PEA :
   17,2 % après 5 ans ; AV après 8 ans, arbitrages internes non imposés) est un écart **certain** du
   même ordre que les edges cherchés.

**Solide, à garder :** pré-enregistrement, t calendar-time (#28), lag +1 anti-bounce (#8/#27),
comparaison à vol égale (#36), refus d'abaisser un hurdle. Les faux GO démasqués (VRP, CEF, LST,
#29) sont réels.

### Pistes neuves (filtrées contre les 36 études + les rejets de ce log)

#### P1 — #37 Stress séculaire du deliverable + puissance du trend ★ recommandé

- **Question.** 1,5 × (60/40 + trend) survit-il aux régimes absents de 2006-2026 (stagflation
  1966-81 à corr actions/obligs positive et obligs < cash ; répression financière 1940s) ? Le
  premium trend est-il significatif sur un échantillon qui a la puissance ?
- **Data gratuite.** Ken French (marché US 1926+), Shiller (S&P + GS10 1871+, obligs reconstruites
  par duration), FRED TB3MS (1934+), AQR Data Library (TSMOM 58 marchés 1985+ ; vérifier si les
  séries « Century » couvrent le trend, et brut/net de coûts).
- **Gates à pré-enregistrer.** (A) maxDD à L=1,5 sur 1926→2025 > −35 % (critère de ruine #34) ;
  (B) excès du levier > 0 sur 1966-1981 ; (C) TSMOM AQR t > 2 et ΔSharpe du sleeve > 0 hors
  2006-2026.
- **Pourquoi d'abord.** Seule question du programme où une erreur coûte de l'argent réel ; attaque
  les deux points faibles (#1 sous-puissant, #34 mono-régime). ~1 j. Si A ou B FAIL → L* baisse ou le
  cœur doit inclure un actif réel → DEPLOIEMENT.md change.
- **FAIT (2026-09-11) → CONFIRMÉ + 2 caveats** ([`FINDINGS-secular.md`](../risk-premia-portfolio/docs/FINDINGS-secular.md)).
  Levier +1,76 pt/an hors fenêtre ; stagflation −0,87 pt/an ; ruine −35 % = propriété de 2006-26
  (1974 −38 %, 1929 −71 %) ; trend t = 5,4 sur 41 ans mais déclin Welch t = 3,2 (Sharpe 0 depuis 2016).

#### P2 — #38 Vol-target rapide (vol quotidienne 21-63 j ou VIX)

- Rouvre #36 sur la version publiée. Composants daily yfinance + ^VIX. Gates de #36 inchangés (vol
  égale C\*, |ΔL| coûté, 2008 inclus) + contrainte fiscale : exécutable en CTO seulement si le coût
  fiscal des ventes est inclus, sinon enveloppe AV.
- Prior : favorable sur actions/risk-parity (Harvey 2018), défavorable en moyenne cross-facteurs
  (Cederburg et al. 2020). ~0,5 j.

#### P3 — #39 Capture de dividende sous statut PEA (arme neuve = statut fiscal)

- **Arme jamais testée.** Le re-vois ne voit le statut que comme contrainte. En PEA, dividende non
  imposé ; le cours ex-date baisse de ρ·D, ρ fixé par la fiscalité du price-setter marginal
  (étrangers en retenue à la source). Si ρ < 1, acheter cum (close J−1) / vendre ex (open J) capte
  (1−ρ)·D net des frais PEA.
- **Tueur probable.** Price-setter tax-neutre (OPCVM, dealers en prêt-emprunt cum-cum) → ρ ≈ 1 ;
  frais PEA 0,1-0,5 %/ordre vs (1−ρ)·D ~ 0,3 % ; bruit overnight ~1,5 %.
- **Data.** yfinance `.PA` (dividendes + OHLC) SBF 120, 2005-2026, ~2-3 k événements → puissance
  suffisante si effet ≥ 0,1 %. Market-adjust par l'ouverture/clôture du CAC 40.
- **Gates.** (A) ρ̂ < 1, t inter-mois > 2 ; (B) net de 2 × frais PEA réalistes > 0 ; (C) 2015+ pas
  significativement inférieur (test de différence, cf. critique 2) ; (D) survit hors top-5 noms.
  Variante sur le même panel : *dividend month premium* (Hartzmark-Solomon 2013).
- Prior ~15 %. ~1 j. Clause-safe (titres UE éligibles PEA).
- **FAIT (2026-09-12) → KILL friction** ([`FINDINGS.md`](../dividend-pea/docs/FINDINGS.md)). Tueur non vu
  ici, trouvé en écrivant la SPEC : la TTF (0,40 %, overnight non exonéré, PEA compris). ρ ≈ 0,85-0,90
  réel depuis 2013, mais y ≥ 3 % net 2015+ −0,08 % ; hors TTF +0,32 % (t = 4,55) → porte = sociétés
  < 1 Md€ exonérées (#40, SPEC à écrire). DOWNGRADE mécanique invalidé : 2005-08 yfinance désaligné.
- **#40 (2026-09-12) → UNTESTABLE** ([`FINDINGS-smallcap.md`](../dividend-pea/docs/FINDINGS-smallcap.md)).
  Exonérés TTF (455 ISIN FR hors liste BOFiP 2025) : data fiable, mais le segment déployable 2015+ ne
  compte que 85 événements (< 100 pré-enregistrés), A-D non lus. ρ̂ petites 0,87-0,92 ≈ SBF 120 : pas
  de signe de capacité. Ensemble d'opportunités ~7 trades/an. Re-test à SPEC inchangée vers 2028.

#### Suite de P1 — #41 actif réel contre la stagflation (2026-09-12)

- **Or, 10 % du deliverable → ASSURANCE 1970s SEULEMENT, non ajouté**
  ([`FINDINGS-gold.md`](../risk-premia-portfolio/docs/FINDINGS-gold.md)). +1,51 pt/an réel en 1968-81,
  mais moins bien que la même part en cash dans chaque choc d'inflation post-1982 (−2,61 pts / 47 mois).
  Protection = réévaluation post-Bretton Woods. TIPS/OATi non testables en gratuit (séries 1997+).

#### P4 — Lever le mur data (décision budget)

- 4 résultats bloqués par le même mur (délistés / roll) : #32 merger-arb UNTESTABLE, SPAC Gate D,
  survivorship PEAD, trend futures back-adjusté. Un mois de data EOD avec délistés (EODHD, Norgate —
  tarifs à vérifier) les débloque tous. Conforme à la règle « exiger base payante ou kill ».

#### P5 — Short-vol conditionnel VRP × GEX (interaction de deux effets réels) — prior bas

- #4 : prime réelle (t=4,03) tuée par le tail. #18 : prédicteur de variance robuste (t≈−16) tué car
  muet sur la moyenne. Interaction jamais testée : la prime est-elle concentrée en GEX haut, le tail
  en GEX négatif ? Data déjà sur disque (DIX.csv, VIX, SVXY).
- Tueurs connus : krach en un jour depuis un régime calme (5 fév. 2018) non évitable par un filtre
  J−1 ; le risque défini rachète la partie la plus chère (puts OTM) ; ETP VIX inaccessibles au
  résident FR (PRIIPs) → options SPX/Eurex seulement. Kill cheap (~2 h).

#### Rejetées au filtre

- Arb Polymarket/Kalshi, rewards de liquidité Polymarket : Polymarket géo-bloqué en France (ANJ,
  fin 2024), Kalshi réservé aux US → sous-type 5 (clause).
- Rebal d'indices S&P/Russell : effet d'inclusion documenté comme disparu (Greenwood-Sammon 2022),
  prior < 5 %.
- OPA/retrait obligatoire France : plancher contractuel type SPAC, mais même mur délistés que #32
  → dépend de P4.

### Reco

P1 d'abord (argent réel en jeu, ~1 j), puis P3 (seule arme neuve, kill cheap). P2 si P1 passe. P4 =
décision budget de Rémi. Aucun résultat regardé avant spec : P3 exige sa SPEC pré-enregistrée avant
tout pull.

---

## 2026-09-16 — Session automatisée de scouting (tâche planifiée)

### Contexte lu avant de proposer

- RESEARCH-ROADMAP.md intégral relu (41 études, 0 edge déployable) + queue ouverte du 2026-09-11
  (P1-P5, ce log) + FINDINGS des pistes #30 (commodity-carry, DOWNGRADE DSR 0.895), #31 (ILS
  cat-bond, DOWNGRADE sub-hurdle), #32 (merger-arb, UNTESTABLE mur délistés).
- Motif unifié confirmé sans exception sur 41 études : tout edge à **information/prix public
  continu** est mangé (no-edge brut, friction, ou tail/non-répétabilité). Les 2 étangs à
  contrepartie non-optimisatrice testés (CEF, Polymarket) sont morts aussi.
- Queue déjà ouverte non actionnée : P5 (VRP×GEX interaction, prior bas, kill cheap ~2h), P4
  (décision budget data payante — bloque #30/#31/#32/PEAD/trend futures back-adjusté).
- Filtre appliqué à toute nouvelle piste avant écriture : (1) info/prix public déjà mangé ? (2)
  data accessible gratuitement ou déjà dispo aujourd'hui ?

### Pistes examinées + verdict filtre

#### Piste A — SCPI (immobilier non coté FR) : décote marché secondaire vs NAV, crise 2023-2025

- **Thèse.** Plusieurs grandes SCPI (Primonial, Corum, Sofidy…) ont révisé leur NAV −10 à −17 %
  depuis 2023 (immobilier de bureau + taux). Les demandes de retrait forment une **file d'attente**
  (délai de retrait plusieurs mois) : vendeurs structurellement forcés (besoin de liquidité, pas de
  vue sur le prix). La NAV elle-même est une **expertise immobilière** (mise à jour trimestrielle,
  sticky), pas un prix de marché continu — le prix de compensation sur le marché secondaire peut
  diverger de la NAV publiée.
- **Filtre 1 (info/prix public mangé ?) — PASSE.** Contrairement à toutes les pistes mortes du
  programme, il n'y a **pas de prix continu public** ici : la NAV est une estimation d'expert
  décalée, et le prix de compensation secondaire n'est pas un flux temps réel que des algos
  institutionnels peuvent arbitrer. Les fonds ne sont structurellement pas acheteurs sur ce marché
  (les SCPI sont un produit retail par construction — pas d'AP, pas de short possible côté
  institutionnel). Famille distincte de tout ce qui a été tué (cf. la même logique CEF #8, mais ici
  sans cotation continue du tout, contrairement au CEF listé).
- **Filtre 2 (data gratuite/déjà dispo ?) — ÉCHOUE aujourd'hui.** Pas d'API centralisée pour les
  prix d'exécution du marché secondaire ni l'historique NAV par SCPI : données éparpillées dans les
  bulletins trimestriels PDF de ~180 sociétés de gestion. ASPIM/IEIF agrègent mais l'accès complet
  est payant. Construire un panel exploitable = plusieurs jours de scraping PDF, hors budget frugal
  du jour.
- **Verdict : REJET (filtre 2) pour aujourd'hui**, mais **flag conservé** — c'est la seule famille
  structurellement neuve trouvée cette session (opacité + file d'attente forcée ≠ prix public
  continu). À traiter comme **P4-bis** : décision budget/scraping avant toute mini-spec, même
  logique que le mur data #30/#31/#32.

#### Piste B — OPRA (offre publique de rachat) small-cap FR : capture pré-offre

- **Thèse.** Rachat d'actions à prix fixe annoncé par l'émetteur lui-même ; fenêtre entre annonce et
  clôture d'offre sur des small-caps peu suivies.
- **Filtre 1 — ÉCHOUE.** Même famille que merger-arb (#32) et SPAC (#27) : événement de prix **daté
  et public** dès l'annonce, spread résiduel = prime de risque de deal-break déjà pricée par les
  mêmes acteurs (arbitrageurs de fusion). Aucun mécanisme neuf vs les 2 pistes déjà mortes/bloquées.
- **Filtre 2 — même mur.** Univers small-cap FR délistées = même problème de survivorship/données
  que #32 (UNTESTABLE, mur délistés déjà documenté).
- **Verdict : REJET direct (filtre 1 + redondance filtre 2).** Pas de spec écrite — risque de
  reproduire une étude déjà classée mur-de-données sans apporter d'arme neuve.

#### Piste C — Choix de domiciliation ETF (Irlande vs Luxembourg) pour retenue à la source

- **Thèse.** Un ETF domicilié en Irlande récupère le taux conventionnel US (15 %) sur dividendes vs
  30 % pour un domicile moins favorable ; écart mécanique en faveur du résident FR.
- **Verdict : REJET — pas un mécanisme testable par la machine gate-kill.** C'est un choix de
  produit statique (sélection du bon ETF), pas un signal répété avec un null à falsifier (ni t-stat,
  ni DSR, ni miroir long/short possibles — un seul choix, pas un trade). Même distinction que le
  programme a déjà faite entre backtest de prix (xs-momentum #13) et ledger d'EV opérationnel
  (airdrop #14) : ceci n'est ni l'un ni l'autre, c'est de l'allocation, hors périmètre du programme
  edge.

### Verdict du jour : **no candidate**

Aucune piste ne survit aux deux filtres avec une mini-spec exploitable aujourd'hui. La piste A (SCPI)
est la seule famille structurellement neuve identifiée en 42 sessions (opacité NAV + file d'attente
forcée, par opposition à tout prix public continu déjà mangé) mais elle est bloquée par le même type
de mur data que #30/#31/#32 — pas un mur définitif, un mur de **budget/scraping**. Aucune spec
falsifiable écrite tant que ce mur n'est pas levé (même règle que P4 : décision de Rémi avant tout
pull de données).

### Résumé 3 lignes

3 pistes examinées (SCPI marché secondaire, OPRA small-cap, domiciliation ETF) — 2 rejetées au
filtre 1/redondance, 1 (SCPI) bloquée au filtre 2 données. Aucune mini-spec falsifiable produite
aujourd'hui = **no candidate**, résultat valide. Seul point actionnable neuf : SCPI marché secondaire
mérite une décision budget/scraping (P4-bis), à traiter avec le mur data existant #30/#31/#32.

---

## 2026-09-20 — Session automatisée de scouting (tâche planifiée)

### Contexte lu avant de proposer

- RESEARCH-ROADMAP.md intégral (41 études, 0 edge déployable) + ce log jusqu'à la session du
  2026-09-16 (verdict **no candidate** : SCPI flaggée P4-bis mais bloquée filtre 2, OPRA et
  domiciliation ETF rejetées au filtre 1/hors-périmètre).
- Motif unifié inchangé sur 41 études : tout edge à **information/prix public continu** est mangé
  (no-edge brut, friction, ou tail/non-répétabilité). Les deux seuls signes de vie transitoires
  restent le **carry structurel** (#6, réel mais tail exchange) et l'**opacité de prix** (CEF #8,
  réel mais bid-ask bounce).
- Queue ouverte non actionnée, revue avant de proposer du neuf : **P4** (budget data payante —
  débloquerait #32 merger-arb, SPAC Gate D, survivorship PEAD, trend futures back-adjusté), **P4-bis**
  (SCPI marché secondaire, bloqué filtre 2), **P5** (interaction VRP×GEX, prior bas, kill cheap ~2h,
  data déjà sur disque `DIX.csv`/VIX/SVXY — seule piste pré-spécifiée non encore run).
- Filtre appliqué à toute piste neuve avant écriture : (1) info/prix public déjà mangé ? (2) data
  accessible gratuitement ou déjà dispo aujourd'hui ?

### Pistes examinées + verdict filtre

#### Piste A — Buyback drift : dérive post-annonce de rachat d'actions (France)

- **Mécanisme candidat.** Après l'annonce d'un programme de rachat d'actions "open market", le titre
  sur-performe en moyenne sur les 1-3 ans suivants (Ikenberry, Lakonishok & Vermaelen 1995) : signal
  managérial crédible + pression d'achat réelle mais discrétionnaire (le rythme d'exécution n'est pas
  connu à l'avance). Univers France (SBF 120) jamais testé par le programme.
- **Filtre 1 (info/prix public mangé ?) : ÉCHOUE.** L'effet est un facteur systématique documenté et
  packagé depuis 20 ans (ETF "shareholder yield" / "net share issuance" — PKW, facteurs AQR/DFA
  quality-shareholder-yield). Les fonds smart-beta répliquent ce signal à l'échelle mondiale, Europe
  incluse. Ce n'est pas une contrainte de mandat ni une opacité de prix nouvelle : c'est une variante
  directe de la piste 1 (prime documentée, compressée par la réplication systématique).
- **REJET.** Même famille que la piste 1 (trend/premia documentés) déjà tuée sous sa forme la plus
  favorable ; aucune arme structurelle neuve identifiée pour justifier un re-test régional France.

---

#### Piste B — Marchés de "bribe" de gouvernance DeFi (vote-buying veToken)

- **Mécanisme candidat.** Les détenteurs de tokens de gouvernance verrouillés (veCRV, veBAL) reçoivent
  des paiements ("bribes", via Votium/Hidden Hand) pour orienter leur vote de répartition des
  émissions vers certains pools. Le rendement total (staking + bribes) peut excéder le rendement de
  base et fluctue selon la concurrence pour les votes — mécanisme jamais testé par le programme
  (distinct de Pendle #23, qui pricait un risque actuariel, pas un marché de vote).
- **Filtre 1 (info/prix public mangé ?) : ÉCHOUE.** Ce marché est dominé depuis 2020 par des
  agrégateurs DeFi-natifs à capital important (Convex Finance TVL plusieurs milliards $, Redacted
  Cartel) dont le métier exclusif est d'accumuse le pouvoir de vote et d'arbitrer le prix du bribe par
  unité de vote. La barrière n'est pas une absence d'acteur optimisateur (comme le sont les fonds
  réglementés sur Pendle) mais une **présence dominante d'acteurs spécialisés mieux capitalisés qu'un
  solo** — structure inverse de ce qui a fait persister le carry ou l'inefficience Pendle.
- **REJET.** Contrepartie optimisatrice dominante identifiée dès le filtrage ; pas de niche solo.

---

#### Piste C (reprise de P4-bis) — SCPI marché secondaire : re-test du mur data

- Le 2026-09-16, cette piste avait passé le filtre 1 (opacité de NAV + file d'attente forcée = famille
  structurellement neuve, aucun prix continu public à arbitrer) mais avait échoué le filtre 2 par
  manque de temps pour vérifier l'existence d'une source gratuite.
- **Vérification ciblée aujourd'hui (recherche web, ~5 min) : mur CONFIRMÉ, pas levé.** Aucune API
  publique ou jeu de données bulk gratuit trouvé sur data.gouv.fr (l'API "info-financière" AMF couvre
  les émetteurs cotés, pas les SCPI). Les agrégateurs (2ndMarket, Louve Invest, ASPIM/IEIF) exposent
  des tableaux de consultation manuelle ou des simulateurs, pas de série historique téléchargeable —
  construire un panel exploitable resterait plusieurs jours de scraping PDF par société de gestion.
- **Verdict : toujours REJET filtre 2 aujourd'hui.** Statut inchangé depuis le 2026-09-16 : décision
  de budget/scraping à prendre par Rémi avant toute mini-spec (même règle que P4).

### Verdict du jour : **no candidate**

Aucune piste neuve ne survit aux deux filtres avec une mini-spec actionnable aujourd'hui. Les deux
pistes nouvelles (buyback France, bribe markets DeFi) échouent au filtre 1 pour la même raison
structurelle : un acteur optimisateur bien capitalisé (smart-beta systématique pour le buyback,
agrégateurs DeFi natifs pour les bribes) occupe déjà exactement la niche visée — contraste net avec
le carry ou Pendle, où l'acteur optimisateur était **structurellement absent**, pas juste concurrent.
La piste SCPI reste bloquée au même mur data qu'il y a 4 jours ; aucune nouvelle information ne change
sa classification P4-bis. Aucune régression : le programme ne re-teste aucune piste déjà tuée.

**Point actionnable inchangé** : **P5** (interaction VRP×GEX) demeure la seule piste pré-spécifiée,
peu coûteuse (~2h), non encore run — prior bas mais c'est la prochaine étape naturelle si Rémi veut
consommer le budget d'une session (hors scope "proposition écrite seule" d'aujourd'hui).

### Résumé 3 lignes

2 pistes neuves rejetées au filtre 1 (buyback France = variante compressée piste 1, déjà capturée par
les ETF shareholder-yield ; bribe markets DeFi = niche déjà dominée par agrégateurs natifs
sur-capitalisés, pas une absence d'acteur). SCPI (P4-bis) re-vérifiée : mur data gratuite confirmé,
statut inchangé. **No candidate** aujourd'hui — résultat valide, motif unifié tient sans exception sur
41 études ; seul reste actionnable = P5 (VRP×GEX, cheap, en attente).

---

## 2026-09-21 — Session automatisée de scouting (tâche planifiée)

### Contexte lu avant de proposer

- RESEARCH-ROADMAP.md intégral (41 études, 0 edge déployable) + ce log jusqu'à la session du
  2026-09-20 (verdict **no candidate** : buyback France et bribe markets DeFi rejetés filtre 1, SCPI
  re-vérifiée mur data toujours fermé).
- Queue ouverte non actionnée, revue avant de proposer du neuf : **P4** (budget data payante délistés,
  bloque #32/SPAC Gate D/survivorship PEAD/trend futures), **P4-bis** (SCPI, mur data confirmé deux
  fois), **P5** (interaction VRP×GEX, pré-spécifiée depuis le 2026-09-11, ~2 h, data déjà sur disque
  `DIX.csv`/VIX/SVXY — seule piste prête à courir, jamais lancée faute de budget-temps de session).
- Filtre appliqué à toute piste neuve avant écriture : (1) info/prix public déjà mangé ? (2) data
  accessible gratuitement ou déjà dispo aujourd'hui ?

### Pistes examinées + verdict filtre

#### Piste A — Décote de holding (Eurazeo, Wendel, GBL, Ackermans & van Haaren) vs NAV des participations cotées

- **Mécanisme candidat.** Ces holdings cotent structurellement sous la somme de leurs participations
  (décote 20-40 %), sans mécanisme de création/rachat façon ETF — même absence structurelle d'AP que
  le CEF (piste 8).
- **Filtre 1 (info/prix public mangé ?) : ÉCHOUE.** Contrairement au CEF (piste 8, petits fonds sous
  le radar), ces holdings sont liquides (1-8 Md€ de capitalisation), couverts par des analystes
  sell-side dédiés, et la décote est documentée depuis 30 ans comme **compensation rationnelle** du
  risque de gouvernance (contrôle familial verrouillé, primes de contrôle inaccessibles, fiscalité de
  plus-value latente au niveau holding) — pas une inefficience. Des fonds « special situations »
  européens suivent spécifiquement ce segment. C'est l'anti-value-trap (gate E de la piste 8) qui
  tuerait cette piste d'emblée : la décote est justifiée, pas une convergence à capter.
- **REJET.** Même mécanisme structurel que #8 (déjà tué), mais à une échelle de liquidité où le tueur
  « décote justifiée » domine au lieu du bounce microstructure — aucune arme neuve, verdict identique
  attendu sans lancer de run.

---

#### Piste B — Arbitrage convertibles micro-cap FR (delta-hedge vs emprunt de titre)

- **Mécanisme candidat.** Les fonds convertible-arb institutionnels ont besoin de liquidité pour
  shorter le delta ; les émissions micro-cap (<50 M€) seraient sous-couvertes.
- **Filtre 1 : AMBIGU en apparence, mais échoue en pratique.** La barrière (taille d'émission) est
  réelle, mais le mécanisme de capture (short delta) exige d'emprunter le titre sous-jacent — exactement
  le point qui a tué la piste 3 (capacité fantôme, spread réel mais rien derrière). Sur un micro-cap
  FR, le prêt-emprunt est soit indisponible soit à un coût qui dépasse la mispricing visée.
- **REJET.** Variante directe de la piste 3 déjà tuée : la même contrainte qui écarte l'institutionnel
  (illiquidité du sous-jacent) empêche aussi le solo d'exécuter la jambe de couverture.

---

#### Piste C — Décote des droits préférentiels de souscription (DPS) sur augmentations de capital small/micro-cap FR ★ CANDIDATE

- **Filtre 1 (info/prix public mangé ?) : AMBIGU — passe prudemment.** L'annonce de l'augmentation de
  capital et sa parité sont publiques (BALO/AMF), mais ce n'est pas l'objet du pari : le pari porte sur
  le **prix de marché du droit lui-même** pendant sa fenêtre de négociation (10-15 séances), qui peut
  diverger de sa valeur théorique `(cours ex-droit − prix de souscription) / parité`. Deux mécanismes
  non-prédictifs plausibles : (a) désintérêt mécanique de l'actionnariat retail dominant (vend au
  premier prix ou laisse expirer, sans lien avec une vue sur le titre), (b) contrainte OPCVM/UCITS sur
  la détention d'instruments assimilés à des dérivés de courte durée, qui limite la participation
  institutionnelle activement arbitragiste.
- **Filtre 2 (data gratuite ?) : PASSE avec effort.** Dates + paramètres d'émission via avis
  BALO/AMF (gratuit) ; cours du droit et de l'action pendant la fenêtre via Euronext historical data /
  Boursorama (gratuit, à scraper). Univers estimé ~15-30 opérations DPS/an sur small/micro-cap FR,
  2015-2026.
- **PASSE les deux filtres prudemment**, avec un doute explicite en filtre 1 tranché ci-dessous par le
  Gate de contrôle (D).

---

### Mini-spec piste C — Arbitrage DPS small/micro-cap FR

#### Hypothèse d'edge

Pendant la fenêtre de négociation d'un droit préférentiel de souscription sur une augmentation de
capital small/micro-cap FR, le prix coté du droit est en moyenne **inférieur** à sa valeur théorique.
Acheter le droit sous-évalué (et, si économiquement viable, souscrire ou revendre immédiatement après
exercice) capte l'écart net de frais.

#### Source de l'inefficience structurelle — pourquoi NON entièrement arbitrée

1. **Forced-selling comportemental, pas informationnel.** Le vendeur marginal (actionnaire retail) ne
   vend pas sur une vue de prix — il se débarrasse d'un instrument qu'il ne comprend pas ou qu'il ne
   veut pas exercer (il n'a pas le cash pour souscrire). C'est un flux mécanique proche de la famille
   « flux forcés » (piste 2) mais sans date de résultat public à anticiper : rien à « pricer en avance ».
2. **Contrainte de mandat.** Un droit de souscription est structurellement proche d'un warrant court
   terme ; certains OPCVM UCITS le classent hors univers investissable ou le liquident au plus vite
   après attribution, sans chercher le meilleur prix (contrainte de compliance, pas d'EV).
3. **Taille d'émission sous le radar des arbitragistes dédiés.** Une levée <20-30 M€ ne justifie pas la
   mise en place d'un desk spécialisé pour quelques jours de fenêtre.

#### Falsifiabilité — pourquoi ça peut mourir

- Le « discount » mesuré est un artefact de calage (mauvais cours de référence ex-droit, délai de
  détachement mal aligné) → à vérifier avant tout calcul de rendement.
- Discount réel mais **inférieur aux frais de courtage + au spread bid-ask du droit lui-même** (souvent
  très illiquide) → net ≤ 0, tueur le plus probable.
- **Capacité fantôme** (leçon piste 3) : la taille exécutable réelle sur un droit à volume quotidien
  minuscule peut être proche de zéro même si le % de discount est net positif.
- Échantillon annuel faible (15-30 opérations/an) → puissance statistique limitée, risque qu'un
  drop-top-3 tue tout le résultat (leçon piste 9/LST : t élevé sur peu d'épisodes ≠ edge).
- Si le discount est identique sur les grandes capitalisations (SG, Elior…) où des desks arb sont déjà
  actifs → ce n'est pas un effet de taille/capacité, juste un artefact de mesure (Gate D ci-dessous).

#### Data source

| Source | Données | Accès |
|--------|---------|-------|
| BALO / AMF (info-financière) | Avis d'augmentation de capital : date, prix de souscription, parité | Gratuit, API/consultation |
| Euronext historical data / Boursorama | Cours quotidien du droit (ISIN dédié) et de l'action pendant la fenêtre | Gratuit (scraping léger) |

#### Gates de décision — pré-enregistrés ici avant tout run

| Gate | Critère PASS | Critère KILL |
|------|-------------|--------------|
| **(A) Discount brut** | moyenne `(valeur théorique − prix coté)/valeur théorique > 0`, t>2, sur toute la fenêtre | brut≤0 ou t≤2 |
| **(B) Net>0** | après frais de courtage réalistes ×2 + spread bid-ask observé sur le droit (pas hypothétique) | net≤0 → frais mangent tout |
| **(C) Pas de concentration** | drop-top-3 opérations : le résultat survit | meurt → bruit d'échantillon |
| **(D) Contrôle taille** | discount significativement plus grand sur small/micro-cap que sur grandes caps à desk arb actif (SG, Elior…) | même ampleur partout → artefact de mesure, pas un effet de capacité |
| **(E) Capacité réelle** | volume $ exécutable réel sur le droit (pas le théorique) > seuil minimal | capacité fantôme (leçon piste 3) |
| **(F) DSR** | DSR(best, N=3 fenêtres d'entrée J1/J2/Jmid) > 0.95 | <0.95 → overfit |

#### Coût d'implémentation

~150-200 lignes (scraping BALO/AMF + Euronext/Boursorama). Estimation 1-2 jours. Aucun levier ; taille
de position bornée par le montant de l'émission elle-même (contrainte dure, pas juste théorique).

#### Honnêteté brutale

Prior de survie ~15-20 %. Le tueur le plus probable est un mélange de (B) et (E) : même si le discount
existe sur le papier, le droit lui-même est si peu liquide que la taille réellement exécutable est
proche de zéro — exactement le motif « capacité fantôme » qui a déjà tué la piste 3 et menacé la piste B
(convertibles, rejetée ci-dessus pour la même raison). C'est la première fois que ce motif est testé sur
un instrument dérivé de très courte durée plutôt que sur un carnet d'ordres au comptant ; s'il meurt de
la même façon, ce sera une confirmation supplémentaire du motif unifié plutôt qu'un résultat nouveau.

---

### Verdict du jour : **1 candidate produite (Piste C — DPS small/micro-cap FR)**

2 pistes rejetées en filtrage direct (décote de holding = variante liquide de #8 avec tueur "décote
justifiée" au lieu du bounce ; convertibles micro-cap = variante de la piste 3, même contrainte
d'emprunt de titre qui tue capacité institutionnelle ET solo). La piste C (DPS) est la première
proposition du programme sur un instrument dérivé de courte durée plutôt qu'une action/un fonds au
comptant — mécanisme comportemental + contrainte de mandat distincts de tout ce qui a été testé, mais
prior de survie bas (même motif de capacité fantôme attendu). Aucun run lancé aujourd'hui (hors budget
temps de la tâche) : la mini-spec est pré-enregistrée, prête à exécuter en 1-2 jours si Rémi valide.

**Backlog toujours ouvert, inchangé** : P4 (budget data payante), P4-bis (SCPI, mur confirmé), P5
(VRP×GEX, ~2h, seule piste déjà prête à courir sans nouvelle spec).

### Résumé 3 lignes

2 pistes neuves rejetées au filtre 1 (holding discount FR = variante liquide de #8, tueur "décote
justifiée" ; convertibles micro-cap = variante piste 3, capacité fantôme côté couverture). **1 candidate
produite** : arbitrage DPS small/micro-cap FR — mécanisme comportemental + contrainte de mandat neuf,
data gratuite mais à assembler, prior de survie ~15-20 % (tueur attendu = capacité fantôme, motif déjà
vu ×2). Aucun run aujourd'hui ; backlog P4/P4-bis/P5 toujours en attente d'une décision de Rémi.

---

## 2026-09-24 — Session automatisée de scouting (tâche planifiée)

### Contexte lu avant de proposer

- RESEARCH-ROADMAP.md intégral (41 études, 0 edge déployable) + ce log jusqu'à la session du
  2026-09-21 (1 candidate produite : DPS small/micro-cap FR, mini-spec pré-enregistrée, jamais lancée).
- Backlog ouvert, non actionné, revu avant de proposer du neuf : **P4** (budget data payante délistés,
  bloque #32/SPAC/PEAD/trend futures), **P4-bis** (SCPI marché secondaire, mur data gratuite confirmé
  deux fois : 09-16 et 09-20), **P5** (interaction VRP×GEX, pré-spécifiée depuis 09-11, data déjà sur
  disque, jamais lancée), **Piste C** (DPS small/micro-cap FR, spec écrite 09-21, jamais lancée).
- Filtre appliqué à toute piste neuve : (1) info/prix public déjà mangé ? (2) data accessible
  gratuitement ou déjà dispo aujourd'hui ?

### Pistes examinées + verdict filtre

#### Piste A — Dérive de fin de lock-up sur IPO actions (lock-up expiry drift)

- **Mécanisme candidat.** À l'expiration du lock-up post-IPO (~180 j), les insiders/pré-IPO investors
  peuvent vendre ; la pression d'offre anticipée crée un excès de rendement négatif autour de la date.
  Documenté (Field & Hanley 2009, Bradley et al. 2001) comme effet de flux (courbe de demande à pente
  négative), pas purement informationnel.
- **Filtre 1 (info/prix public mangé ?) : ÉCHOUE, par analogie directe avec la piste 2 (unlocks
  crypto) déjà tuée.** La date de lock-up est publique dès le prospectus d'IPO. Le short pré-expiry est
  une stratégie event-driven documentée et pratiquée depuis 20+ ans (hedge funds dédiés). La piste 2 a
  montré sur les unlocks crypto que toute la dérive a lieu **avant** la date publique et que le résiduel
  post-date est ≈ zéro — même structure d'anticipation ici, aucune raison qu'un solo capture un résidu
  que les funds event-driven laissent sur la table.
- **REJET** sans nouveau run — variante actions du mécanisme piste 2, verdict générique déjà établi.

---

#### Piste B — Seuil de capitalisation PEA-PME (5 Md€) : flux forcé réglementaire

- **Mécanisme candidat.** Le PEA-PME (enveloppe fiscale française) restreint l'éligibilité aux
  entreprises sous un seuil de taille (capitalisation/critères PME-ETI UE). Une société qui franchit le
  seuil à la hausse perdrait son éligibilité → vente forcée par les détenteurs PEA-PME, indépendante du
  prix — famille "flux forcé par mandat" (comme #35 fallen angels), jamais testée sur ce seuil précis.
- **Filtre 1 : ÉCHOUE — le mécanisme de flux forcé n'existe pas tel qu'imaginé.** Vérification de la
  règle : l'éligibilité PEA-PME est appréciée à l'**achat** ; une position déjà détenue qui franchit le
  seuil est généralement conservable (pas de vente forcée rétroactive), seul le réinvestissement de
  nouveaux versements dans ce titre serait bloqué. Sans obligation de vente, il n'y a pas de contrepartie
  insensible au prix — juste une hypothétique baisse de la demande marginale, beaucoup plus faible et
  non datée précisément. Le segment est en outre déjà surveillé par des gérants small/mid-cap dédiés
  (Amiral Gestion, Sycomore, Moneta) qui suivent ces franchissements de seuil pour leurs propres mandats.
- **REJET.** Pas de mécanisme de flux forcé daté, contrairement à l'hypothèse de départ — le filtre 1
  échoue pour une raison structurelle (règle mal identifiée), pas seulement pour cause de crowding.

---

#### Piste C — Dérive post-spin-off sur les scissions d'entreprises européennes ★ examinée en détail

- **Mécanisme candidat.** Après une scission (spin-off), l'entité détachée sous-performe/sur-performe
  selon la littérature US (Cusatis-Miles-Woolridge 1993, McConnell-Ovtchinnikov 2004) : les fonds
  indiciels qui ne peuvent pas détenir la nouvelle entité (hors indice, capitalisation trop faible,
  mandat géographique) la vendent mécaniquement dès l'attribution, indépendamment du prix. Aux US, ce
  signal est désormais packagé (Invesco S&P Spin-Off ETF, ex-CSD) → mangé. **Le sous-univers européen
  n'a, à notre connaissance, aucun véhicule indiciel dédié** — arme potentiellement encore ouverte.
- **Filtre 1 : PASSE prudemment.** Le mécanisme de flux forcé (mandat indiciel, pas timing) est réel et
  distinct des unlocks/DPS déjà traités. Pas de réplication systématique identifiée sur le segment
  européen spécifiquement.
- **Filtre 2 (data gratuite ?) : ÉCHOUE aujourd'hui — même mur que la SCPI (P4-bis).** Il n'existe pas
  de base téléchargeable gratuite des scissions européennes (dates, ratio de distribution, tickers) ;
  contrairement aux unlocks crypto (DefiLlama) ou aux fusions US (EDGAR 8-K structuré), l'information est
  dispersée dans des communiqués de presse et prospectus par émetteur, sur ~15-25 ans et ~10-20 pays. Un
  panel exploitable (même seulement 30-50 événements) demanderait plusieurs jours de recherche manuelle
  — hors budget frugal du jour, même ordre de grandeur que le mur SCPI.
- **Verdict : REJET (filtre 2) pour aujourd'hui, flag conservé** — troisième famille bloquée par le même
  type de mur (données événementielles non structurées, pas de wall définitif). À regrouper avec P4-bis
  sous une même décision budget/scraping si Rémi veut lever ce mur un jour (SCPI + spin-offs EU +
  probablement OPRA/retrait obligatoire partagent le même goulot : événements corporate FR/UE sans API
  publique structurée).

### Verdict du jour : **no candidate**

Aucune piste neuve ne produit de mini-spec actionnable aujourd'hui. Piste A tombe par analogie directe
avec un mécanisme déjà tué (pas besoin de re-tester). Piste B tombe sur une prémisse fausse (pas de
vente forcée réelle une fois vérifiée la règle — leçon : vérifier le mécanisme juridique/réglementaire
avant d'écrire un "pourquoi ça résisterait", pas après). Piste C est la plus intéressante structurellement
mais rejoint le mur data déjà identifié pour la SCPI — troisième cas qui suggère que **la frontière
restante du programme n'est plus "trouver un mécanisme neuf" mais "financer/automatiser l'accès aux
événements corporate non-US non structurés"**, un problème de données, pas de méthode.

**Observation méta (honnêteté brutale).** Cinq sessions consécutives (09-11 partiel, 09-16, 09-20, 09-21,
09-24) produisent soit "no candidate" soit un candidat à prior de survie ~15-20 % jamais lancé. L'espace
des mécanismes structurels accessibles à data gratuite semble proche de l'épuisement. Le backlog actionnable
(P5 VRP×GEX : ~2h, données déjà sur disque ; Piste C DPS 09-21 : spec prête) contient plus de valeur
immédiate que continuer à générer des pistes candidates non lancées — recommandation : la prochaine session
devrait **lancer un run du backlog existant** plutôt qu'ajouter une 5ᵉ piste non testée à la pile, sauf
décision contraire de Rémi.

**Backlog inchangé, désormais à 5 éléments non actionnés** : P4 (budget data payante), P4-bis (SCPI, mur
confirmé ×2), P5 (VRP×GEX, prête, ~2h), Piste C/DPS (09-21, prête, 1-2 j), flag spin-offs EU (nouveau,
même mur que P4-bis).

### Résumé 3 lignes

3 pistes neuves examinées : lock-up expiry actions (rejet par analogie directe avec unlocks #2 déjà
tué), seuil PEA-PME (rejet — vérification de la règle infirme l'hypothèse de vente forcée), spin-off
drift européen (mécanisme structurel plausible mais mur data identique à la SCPI). **No candidate**
aujourd'hui — résultat valide. Recommandation explicite : le backlog existant (P5, DPS) contient plus
de valeur qu'une nouvelle piste non lancée ; prioriser son exécution avant d'élargir encore la liste.

---

## 2026-10-02 — Session automatisée de scouting (tâche planifiée)

### Contexte lu avant de proposer

- RESEARCH-ROADMAP.md (41 études, 0 edge déployable ; dernière = #41 or) + ce log jusqu'au 2026-09-24
  (no candidate ; reco méta : exécuter le backlog plutôt qu'empiler des pistes). Depuis, seule
  c2c-dispersion a bougé (tâche 0 réfutée, arrêtée avant collecte). P5 (VRP×GEX) et DPS jamais lancés.
- Grep du repo : aucune étude ni piste antérieure sur les futures de dividende ou les autocalls.
- Filtres : (1) info/prix public déjà mangé ? (2) data gratuite ou déjà disponible ?

### Pistes examinées + verdict filtre

#### Piste A — Flux de couverture des autocalls près des barrières (Euro Stoxx 50)

- **Mécanisme.** Les émetteurs d'autocalls sont courts gamma près des barrières knock-in. Leur
  couverture amplifie les mouvements autour de niveaux d'indice connus.
- **Filtre 1 : ÉCHOUE.** Même famille que GEX #18 : la position des dealers prédit la variance, pas la
  moyenne. Les barrières agrégées ne sont pas publiques en gratuit (filtre 2 KO aussi).
- **REJET.**

#### Piste B — Chasse aux barrières knock-out des turbos retail

- **Mécanisme.** Les KO de turbos se regroupent sur des niveaux ronds. L'émetteur (B-book) aurait
  intérêt à pousser le sous-jacent à travers.
- **Filtre 1 : ÉCHOUE.** Stop-clustering documenté (Osler 2003), terrain HFT. Contrepartie = émetteur
  à marge maison (motif #16, axe prop clos).
- **Filtre 2 : ÉCHOUE.** Pas de distribution historique gratuite des encours par barrière.
- **REJET.**

#### Piste C — Prime de couverture sur les futures de dividende Euro Stoxx 50 (FEXD) ★ CANDIDATE

- **Mécanisme.** Les banques qui émettent des autocalls (produit retail européen et asiatique) sont
  structurellement longues des dividendes futurs : le produit ne verse pas les dividendes au porteur.
  Elles couvrent ce risque en **vendant** des futures de dividende. Ce flux suit les volumes d'émission
  retail (demande de coupons), pas une vue sur le prix. La littérature (van Binsbergen-Brandt-Koijen
  2012 ; Kragt-de Jong-Driessen, *The dividend term structure*) relie la décote des dividendes longs à
  cette pression de couverture.
- **Filtre 1 : PASSE prudemment.** Le prix est public et continu : le filtre devrait tuer. Mais la
  contrepartie n'optimise pas le prix, c'est un hedger contraint, comme dans le carry (#6) et la VRP
  (#4/#12). Ces deux pistes avaient une prime **réelle**, tuée par le tail ou la faiblesse. Le tueur
  attendu est donc connu : prime ≈ risque (bêta actions + coupes de dividende en crise : 2009, et 2020
  avec la recommandation BCE aux banques). L'arbitrage est freiné par la charge en capital d'un risque
  de flux actions sur 2-5 ans (FRTB). Le motif « prix public mangé » cible l'edge informationnel ; ici
  le pari porte sur une prime de transfert de risque.
- **Filtre 2 : PASSE sous condition.** Investing.com publie l'historique quotidien des contrats
  génériques FEXD (c1, c2…) avec téléchargement. Le téléchargement exige un compte gratuit que Rémi
  doit créer (je n'en crée pas). Barchart ne montre que 3 mois. Le prix de règlement final de chaque
  contrat de décembre = dividendes réalisés : pas besoin d'autre source pour le réalisé.
- **Accès.** Eurex, 100 € par point d'indice (~16 k€ de notionnel par contrat à ~160 points),
  disponible chez IBKR pour un résident FR. Hors PEA : CTO uniquement, flat tax sur les gains.

### Mini-spec piste C — Futures de dividende Euro Stoxx 50

#### Hypothèse d'edge

Un long roulé sur le contrat FEXD de décembre à horizon 2-3 ans, tenu jusqu'à sa première année, gagne
un excès de rendement positif. Cet excès n'est **pas** expliqué par le bêta Euro Stoxx 50. Il améliore
le deliverable #22 levé 1,5× quand on l'ajoute comme sleeve.

#### Source de l'inefficience — pourquoi elle ne serait pas arbitrée

1. Vendeur structurel insensible au prix : couverture des émetteurs d'autocalls, volume dicté par la
   demande retail de coupons.
2. Acheteurs naturels rares : pensions et hedge funds paient une charge en capital pour un risque
   actions de plusieurs années, avec un tail de crise concentré.
3. Taille solo négligeable devant l'open interest : pas de capacité fantôme à craindre (contrairement
   à la piste 3 et au DPS du 09-21).

#### Pourquoi ça peut mourir (tueurs pré-déclarés)

- La prime n'est que du bêta actions (gate B).
- Le tail 2020 détruit le profil levé : le contrat 2020 a perdu une large part de sa valeur (chiffre à
  mesurer, pas supposé).
- La prime a été arbitrée depuis sa publication (~2012) : déclin McLean-Pontiff (gate E).
- Puissance : FEXD existe depuis 2008, donc ~17 échéances indépendantes seulement.

#### Data

| Source | Données | Accès |
|--------|---------|-------|
| Investing.com | FEXD génériques c1-c4 quotidiens, 2008+ | Gratuit, compte requis (Rémi) |
| yfinance `^STOXX50E` | Indice prix pour le bêta | Gratuit |
| €STR / EONIA (BCE SDW) | Rendement du collatéral | Gratuit |
| Disque | Série du deliverable #22 | Déjà disponible |

Point d'attention : vérifier le raccord des génériques au roll de décembre (saut de contrat, pas un
rendement). Reconstruire le rendement contrat par contrat avant toute stat.

#### Gates pré-enregistrés (avant tout téléchargement)

| Gate | PASS | KILL |
|------|------|------|
| (A) Prime brute | excès mensuel moyen du long roulé > 0, t NW (lag 12) > 2 sur 2008-2026 | t ≤ 2 |
| (B) Alpha | alpha vs SX5E (régression mensuelle, NW lag 3) > 0 et t > 2 | alpha ≤ 0 ou t ≤ 2 = bêta déguisé |
| (C) Tail au levier tenable | 1× notionnel collatéralisé : maxDD > −35 % (critère de ruine #34), 2009 et 2020 inclus | maxDD ≤ −35 % |
| (D) Valeur en sleeve | 10 % dans le deliverable #22 (1,5×) : ΔSharpe ≥ +0,05 et maxDD dégradé de moins de 2 pts | ΔSharpe < 0,05 |
| (E) Déclin | 2016+ pas significativement inférieur à 2008-2015 (Welch t < 2) | déclin significatif = arbitrée |
| (F) Overfit | DSR > 0,95 avec N = 3 tenors testés (Z+1, Z+2, Z+3) | DSR < 0,95 |
| Coûts | IBKR + Eurex ~3 €/contrat/côté, spread 0,3 point (30 €) par roll, déduits en net | — |

Pas de miroir long/short : c'est une prime, le short perd par construction. Le contrôle équivalent est
(B) + (E). Si moins de 15 échéances indépendantes exploitables : **UNTESTABLE**, pas de lecture.

#### Coût d'implémentation

~0,5 jour. Un script ~120 lignes : chargement CSV Investing, reconstruction par contrat, stats, sleeve.
Bloqué uniquement par la création du compte Investing par Rémi.

#### Honnêteté brutale

Prior de survie ~15 %. Tueur le plus probable : (B), la prime est du bêta actions au sortir de 2009 et
2020. Sinon (C)/(D) : le tail 2020 annule le gain en sleeve. C'est le troisième test du motif « prime
réelle de hedger tuée par le tail » (après #6 et #4/#12). Un KILL ne serait pas un résultat neuf, mais
il coûte une demi-journée et ferme proprement une famille jamais touchée.

### Verdict du jour : **1 candidate (Piste C — FEXD)**

Backlog jamais lancé : P4, P4-bis (SCPI), P5 (VRP×GEX, ~2 h), DPS (1-2 j), spin-offs UE, FEXD (~0,5 j).
Ordre conseillé, par coût croissant : P5, puis FEXD, puis DPS. La reco du 09-24 tient : exécuter avant
d'ajouter.

### Résumé 3 lignes

2 pistes rejetées : barrières autocall (famille GEX #18, variance sans moyenne) et chasse aux KO turbos
(B-book, pas de data). 1 candidate : prime de couverture des futures de dividende FEXD, data gratuite
via Investing (compte à créer par Rémi), prior ~15 %, tueur attendu = bêta ou tail 2020. Backlog à 6
éléments jamais lancés : exécuter P5 puis FEXD avant toute nouvelle piste.

---

## 2026-10-05 — Session automatisée de scouting (tâche planifiée)

### Contexte lu avant de proposer

- RESEARCH-ROADMAP.md (41 études, 0 edge déployable) + ce log jusqu'au 2026-10-02 (candidate FEXD ;
  backlog P4, P4-bis, P5, DPS, spin-offs UE, FEXD jamais lancé).
- Grep du repo : aucune étude ni piste antérieure sur les déclarations de dirigeants (MAR art. 19),
  le dividende en actions (scrip) ou l'effet tax-loss de janvier.
- Filtres : (1) info/prix public déjà mangé ? (2) data gratuite ou déjà disponible ?

### Pistes examinées + verdict filtre

#### Piste A — Arbitrage du dividende en actions (option scrip, décote légale jusqu'à 10 %)

- **Mécanisme.** Plusieurs sociétés FR proposent le dividende en actions à un prix d'émission décoté.
  L'actionnaire choisit cash ou actions en fin de fenêtre : il détient une option gratuite.
- **Filtre 1 : ÉCHEC.** Les desks de dividend arbitrage connaissent ce trade. La décote se reflète
  dans le coût de prêt-emprunt du titre autour de la date ex. Le retail ne peut pas prêter ses titres.
- **Ordre de grandeur.** Gain ≈ rendement × décote ≈ 4 % × 8 % ≈ 0,3 % de la position par événement,
  avec un risque marché d'environ un mois. Quelques événements par an seulement.
- **Filtre 2 : ÉCHEC partiel.** yfinance ne donne pas les termes de l'option. Il faut les lire à la
  main dans les communiqués. **REJET.** C'est une optimisation de rendement pour un porteur existant,
  pas un edge.

#### Piste B — Effet tax-loss / janvier sur les small caps FR

- **Filtre 1 : ÉCHEC.** L'effet est documenté depuis les années 1970 et décroît. Il appartient à la
  famille calendrier (#5, KILL). En PEA, la motivation fiscale n'existe pas. Prior < 5 %. **REJET.**

#### Piste C — Achats « opportunistes » des dirigeants (déclarations AMF, MAR art. 19) ★ CANDIDATE

- **Filtre 1 : SURVIT SOUS CONDITION.** L'information est publique : c'est le motif unifié qui a tué
  #2. Mais la piste a deux protections structurelles, déclarées ci-dessous. La littérature
  (Cohen-Malloy-Pomorski 2012 aux US, études UK) montre que l'essentiel de la réaction arrive dès J0-J1.
  Un drift résiduel est donc l'hypothèse fragile, à tester comme telle.
- **Filtre 2 : SURVIT.** Les déclarations AMF (BDIF) sont gratuites mais publiées en PDF semi-structuré.
  Les prix viennent de yfinance `.PA`, avec le risque connu des titres délistés (voir gate F).

### Mini-spec piste C — Achats opportunistes des dirigeants, Euronext Paris + Growth

#### Hypothèse d'edge

Un achat de dirigeant **non routinier** (pas d'achat le même mois calendaire les 3 années
précédentes, définition CMP 2012), ou un **cluster** (≥ 2 dirigeants distincts en 30 jours), prédit un
rendement anormal positif sur J+1 → J+63. J0 = date de **publication AMF**, pas la date de transaction.
Le drift doit survivre aux coûts réels des small/micro-caps.

#### Source de l'inefficience — pourquoi elle ne serait pas arbitrée

1. **Capacité.** Le signal se concentre dans les micro-caps. Un fonds ne peut pas y placer de taille.
   Un compte à 5 k€ par ligne le peut. C'est le même argument que #3, à vérifier contre le même tueur
   (profondeur fantôme).
2. **Saleté de la donnée.** Les déclarations sont des PDF hétérogènes. Il faut les parser, dédupliquer
   et séparer achats, exercices d'options et attributions gratuites. C'est la « prime de saleté » V3.
3. **Mandat.** Beaucoup de fonds small-cap ont un plancher de liquidité ou de capitalisation qui exclut
   Euronext Growth.

Aucun de ces trois points n'est garanti. Si le drift existe aussi sur le SBF 120, la capacité n'est pas
la raison, et le tueur « priced-in » de #2 redevient le suspect principal.

#### Pourquoi ça peut mourir (tueurs pré-déclarés)

- **T1 priced-in.** La réaction est entièrement à J0. Le CAR de J+1 à J+63 vaut ≈ 0.
- **T2 coûts.** Le spread des micro-caps (Corwin-Schultz sur OHLC quotidien) mange le drift.
- **T3 survivant.** Les faillites manquantes dans yfinance gonflent le CAR. Ce biais va **dans le sens
  de l'hypothèse**, donc il faut le traiter d'abord.
- **T4 bêta small-cap.** Le « drift » n'est que la prime de taille de la période. Le benchmark taille
  doit l'absorber.

#### Data

| Source | Contenu | Coût |
|---|---|---|
| AMF BDIF (déclarations des dirigeants) | Date de publication, déclarant, nature, prix, volume | Gratuit, scraping + parsing PDF |
| yfinance `.PA` | OHLC + volume quotidien, 2012-2025 | Gratuit, trous sur les délistés |
| Indices CAC Small / CAC Mid & Small | Benchmark taille | Gratuit (Euronext / Investing) |

#### Gates pré-enregistrés (avant tout téléchargement de prix)

- **F (data, en premier).** ≥ 95 % des événements ont un prix sur la fenêtre complète, ou le délisting est
  expliqué (OPA = prix d'offre, faillite = −100 %). Sinon : **UNTESTABLE**, branche P4 (base payante).
- **A (signal).** CAR(J+1, J+63) des achats opportunistes vs benchmark taille ajusté du bêta > 0,
  t > 3 (erreurs clusterisées par mois, seuil Harvey-Liu-Zhu), n ≥ 300 événements.
- **B (miroir et placebo).** Les achats routiniers donnent un CAR ≈ 0 (|t| < 1,5). Des dates placebo
  tirées dans les mêmes titres donnent ≈ 0. Si les routiniers « marchent » autant, c'est de la prime de
  taille (T4) : KILL.
- **C (net).** CAR net de l'aller-retour estimé (Corwin-Schultz, plancher 1 %) > 0, t > 2. Position
  ≤ 10 % de l'ADV sur 5 jours, à 5 k€ par ligne.
- **D (régime).** Le résultat est > 0 sur 2012-2018 **et** sur 2019-2025. Pas de dépendance à une seule
  année (retirer la meilleure ne doit pas faire passer t sous 2).
- **E (DSR).** Portefeuille calendaire mensuel, N essais = 6 (2 signaux × 3 horizons 21/63/126 j,
  déclarés ici). DSR ≥ 0,95.
- **Lecture honnête.** Le trade est long-only et loge en PEA (pas d'impôt, pas de financement). Il reste
  exposé au bêta small-cap, sans couverture possible en PEA. Rapporter le Sharpe couvert (short CAC hors
  PEA) **et** non couvert. Comparer ce dernier au deliverable #22 levé 1,5×, pas au cash.

#### Coût d'implémentation

- Scraper + parser BDIF : 1-1,5 j (le plus gros risque technique est le parsing des PDF antérieurs à 2017).
- Event study + gates : ~0,5 j, en réutilisant `overfit_audit.py`.
- Main-d'œuvre en live : quelques ordres par mois, flux AMF automatisable. Le coût opérationnel est faible
  et respecte la contrainte main-d'œuvre.

#### Honnêteté brutale

Prior ~10 %. Le tueur le plus probable est T1 : marché efficient sur une info publique, comme pour #2.
T2 vient ensuite : la profondeur fantôme des micro-caps, comme pour #3. Cette piste combine deux motifs
déjà tueurs. Elle n'est retenue que parce qu'elle est la seule du jour à avoir un mécanisme nommé et une
data gratuite. Elle ne passe pas devant le backlog.

### Verdict du jour : **1 candidate faible (Piste C — achats de dirigeants AMF)**

Backlog jamais lancé : P4, P4-bis, P5 (~2 h), DPS (1-2 j), spin-offs UE, FEXD (~0,5 j), dirigeants AMF
(~2 j). L'ordre conseillé reste P5, puis FEXD, puis DPS. Le gate F des dirigeants peut servir de test
à faible coût du mur data délistés FR, partagé avec DPS.

### Résumé 3 lignes

2 pistes rejetées : arbitrage scrip (desks de dividend arb, ~0,3 %/événement) et tax-loss janvier
(famille calendrier #5). 1 candidate faible : achats opportunistes de dirigeants via les déclarations
AMF, prior ~10 %, tueurs attendus = priced-in J0 et spread micro-cap. Backlog à 7 éléments : exécuter avant d'ajouter.



---

## 2026-10-06 — Session automatisée de scouting (tâche planifiée)

Lu avant de proposer : `RESEARCH-ROADMAP.md` (40 études, 0 edge), les rejets et candidates des logs du 2026-09-16 → 10-05. Le backlog contient déjà 7 pistes spécifiées jamais lancées (P4, P4-bis, P5, DPS, spin-offs UE, FEXD, dirigeants AMF). Ajouter une 8e spec sans en exécuter une n'apporte rien.

### Pistes examinées + verdict filtre

#### Piste A — Sous-évaluation des IPO françaises via l'offre à prix ouvert (OPO) retail
- Mécanisme : décote d'introduction (littérature : +5-10 % au J1 sur Euronext), part retail de l'allocation.
- Filtre 1 (info publique mangée) : **échoue en partie**. Le prospectus, la fourchette et le carnet sont publics, et les banques fixent le prix pour garantir un J1 positif. Surtout, l'allocation retail est **rationnée** (ordres A1/A2 servis partiellement), donc l'avantage de capacité du solo est neutralisé : on ne choisit pas la taille.
- Filtre 2 (data) : liste des IPO Euronext gratuite, mais **~8-15 IPO/an**, soit N < 100 sur 10 ans. Même cas que #40 : sous-puissant avant tout run.
- **REJET** (N trop petit + capacité d'allocation non contrôlée). Aucun run possible à la barre t > 3.

#### Piste B — Écart de prix OPA / retrait obligatoire sur small caps FR (stub vs prix d'offre)
- Mécanisme : après une OPA, le titre cote sous le prix de l'offre ou du retrait obligatoire ; capter l'écart jusqu'au règlement.
- Filtre 1 : même famille que le merger-arb #32. Les arbitragistes event-driven fixent déjà l'écart, et le risque résiduel (offre non réussie) est le prix de l'écart.
- Filtre 2 : **mur data délistés** (feedback gelé). L'issue gagnante = délisting, et yfinance/Stooq perdent la jambe gagnante : biais directionnel dans le sens de l'hypothèse.
- **REJET** (filtre 2, identique à #32 UNTESTABLE).

#### Piste C — Réaction aux relèvements du taux du Livret A / LEP (formule officielle, publiée à l'avance)
- Mécanisme : taux fixé par formule publique (inflation + €STR), annoncé aux dates connues ; position sur les flux bancaires ou obligataires.
- Filtre 1 : **échoue net**. La formule est publique et mécanique, les prévisions de taux sont consensuelles. Aucune contrepartie contrainte nommée, et aucun instrument coté qui encaisse l'écart.
- **REJET** (filtre 1, aucun mécanisme structurel).

### Verdict du jour : **no candidate**

Aucune des trois pistes ne passe à la fois « info/prix public déjà mangé ? » et « data gratuite exploitable ». Piste A tombe sur N (comme #40), B sur le mur délistés (comme #32), C sur l'absence de mécanisme. Je n'invente pas de spec.

Recommandation honnête : cesser de générer des pistes tant que le backlog n'est pas consommé. Ordre conseillé inchangé : P5 (~2 h), puis FEXD (~0,5 j), puis DPS, puis dirigeants AMF. Le gate F des dirigeants AMF sert aussi de test à faible coût du mur data délistés FR.

### Résumé 3 lignes

3 pistes rejetées : IPO/OPO FR (N < 100, allocation rationnée), OPA/retrait obligatoire (mur data délistés, = #32), taux Livret A (formule publique, aucun mécanisme).
Verdict : no candidate. Rien à committer, aucun run lancé.
Backlog de 7 pistes à exécuter avant d'en ajouter une nouvelle (P5 d'abord).


---

## 2026-10-09 — Session automatisée de scouting (tâche planifiée)

Lu avant de proposer : `RESEARCH-ROADMAP.md` (40 études, 0 edge) et les logs du 2026-06-23 → 10-06. Backlog toujours à 7 pistes spécifiées jamais lancées (P4, P4-bis, P5, DPS, spin-offs UE, FEXD, dirigeants AMF). Aucune des pistes ci-dessous n'apparaît dans les logs. Seule l'inclusion d'indices S&P/Russell y figure, comme effet disparu.

### Pistes examinées + verdict filtre

#### Piste A — Prime A/H (actions chinoises doubles cotées) : tilt long des H décotées vs leur A
- Mécanisme : contrôles de capitaux et non-fongibilité. La même société cote 20-40 % plus cher en A (Shanghai/Shenzhen) qu'en H (Hong Kong), et aucun arbitragiste ne peut convertir. L'inefficience est donc structurelle, pas une simple lenteur.
- Filtre 1 : **échoue en partie**. Le mécanisme est réel, mais la jambe qui capte l'écart est un short sur l'A. Il est indisponible ou très restreint pour un particulier via Stock Connect. Il reste un tilt long-seul sur les H décotées, soit un **facteur value + bêta Chine** sans couverture. La prime est un indice Hang Seng publié depuis 2007, donc connue.
- Filtre 2 : yfinance couvre les paires survivantes. Les H délistées ou privatisées disparaissent (**mur délistés**, biais directionnel favorable à l'hypothèse). Univers liquide ~40-60 paires : sous-puissant sur coupe transversale mensuelle.
- **REJET** (filtre 1 : jambe courte inaccessible, résidu = value déguisé ; filtre 2 : mur délistés).

#### Piste B — Spread actions de préférence / ordinaires (VW, Henkel, Fresenius, Schaeffler, Porsche SE)
- Mécanisme : le spread reflète la prime de contrôle (droit de vote) et reste non arbitrable faute de conversion.
- Filtre 1 : **échoue**. Les desks de stat arb tradent ces paires depuis 20 ans. Le spread est une compensation rationnelle (gouvernance, événements de contrôle), comme la décote de holding déjà rejetée le 2026-09-21. N ≈ 15 paires.
- **REJET** (filtre 1 + N trop petit).

#### Piste C — Réforme TSE Japon (P/B < 1) : engagement de gouvernance des small caps
- Mécanisme : pression réglementaire publique pour relever le ROE et racheter des titres.
- Filtre 1 : **échoue net**. Réforme annoncée en 2023, très médiatisée, flux étrangers massifs et déjà tradés. Le catalyseur a été consommé. Univers ~600 titres, data JPX gratuite mais le signal est public depuis trois ans.
- **REJET** (filtre 1, priced-in).

### Verdict du jour : **no candidate**

Aucune piste ne passe les deux filtres. A est la seule avec un vrai mécanisme structurel. Elle meurt sur l'accessibilité de la jambe qui capte l'écart, et le résidu long-seul est un facteur value, pas un edge neuf. Je n'invente pas de spec.

Recommandation inchangée : arrêter de générer des pistes jusqu'à consommation du backlog (P5 ~2 h, puis FEXD ~0,5 j, puis DPS, puis dirigeants AMF). Rien committé, aucun run lancé.

### Résumé 3 lignes

3 pistes rejetées : prime A/H (jambe short inaccessible + mur délistés), pref/ord (stat arb existant, N≈15), réforme TSE Japon (priced-in).
Verdict : no candidate. Rien committé, aucun run lancé.
Backlog de 7 pistes à exécuter avant d'en ajouter (P5 d'abord).

---

## 2026-10-10 — Session automatisée de scouting (tâche planifiée)

Lu avant de proposer : `RESEARCH-ROADMAP.md` (41 études, 0 edge ; piste 2 « flux forcés », bilan #25 LETF) et les logs du 2026-06-23 → 10-09. Backlog toujours à 7 pistes spécifiées jamais lancées. Vérifié par grep : ni le rebalancement des pensions, ni l'enchère de clôture Euronext, ni le réinvestissement des dividendes n'apparaissent dans les logs. Le « Goldman roll » est déjà rejeté (2026-06-23) et la famille calendrier est KILL (#5).

### Pistes examinées + verdict filtre

#### Piste A — Rebalancement de fin de mois/trimestre des fonds de pension (actions vs obligations) ★ candidate faible
- Mécanisme : les pensions et fonds diversifiés ont des poids cibles (ex. 60/40). Quand les actions battent les obligations sur le mois ou le trimestre, ils **doivent** vendre des actions et acheter des obligations autour de la date de fin de période. Référence : Harvey, Mazzoleni, Melone (2025), « The Unintended Consequences of Rebalancing » ; Etula et al. (2020) sur la liquidité de fin de mois.
- Filtre 1 (info publique mangée ?) : **passe de justesse**. Le signal (écart de performance actions − obligations depuis le début de la période) est public et trivial à calculer. Mais la contrepartie est nommée, insensible au prix et contrainte par mandat. Surtout, sa taille (~20 000 Md$ d'actifs de pension) est d'un autre ordre que le `G` des LETF de #25 (100-300 Md$). C'est le seul cas du programme où « flux > capital d'arbitrage » est plausible a priori. Contre : la publication date de 2025, donc la décroissance post-publication (McLean-Pontiff) a commencé, et #25 a montré qu'un flux public et daté est absorbé sur les instruments les plus liquides.
- Filtre 2 (data) : **passe**. SPY/IEF/TLT ajustés via yfinance depuis 2003 (ou ES=F/ZN=F), ~280 fins de mois, ~90 fins de trimestre. Aucun mur délistés (indices).
- **SURVIT aux deux filtres, prior faible (≤ 10 %).**

#### Piste B — Déséquilibre de l'enchère de clôture Euronext (fixing 17h30) les jours de rebalancement d'indices
- Mécanisme : les trackers CAC/Stoxx/MSCI doivent exécuter au fixing ; fournir la liquidité contre le déséquilibre publié.
- Filtre 1 : **échoue**. Même famille que #25 (flux public et daté, absorbé). Les teneurs de marché voient le déséquilibre indicatif en temps réel, un solo non.
- Filtre 2 : **échoue**. Les données de déséquilibre d'enchère et l'intraday Euronext sont payantes.
- **REJET** (filtres 1 et 2).

#### Piste C — Pression d'achat par réinvestissement des dividendes (Hartzmark-Solomon 2022, « Predictable Price Pressure »)
- Mécanisme : les jours de gros versements de dividendes, les investisseurs réinvestissent, ce qui pousse le marché agrégé.
- Filtre 1 : **échoue**. Le calendrier des versements est public, l'effet est publié depuis 2022 et porte sur l'indice agrégé, l'instrument le plus liquide (même sous-type #2 absorbé que #25). L'effet est de quelques bp par jour, sous le coût d'un aller-retour quotidien levé.
- **REJET** (filtre 1).

### Mini-spec piste A — Flux de rebalancement des pensions (pré-enregistrée avant tout téléchargement)

#### Hypothèse d'edge
Sur les 3 derniers jours de bourse d'un mois, le rendement de la jambe actions − obligations (duration-ajustée) est **négativement** relié à l'écart de performance actions − obligations cumulé depuis le début du mois (signal `s`). Mesure principale : fin de mois. Fin de trimestre rapportée en secondaire (effet attendu plus fort, N plus petit).

#### Source de l'inefficience — pourquoi elle ne serait pas arbitrée
1. Contrepartie contrainte : mandats à poids cibles et rebalancement calendaire, imposés par la gouvernance des fonds et non par un calcul de prix.
2. Taille : le flux potentiel (dizaines de Md$ par fin de mois selon le papier) dépasse le capital que les desks consacrent à ce trade risqué en bêta.
3. Risque porté par l'arbitragiste : la jambe est directionnelle sur 3 jours (bêta actions/taux), donc chère en capital pour un desk à VaR limitée. C'est la seule raison qui ne dépend pas de la lenteur des autres.

#### Pourquoi ça peut mourir (tueurs pré-déclarés)
- Absorption, comme #25 : ES et ZN sont les contrats les plus liquides du monde.
- Front-running des banques déjà documenté : l'effet migre **avant** la fenêtre (dérive pré-fenêtre, comme les unlocks).
- Publication 2025 : l'échantillon post-publication est trop court pour juger ; un PASS ne vaut que sur l'historique.
- Un PASS pourrait n'être qu'un reversal court terme générique actions/obligations. Le contrôle exige que l'effet soit concentré en fin de période et absent les autres jours.

#### Data
yfinance : SPY, IEF (ou TLT) ajustés 2003-2026. Option de contrôle : ES=F/ZN=F. Coût nul. €STR/Fed funds (FRED) pour le coût de financement.

#### Gates pré-enregistrés
| Gate | PASS | KILL |
|------|------|------|
| G1 signal | pente de `r(fenêtre)` sur `s`, Newey-West, t ≤ −3 | t > −3 |
| G2 miroir | même signe et significatif (t ≤ −2) séparément pour `s > 0` et `s < 0` | un seul côté porte l'effet |
| G3 placebo | même régression sur les 3 jours d'une fenêtre milieu de mois : t > −1,5 | effet aussi fort hors fin de mois (= reversal générique) |
| G4 dose-réponse | rendement monotone sur les quintiles de `|s|` | non monotone ou inversée (comme #25) |
| G5 régime | même signe sur 2003-2014 et 2015-2026, chaque t ≤ −2 | une sous-période porte tout |
| G6 DSR | DSR > 0,95 avec N essais = 4 (fenêtres 1/3/5 jours + variante trimestre) | DSR ≤ 0,95 |
| G7 net levé | stratégie vol-ciblée 10 %, coûts ETF 2 bp/jambe/trade + financement €STR sur la jambe courte : Sharpe net > 0,3 ET corrélation < 0,3 avec le deliverable | Sharpe net ≤ 0,3 |

Règle : un seul KILL sur G1-G4 ou G7 = KILL de la piste. G5 et G6 en échec = DOWNGRADE (non déployable).

#### Coût d'implémentation
~1 h : un script de ~150 lignes, data gratuite, aucun compte requis pour le test. Le déploiement réel exigerait des futures (IBKR, fork déjà ouvert) ou des ETF avec short, ~12 trades/an × 2 jambes, quasi nul en temps humain (contrainte main-d'œuvre respectée).

#### Honnêteté brutale
Prior ≤ 10 %. C'est la même famille « flux forcé daté » que les unlocks (priced-in) et #25 (absorbé). La seule différence défendable est l'ordre de grandeur du flux et le risque bêta porté par l'arbitragiste. Un KILL confirmerait le motif sur l'actif le plus gros du monde, ce qui fermerait la famille « flux forcés » de façon définitive. C'est une info utile, mais pas neuve. Elle passe devant le backlog uniquement parce qu'elle coûte moins cher (~1 h vs 2 h pour P5).

### Verdict du jour : **1 candidate faible (Piste A — rebalancement des pensions)**

B et C rejetées (flux daté absorbé, data payante pour B). A survit aux deux filtres grâce à la taille de la contrepartie et au coût en capital du trade pour les desks. Prior ≤ 10 %. Rien committé, aucun run lancé.

### Résumé 3 lignes

3 pistes examinées : enchère de clôture Euronext (data payante + absorbé), réinvestissement des dividendes (publié, absorbé), rebalancement des pensions (survit).
Verdict : 1 candidate faible (prior ≤ 10 %), gates G1-G7 pré-enregistrés, test ~1 h en data gratuite.
Rien committé, aucun run lancé ; à arbitrer contre le backlog de 7 pistes (P5 d'abord).

---

## 2026-10-12 — Session automatisée de scouting (tâche planifiée)

Lu avant de proposer : `RESEARCH-ROADMAP.md` (41 études, 0 edge) et les logs du 2026-09-16 → 10-10. Le backlog compte maintenant 8 pistes spécifiées jamais lancées (P4, P4-bis, P5, DPS, spin-offs UE, FEXD, dirigeants AMF, rebalancement des pensions). Vérifié par grep : ni le cycle des adjudications du Trésor US, ni l'extension de duration des indices obligataires n'apparaissent dans les logs. Le Goldman roll est déjà rejeté (2026-06-23) et l'inclusion d'indices actions est notée comme effet disparu.

### Pistes examinées + verdict filtre

#### Piste A — Cycle des adjudications du Trésor US (Lou, Yan, Zhang 2013, RFS, « Anticipated and Repeated Shocks in Liquid Markets ») ★ candidate faible
- Mécanisme : avant chaque adjudication de coupons, les primary dealers doivent absorber l'offre nouvelle avec un bilan limité. Les taux montent dans les jours qui précèdent (concession), puis le prix récupère après le règlement. Le calendrier est public des semaines à l'avance.
- Filtre 1 (info publique mangée ?) : **passe de justesse**. Le calendrier est public et le papier date de 2013. Mais ce que capte le trade n'est pas une information : c'est la rémunération du stockage d'inventaire. Le capital d'arbitrage qui pourrait l'écraser est le bilan des dealers. Depuis 2014, le ratio de levier SLR rend ce bilan cher, ce qui est une contrainte réglementaire et non une lenteur. Contre : c'est le marché le plus liquide du monde, et la famille « flux daté » est morte deux fois (unlocks, #25).
- Filtre 2 (data) : **passe**. Taux FRED (DGS10, DGS30) et ETF IEF/TLT via yfinance, gratuits. Historique des adjudications (date, taille, part des primary dealers) gratuit via l'API TreasuryDirect / Fiscal Data. Aucun mur délistés. Accès à l'API à vérifier au premier appel (non testé aujourd'hui).
- Atout propre : le deliverable détient déjà une jambe Treasury futures (#22 levé 1,5×). Le déploiement serait un **overlay de timing** sur une jambe existante (moduler le poids autour des adjudications), sans short nouveau ni compte nouveau.
- **SURVIT aux deux filtres, prior faible (≤ 15 %).**

#### Piste B — Extension de duration de fin de mois des indices obligataires (Bloomberg US Aggregate)
- Mécanisme : à chaque fin de mois, l'indice intègre les nouvelles émissions et sa duration s'allonge. Les fonds passifs obligataires doivent alors acheter du long.
- Filtre 1 : **échoue**. Le flux est connu à l'avance au jour près, publié par l'indexeur, et tradé par chaque desk taux depuis des décennies. C'est le sous-type #2 « flux daté absorbé » de #25. De plus, il chevauche presque entièrement la fenêtre de la piste « rebalancement des pensions » du 2026-10-10. Il ne serait pas identifiable séparément.
- **REJET** (filtre 1 + confondu avec une spec existante).

#### Piste C — Repondération annuelle des indices matières premières (BCOM / S&P GSCI, 6e-10e jour ouvré de janvier)
- Mécanisme : les fonds indiciels matières premières rebalancent leurs poids une fois par an, sur une fenêtre publiée.
- Filtre 1 : **échoue**. C'est la même famille que le Goldman roll déjà rejeté : fenêtre publique, poids cibles publiés à l'automne, front-running documenté.
- Filtre 2 : **échoue**. Un événement par an et par contrat donne N ≈ 25 par matière première sur 25 ans. C'est sous-puissant, comme #40.
- **REJET** (filtres 1 et 2).

### Mini-spec piste A — Concession des adjudications du Trésor US (pré-enregistrée avant tout téléchargement)

#### Hypothèse d'edge
Sur les adjudications de coupons 10 ans et 30 ans (émissions nouvelles et réouvertures), le rendement excédentaire de la jambe duration (IEF ou ZN, TLT ou ZB) est **négatif** sur la fenêtre [t−5, t−1] avant l'adjudication et **positif** sur [t, t+3] après. Mesure principale : 10 ans, environ 12 adjudications par an, soit N ≈ 400 sur 1990-2026 via les taux FRED, et ≈ 280 sur 2003-2026 via IEF.

#### Source de l'inefficience — pourquoi elle ne serait pas arbitrée
1. Contrepartie contrainte : les primary dealers sont tenus de soumissionner. Ils absorbent l'offre que la demande finale ne prend pas, quel que soit le prix.
2. Capital d'arbitrage rationné : stocker de la duration avant l'adjudication consomme du bilan. Depuis le SLR (2014), ce bilan a un coût réglementaire explicite. La concession est son prix.
3. Le trade est directionnel sur la duration pendant 5 jours. Il est donc coûteux en VaR pour un desk, mais quasi gratuit pour un overlay sur une jambe obligataire déjà détenue. C'est le seul argument qui ne repose pas sur la lenteur des autres.

#### Tueurs pré-déclarés
- Absorption, comme #25 : le marché est le plus liquide du monde, et l'effet publié en 2013 a eu 13 ans pour décroître.
- Confusion avec les autres chocs : FOMC, chiffres d'emploi et CPI tombent souvent dans les mêmes fenêtres. Contrôle : exclure les fenêtres qui contiennent un FOMC ou un NFP, et rapporter les deux versions.
- Chevauchement des tenors : 2, 3, 5 et 7 ans tombent dans les mêmes semaines. Le test isole donc le 10 ans et le 30 ans, et rapporte le reste en secondaire.
- Un PASS sur 1990-2013 seul ne vaut rien. Le gate de régime l'exige sur la période post-publication.

#### Data
FRED : DGS10, DGS30, DTB3 (financement), dates FOMC. yfinance : IEF, TLT ajustés (2002+) ; option ZN=F/ZB=F. TreasuryDirect / Fiscal Data : dates d'adjudication, montant offert, part allouée aux primary dealers. Coût nul.

#### Gates pré-enregistrés
| Gate | PASS | KILL |
|------|------|------|
| G1 concession | rendement excédentaire moyen de [t−5, t−1] vs jours hors fenêtre, Newey-West, t ≤ −3 | t > −3 |
| G2 miroir | rebond post-adjudication [t, t+3] de signe opposé, t ≥ 2 ; et G1 tenu séparément sur 10 ans et sur 30 ans (t ≤ −2 chacun) | une seule jambe ou un seul tenor porte l'effet |
| G3 placebo | 1 000 jeux de fausses dates, même jour de semaine et même mois : G1 réel sous le 1er percentile | G1 réel dans la distribution placebo |
| G4 dose-réponse (test du mécanisme) | concession monotone sur les terciles de part allouée aux primary dealers (ou de taille d'adjudication / encours) | plate ou inversée |
| G5 régime | même signe sur 1990-2013 et 2014-2026 (post-SLR, post-publication), t ≤ −2 sur 2014-2026 | 2014-2026 non significatif |
| G6 DSR | DSR > 0,95 avec N essais = 6 (fenêtres 3/5/7 jours × avec ou sans exclusion FOMC/NFP) | DSR ≤ 0,95 |
| G7 net levé | overlay sur la jambe Treasury du deliverable : poids −50 % sur [t−5, t−1], +50 % sur [t, t+3], vol-ciblé, coûts 1 bp/trade sur futures + financement DTB3. Gain de Sharpe du deliverable > +0,05 ET Sharpe de l'overlay seul > 0,3 | gain ≤ +0,05 |

Règle : un seul KILL sur G1-G4 ou G7 = KILL de la piste. G5 ou G6 en échec = DOWNGRADE (non déployable).

#### Coût d'implémentation
~1,5 h. Le script réutilise la structure de la piste « pensions » du 2026-10-10 (mêmes ETF, même financement, même Newey-West). Il ajoute un chargeur d'adjudications. Les deux pistes peuvent tourner dans un même run, ce qui fait baisser le coût marginal à ~45 min. Déploiement : ~24 ajustements de poids par an sur des futures déjà détenus, quasi nul en temps humain (contrainte main-d'œuvre respectée).

#### Honnêteté brutale
Prior ≤ 15 %. C'est la troisième piste « flux forcé daté » ; les deux premières sont mortes (priced-in, absorbée). Deux choses la distinguent : la contrepartie rationnée par une règle de bilan, et le fait qu'un overlay ne paie pas le coût de capital qui protège l'effet. G4 est le gate le plus informatif : s'il échoue, le mécanisme invoqué est faux, même si G1 passe. Sur le levier : l'overlay module une jambe déjà levée 1,5×, donc G7 se lit sur le deliverable levé et financé, pas sur un Sharpe brut. L'ordre de grandeur de la concession rapporté par le papier n'a pas été relu aujourd'hui ; il faut le relire avant le run pour fixer l'attente.

### Verdict du jour : **1 candidate faible (Piste A — adjudications du Trésor US)**

B rejetée (flux daté absorbé, confondu avec la piste « pensions »). C rejetée (famille Goldman roll, N ≈ 25). A survit aux deux filtres. Le mécanisme est un bilan rationné par une règle, et l'implémentation est un overlay sur une jambe déjà détenue. Prior ≤ 15 %. Rien committé, aucun run lancé.

Recommandation : ne pas l'ajouter comme 9e spec isolée. La lancer **dans le même run** que la piste « pensions » (même data, même script). Un double KILL fermerait la famille « flux forcés » sur les deux plus gros marchés du monde, pour ~2 h au total.

### Résumé 3 lignes

3 pistes examinées : extension de duration des indices obligataires (absorbée, confondue avec « pensions »), repondération BCOM/GSCI (= Goldman roll, N ≈ 25), adjudications du Trésor US (survit).
Verdict : 1 candidate faible (prior ≤ 15 %), gates G1-G7 pré-enregistrés, dont G4 qui teste le mécanisme ; overlay sur la jambe Treasury du deliverable.
Rien committé, aucun run lancé ; à lancer avec la piste « pensions » dans un même run de ~2 h.

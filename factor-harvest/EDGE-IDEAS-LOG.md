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


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
3. **Piste 10** (récréatif) — le pari conceptuel : change l'étang pour de vrai. Honnêteté d'avance : la vig tue probablement le net sur books classiques.
4. **Pistes 9, 11** — opportunistes (9 = tail à la carry ; 11 = bolt-on cheap).

**Prior honnête.** Après 7 kills à motif serré, proba qu'une piste neuve donne un edge déployable =
basse. Mais 8 et 10 attaquent un étang *structurellement différent*, pas une nouvelle canne dans
l'eau morte. C'est la seule façon de ne pas refaire les 7 mêmes kills.

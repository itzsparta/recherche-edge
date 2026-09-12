# FINDINGS — index global de la chasse à l'edge

**Index pur. Zéro duplication.** Chaque ligne pointe vers le FINDINGS canonique qui
vit à côté de son code. Source de vérité = les fichiers liés ; ce document ne fait
que les recenser. Synthèse narrative complète = [`RESEARCH-ROADMAP.md`](RESEARCH-ROADMAP.md).

**Bilan : 25 études (24 chasses + 1 construction), 0 edge déployable.** Motif unifié —
*à information/prix public, un solo sans latence/infra/capital n'a pas d'edge récoltable* ;
et même l'edge **opérationnel** (airdrop, hors prix/info) échoue au seuil de labeur +
survivorship ; et **changer la contrepartie** (CEF, Polymarket, books sportifs) ne sauve
pas (0/3). Raffinement piste 15 (V3 LP) : le premier **edge agrégé réel** (frais > LVR,
payoff non-directionnel) existe — mais **capté par le participant sophistiqué** (LP
actif/JIT), pas déployable solo. La mort se déplace de *« pas d'edge »* vers *« edge capté
par le sharp »*. **Aboutissement = la construction META** : empaqueter le seul survivant
(trend) en portefeuille = **KEEP-2-SLEEVE-FAIBLE** — trend sur 60/40 est une **assurance-
crise conditionnelle** (coupe ~½ du drawdown 2008/2022, dilue en bull calme), pas un alpha ;
empiler le carry **dilue** (orthogonal au trend mais corrélé +0.41 au cœur).
**Réouverture « arme structurelle neuve » (#25, flux forcé LETF) = KILL** : le flux de
rebalancement des ETF à levier est réel mais **absorbé** sur les gros sous-jacents (QQQ/SOXX/
SPY) — dose-réponse *inversée*, fade overnight net négatif (#2). La famille « flux forcé »
reste mangée par la liquidité là où elle est grosse.

## Pré-reframe (edge prédictif)

| Étude | Verdict | Tueur | Fichier |
|---|---|---|---|
| orderflow level-edge | KILL | no-edge brut, DSR(N=50)=0.008 | [`orderflow-bot/docs/FINDINGS.md`](orderflow-bot/docs/FINDINGS.md) |
| meme-coin pump.fun | KILL | no-edge réel Dune, t=−35, −28 %/trade | [`bots/meme-coin-solana/FINDINGS.md`](bots/meme-coin-solana/FINDINGS.md) |

## V1 — edge structurel (capacité / flux forcé)

| Piste | Étang | Verdict | Tueur | Fichier |
|---|---|---|---|---|
| 1 — primes de risque | premium réel | KILL standalone | trop faible (t=1.87) ; sleeve +0.12 seul deliverable | [`factor-harvest/docs/FINDINGS.md`](factor-harvest/docs/FINDINGS.md) |
| 2 — flux forcés (unlocks) | non-contraint vs forcé | KILL | priced-in (dérive avant date publique, ≈0 après) | [`forced-flows/docs/FINDINGS-unlocks.md`](forced-flows/docs/FINDINGS-unlocks.md) |
| 3 — niche capacité | taille fonds | KILL | spread fantôme (persistant mais ~1 k$ profondeur) | [`capacity-niche/docs/FINDINGS-niche.md`](capacity-niche/docs/FINDINGS-niche.md) |
| 18 — dealer gamma (GEX) | hedging forcé | KILL-tradable | prédit la VARIANCE (corr −0.26 robuste) pas la MOYENNE ; vol-forecast réel, zéro alpha de rendement | [`gex-gamma/docs/FINDINGS.md`](gex-gamma/docs/FINDINGS.md) |
| 25 — flux forcé EOD (LETF) | rebalancement levier | KILL | absorbé sur gros sous-jacents : interaction G/vol$ t=−0.6 (mûr), **dose-réponse inversée**, fade overnight net −3.2σ (#2) | [`eod-flow/docs/FINDINGS.md`](eod-flow/docs/FINDINGS.md) |

## V2 — prime d'assurance / calendrier / carry

| Piste | Verdict | Tueur | Fichier |
|---|---|---|---|
| 4 — VRP | DOWNGRADE (faux GO) | tail catastrophique (SVXY −95 %), Sharpe aveugle au skew | [`vol-risk-premium/docs/FINDINGS.md`](vol-risk-premium/docs/FINDINGS.md) |
| 5a — overnight | DOWNGRADE | prime réelle mangée par le turnover quotidien | [`calendar-premium/docs/FINDINGS-overnight.md`](calendar-premium/docs/FINDINGS-overnight.md) |
| 5b — pré-FOMC | KILL | priced-in post-2015 (+2.3 bps, t=0.20, −93 %) | [`calendar-premium/docs/FINDINGS-fomc.md`](calendar-premium/docs/FINDINGS-fomc.md) |
| 6 — carry crypto-funding | GO Phase-1 → KILL-FORWARD Phase-2 | OOS 24m +3.8 % < hurdle 8 % ; break-even default exchange 3.6 % < gate 5 % | [`carry/docs/FINDINGS-phase2.md`](carry/docs/FINDINGS-phase2.md) |
| 7 — RV BTC/ETH | KILL | non-stationnaire IS+OOS (marche aléatoire, pas de niveau) | [`relative-value/docs/FINDINGS-rv.md`](relative-value/docs/FINDINGS-rv.md) |
| 12 — VRP crypto (defined-risk) | KILL | prime fat = artefact early-market ; compressée au niveau actions en marché mûr (2023+ BTC +5.2 pts t=1.88 ns) | [`vol-risk-premium/docs/FINDINGS-crypto.md`](vol-risk-premium/docs/FINDINGS-crypto.md) |
| 17 — FX carry G10 (sleeve) | KILL | prime insignifiante (t=0.99, DSR 0.754) noyée par la décennie ZLB 2009-21 ; orthogonale au trend (corr +0.01) mais sans prime propre = pas un sleeve | [`fx-carry/docs/FINDINGS.md`](fx-carry/docs/FINDINGS.md) |

## V2 — « changer l'étang » (contrepartie non-optimisatrice) : 0/3

| Piste | Verdict | Tueur | Fichier |
|---|---|---|---|
| 8 — CEF discount | KILL (faux GO t=7.13) | bid-ask bounce non-capturable ; lag +1m inverse l'alpha | [`cef-discount/docs/FINDINGS-cef.md`](cef-discount/docs/FINDINGS-cef.md) |
| 10 — favorite-longshot Polymarket | KILL | biais INVERSÉ (longshots sous-cotés) ; foule arbitrée/efficiente | [`prediction-markets/docs/FINDINGS-pm.md`](prediction-markets/docs/FINDINGS-pm.md) |
| 16 — biais books sportifs | KILL | biais FL réel mais < vig sharp ; seul +EV (CLV soft +2.37 %) inencaissable (books bannissent) | [`sportsbook-bias/docs/FINDINGS.md`](sportsbook-bias/docs/FINDINGS.md) |

## V3 — alpha opérationnel (hors prix/info, moat sybil)

| Piste | Verdict | Tueur | Fichier |
|---|---|---|---|
| 14 — airdrop farming (EV-ledger) | KILL | plafond best-case 8.4 €/h < labeur ; 53 % du $ sur 2 jackpots ; base-rate EV négative | [`airdrop-ev/docs/FINDINGS.md`](airdrop-ev/docs/FINDINGS.md) |

## V3 — payoff non-directionnel (cashflow vs adverse-selection)

| Piste | Verdict | Tueur | Fichier |
|---|---|---|---|
| 15 — Uniswap V3 LP (net de LVR) | **DOWNGRADE** | gate A PASS (frais > LVR markout, MMR naïf falsifié, robuste) mais agrégé capté par LP actifs/JIT ; solo passif : gas mainnet > edge | [`univ3-lvr/docs/FINDINGS.md`](univ3-lvr/docs/FINDINGS.md) |

## V3 — DeFi complex yield (prime de smart-contract)

| Piste | Verdict | Tueur | Fichier |
|---|---|---|---|
| 19/#23 — Pendle PT spread | KILL | Gate A PASS (prime brute +3.7 % médiane, marché mûr) mais Gate B : prime **priced-in** là où assurable (PT Ethena edge −1.3/−2.3 % vs cover Nexus live 3.4 %) et **inassurable** là où grasse (msUSD/USDai +4-6 %, 0 cover depeg) — efficience actuarielle bipolaire, 0 survivant à 200 bps | [`pendle/docs/FINDINGS.md`](pendle/docs/FINDINGS.md) |

## Opportunistes (bolt-on)

| Piste | Verdict | Tueur | Fichier |
|---|---|---|---|
| 9 — LST convergence (stETH/ETH) | KILL | edge one-off pré-Shapella, n=1 régime ; pinné post-redemption | [`lst-convergence/docs/FINDINGS-lst.md`](lst-convergence/docs/FINDINGS-lst.md) |
| 11 — funding cross-sectionnel | KILL | brut +52 %/an réel → net −20.6 % (turnover 8h ≈72 %/an) | [`funding-xs/docs/FINDINGS-xs.md`](funding-xs/docs/FINDINGS-xs.md) |
| 13 — momentum cross-sectionnel crypto | KILL | brut ns (t=0.84) ; artefact 2021, mûr 2023+ net −19 %/an ; DSR 0.660 | [`xs-momentum/docs/FINDINGS.md`](xs-momentum/docs/FINDINGS.md) |

## META — construction (le deliverable, pas un edge)

| Étude | Verdict | Contenu | Fichier |
|---|---|---|---|
| 22 — portefeuille risk-premia | **KEEP-2-SLEEVE-FAIBLE** | combine les sleeves réels sous poids pré-committés (inverse-vol + fixes, zéro opt in-sample). 3-sleeve FAIL (carry dilue : orthogonal au trend mais corr +0.41 au cœur = risk-on). Deliverable = 60/40 + trend = **assurance-crise** (2008 −9.9% vs −16.7%, 2022 −10.1% vs −16.4%) mais incrément régime-dépendant (+0.06 full ; dilue post-2009 sans 2008). DSR absolu ≠ incrément sur le cœur | [`risk-premia-portfolio/docs/FINDINGS.md`](risk-premia-portfolio/docs/FINDINGS.md) |
| 22b — META v2 (remplacer FX-carry) | **KEEP-FAIBLE = inchangé** | remplace le FX-carry diluant par les 2 primes les plus orthogonales au cœur (carry_energy #30 corr −0.105, ils #31 +0.106). Hypothèse « vrai-ortho ajoute l'incrément » **réfutée** : (M1) FAIL, les neufs DILUENT encore (RP4 +0.61 < RP2 +0.84 < cœur +0.87), incrément −0.14. Cause ≠ v1 : pas la corr (décorrélés) mais Sharpe propre trop faible (carry_energy −0.20, ils +0.38) → **orthogonalité nécessaire mais non suffisante, faut prime propre +**. Crisis-alpha 2022 fort (fixe −1.5% vs −16.4%) mais 2008 INTESTABLE (ils dès 2013). Deliverable 60/40+trend inchangé | [`risk-premia-portfolio/docs/FINDINGS.md`](risk-premia-portfolio/docs/FINDINGS.md) |
| 34 — deliverable levé | **EXTENSION-LEVIER** (L\*=1,5) | levier constant 1,5× financé T3M+0,40 : +2,7 pts/an, maxDD −29 % ; A-D PASS dont both-halves (mais même régime, cf. #37) | [`risk-premia-portfolio/docs/FINDINGS-lever.md`](risk-premia-portfolio/docs/FINDINGS-lever.md) |
| 36 — vol-target du deliverable | **KILL artefact** | domination du diag #34 = fenêtre sans 2008 ; à vol égale ΔSharpe < 0 sur W 12-48 m. Ne vaut que pour le VT **lent** (vol mensuelle) | [`risk-premia-portfolio/docs/FINDINGS-voltarget.md`](risk-premia-portfolio/docs/FINDINGS-voltarget.md) |
| 37 — stress séculaire | **CONFIRMÉ + 2 caveats** | levier paie hors fenêtre (+1,76 pt/an 1926-2006) ; stagflation 1966-81 −0,87 pt/an ; ruine −35 % = propriété de 2006-26 (1974 : −38 %, 1929 : −71 %) ; trend t=5,4 sur 41 ans mais déclin significatif (Sharpe 0,00 depuis 2016). Errata : Sharpe du programme = rendement total | [`risk-premia-portfolio/docs/FINDINGS-secular.md`](risk-premia-portfolio/docs/FINDINGS-secular.md) |

**Leçon meta** : la diversification n'est un free-lunch que si le sleeve ajouté est
orthogonal au **CŒUR**, pas seulement aux autres sleeves. Le carry (orthogonal au trend,
corrélé au 60/40) n'ajoute rien. Et un Sharpe absolu significatif (DSR 1.000 sur un combo
70 % obligs/actions) **ne teste pas** si le sleeve bat le cœur — seul l'incrément compte.

## Objectif prop firm (révisé 2026-06-25) — méta-gate

| Étude | Verdict | Tueur | Fichier |
|---|---|---|---|
| 24 — méta-gate prop (ledger d'EV + barrière) | **KILL** | **loterie** : sans edge médiane = −fee (moyenne portée par queue chanceuse 10 %, motif #14) ; même avec trend 0.42 la médiane reste −fee (P(net>0) 23 % < 50 %) ; Topstep trailing/consistance ≈ $0. Robuste au coût. Convexité réelle dans la moyenne mais lottery-shaped | [`prop-firm-gate/docs/FINDINGS.md`](prop-firm-gate/docs/FINDINGS.md) |

Le pivot d'objectif (« valider un compte prop firm ») ne lève pas le constat no-edge : il le
**re-emballe en loterie à marge maison**. Le challenge est un wrapper de payoff dont la médiane est
−fee, et le seul edge réel (sleeve trend, diversifié 0.42 — donc *optimiste* en mono-compte) ne
pousse pas la médiane positive. Gradient #16 chiffré : la convexité exploitable (refund + skim du
compte financé) vit dans les règles que les firmes retirent (trailing-DD, consistance).

## V4 — clause-safe / anomalies publiées / répétabilité (#25-#33 + re-creusage)

| Étude | Verdict | Tueur | Fichier |
|---|---|---|---|
| 25 — flux LETF fin de séance | **KILL** | flux réel et mécanique, empreinte nulle (interaction t=−0.30, dose-réponse **inversée**), fade overnight net t=−3.20 | [`eod-flow/docs/FINDINGS.md`](eod-flow/docs/FINDINGS.md) |
| 26 — prop répété (buffer-harvest live) | **KILL pré-live** | **tenaille** : la config +EV est interdite verbatim (FTMO « one-sided bets », « account rolling »), la config autorisée est −EV (#24) ; racine B-book partagée → aucun screener ; **règle permanente : clause-safe ∧ +EV requis AVANT toute heure** | [`prop-firm-gate/docs/FINDINGS-repeated.md`](prop-firm-gate/docs/FINDINGS-repeated.md) |
| 27 — arbitrage SPAC-trust | **KILL hurdle** | discount-vers-trust **réel, robuste, clause-safe** (t inter-noms +11 à +15, pas un bounce) mais excès **+85-145 bps < hurdle 200 bps** — compressé sous la barre | [`spac-trust/docs/FINDINGS.md`](spac-trust/docs/FINDINGS.md) |
| 28 — PEAD | **KILL** | l'anomalie la plus publiée du factor-zoo **absente de l'univers liquide** : spread +0,00 %, t=+0,01 sur 58 917 événements 8-K (S&P 500+400, 2004-26) | [`pead/docs/FINDINGS.md`](pead/docs/FINDINGS.md) |
| 29 — Univ3 LP sur L2 (ph.1→2.5) | **GO→KILL** | phase 2 ne trouve aucun tueur simulable, phase 2.5 mesure : **fees/LVR 0.90-0.94 à TOUTES concentrations** ; le net positif résiduel = funding carry = #6 dominé | [`univ3-l2/docs/FINDINGS-phase2.5.md`](univ3-l2/docs/FINDINGS-phase2.5.md) |
| 30 — carry commodités (énergie) | **DOWNGRADE** | carry symétrique falsifié ; résidu long-backwardation réel + orthogonal mais DSR<0.95, décay 2009-19, narrow ; sleeve +0.04 sub-barre → non promu | [`commodity-carry/docs/FINDINGS.md`](commodity-carry/docs/FINDINGS.md) |
| 31 — prime ILS / cat-bond | **DOWNGRADE** | prime réelle, **meilleure orthogonalité du programme** (corr SPY +0.10) mais excès +2.56 % < 3 % (t=1.51), SRRIX ~0, tout le positif = hard-market post-2022 ; skew −2.95 dans la queue | [`ils-catbond/docs/FINDINGS.md`](ils-catbond/docs/FINDINGS.md) |
| 32 — merger-arb small-cap cash | **UNTESTABLE** | yfinance sert 0/10 cibles délistées → **survivorship directionnel** : la jambe gagnante (deals clos) disparaît du panel gratuit | [`factor-harvest/merger-arb/docs/FINDINGS.md`](factor-harvest/merger-arb/docs/FINDINGS.md) |
| 33 — free-rolls à payout réel (+ crypto) | **KILL d'axe** | cash = montants marketing ; matériel = crédit/ticket non-cash ; gros pools interdits au résident FR (ESMA) ; variance de tournoi dissipée ; crypto : **le prix EST un mini-compte prop**. Objectif payout fermé sur ses 3 branches (#24, #26, #33) | [`prop-firm-gate/docs/FINDINGS-freeroll.md`](prop-firm-gate/docs/FINDINGS-freeroll.md) |
| 39 — capture de dividende sous statut PEA | **KILL friction** (DOWNGRADE mécanique, override défavorable) | ρ ≈ 0,85-0,90 réel depuis 2013 (le statut PEA capte ~10-15 % du dividende le jour ex) mais **la TTF 0,40 % le reprend** : y ≥ 3 % net 2015+ −0,08 % (hors TTF +0,32 %, t=4,55) ; 2005-08 yfinance désaligné (G0 poolé l'a masqué) | [`dividend-pea/docs/FINDINGS.md`](dividend-pea/docs/FINDINGS.md) |
| 11-v2 — funding XS lissé 7j (re-creusage) | **KILL** | le mur de frais v1 **se dissout** (72→3.25 %/an, brut retenu +38.8 %) mais révèle une **assurance-crash crypto** one-sided (short −10.9 %/an), concentrée (t=1.58 sans top-2), médiane +1.27 %, en compression (12 mo −4.3 %), non clause-safe FR (perps) | [`funding-xs/docs/FINDINGS-xs-v2.md`](funding-xs/docs/FINDINGS-xs-v2.md) |

## Les cinq sous-types de mort

1. **No-edge brut** — orderflow, meme-coin, RV BTC/ETH, XS-momentum (brut ns t=0.84). Pas même de signal.
2. **Brut réel mangé par la friction** — funding-XS (turnover 8h), niche capacity,
   CEF (bounce). L'edge ≈ son coût d'extraction.
3. **Brut réel mangé par le tail / non-répétabilité** — carry (default exchange),
   LST (pré-redemption n=1), VRP actions (tail SVXY), VRP crypto (prime fat = early-market
   2021-22, compressée au niveau actions en marché mûr), **Pendle complex yield #23** (prime
   réelle ≤ coût d'assurance live Nexus là où assurable ; inassurable là où grasse). La prime ≈
   le risque, ou un seul régime. Cas Pendle = le plus net : le prix du risque est **lu sur un
   marché d'assurance actuariel**, pas estimé.
4. **Edge agrégé réel, capté par le participant sophistiqué** — V3 LP #15 (frais > LVR au
   niveau pool, mais récolté par les LP actifs/JIT ; solo passif tué par le gas). Même forme
   que CEF #8 (bounce capté par le plus rapide) et books sportifs #16 (+EV au book qui bannit).
   L'edge existe ; l'efficience est dans **qui** le capte, pas dans son absence.
5. **Edge réel interdit par la contrepartie qui contrôle les règles** — prop répété #26 (la
   config +EV est nommément interdite, la config autorisée est −EV), free-rolls #33 (pools
   matériels fermés au résident FR ; prix crypto = mini-compte prop), perps #11-v2 (assurance
   réelle, accès non clause-safe FR). La clause bat l'edge : le mur n'est plus le marché mais
   **le contrat/le régulateur**.

## Le re-vois (2026-07-02) : carte de couverture et frontières

Question posée après 34 verdicts : « aucun edge trouvable nulle part ? ». Audit de couverture —
le programme ne prouve pas un théorème universel, il prouve un théorème **conditionnel** :

> Sous {solo, données gratuites, zéro infra, marchés publics liquides, résident FR, clause-safe},
> aucun edge récoltable n'a survécu, et les morts se rangent exhaustivement dans les 5 mécanismes
> ci-dessus.

**Où l'edge EXISTE — démontré par le programme lui-même, de l'autre côté d'une contrainte :**

| Contrainte relâchée | Preuve interne que l'edge y vit | Coût d'entrée |
|---|---|---|
| **Infra/latence** | le bounce CEF (#8), le JIT-LP (#15) et le MEV sont récoltés — par d'autres | devenir le sophistiqué (emploi/statut) |
| **Data payante** | #32 untestable en gratuit ; l'alt-data entière hors périmètre | budget data (Norgate, terminaux) |
| **Capital + patience** | les primes sub-hurdle sont RÉELLES (#27 +85-145 bps, #6 +3.8 %, #30, #31) — trop maigres pour transformer un petit compte, honnêtes sur du capital | épargne ; c'est le deliverable #22 (60/40+trend) |
| **Statut/juridiction** | #16 (le book bannit les gagnants), #33 (pools fermés ESMA), #11-v2 (perps non clause-safe FR) | pro/expat — hors de question à court terme |

**Classes non-testées restantes, avec prior honnête :**
- **MEV / liquidations on-chain** : accessible sans statut, data Dune gratuite — mais gagné en
  gas-auction par des searchers à infra (sous-type 4 quasi-certain). Prior <5 %, info marginale
  ≈ 0. Pas d'étude #34 recommandée.
- **Poker / jeux de skill** : edge réel possible mais c'est un **job à variance** (~seuil 15 €/h
  aux micro-limites), pas un edge de marché. Hors périmètre.
- **Marchés SANS ticker** (enchères, liquidations physiques, immobilier décoté) : le seul étang
  où l'information ne circule structurellement pas — asymétrie locale réelle, non-backtestable,
  demande heures + capital + présence. C'est de l'entrepreneuriat, pas du trading.

**Conclusion du re-vois** : rien d'oublié dans le périmètre. La sortie n'est pas une 35ᵉ étude —
c'est **relâcher une contrainte** : (a) capital lent sur les primes réelles (#22), (b) devenir le
sophistiqué — le pipeline de 34 verdicts pré-enregistrés EST le dossier de candidature, (c) les
marchés sans ticker, hors programme.

## Le seul deliverable & le vrai capital

- **Trading** : sleeve trend **mono-sleeve sur 60/40**, désormais cadré (META #22) comme
  **assurance-crise conditionnelle** — coupe ~½ du drawdown 2008/2022, +0.06 à +0.12 Sharpe
  quand une crise est en échantillon, mais **dilue en bull calme** (régime-dépendant). Pas
  un alpha. Le **carry #17 confirmé inutile en portefeuille** (dilue : corrélé +0.41 au cœur)
  → le deliverable reste **mono-sleeve**, et cette construction est l'aboutissement, pas un
  22ᵉ edge.
- **Méthode** : le **pipeline de 23 verdicts pré-enregistrés** — dont deux faux GO
  (VRP, CEF t=7.13) et un mirage in-sample (LST t=3.14) démasqués *avant* déploiement, un
  edge agrégé réel mais non-déployable honnêtement classé DOWNGRADE (V3 LP #15), et la
  construction META où un **faux « FORT » (DSR 1.000) a été rétrogradé en FAIBLE** parce que
  le DSR absolu ne teste pas l'incrément sur le cœur. La rigueur du kill — et du *keep* — ≫ le P&L.

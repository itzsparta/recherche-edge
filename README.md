# Recherche d'edge

Programme de recherche quantitative mené seul depuis juin 2026 : 43 thèses de
trading testées sur données réelles, de la lecture du carnet d'ordres du bitcoin
jusqu'à un portefeuille de primes de risque reconstitué sur un siècle.

Résultat : aucune stratégie déployable n'a passé ses propres critères. 29 thèses
sont tuées, 7 rétrogradées, 3 impossibles à tester proprement avec des données
gratuites, 4 gardées (toutes dans la partie construction de portefeuille). Ce
dépôt documente pourquoi chaque idée meurt, chiffres à l'appui.

Le registre complet se lit dans [`edge-site/`](edge-site/), un site statique qui
présente chaque thèse : données, méthode, critères fixés d'avance, résultat,
tests de robustesse.

## Méthode

Chaque étude suit le même protocole :

1. **Critères écrits avant le test.** Seuil de Sharpe, t-statistique minimale,
   coûts à inclure, condition de kill. Un critère ajusté après avoir vu le
   résultat invalide l'étude.
2. **Résultats nets.** Frais, spread, taxes (TTF, flat tax), coût de financement
   du levier. Un backtest qui n'est pas ramené à un levier tenable n'est pas lu.
3. **Correction du data-snooping.** Deflated Sharpe Ratio (López de Prado)
   calculé sur le nombre réel d'essais.
4. **Robustesse.** Sous-périodes et régimes, test miroir (le signal inversé
   doit perdre), stress sur les queues de distribution.
5. **Autopsie d'un résultat favorable.** Un GO déclenche une recherche de
   biais avant toute conclusion. Cinq thèses passées au vert sont tombées
   ensuite (#4, #6, #8, #26, #29).

Chaque dossier contient le code, une `SPEC` écrite avant le test et un
`FINDINGS` qui conclut.

## Les 43 thèses

Les cinq façons de mourir qui reviennent : pas de signal, mangé par la
friction, mangé par la queue (la prime rémunère un vrai risque de krach),
capté par un acteur plus rapide, interdit par la règle de la plateforme.

### Avant le programme

| # | Thèse | Verdict | Chiffre clé |
|---|---|---|---|
| OF | Lire le carnet d'ordres du bitcoin | KILL (pas de signal) | brut +0,021R, t = 0,83 |
| MC | Sniper les meme-coins pump.fun | KILL (pas de signal) | t = −35, −28 % par trade |

### V1 : l'edge structurel

| # | Thèse | Verdict | Chiffre clé |
|---|---|---|---|
| #1 | Suivre la tendance | KILL seul | Sharpe 0,42, t = 1,87 |
| #2 | Vendre avant les déblocages de tokens | KILL (pas de signal) | après la date : −0,22 %, t = −0,16 |
| #3 | Arbitrer les petites cryptos entre plateformes | KILL (friction) | 1 253 $ de profondeur au total |
| #18 | Suivre la couverture des teneurs de marché | KILL (pas de signal) | prédit la vol (t ≈ −16), pas le sens |

### V2 : assurance, calendrier, carry

| # | Thèse | Verdict | Chiffre clé |
|---|---|---|---|
| #4 | Vendre de l'assurance sur la volatilité | Faux GO (queue) | Sharpe 1,86… puis −95 % |
| #5a | Ne détenir les actions que la nuit | Rétrogradé (friction) | +10-14 %/an brut, −2,5 % net |
| #5b | Acheter la veille des annonces de la Fed | KILL (pas de signal) | +31 pb, puis +2,3 pb par annonce |
| #6 | Encaisser le financement crypto (cash-and-carry) | GO puis KILL (queue) | +10,5 %/an, +3,8 % récent |
| #7 | Parier sur le retour du ratio BTC/ETH | KILL (pas de signal) | ADF p = 0,38 puis 0,77 |
| #9 | Attendre que le stETH revienne à 1 ETH | KILL (queue) | t = 3,14 sur un seul épisode |
| #11 | Classer les cryptos par financement | KILL (friction) | +52 %/an brut, −20,6 % net |
| #11 v2 | Le même, lissé sur 7 jours | KILL (règle) | frais 72 % → 3,25 %/an |
| #12 | Vendre la volatilité crypto, avec filet | KILL (queue) | +25 pts (2021), +4,5 pts (2024+) |
| #13 | Momentum entre cryptos | KILL (pas de signal) | t = 0,84 ; depuis 2023 : −19,4 %/an |
| #17 | Le carry des devises | KILL (pas de signal) | Sharpe 0,21, t = 0,99 |

### Changer de contrepartie

| # | Thèse | Verdict | Chiffre clé |
|---|---|---|---|
| #8 | Fonds fermés décotés | Faux GO (friction) | t = 7,13, puis −0,64 |
| #10 | Parier contre les outsiders sur Polymarket | KILL (pas de signal) | biais inversé, t = +2,26 |
| #16 | Battre les bookmakers récréatifs | KILL (plus rapide) | +2,37 % chez Bet365, −3,18 % chez Pinnacle |

### V3 : la prime de saleté

| # | Thèse | Verdict | Chiffre clé |
|---|---|---|---|
| #14 | Farmer les airdrops | KILL (queue) | 8,4 €/h au mieux |
| #15 | Fournir de la liquidité sur Uniswap | Rétrogradé (plus rapide) | frais > pertes, mais au niveau du pool |
| #23 | Les rendements complexes de Pendle | KILL (queue) | prime 1,1-2,1 % < assurance 3,4 % |
| #29 | Uniswap sur un réseau bon marché | GO puis KILL (pas de signal) | frais / pertes = 0,90-0,94 |

### Prop firms et gains gratuits

| # | Thèse | Verdict | Chiffre clé |
|---|---|---|---|
| #24 | Réussir un challenge de prop firm | KILL | médiane = perte du droit d'entrée |
| #26 | Enchaîner les comptes financés | GO puis KILL (règle) | stratégie +EV interdite par le contrat |
| #33 | Tournois et concours gratuits | KILL (règle) | fermé sur les trois branches |

### V4 : anomalies publiées, flux forcés, fiscalité

| # | Thèse | Verdict | Chiffre clé |
|---|---|---|---|
| #25 | Contrer les ETF à levier en fin de séance | KILL (friction) | pari de nuit : t = −3,2 |
| #27 | Les SPAC sous la valeur de leur trésorerie | KILL (friction) | +85 à 145 pb < barre de 200 pb |
| #28 | La dérive après les résultats | KILL (pas de signal) | t = +0,01 sur 58 917 publications |
| #30 | Le carry de l'énergie | Rétrogradé (pas de signal) | apport au portefeuille : +0,04 |
| #31 | Assurer les ouragans (cat bonds) | Rétrogradé (queue) | +2,56 %/an < 3 %, asymétrie −2,95 |
| #32 | L'arbitrage de fusions | Non testable | 0 cible rachetée sur 10 dans les données gratuites |
| #35 | Les anges déchus | KILL (queue) | alpha +1,77 %, mais DSR 0,887 |
| #39 | Capturer le dividende en PEA | KILL (friction) | sans TTF +0,32 %, avec TTF −0,08 % |
| #40 | Le même, sur les petites valeurs sans taxe | Non testable | 85 événements < 100 requis |

### Construire avec ce qui reste

| # | Thèse | Verdict | Chiffre clé |
|---|---|---|---|
| #22 | Assembler les primes en portefeuille | Gardé, faible | 2008 : −9,9 % au lieu de −16,7 % |
| #22b | Remplacer le carry par plus décorrélé | Inchangé | apport : −0,14 |
| #34 | Lever le portefeuille à 1,5× | Extension | +10,0 %/an, perte max −29 % |
| #36 | Moduler le levier selon la volatilité | KILL | apport négatif sur 4 fenêtres |
| #37 | Le portefeuille face à un siècle | Confirmé | +1,76 pt/an sur 1926-2006 |
| #41 | De l'or contre la stagflation | Non ajouté (queue) | 1968-81 : +1,51 pt/an, ensuite moins que le cash |

## Organisation

| Chemin | Contenu |
|---|---|
| [`RESEARCH-ROADMAP.md`](RESEARCH-ROADMAP.md) | Récit complet du programme, piste par piste |
| [`FINDINGS.md`](FINDINGS.md) | Index des conclusions, avec un lien vers chaque étude |
| [`EDGE-PISTES-V2.md`](EDGE-PISTES-V2.md) | Cadrage des pistes V2 et V3 |
| `orderflow-bot/` | Bot orderflow BTC (carnet d'ordres, tape) avec tests, la thèse de départ |
| `bots/meme-coin-solana/` | Bot de snipe pump.fun et données Dune |
| `factor-harvest/`, `risk-premia-portfolio/` | Primes de risque et portefeuille final |
| Autres dossiers | Une étude chacun (`carry/`, `pead/`, `spac-trust/`, `univ3-lvr/`…) |
| [`edge-site/`](edge-site/) | Registre en ligne des 43 thèses |

## Stack

Python 3.11 : pandas, NumPy, DuckDB, statsmodels, SciPy. Sources : yfinance,
Binance, Deribit, Dune (SQL), FRED, SEC EDGAR, Polymarket, Stooq. Simulations
Monte Carlo parallélisées pour les prop firms (#24).

Les scripts qui interrogent SEC EDGAR demandent un User-Agent avec une adresse
de contact : remplacer `contact@example.com` par la vôtre.

## Avertissement

Projet de recherche personnel. Rien ici n'est un conseil en investissement.

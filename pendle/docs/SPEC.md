# SPEC — Piste 19 : Pendle "Complex Yield" (prime de smart-contract)

> **Pré-enregistrement.** Les gates ci-dessous sont repris **verbatim** de la mini-spec
> datée du **2026-06-24** dans [`factor-harvest/EDGE-IDEAS-LOG.md`](../../factor-harvest/EDGE-IDEAS-LOG.md)
> (section « Piste C — Pendle Finance Principal Token spread »), elle-même committée avant
> tout pull de données. Ce fichier ne fait que les rendre canoniques à côté du code. Aucun
> seuil n'a été ajusté après avoir vu une donnée. Numérotation : ROADMAP V3 piste 18 « DeFi
> Complex Yield » — le slot « 18 » ayant été pris par GEX, cette étude est indexée **#23**
> dans le bilan global (le 1er candidat pré-enregistré jamais run du programme).

## Hypothèse d'edge

Un Principal Token (PT) Pendle sur un actif **stablecoin** (sUSDe, USDe, PT-USDC-*) offre un
taux fixe jusqu'à maturité = `(1 − PT_price) / T_years` (en APY composé). Ce taux implicite
incorpore une prime pour le **smart-contract risk** (Pendle + protocole sous-jacent). Si cette
prime est **systématiquement supérieure à l'actuariel** (coût de couverture SC via Nexus
Mutual), alors : acheter le PT + couvrir le SC risk = rendement net positif vs USDC lending
(AAVE), **sans exposition directionnelle crypto**.

Formellement, edge ssi :

```
PT_yield_implied − USDC_AAVE_rate − SC_insurance_annual_cost > 0
```

de façon **persistante sur ≥ 12 mois**, dont le sous-échantillon **mûr 2025-2026** (leçon
p12+p13 : Gate G crypto obligatoire).

## Source de l'inefficience structurelle — pourquoi NON entièrement arbitrée

1. **Barrière compliance institutionnelle** : aucun fonds réglementé (UCITS, 40-Act, pension)
   ne peut positionner en DeFi non-KYC sur Ethereum mainnet. Les desks de taux fixes qui
   pourraient comparer un PT 6 mois à un T-bill sont structurellement **absents**.
2. **Complexité opérationnelle réelle** : mécanique PT/YT + risque oracle + AMM SY = barrière
   d'entrée documentée, pas un prospectus lisible par un analyste credit.
3. **Capacité** : TVL pools stablecoin Pendle $50M-$500M. Pour $5k-$50k : impact négligeable.
   Un fonds à $50M déplacerait le marché.
4. **SC insurance** : Nexus couvre Pendle à ~1-3 %/an, **rarement achetée** en pratique → la
   prime brute inclut le SC risk payé, mais pas par des acteurs diversifiés qui le compresseraient.

## Falsifiabilité — pourquoi ça peut mourir

- **Gate A** : PT yield ≤ USDC lending + 100 bps sur le panel récent → aucun spread, KILL (<30 min).
- **Gate B actuariel** : prime brute = coût Nexus → entièrement priced-in. **Tueur le plus
  probable** : le marché Pendle peut être « efficient » au sens où spread brut = exactement la
  prime de SC risk.
- **Gate C OOS mûr** : spread présent 2023-2024 mais pas 2025-2026 (densification LP) → artefact
  early-market (même leçon p12+p13 crypto).
- **Hack matérialisé** : Penpie (adjacent Pendle) hacké $27M sept. 2024 → le tail SC s'est déjà
  réalisé une fois ; la prime peut être correctement calibrée.
- **Yield aggregators** : Equilibria / Convex Pendle apportent du capital institutionnalisé →
  compriment le spread.

## Data sources (toutes gratuites, connectivité vérifiée 2026-06-25)

| Source | Données | Accès |
|--------|---------|-------|
| `api-v2.pendle.finance/core/v1/{chainId}/markets/active` | Prix PT, yield implicite, pools actifs, TVL | REST public, no auth |
| `yields.llama.fi/pools` | USDC lending rate AAVE/Compound, par chaîne | REST public |
| `api.nexusmutual.io/v2/products` + cover quote | Cover cost annuel par protocole | REST public |
| The Graph (Pendle subgraph) | Historical PT prices, swaps (Gate C) | GraphQL public |

## Gates de décision — pré-enregistrés (verbatim 2026-06-24)

| Gate | Critère PASS | Critère KILL |
|------|-------------|--------------|
| **(A) Spread brut positif** | `PT_yield − USDC_AAVE_rate > 100 bps` sur ≥ 80 % des obs récentes (pools stablecoins matures) | Médiane ≤ 100 bps → insuffisant pour couvrir gas + slippage |
| **(B) Actuariel** | `spread_brut − SC_insurance_cost (Nexus) > 0` de façon persistante | Spread ≤ cover cost → entièrement priced-in, pas d'inefficience |
| **(C) Persistance OOS mûr** | Spread net positif sur 2025-06 → 2026-06 (12 mois récents) ; Gate G obligatoire | Disparaît sur sous-échantillon mûr → artefact early-market |
| **(D) Dose-réponse** | Spread croît avec la durée à maturité (risque temporel SC = logique) | Plate ou inversée → structure incohérente |
| **(E) Liquidité réelle** | Exécution $10k sans impact > 25 bps sur pool cible | Impact > spread → capacité fantôme (leçon piste 3) |

**Signal pré-enregistré** : PT **stablecoin uniquement** (sUSDe, USDe, PT-USDC-*) — exclut les
PT sur actifs volatils (stETH, BTC) qui ajoutent de l'exposition directionnelle. Durée cible :
**1-6 mois** à maturité (assez court pour que la comparaison AAVE soit valide, assez long pour
absorber le gas).

## Coût d'implémentation et levier

Aucun levier. Achat direct de PT sur mainnet ou Arbitrum. Frais : Pendle swap 0.1 % + gas
($3-$10 sur Arbitrum L2). Pour 3-6 mois à maturité, frais absorbables si spread > 200 bps.

**Honnêteté brutale (pré-run).** Tueur le plus probable = Gate B : le spread brut visible sur
Pendle **existe** (pools stablecoin affichaient 6-12 % APY fixe en 2023-2024 vs AAVE 3-8 %), mais
cette différence peut être **exactement** le SC risk correctement pricé (Penpie hack = réalisation
du tail). Le test dit si c'est un artefact ou un edge.

## Ordre d'attaque

1. **Gate A + B sur snapshot courant** (data-pull + arithmétique) — peut KILL en <1h.
2. Si survit : Gate C (historique subgraph, mûr 2025+) + D + E.

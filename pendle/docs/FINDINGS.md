# FINDINGS — Étude #23 : Pendle "Complex Yield" (prime de smart-contract)

**Verdict : KILL — Gate B (actuariel). La prime de "complex yield" est priced-in là où le
risque est assurable, et inassurable là où la prime est grasse.** Snapshot marché **mûr**
2026-06-25. Gate A PASS (la prime brute existe), Gate B KILL (elle ≤ le coût actuariel réel
de couverture, mesuré live sur Nexus Mutual). Spec + gates pré-enregistrés 2026-06-24 :
[`SPEC.md`](SPEC.md). Code : [`../pull_and_gate_ab.py`](../pull_and_gate_ab.py). Données
horodatées : `../data/gate_ab_results.json`.

## Ce qui a été testé

Dernier candidat **pré-enregistré jamais run** du programme (ROADMAP V3, thème "DeFi Complex
Yield / Pendle"). Hypothèse : le taux fixe d'un Principal Token Pendle sur stablecoin
(`PT_yield = (1−PT_price)/T`) incorpore une prime de smart-contract risk **supérieure à
l'actuariel** → acheter le PT + couvrir le SC risk via Nexus = rendement net > USDC lending,
sans exposition directionnelle. Barrière structurelle invoquée : compliance institutionnelle
(aucun fonds réglementé en DeFi non-KYC) + complexité opérationnelle + capacité solo.

Data, tout gratuit, connectivité vérifiée : Pendle v1 `markets/active` (63 PT actifs, dont 7
stablecoin, `impliedApy` = taux fixe), DefiLlama `yields` (AAVE-v3 USDC supply = benchmark
sans-risque DeFi pré-enregistré), Nexus Mutual `v2/capacity` (coût de couverture **live**
`minAnnualPrice`/`maxAnnualPrice` + capacity dispo par produit).

## Gate A — PASS : la prime brute existe (même en marché mûr)

7 PT stablecoin, spread = `impliedApy − USDC_AAVE` (par chaîne ; AAVE USDC = 3.21 % eth / 2.48 %
arb). **Médiane +3.73 %, 7/7 > 100 bps → PASS.** La prime de complex yield est réelle et
substantielle aujourd'hui, pas un artefact early-market (contraste p12/p13 où le test mûr tuait).

## Gate B — KILL : décomposition contre le coût de couverture LIVE (Nexus)

Coûts de couverture annuels live (Nexus, 2026-06-25) : **Pendle SC (id 128) = 1.15–1.50 %/an,
capacity $13.2M** ; **Ethena USDe depeg (id 253) = 2.25–3.50 %/an, capacity $2.5M**. Les covers
PT-spécifiques (id 170 sUSDe, 379/380 PT-Ethena-Aave) sont à **$0 capacity = sold-out,
inachetables**.

| chain | PT | ytm | impApy | spread vs USDC | cover live (floor–max) | edge (spread−cover) | TVL | assurable ? |
|---|---|--:|--:|--:|--:|--:|--:|---|
| eth | msUSD | 0.09 | 9.67 % | **+6.46 %** | 1.15–1.50 % | +5.31 % | $0.4M | **NON** (sous-jacent obscur, 0 cover depeg) + TVL fantôme |
| arb | USDai | 0.67 | 6.91 % | +4.42 % | 1.15–1.50 % | +3.27 % | $0.1M | **NON** + TVL fantôme |
| eth | USDat | 0.17 | 7.46 % | +4.25 % | 1.15–1.50 % | +3.10 % | $9.8M | **NON** (0 cover depeg) |
| arb | USDai | 0.30 | 6.21 % | +3.73 % | 1.15–1.50 % | +2.58 % | $50.5M | **NON** (0 cover depeg) |
| eth | USDe | 0.13 | 5.31 % | +2.10 % | **3.40–5.00 %** | **−1.30 %** | $0.5M | oui → **edge négatif** |
| eth | sUSDS | 0.42 | 4.98 % | +1.77 % | 1.15–1.50 % | +0.62 % (floor) / **+0.27 % (max)** | $5.8M | partiel (USDS non-couvert) |
| eth | sUSDe | 0.13 | 4.32 % | +1.12 % | **3.40–5.00 %** | **−2.28 %** | $9.4M | oui → **edge négatif** |

**Survivants déployables (barre pré-enreg : assurable ∧ edge au coût max > 200 bps ∧ TVL ≥ $3M)
= 0.**

La barre 200 bps n'est pas tunée a posteriori : c'est le seuil "frais absorbables si spread >
200 bps" écrit dans la SPEC le 2026-06-24. Le seul edge positif assurable est sUSDS à **+0.27 %
au coût max** (+0.62 % au floor) — sous la barre gas, mono-nom, mono-maturité, et n'assure que
le **wrapper** Pendle (le peg USDS lui-même reste non-couvert, aucun produit Nexus) → in-fine
même bucket que les autres.

## Le mécanisme du kill — efficience actuarielle bipolaire

Le tableau **est** le verdict. Les 7 PT se scindent en deux familles, sans quadrant exploitable :

1. **Assurable → priced-in.** Là où le risque est entièrement couvrable (PT Ethena : Pendle SC +
   depeg), la prime brute (1.1–2.1 %) est **inférieure** au coût de couverture (3.40 % floor) →
   **edge négatif (−1.3 %, −2.3 %)**. Acheter le PT + s'assurer = perdre vs USDC. La prime ≈ (en
   fait <) le prix actuariel du risque qu'elle paie.
2. **Prime grasse → inassurable.** Là où la prime est grosse (msUSD +6.5 %, USDai/USDat +3.7–4.4 %),
   le sous-jacent est obscur et **aucun assureur ne price le risque** (0 cover depeg Nexus). La
   prime ne rémunère pas une inefficience : elle paie un **tail in-hedgeable** que le marché
   d'assurance refuse de coter. Deux des quatre ont une TVL fantôme ($0.1–0.4M, Gate E).

Il n'existe pas de PT à **grosse prime ET risque assurable cheap** — exactement ce que Gate B
était pré-enregistré pour détecter. **Le marché d'assurance on-chain révèle lui-même le
priced-in** : il met le bon prix sur ce qu'il accepte de couvrir, et se retire de ce qu'il ne
peut pas quantifier.

## Robustesse / honnêteté

- **Pas un artefact early-market** : le snapshot est le marché Pendle mûr de 2026 (TVL $50M+ sur
  les pools profonds). La prime brute existe *toujours* (Gate A PASS) — ce n'est pas une prime
  qui s'est compressée à zéro (contraste VRP-crypto p12), c'est une prime **réelle qui paie
  exactement son risque**.
- **Benchmark pré-enregistré** : USDC AAVE-v3, le proxy sans-risque DeFi le plus liquide. Il
  porte lui-même un SC risk AAVE → si quoi que ce soit, il *sur-estime* le spread net d'un PT
  (les deux portent du SC risk) ; le KILL est donc conservateur.
- **Capacity** : même la couverture "buyable" est rationnée ($13.2M Pendle SC, $2.5M depeg) et
  les covers PT-spécifiques sont sold-out → la jambe "hedge" du trade n'est ni gratuite ni
  scalable. Renforce le KILL côté déployabilité.
- **Cadre double** : que l'on *hedge* (edge négatif, supra) ou que l'on *porte nu* (on encaisse
  1–2 % pour un risque que Nexus price 3.4 %+) → no edge dans les deux lectures.
- Gates C (persistance historique subgraph), D (dose-réponse durée), E (slippage $10k) non
  atteints : inutile, le cut A+B sur snapshot mûr est décisif (KILL en <1h de code comme prévu
  par la SPEC).

## Place dans le programme — sous-type de mort #3, mécanisme neuf

Cousin direct du **carry exchange-default (p6)**, du **LST pré-redemption (p9)** et du **VRP
(p4)** : *brut réel mangé par le tail / la prime ≈ le risque*. Nouveauté de mécanisme : ici le
prix du risque n'est pas estimé par nous (break-even implicite) mais **lu directement sur un
marché d'assurance actuariel** (Nexus), qui tranche sans ambiguïté — et confirme le motif
unifié du programme : *structurel ≠ gratuit*. La barrière compliance institutionnelle invoquée
est **réelle** (les fonds réglementés sont bien absents) mais ne produit pas d'edge : le marché
DeFi natif (LP yield-hunters, Equilibria/Convex, et l'assureur Nexus lui-même) price le risque
efficacement sans eux.

**Bilan programme : 23 études, 0 edge déployable.**

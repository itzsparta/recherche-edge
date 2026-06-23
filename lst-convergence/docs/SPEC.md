# SPEC — Piste 9 : LST convergence (stETH/ETH) — pré-enregistré

> Écrit AVANT tout chiffre. Étang ≠ : la convergence est **garantie par le mécanisme de redemption du
> protocole** (1 stETH → 1 ETH une fois la queue de retrait purgée), pas un pari directionnel.

## Hypothèse d'edge

Les liquid-staking tokens (stETH) tradent à **discount** vs ETH en stress (queue de retrait engorgée,
ventes forcées) ; la convergence vers 1.0 est mécanique. Acheter le LST décoté / hedger en shortant ETH
→ capter la reconvergence `discount → 0`.

`discount(t) = stETH_price / ETH_price − 1` (≈ 0 en régime normal, < 0 en stress).

## Source de l'inefficience structurelle

Convergence garantie protocolairement = **non-prédictif** (on attend une égalité mécanique, on ne
devine pas un prix). Le discount = prix d'une **illiquidité de queue**, payé à celui qui peut attendre.
Les gros acteurs sous contrainte de redemption/VaR ne peuvent pas porter la queue ; le solo patient, si.

## Tension structurelle anticipée (le piège à garder en tête)

Le mécanisme qui **garantit** la convergence (redemption 1:1, activée par Shapella avr-2023) est aussi
celui qui **détruit le discount** une fois qu'il marche : post-Shapella, le retrait stETH→ETH est rapide
→ le discount est pinné à ~0 → **plus rien à capter**. Le gros discount exploitable (juin 2022, jusqu'à
−7 %) est PRÉ-Shapella = avant que la redemption existe. Donc le risque = l'edge est **un événement
unique non-répétable** (n=1), pas une prime récurrente.

## Données (gratuites)

- CoinGecko `market_chart?vs_currency=usd&days=max` pour `staked-ether` et `ethereum` (prix USD daily).
- `discount = stETH_usd / ETH_usd − 1`. Fenêtre ~déc-2020 → 2026.
- Fallback si CoinGecko échoue : DeFiLlama coins API (contrat stETH `0xae7ab9…`).

## Gates de décision (pré-enregistrés, cheap-first)

| Gate | PASS | KILL |
|------|------|------|
| **(A) reconvergence** | après excursion `discount < −σ`, retour à ~0 mesuré ; **taux de succès** + half-life tradable | ne reconverge pas / half-life > horizon portable |
| **(B) brut > 0, t > 2** | stratégie buy-discount/hedge-ETH, entrée si `discount < −seuil`, sortie à ~0 | brut ≤ 0 ou t ≤ 2 |
| **(C) net > 0** | après frais swap (Curve ~4-10 bps) + gas + **coût hedge** (funding short ETH ~5-10 %/an) | net ≤ 0 |
| **(D) tail explicite** | break-even `P(slashing / dépeg permanent)` implicite > seuil plausible (méthode carry phase-2) | break-even < seuil → discount **priced-in**, rime avec KILL carry |
| **(E) échantillon** | l'edge tient sur **≥ 2 épisodes de stress indépendants** (pas seulement juin-2022) | 1 seul épisode = n=1, aucune puissance statistique |

Seuil d'entrée pré-enregistré : `discount < −1.5 %` (≈ −σ historique hors-stress). Sortie à `discount ≥ −0.25 %`.

## Falsifiabilité — RIME AVEC LE KILL CARRY (piste 6)

1. Si le discount price **juste** le risque slashing/dépeg permanent → net ≈ 0 (priced-in, le tail
   exchange qui a tué le carry) → KILL Gate D.
2. Si mean-rev réelle mais half-life > horizon finançable → KILL Gate B/C.
3. **Si un seul épisode de stress (2022) porte tout l'edge → KILL Gate E** (n=1, non-répétable, et
   post-Shapella le discount est mort) — tueur le plus probable vu la tension structurelle ci-dessus.

## Verdict attendu a priori

Prior bas. Issue la plus probable = **KILL Gate E** : le seul vrai discount (juin-2022) est un événement
unique pré-redemption ; une fois la redemption activée, le discount disparaît → pas de prime récurrente,
juste une reconvergence one-off qu'on ne peut pas back-tester pour un edge déployable.

## Verdict RÉEL

**KILL (2026-06-23)** — conforme au prior. Gates B/C PASS (brut +82 %, net +76.8 %, t=3.14) mais
**A/D/E KILL**. Le PASS B/C est un **artefact in-sample** : les 26 épisodes de stress sont **tous
pré-Shapella**. Post-Shapella (169 j, avr→sep 2023, présents) le discount est pinné (min −0.40 %,
jamais < seuil −1.5 %) → **edge mort post-redemption**, exactement le `KILL Gate E` prédit. Gate D :
au creux −7.5 %, breakeven n'exige que P(perte 50 %)=13 % → prime ≈ risque de queue réel (priced-in
plausible). Détail dans [`FINDINGS-lst.md`](FINDINGS-lst.md).

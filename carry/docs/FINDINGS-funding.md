# Piste 6 — Carry (crypto perp funding) : FINDINGS

**Verdict (2026-06-23) : GO (avec caveats) — PREMIER non-kill du programme.** Le carry du funding
crypto est **réel, statistiquement significatif (t mensuel 6.88), market-neutral (corr 0.09) et
positif dans CHAQUE régime** dont le bear 2022 (+3.0 %) — net +10.5 %/an, au-dessus du hurdle 5 %,
robuste au drop-du-meilleur-régime. (A) PASS, (B) PASS. C'est la seule piste du programme (V1+V2)
qui n'est ni prédictive ni un edge à prix public : un **carry structurel** = on est payé pour
fournir le côté short aux longs levés. **Mais** il **compresse** vite (2026 ≈ +1 %) et porte un
**risque de queue non modélisé** (liquidation / exchange) — ce que la Phase-2 doit trancher.

> Reproduire : `python run_carry.py`. Données : funding 8 h `fapi.binance.com` (urllib paginé,
> fenêtres bornées), BTCUSDT 2019-09 → 2026-06 (7433 pts), ETHUSDT robustesse.

## (A) Le carry existe — PASS
- `mean(carry/jour) = +3.22 bps`, `gross_ann = +11.7 %`.
- **t mensuel non-chevauchant = +6.88** (significatif). ⚠️ Le t daily (+27.6) est **gonflé** par
  la très forte autocorrélation du funding — non cité.

## (B) Worth-it net, robuste régime — PASS

BTCUSDT (primaire), net annualisé (gross − 1.2 %/an de rééq.) :

| régime | net_ann |
|---|---|
| 2019-20 lancement/COVID | +13.7 % |
| **2021 bull** | +29.4 % |
| **2022 bear** | **+3.0 %** |
| 2023-24 reprise | +8.7 % |
| 2025-26 | +2.6 % |

- net full **+10.5 % > 5 %** ✓
- **positif dans chaque régime** (y compris le bear 2022 : le carry ne s'éteint pas) ✓
- drop du meilleur régime (bull) → **+7.3 % > 5 %** ✓ (pas un artefact mono-bull)
- `corr(carry, rendement BTC) = +0.09` → **vraiment market-neutral**, pas du beta-long déguisé.

ETHUSDT (robustesse) confirme (+13.0 % net) **sauf le bear** (−0.4 %, ~plat) — la marge
fair-weather est donc **mince** côté ETH.

## Pourquoi ça survit là où tout le reste est mort

Les 5 autres pistes (V1 : trend/unlocks/niche ; V2 : VRP/calendrier) chassaient un edge à
**information ou prix public** → toutes mangées. Le carry funding est **différent par nature** :
ce n'est pas un pari sur le prix, c'est une **prime de transfert de risque market-neutral** — les
longs levés *paient* en continu pour leur levier, et on encaisse en fournissant le côté short.
Tant que la demande de levier long existe, la prime existe. C'est la confirmation positive de la
thèse du programme : l'edge **structurel** (≠ prédictif) est le seul qui persiste.

## Caveats = les vraies portes de la Phase-2

1. **Compression** (le plus important). Gross_ann par année : 2021 **+30.6 %** → 2022 +4.2 %
   → 2023 +7.9 % → 2024 +11.9 % → 2025 **+5.1 %** → 2026 **+1.0 %**. L'arbitrage cash-and-carry
   ronge la prime ; le carry **forward** ressemble plus à ~2-5 %/an qu'au +10.5 % historique.
2. **Tail non modélisé.** Le short perp peut être **liquidé** sur un squeeze avant le rééq.
   mensuel ; risque **exchange** (FTX). Le hurdle 5 % les proxy mais la Phase-2 doit les haircut
   explicitement. Un +3 % net qui encaisse une probabilité de −100 % (exchange) n'est pas un GO.
3. **Capacité / $.** 10.5 % (et plus probablement ~3-5 % forward) sur un capital solo modeste =
   peu de $ pour la complexité opérationnelle (deux jambes, custody, marge).
4. **Proxy.** `markPrice ≈ spot` (le vrai cash-and-carry porte le spot réel + la base perp-spot,
   ici supposée converger via le funding — approximation de 1er ordre).

## Décision

**GO** vers la Phase-2 (exécution réelle spot+perp, modélisation liquidation, haircut
exchange-risk, walk-forward **sur le régime récent compressé** — pas sur l'historique flatteur).
C'est la première piste qui mérite du travail plus profond. Mais yeux ouverts : l'edge **décroît**
et le verdict final dépend du **tail**, exactement ce qui a tué le VRP (piste 4). Le carry y est
bien plus survivable (market-neutral, pas −95 %), mais le risque exchange/liquidation reste la
question ouverte.

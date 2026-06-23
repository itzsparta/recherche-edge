# Piste 15 — Uniswap V3 LP, EV net de LVR : FINDINGS

**Verdict (2026-06-23) : DOWNGRADE.** Surprise du programme : **le gate A PASSE honnêtement**.
Sur les majors V3 Ethereum 2024, les **frais dépassent la LVR** mesurée par markout — WETH/USDC 0.05 % :
frais **\$47.7M** vs LVR **\$24.2M** (net **+\$23.4M**) ; WBTC/WETH 0.30 % : frais **\$22.2M** vs LVR
**\$3.4M** (net **+\$18.8M**). Robuste sur **tous les horizons 1-60 min** et sur **les deux pools**.
**La prédiction naïve Milionis-Moallemi-Roughgarden « les LP perdent toujours contre la LVR » est
empiriquement FAUSSE pour ces pools/2024.** MAIS l'edge est **agrégé** (capté par les LP actifs/JIT) et
**non-déployable par un solo passif** : à taille solo le gas mainnet de gestion active (\$4-8k/an)
dépasse l'edge en dessous de ~\$26-85k de capital, le JIT skimme les frais des gros swaps noise, et un
passif large-range gagne **sous** la LVR. Gate A PASS, Gate B PASS, **Gate C/D FAIL → DOWNGRADE**.

> Reproduire : `python run_lvr.py` (applique les gates aux mesures Dune). Mesures : `queries/markout_minute.sql`
> sur `dex.trades` (engine free), exec ids dans `run_lvr.py`. C'est le **premier payoff non-directionnel**
> du programme (cashflow vs sélection adverse, pas prédiction de prix).

## Ce qui a été testé

Pré-enregistré dans [`SPEC.md`](SPEC.md). **Ledger d'EV structurel** : le cashflow (frais de swap)
dépasse-t-il le coût structurel (LVR = profit des arbitragistes = perte du LP) ? Mesure **concentration-
correcte** = markout des swaps réels (`dex.trades`), flux signé par bucket × rendement forward, PAS la
lentille naïve « apyBase vs IL full-range » (trompeuse dans les deux sens car la concentration amplifie
frais ET LVR). Pools canoniques, fenêtre **2024 mature** (Gate G).

## Gates

| Gate | Résultat | |
|---|---|---|
| **(A) frais > LVR markout** | ETH/USDC net **+\$23.4M** ; WBTC/WETH net **+\$18.8M** (LVR = max sur 1-60 min) | **PASS** — MMR naïf falsifié |
| **(B) mirage cross-pool** | 2/2 pools nets-positifs (volatil ET moins volatil) | **PASS** — pas un mirage mono-pool |
| **(C/D) déployabilité solo** | gas actif \$4-8k/an > edge sous ~\$26-85k capital ; JIT skim ; passif < LVR | **FAIL** — non-capturable solo passif |

## Le gate A passe — et je n'ai pas bougé les poteaux

La mesure markout a été **durcie dans le sens difficile** (anti-faux-GO, leçon VRP/CEF) :
- **Horizon court** testé exprès car l'horizon long sous-compte la LVR (arbs round-trip). Résultat
  **stable 1→60 min** (\$19→24M ETH/USDC) — la LVR ne se cache pas dans un horizon particulier.
- **LVR = max** sur les horizons retenue pour le net (le plus dur pour le LP).
- **Niveau bloc** tenté (capter l'arb atomique intra-minute) : **inexploitable** — VWAP par bloc sur
  blocs creux explose la division (`lvr_5blk` = \$501 **milliards** = outliers). La granularité minute
  lisse ce bruit ; le 1-min capte déjà 80 % du plateau → pas de LVR massive cachée sous la minute.

Même en durcissant, frais > LVR sur les deux pools. **Le gate passe pour de vrai** — contrairement au
faux GO CEF (t=7.13 retourné par le lag-bounce) et au faux GO VRP (Sharpe aveugle au tail), ici la
robustesse **ne** retourne **pas** le signe. Honnêteté pré-enregistrée : casser un gate favorable dans
le sens dur et le voir survivre = ce qui rend le PASS crédible. Donc **pas un KILL** — un DOWNGRADE.

## Pourquoi DOWNGRADE et pas GO — la déployabilité (le tueur)

L'edge **agrégé** (+\$23.4M / TVL \$150-250M ≈ **+9 à +16 % APR**) est **réel** mais accrue aux
participants **sophistiqués**, pas à un solo passif :

1. **Gas mainnet vs taille solo** (motif niche-capacité #3 / labeur airdrop #14). Capter le taux agrégé
   exige une **gestion active tight-range** (ETH/USDC bouge 3-5 %/j → rebalancer tous les 1-3 j).
   Gas mint+burn \$4-8k/an → **capital break-even \$26-85k juste pour le gas**. En dessous, l'edge est
   **entièrement** mangé. À taille solo réaliste (\$5-30k), négatif.
2. **JIT skim**. Les bots JIT (mint-swap-burn atomique) capturent les frais des **gros swaps noise**
   sans porter de LVR. Le LP passif hérite du **flux toxique** (LVR) + frais résiduels **≪** le taux
   agrégé que j'ai mesuré.
3. **Passif large-range** (sans rebalancing, gas faible) : la part de frais par dollar **s'effondre**
   sous la LVR → net ≤ 0. Le sign agrégé positif **ne se transmet pas** au passif.

Donc l'agrégé positif est capté par les **LP actifs/JIT** — un solo passif ne le récolte pas.

## Leçon — un NOUVEAU motif de mort, et un premier gate A survivant

- **Premier payoff non-directionnel à passer le gate A sur ses propres mérites** (cashflow vs adverse-
  selection, non mangé par l'efficience de prix). C'est une vraie info : **changer le TYPE de payoff
  a produit un edge agrégé réel** là où 14 paris directionnels échouaient. Mais…
- **…la mort se déplace de « pas d'edge » vers « edge capté par le participant sophistiqué »** — le
  MÊME motif que CEF #8 (réel/non-capturable, bounce), niche #3 (réel/sans profondeur) et sportsbook
  #16 (+EV seulement pour le MM). Ici le « sophistiqué » = LP actif/JIT ; le solo passif est le
  dindon. L'efficience n'est pas dans l'absence d'edge mais dans **qui** le capte.
- **MMR naïf est daté** : en 2024 (vol ETH basse, flux retail/MEV-share énorme), les majors V3 sont
  **net-positifs au niveau pool**. La littérature « >50 % des LP perdent » décrit surtout 2021-22
  haute-vol + LP mal-rangés. Mise à jour honnête du prior.

## Caveat

LVR mesurée au markout minute (concentration-correcte via prix d'exécution réels, nette arbs/noise) ;
le block-level aurait capté l'arb atomique mais est inexploitable (outliers). Si la vraie LVR sub-minute
était ~2× ma mesure, ETH/USDC tendrait vers le break-even (KILL plus net) — mais WBTC/WETH (frais 7×
la LVR) resterait positif, et le 1-min capture déjà l'essentiel → le PASS du gate A est robuste à une
sous-estimation raisonnable. Le **verdict ne dépend pas** de cette précision : il repose sur la
**déployabilité** (gas/JIT/passif-vs-actif), qui tue l'edge solo quel que soit le niveau exact de LVR.
TVL 2024 approximée (\$150-250M) ; l'argument gas est robuste sur toute la fourchette.

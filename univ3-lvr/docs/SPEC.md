# SPEC — Piste 15 : Uniswap V3 LP, EV net de LVR (pré-enregistré)

> Écrit **avant** tout chiffre de verdict. Comme p14/p16, **ce n'est PAS un backtest de prédiction** :
> c'est un **ledger d'EV structurel** sur un autre TYPE de payoff. Les 16 pistes précédentes pariaient
> sur une **direction de prix** ; ici le payoff est un **cashflow** (frais de swap) **moins un coût
> structurel** (sélection adverse par les arbitragistes = *loss-versus-rebalancing*). La question :
> le LP passif Uniswap V3 dégage-t-il une **EV positive nette de LVR + gas**, ou les frais ne font-ils
> que payer l'adverse-selection ?

## Hypothèse d'edge

Fournir de la liquidité concentrée sur Uniswap V3 dégage une **EV positive** pour un LP passif solo :
les frais de swap encaissés **dépassent** la perte structurelle (IL / LVR) infligée par les
arbitragistes qui rééquilibrent le pool à chaque mouvement de prix.

## Pourquoi ça pourrait persister — l'arme structurelle inédite

C'est le **premier payoff non-directionnel** du programme : pas deviner un prix, pas arbitrer un écart,
mais **encaisser un cashflow récurrent** (frais) en échange d'un **service** (liquidité). La contrepartie
qui paie les frais (noise traders) **subventionne** le LP. Si le flux de frais > la LVR, l'EV est réelle
et **non mangée par l'efficience de prix** (elle ne dépend d'aucune prédiction). Famille airdrop #14
(cashflow vs coût) mais avec un flux **on-chain, continu et mesurable**, pas une loterie de subvention.

## Le null honnête (= verdict attendu a priori)

Prior bas (16 kills). Le résultat **Milionis-Moallemi-Roughgarden (LVR, 2022)** : tout CFMM est
**systématiquement sélectionné adversement** — à chaque bloc où le prix bouge, l'arbitragiste prend le
pool « à l'envers » et son profit **EST** la perte du LP. Le marché a fait entrer du capital LP jusqu'à
ce que **frais ≈ LVR** (équilibre concurrentiel) — souvent **frais < LVR** car les LP retail courent
l'APR affiché sans price-er l'adverse-selection. Morts pré-enregistrées :

1. **LVR ≥ frais (tueur #1, MMR)** — sur les pools volatils (ETH/USDC, WBTC/ETH), le markout des
   arbitragistes mange tout le flux de frais → LP **−EV avant même le gas**. Études connues : >50 %
   des LP V3 auraient mieux fait de **hold**.
2. **Concentration = piège (lentille naïve trompeuse)** — la concentration **amplifie frais ET LVR**
   tant qu'on est in-range, mais **sort-de-range** = frais coupés en gardant l'exposition divergente.
   Toute mesure naïve « apyBase (frais concentrés) vs IL full-range » **double-favorise** le LP à tort.
   **Seule la LVR par markout (prix d'exécution réels) est concentration-correcte** → c'est la mesure.
3. **Niche stable** — pools stable/stable (USDC/USDT) : LVR ≈ 0 (σ≈0) mais frais minuscules et
   compétitionnés → marginal, mangé par le gas/rebalancing (motif niche-capacité #3).
4. **Coût opérationnel** — gas de mint/burn/rebalance + le labeur de gestion active (EV/heure #14).

## Univers / pools (FIXE — déterministe, anti-cherry-pick)

Pools canoniques Uniswap V3 **Ethereum** par TVL, fee tier le plus liquide :
- **Volatils** : WETH/USDC 0.05 %, WETH/USDT 0.05 %, WBTC/WETH 0.30 %.
- **Stable (contrôle)** : USDC/USDT 0.01 %.
Fenêtre **mature 2024** (Gate G : marché V3 dense/algorithmisé, ≠ 2021 immature ; leçon p12/p13).
Liste figée par TVL avant tout calcul de verdict.

## Mesure (FIXE) — LVR par markout, concentration-correcte

Pour chaque pool, à partir des **swaps réels** (Dune `dex.trades`, filtré au pool) :
- **Prix d'exécution** par swap `p_exec = amount_usd / token_amount`.
- **Référence** = VWAP du pool sur la **fenêtre suivante** (horizon court pré-fixé, p.ex. 30 min /
  N blocs) = le prix « vrai » après absorption du flux.
- **Markout du swap** `mk = taille_$ × (p_ref − p_exec) × sens` = profit du *swapper* = **perte du LP**.
- **LVR annualisée** `= Σ markout / TVL × (an / fenêtre)`. C'est la perte structurelle du LP, exacte
  à la concentration près (prix d'exécution réels).
- **Frais annualisés** `= Σ (volume × fee_tier) / TVL` (= rendement frais, ≈ apyBase DefiLlama, cross-check).
- **EV nette LP** `= frais − LVR − gas`. Benchmark = **hold** (le coût d'opportunité du LP).

## Gates de décision (pré-enregistrés)

- **(A) Frais > LVR au markout** : sur les pools volatils, `frais_APR − LVR_APR > 0` (médiane), avec la
  LVR mesurée par markout. Si `LVR ≥ frais` → **KILL** (l'adverse-selection mange le cashflow = MMR).
- **(B) Robustesse / Gate G** : tient sur **2024 mature** ET pas porté par **un seul pool ou un seul
  mois** (chasse mirage — leçon meme-coin/CEF/airdrop). Sous-périodes du même signe.
- **(C) Net du coût opérationnel** : `frais − LVR − gas − rebalancing > 0` ET, si actif,
  **EV/heure > 15 €/h** (la gestion de range est un travail — ledger #14). Sinon **DOWNGRADE**.
- **(D) Stable-pool** : USDC/USDT testé à part — si seul lui est `+`, edge = niche minuscule
  compétitionnée → **DOWNGRADE** (pas un edge d'investissement).

## Décision pré-enregistrée

- **(A) ∧ (B) ∧ (C) ⇒ GO** : cashflow structurel réel net d'adverse-selection — projet LP séparé.
  **Chasse mirage obligatoire** (un pool/mois ne porte pas tout ; le markout n'est pas un artefact de
  fenêtre de référence).
- **(A) ∧ ¬(C) ⇒ DOWNGRADE** : frais > LVR brut mais mangé par gas/labeur, ou seulement sur le stable.
- **¬(A) ⇒ KILL** : LVR ≥ frais = MMR confirmé, le LP subventionne l'arbitragiste.

## Falsifiabilité (comment ça meurt)

1. `LVR_markout ≥ frais` sur les volatils → KILL (A). 2. Edge porté par 1 pool/1 mois → mirage (B).
3. `frais − LVR > 0` mais `< gas + labeur` → DOWNGRADE (C). 4. Seul le stable survit → DOWNGRADE (D).
5. Markout sensible à la fenêtre de référence (30m vs 2h flippe le signe) → mesure non-robuste, KILL prudent.

## Données & implémentation

- **Swaps / volume** : Dune `dex.trades` (project uniswap, version 3, pool = `project_contract_address`),
  partition `block_month` + `blockchain='ethereum'` (pruning coût). **TVL / fee tier / apyBase cross-check** :
  DefiLlama yields (`yields.llama.fi/pools`, gratuit, cache). **Prix hold/σ** : klines Binance (gratuit).
- **Sortie** : `data_llama.py` (pools + TVL), `markout.py` (LVR par markout depuis Dune), `run_lvr.py`
  (gates A-D + verdict), `docs/FINDINGS.md`.

## Verdict attendu a priori

Le cashflow est **réel** (les noise traders paient des frais) — premier payoff non-directionnel, donc
non mangé par l'efficience de prix. Mais MMR prédit la mort en **(A)** : la LVR (markout des arbs) a
été poussée par la concurrence du capital LP jusqu'à **égaler ou dépasser** les frais sur les pools
volatils → le LP passif **subventionne l'arbitragiste**, EV nette ≤ 0 avant gas. Survie possible
seulement si un pool montre **frais > LVR au markout, robuste, net de gas** — un flux de frais qu'un
MM sharp on-chain n'a pas encore arbitré. Le motif unifié rend ça improbable, mais le payoff est
**authentiquement neuf** (cashflow vs adverse-selection, pas prédiction), donc le test est informatif.

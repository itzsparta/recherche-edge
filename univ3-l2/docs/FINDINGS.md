# FINDINGS — Étude #29 : LP Uniswap V3 sur L2 (exec-change, isole gas vs capture)

**Verdict : GO / WIN exec-change — le PREMIER edge déployable du programme, *pending* une confirmation
live d'exécution.** Sur L2 (Base/Arbitrum), l'edge LP-V3-sur-majors que #15 avait classé DOWNGRADE
(réel mais tué solo par le gas mainnet) **devient déployable** : le gas≈$0 retire le tueur de #15, la
capture JIT mesurée est **<4 %**, et le net-de-LVR (**~2,5 bp/$, ~30 % APR** à la TVL mesurée) est
**robuste sur 2022 (crash) / 2023 / 2024**. Tous les gates pré-enregistrés passent **tels qu'écrits**, et
la chasse-au-faux-GO obligatoire (régime) **ne le tue pas**. Discipline [[feedback-gate-override]] : après
28 KILLs je ne fabrique pas un 29ᵉ pour préserver la série — quand la data dit GO, je dis GO, avec les
caveats honnêtes.

Pré-enregistré : [`SPEC.md`](SPEC.md). Code : [`../run_l2.py`](../run_l2.py) (gates, chiffres Dune verbatim
+ execution_id), [`../queries/markout_l2.sql`](../queries/markout_l2.sql). Mesures Dune engine free,
2026-06-26.

## Ce que #29 tranche (que #15 n'avait pas tranché)

#15 a trouvé l'edge **agrégé** RÉEL (frais > LVR) sur les majors mainnet 2024, mais non-déployable solo,
tué par **deux** causes que le verdict **confondait** : **(a) gas mainnet** ($40/rebal) et **(b) capture
par LP actifs/JIT**. Sur L2, gas≈$0,05 → (a) disparaît. #29 = **expérience d'isolation** mesurant
laquelle liait. **Réponse : (a) le gas.** Sur L2, (b) la capture est petite et l'edge survit → l'exec-change
sauve un edge réel.

## Les chiffres (gates pré-enregistrés)

| Pool (2024) | volume | frais (5bp) | LVR_max (1-60min) | net | net/vol | TVL (snap) | **APR** |
|---|---|---|---|---|---|---|---|
| **Base** WETH/USDC 0,05 % | $17,8 B | $8,9 M | $4,4 M | **+$4,5 M** | +2,5 bp | ~$14,1 M | **+29,7 %** |
| **Arb** WETH/USDC 0,05 % | $48,5 B | $24,3 M | $11,4 M | **+$12,8 M** | +2,6 bp | ~$42,4 M | **+29,7 %** |

- **Gate A PASS** : frais > LVR_max sur les deux majors L2 (réplique le finding mainnet de #15, ~2,5 bp/$).
- **Gate C PASS (décisif)** : part JIT (volume servi par liquidité atomique même-bloc) = **Base 0,84 %
  tight / 3,88 % loose ; Arb 0,12 % / 0,92 %** — très **sous le seuil 25 %**. *La capture n'était PAS la
  contrainte liante de #15.*
- **Gate B PASS** : `net_passif = frais·(1−JIT) − LVR_max − gas_L2`, APR = net/TVL ≈ **30 %** sur les deux,
  **robuste à une TVL ×3** (FAIL seulement si TVL > $42 M Base / $126 M Arb, soit 3× le snapshot).

**L'isolation chiffrée (le cœur de #29)** — gas drag sur $100k, 2000 rebal/an :

| | par rebal | par an | **drag APR** |
|---|---|---|---|
| **L2 (#29)** | $0,05 | $100 | **0,1 %** |
| **mainnet (#15)** | $40 | $80 000 | **80 %** |

Le gas mainnet **mangeait** un edge de 30 % ; sur L2 il est négligeable. **C'est tout le résultat** :
changer l'exécution (mainnet → L2) retire la contrainte qui liait, et l'edge devient capturable solo.

## Chasse-au-faux-GO (obligatoire — SPEC : « si B passe »)

Les 2 faux-GO antérieurs (VRP t=1,86 mort sur le tail ; CEF t=7,13 mort sur le bounce au lag+1) imposent
de chercher le tueur non-modélisé **avant** de crier victoire.

1. **Régime (le risque #1 : haute-vol → LVR explose). REJETÉ.** net positif dans **les 3 régimes**, y
   compris le **crash 2022** (Arb WETH/USDC.e : frais $5,2 M − LVR $2,9 M = **+$2,3 M**, +2,2 bp), 2023
   (+$1,8 M, +2,8 bp), 2024 (+2,5/2,6 bp). LVR reste **45-56 % des frais partout** → net ~+2,5 bp/$
   structurel. Le faux-GO régime ne se matérialise pas.
2. **JIT/capture (le tueur supposé de #15). MESURÉ petit (<4 %).** Proxy tight (même bloc + même owner +
   même tick = JIT pur) ET loose (borne haute) tous deux << 25 %. La sophistication ne capte pas l'edge
   sur ces majors L2 2024.
3. **TVL (dénominateur). Robuste.** Snapshot net-de-transferts ; APR survit à TVL ×3.

## Le résidu honnête (ce qui empêche un GO « déploie à taille tout de suite »)

Comme #26 avait son résidu (voiding, finalement résolu par lecture), #29 a **un seul résidu non
mesurable hors-live = la fuite d'exécution du hedge** :

- **L'edge net-de-LVR est celui d'un LP DELTA-HEDGÉ** (Milionis-Moallemi-Roughgarden : LVR = coût d'un
  LP rebalancé en continu). Le déployable n'est PAS un LP passif naïf (qui porterait l'IL/la direction
  ETH) mais un LP qui **shorte ~le delta en perp** et **rebalance le range**. Réalisable solo (range L2
  cheap + perp CEX) mais **actif/sophistiqué**, pas du buy-and-hold.
- **Réalisé < 30 % brut** : hedge discret (pas continu) + funding perp + adverse-sélection **sous-minute**
  non capturée par le markout 1-60min (bornée par le JIT mesuré <4 % et le LVR_max conservateur) →
  réalisé plausible **~15-25 %**, cohérent avec les vaults ALM (Arrakis/Gamma) qui nettent double-digit
  en bon régime.
- **Capacité bornée ~$1-5 M** (pools $14-42 M ; retail-OK, fund-petit) ; **produits existants =** edge
  **connu et concurrencé**, donc s'érode.

**Nature de l'edge** : c'est une **prime de provision de liquidité** (compensation d'être short-gamma /
adverse-sélectionné), PAS un arbitrage sans risque — réelle au même sens que le sleeve trend, avec
variance (une semaine de gap violent peut être net-négative même si l'année est positive). Le résidu se
lève par un **test live cheap et réversible** (déployer $5-20k hedgé sur Base, mesurer le net réalisé),
contrairement à #26 dont le résidu était contractuel.

## Place dans le programme

**GO / WIN, sous-type NOUVEAU = « edge réel rendu déployable en changeant l'exécution ».** Les 28 verdicts
antérieurs : 0 edge déployable, dont #15 = « edge agrégé réel mais capté/gas-mangé, non-déployable solo »
(4ᵉ sous-type de mort). #29 **renverse #15 sur son propre terrain** : en isolant les deux causes, la
mort était le **gas** (retiré par L2), pas la **capture** (mesurée petite). C'est le **premier edge que le
programme classe déployable par un solo** — modeste, borné, actif, *pending* la confirmation live de la
fuite d'exécution, mais réel et robuste-régime. Il confirme la thèse mère du programme par la négative :
*structurel réel ≠ gratuit*, mais ici **la friction qui le rendait inaccessible (gas) était spécifique à
la couche d'exécution, pas à l'edge** — donc changer la couche le libère.

**Réconcilie le reframe « changer l'exécution »** : c'était l'unique axe jamais testé (vs « changer
l'étang » 0/3) ; il **produit le premier résultat déployable** là où changer la canne et changer l'étang
échouaient — parce qu'il s'attaque à la *contrainte de déploiement* (gas) plutôt qu'à l'existence de
l'edge (déjà établie par #15).

**Bilan : 29 études — 28 KILL + 1 GO déployable (#29, *pending*-live).** Deliverable trading = mono-sleeve
trend **+ LP-V3-hedgé-sur-L2 à confirmer live**. Caveat data : markout free-engine (sous-minute non
capturée), TVL snapshot, fee tier 0,05 % supposé par dominance de volume.

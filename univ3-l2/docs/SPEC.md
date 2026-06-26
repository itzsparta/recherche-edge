# SPEC — Étude #29 : LP Uniswap V3 sur L2 (exec-change, isole gas vs capture)

**Pré-enregistré le 2026-06-26, AVANT toute data L2.** Gates numériques figés ici
([[feedback-gate-override]]). Enfant direct de **#15** (`code python/univ3-lvr/`, DOWNGRADE).

## Thèse & ce que #29 tranche que #15 n'a pas tranché

#15 a trouvé l'edge LP V3 **agrégé** RÉEL sur les majors mainnet 2024 (frais > LVR : ETH/USDC net
+$23,4M, WBTC/WETH +$18,8M ; MMR naïf falsifié) **mais non-déployable solo**, tué par **deux** causes
que le verdict a **confondues** : (a) **gas mainnet** ($40/rebal × 100-200/an > edge sous ~$26-85k de
capital) et (b) **capture par les LP actifs/JIT** (mint-swap-burn atomique skimme les frais des gros
swaps sans porter de LVR). Sur un **L2** (Base/Arbitrum), le gas ≈ **$0,05/tx** (≈800× moins) → la cause
(a) **disparaît**. #29 = **expérience d'isolation** :

- si l'edge passif devient déployable sur L2 → **(a) gas était la contrainte liante** → **WIN exec-change**
  (le 1er du programme : changer l'exécution sauve un edge réel) ;
- si l'edge reste capté malgré gas≈0 → **(b) capture était liante**, le L2 n'y change rien → **KILL
  sous-type #4 confirmé** comme vraie cause de mort de #15.

C'est l'unique test « changer l'exécution » du programme : il **mesure** laquelle des deux morts liait.

## Mesures (identité, pré-enregistrées)

Mêmes mesures FIXES que #15, portées sur L2 :
- **LVR** = markout du flux signé par minute × rendement forward (`queries/markout_l2.sql`, copie de
  #15 avec `blockchain ∈ {base, arbitrum}`). On retient **max sur {1,5,15,60} min** (le plus DUR pour le
  LP = anti-faux-GO).
- **frais** = volume × fee_tier. **TVL** du pool (Dune/DefiLlama snapshot).
- **part JIT** (NOUVEAU, le cœur de #29) = part du volume de swap servi par de la liquidité **atomique
  même-bloc** = volume des swaps dans les blocs contenant À LA FOIS un `Mint` ET un `Burn` sur le pool,
  / volume total. Proxy robuste et mesurable de la capture par LP sophistiqués.
- **net passif** (la chaîne déployable) :
  ```
  net_passif_APR = fee_APR·(1 − part_JIT)  −  LVR_APR  −  gas_L2_APR
  fee_APR = frais/TVL    LVR_APR = LVR_max/TVL    gas_L2_APR ≈ 0
  ```
  Le LP passif touche les frais NON-JIT au prorata mais porte TOUTE la LVR (le JIT n'en porte aucune).

## Gates (numériques, figés AVANT data)

| Gate | Test | Seuil |
|---|---|---|
| **A** edge agrégé réplique sur L2 | frais − LVR_max > 0 | sur **≥2** pools majors L2 |
| **B** passif déployable, gas isolé | `net_passif_APR` (formule ci-dessus) | > **10 %** APR (compense l'IL/risque inventaire) |
| **C** isolation capture (décisif) | part JIT (volume même-bloc Mint∧Burn) | seuil **25 %** : >25 % = capture LIANTE |

**Logique de verdict (pré-enregistrée) :**
- ¬A → les majors L2 n'ont même pas l'edge agrégé (finding distinct).
- A ∧ **B** → **WIN exec-change** : sur L2 le passif capte frais>LVR net de gas≈0 → la mort de #15 ÉTAIT
  le gas. (Le 1er GO « déployable » du programme — à traiter avec la chasse-au-faux-GO obligatoire.)
- A ∧ ¬B ∧ **C>25 %** → **KILL #4** : capture liante, le L2/gas n'y change rien → #15 mourait de capture.
- A ∧ ¬B ∧ **C≤25 %** → **KILL #2** : gas retiré mais frais−LVR trop minces sur L2 (volume plus faible).

## Prior honnête

A passe (les majors ont la structure). **B échoue probablement.** C = l'inconnue qui tranche la cause :
le JIT existe sur L2 (profitable partout où les frais se concentrent) mais l'infra MEV/ordering y diffère ;
les frais L2 sont aussi plus minces (volume < mainnet). **Prior = KILL/DOWNGRADE, cause la plus probable =
capture (#4) + frais minces (#2) combinés → gas n'était PAS la seule contrainte → l'exec-change ne sauve
pas.** Mais si B passe, c'est un **vrai WIN** et je le traite comme le faux-GO le plus dangereux du
programme (chasse obligatoire avant de crier victoire).

## Données (free)

- Dune `dex.trades` (`blockchain='base'|'arbitrum'`, `project='uniswap'`) → markout (A/B), engine free.
- Dune `uniswap_v3_base.*` / `uniswap_v3_arbitrum.*` `Mint`/`Burn`/`Swap` décodés → part JIT (C).
- Pools : **Base WETH/USDC 0.05 %**, **Arbitrum WETH/USDC 0.05 %**, **Arbitrum WBTC/WETH 0.30 %**.
- Période **2024** (mirror #15 pour comparabilité). Gas L2 ≈ $0,05/rebal (public, vs $40 mainnet).

## Caveats (déclarés d'avance)

- **part_JIT proxy** (Mint∧Burn même-bloc) majore légèrement le vrai JIT (un Mint et un Burn non liés
  peuvent coïncider) → biais CONTRE la thèse passive (gonfle la capture) → si B passe malgré, c'est
  conservateur ; si B échoue via C élevé, vérifier que le proxy ne sur-compte pas (sensibilité same-tx).
- **TVL** en snapshot (proxy de la moyenne 2024) — net_APR sensible ; je borne haut/bas comme #15.
- **LVR_max** sur 1-60 min = borne haute de l'adverse-selection → net passif est une **borne basse** →
  KILL conservateur, WIN non-exagéré.

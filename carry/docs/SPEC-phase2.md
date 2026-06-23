# Piste 6 — Carry Phase-2 : exécution réelle + tail (PRÉ-ENREGISTRÉ)

> Écrit **avant** de voir le moindre résultat Phase-2. Tout changement après un chiffre = overfit,
> interdit. La Phase-1 a rendu **GO** (carry réel, t mensuel 6.88, net +10.5 %/an, positif chaque
> régime, market-neutral corr +0.09). Phase-1 = « va creuser ». **Phase-2 = décision de déployer
> du capital réel**, et elle peut encore rejeter le déploiement.

## Ce que la Phase-1 a laissé NON modélisé (= ce que la Phase-2 attaque)
Les 4 caveats de `FINDINGS-funding.md` :
1. **Compression** — le +10.5 % est dominé par 2021 (+29 %). Forward réaliste = régime récent
   (gross 2026 ≈ +1.0 %). → walk-forward **OOS sur la fenêtre récente**, pas l'historique flatteur.
2. **Basis réel** — Phase-1 = funding seul, `markPrice ≈ spot` (proxy, legs circulaires). → P&L
   delta-neutre **vrai** = funding + (spot réel − perp réel), spot klines vs perp klines séparés.
3. **Frais 2-jambes réels** — Phase-1 = 1.2 %/an forfaitaire. → taker spot + taker perp,
   entrée+sortie **deux jambes** + rééq. mensuel + slippage.
4. **Tail non modélisé** — liquidation du short perp ; risque exchange (FTX = −100 %).

## Données Phase-2 (FIXE — ajout à la Phase-1)
- **Spot** BTCUSDT klines 1j : `api.binance.com/api/v3/klines` (urllib paginé, même patron que
  `data_funding.py`).
- **Perp** BTCUSDT klines 1j **et 8h** : `fapi.binance.com/fapi/v1/klines` (8h = magnitude des
  squeezes intra-intervalle pour le modèle de liquidation).
- Funding 8h : déjà en cache (Phase-1, 7433 pts 2019-2026).
- ETHUSDT en robustesse si BTC passe.

## Stratégie exécutée (FIXE)
- Long 1 BTC spot + short 1 BTC perp (delta ≈ 0). `pnl_jour = funding_collecté +
  (spot_ret − perp_ret)·notional − frais`.
- **Frais réels** : taker spot **0.10 %** + taker perp **0.04 %** par jambe ; entrée+sortie =
  2 jambes × 2 = ouverture/fermeture, **+ rééq. mensuel** (rebalancer la dérive de delta + la
  marge). Slippage **2 bps**/jambe. Modèle conservateur taker (un solo n'est pas garanti maker).
- **Marge / liquidation** : short perp à levier `L`. Cas (i) **cross/portefeuille** (setup
  compétent) : le gain spot compense la perte perp → pas de liquidation. Cas (ii) **isolé/naïf** :
  liquidation si move adverse ≳ `1/L − maintenance`. On mesure les deux.

## Métriques + critères PRÉ-ENREGISTRÉS

**(C) Survie à l'exécution — TOUT requis**
- Construire le P&L delta-neutre **vrai** (legs réels spot/perp + frais réels).
- **Delta-neutralité vérifiée** : `|corr(pnl_jour, btc_ret)| < 0.2` avec legs réels (pas markPrice
  circulaire).
- **OOS régime compressé** = **24 derniers mois** (le forward réaliste, PAS l'historique). Gate :
  `net_ann_OOS > 8 %`. Hurdle 8 % = risk-free ~4.5 % (T-bill 2024-26) **+ prime** pour la charge
  opé (2 jambes, custody, marge) + le tail exchange. Pour un solo, le carry doit ~**doubler le
  cash** pour valoir le dérangement. (Pré-enregistré : 8 %.)

**(D) Survie au tail — TOUT requis**
- **(D1) Liquidation** : sous cross-margin + buffer, le pire move 8h historique ne liquide pas
  (le spot offsete) → liquidation prob ≈ 0. Reporter aussi la fréquence de liquidation **isolé**
  (coût du naïf). Gate : gérable en cross-margin (pire move 8h < seuil au levier retenu).
- **(D2) Break-even risque exchange** : `p* = net_OOS / (net_OOS + 1)` = proba annuelle de faillite
  exchange qui annule l'EV. Gate : **`p* > 5 %/an`** pour un GO. (Si même un risque exchange de
  2-3 %/an met l'EV à zéro, le carry n'est pas assez gras pour le tail → DOWNGRADE.)
- **(D3, diagnostic)** : pire drawdown cumulé du carry sur l'OOS (funding peut flipper négatif en
  squeeze) ; recouvrable si < une année de carry.

## Décision PRÉ-ENREGISTRÉE
- **(C) ∧ (D) ⇒ GO-DEPLOY** : paper-trade puis capital réel, **sizé pour survivre au tail
  exchange** (position ≤ une fraction du net worth telle que −100 % soit survivable).
- **(C) ∧ ¬(D) ⇒ DOWNGRADE** : net réel sur le forward mais le **tail** (break-even exchange trop
  bas, ou liquidation ingérable) ⇒ pas worth le capital réel pour un solo → paper-only / étagère.
- **¬(C) ⇒ KILL-FORWARD** : le régime compressé + frais réels tuent le net sur la fenêtre
  réaliste ⇒ le +10.5 % historique était de la **chance de régime**, pas un edge déployable
  aujourd'hui. (Possibilité RÉELLE vu gross 2026 ≈ +1 % — c'est ce que la Phase-2 doit surfacer.)

## Implémentation
- `data_prices.py` (spot+perp klines, urllib paginé), `execution.py` (P&L delta-neutre + frais),
  `liquidation.py` (squeezes 8h, cross vs isolé), `tail.py` (break-even exchange), `run_phase2.py`
  (walk-forward OOS + gates C/D + verdict). Sortie : `docs/FINDINGS-phase2.md`. Réutilise
  `audit.py` (tstat). Pas de changement des fichiers Phase-1.

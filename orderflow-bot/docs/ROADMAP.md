# Roadmap orderflow-bot

## État actuel — thèse gelée (no-edge)

Le signal **stacked-imbalance @ zone de volume profile** n'a **pas d'edge
directionnel récoltable** sur BTCUSDT spot (déc. 2025 – juin 2026). Tous les
leviers orderflow-natifs épuisés, **DOM/L2 inclus** (Phase 0 KILL,
2026-06-14) et **régime de volatilité + mur d'exécution** inclus (gel de
thèse, 2026-06-15). Brut ≈ 0 partout, net négatif partout (fee-bound).
Verdict complet, méthode et pièges : [`FINDINGS.md`](FINDINGS.md).

Ce que cette roadmap décrit **n'est donc pas le chemin de mise en prod du
signal v1** (il est mort) — c'est : (1) l'ordre de redeploy par espérance,
(2) le protocole que tout redeploy doit franchir, (3) la vision en couches
réutilisable si un futur signal vit. La valeur conservée = l'**infra + la
méthode**, pas le signal.

## Redeploy — classé par espérance (EV)

Tout redeploy s'entre comme une **hypothèse pré-spécifiée que le rerun
confirme ou tue** — jamais de l'infra bâtie sur un espoir
(« on a la machinerie, autant s'en servir » = version-hop interdit).

1. **Timeframe supérieur / swing** — *meilleure EV*. Dissout le **mur
   structurel** (anti-corrélation edge↔frais) : un R assez gros rend la
   fraction-frais négligeable, là où une venue moins chère ne grignote que le
   numérateur. Garde volume profile + niveaux comme contexte HTF. Le seul move
   qui *dissout* le mur au lieu de le contourner.
2. **Rerun NQ-intraday (IBKR)** — seule cellule positive sur instrument
   **accessible** à un résident FR (NQ/ES via IBKR ; gated par données payantes
   ~dizaines €/mois — **pas** un géo-block, contrairement aux futures crypto
   Binance). Conditionnel à l'hypothèse que l'**inversion de cellule** (#13)
   est spécifique à la mauvaise microstructure BTC-spot (spreads larges,
   taker-out punitif) et se nettoie sur le carnet plus serré de NQ. À tuer vite
   si le rerun ne reproduit pas une cellule franchement nette.
3. **Rebate-crypto** — **mort**. Un artefact ne devient pas réel sur une venue
   moins chère ; l'inversion de cellule survit au changement de frais.

## Protocole de validation (tout redeploy doit le franchir)

Spec « Évaluation & validation », réutilisée telle quelle sur le prochain
instrument/signal — seul `ingestion/` change, le pipeline est agnostique du flux.

1. **Données** : `import --start --end` pour le backtest/walk-forward immédiat ;
   `record` en continu pour le flux temps réel. *Note BTC* : le websocket live
   futures Binance est géo-bloqué depuis la France (connexion acceptée, zéro
   message) — le live crypto ne marche qu'en `market: spot`. Sans objet pour NQ
   (IBKR) ou un timeframe swing alimenté en historique.
2. **Backtest** : `backtest` sur tout l'historique — frais + slippage inclus
   d'office. Comparer les itérations sur Sortino, Calmar, max DD, profit factor
   (offline uniquement, jamais en input de décision live).
3. **Robustesse** : `walkforward --folds 4` — expectancy_r stable et positive
   sur la **majorité** des folds, pas un total flatteur tiré par un seul fold.
   Puis `validate` — Monte Carlo sur les trades réels : dd_p99 et ruin_prob
   compatibles avec le stop journalier (−2 %).
4. **Audit anti-overfit (non négociable, dès le jour 1)** : `overfit_audit.py`
   — Deflated Sharpe Ratio + CSCV. Après k variantes, déflater le meilleur
   Sharpe par le nombre d'essais. *Leçon FINDINGS* : DSR(best, N=50) = 0.008 a
   tranché le no-edge quand les métriques brutes mentaient. Pré-enregistrer la
   règle + le critère de succès **avant** de voir les résultats, à **bornes
   instrument-spécifiques**.
5. **Paper trading** : 1–2 mois via `paper`. Go/no-go : ≥ 100 trades,
   expectancy_r > 0, comportement conforme au backtest (pas de divergence
   inexpliquée de win rate ou de slippage).
6. **Live taille minimale** : risque réduit (0,25 %/trade), mêmes règles.
7. **Montée progressive** : retour au risque nominal (0,75 %) seulement après
   validation des stats live ; plafond v2 = Kelly 1/4 (`validate` →
   `kelly_quarter_cap`), calibré sur la distribution empirique du journal —
   jamais full Kelly, jamais automatique.

## Vision en couches (conditionnelle à un signal vivant)

Confluence de couches — à ne rebâtir **que** si un redeploy passe le protocole.
Ordre = contexte → zone → déclencheur → régime.

- **Couche 1 — contexte HTF** : profil daily + TPO (balance/imbalance, single
  prints, poor highs/lows comme cibles + réparation). Statut : volume profile
  livré ; TPO non bâti.
- **Couche 2 — zone** : VAH/VAL, nPOC, LVN. Fusionner les niveaux options
  (gamma flip, call/put wall, gros strikes 0DTE) → confluence = setup haute
  proba. Statut : zones volume profile livrées ; niveaux options non bâtis.
- **Couche 3 — déclencheur orderflow** : delta/CVD, footprint (absorption,
  imbalances empilées). Statut : stacked-imbalance livré **et tué** sur BTC ;
  à re-tester sur instrument/timeframe de redeploy.
- **Couche 0 — régime (v1.5)** : GEX net, gamma flip, call/put walls. Gamma
  positif → fades aux extrêmes uniquement ; gamma négatif → breakouts/momentum.
  ⚠️ **Le proxy gratuit (RV réalisée) a déjà été testé comme régime
  (#12) → faux gradient, plafond +0.067R non récoltable, GEX vrai payant
  rejeté ($0) car il ne peut pas battre son propre plafond.** Ne re-budgéter du
  GEX payant que si un redeploy montre d'abord un régime récoltable au proxy.
  Cross-checks cheap si besoin : structure de terme VIX, COT, exposant de Hurst,
  put/call ratio (mineur).
- **DOM / L2** : ⚠️ **déjà testé en Phase 0 (2026-06-14) → KILL pour ce
  signal** : le carnet ne sépare pas les morts-nés mieux que le tape (best AUC
  L2 0.535 vs tape 0.521, n=312). Infra réutilisable (`features/book.py`,
  `backtest/separation.py`) mais ne pas re-supposer un edge L2 sans nouveau
  test pré-enregistré sur le nouvel instrument.

## Money management

- **v1** : risque fixe 0,5–1 % (taille depuis la distance du stop), stop
  journalier −2 %, pause après 3 pertes consécutives, partiel à 1R +
  break-even, une position à la fois. *Rappel FINDINGS* : aucun dimensionnement
  ne sauve une espérance ≤ 0 (Kelly d'un edge négatif = 0). Le sizing module la
  variance, ne crée pas d'edge.
- **v2 — Kelly live** : après ~100 trades réels, Kelly 1/4 comme **plafond**
  du risque par trade (le risque fixe reste la consigne par défaut). Calibré
  sur la distribution empirique du journal via Monte Carlo (resampling →
  distribution des drawdowns, risque de ruine). Jamais full Kelly.
- **v2 — Volatility targeting (EWMA)** : sizing inversement proportionnel à la
  vol réalisée. Kelly fixe le plafond, le vol-targeting ajuste en continu.
  Infra présente (n'a pas créé d'edge sur BTC, garde pour un futur signal).
- **Monitoring continu** : Sortino + Calmar + max DD + profit factor. Offline,
  jamais en input de décision live.

## v2.5 — Options comme instrument d'exécution

Les options passent de capteur de contexte (couche 0) à **véhicule
d'exécution**. Framework 4 couches inchangé, seule l'expression du trade change.
Conditionnel : un signal vivant d'abord.

- **Greeks engine** : Black-76 (options sur futures) / Black-Scholes (SPX).
- **Data backtest** : historique IV + chaînes (ThetaData/ORATS).
- **Exécution multi-leg** : ordres combo IBKR natifs.
- **Mapping setups** : +GEX au call wall → call credit spread ; −GEX breakout →
  debit spread (IV chère) ; 0DTE calme en +GEX → iron condor dans l'expected
  move. **Spreads définis obligatoires, jamais de vente nue.**
- **Instrument** : options sur futures ES/NQ (même écosystème) ou SPX/XSP
  (européennes, cash-settled, pas d'assignation). Éviter les options sur
  actions US.
- **Risque** = débit payé ou largeur − crédit. Plus de stop ferme, mais
  surveiller le bid/ask en sortie.

## v3+ — ML & portefeuille

La seule sophistication qui se justifie, et **seulement** avec des centaines de
trades labellisés réels.

- **Meta-labeling (López de Prado)** : les règles (couches 0–3) décident le
  sens, un ML binaire décide si on prend le trade, entraîné via triple-barrier.
  Améliore la précision sans toucher à la logique.
- **Multi-stratégies** : 3–4 stratégies décorrélées → allocation type frontière
  efficiente entre elles.

## Filtre macro (non négociable, toutes versions)

Flat avant/après FOMC, CPI, NFP, OPEX, settlement. Calendrier gratuit
(Fed/BLS/ForexFactory). *Rappel FINDINGS* : NFP testé comme filtre (#11) →
pire que la base = filtre d'évitement du risque, pas un edge.

## Écarté en permanence

ML prédictif brut (LSTM/transformers sur le prix), reinforcement learning,
microstructure HFT, GARCH/HMM en core (EWMA + régime GEX suffisent), sentiment
social/alt-data, vanna/charm, surface IV complète, VaR paramétrique (remplacé
par stops durs + CVaR historique si besoin), alpha de Jensen.

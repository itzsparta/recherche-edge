# Roadmap orderflow-bot

## Protocole de mise en production (spec « Évaluation & validation »)

1. **Collecte** : `record` en continu (plusieurs semaines de ticks Parquet).
2. **Backtest** : `backtest` sur tout l'historique — frais + slippage inclus
   d'office. Comparer les itérations sur Sortino, Calmar, max DD, profit
   factor (offline uniquement, jamais en input de décision live).
3. **Robustesse** : `walkforward --folds 4` — exiger une expectancy_r stable
   et positive sur la majorité des folds, pas un total flatteur tiré par un
   seul fold. Puis `validate` — Monte Carlo sur les trades réels : dd_p99 et
   ruin_prob doivent rester compatibles avec le stop journalier (-2 %).
4. **Paper trading** : 1 à 2 mois via `paper`. Go/no-go : ≥ 100 trades,
   expectancy_r > 0, comportement conforme au backtest (pas de divergence
   inexpliquée de win rate ou de slippage).
5. **Live taille minimale** : risque réduit (ex. 0,25 %/trade), mêmes règles.
6. **Montée progressive** : retour au risque nominal (0,75 %) seulement après
   validation des stats live ; plafond v2 = Kelly 1/4 (`validate` →
   `kelly_quarter_cap`), calibré sur la distribution empirique du journal —
   jamais full Kelly, jamais automatique.

## Jalons fonctionnels

- **v1.2 — TPO** : balance/imbalance du profil, single prints, poor
  highs/lows (cibles + réparation). Enrichit la couche 1 (contexte HTF).
- **v1.5 — Options/GEX** : GEX net, gamma flip, call/put walls, gros strikes
  0DTE. Ajoute la couche 0 (régime) : gamma positif → fades aux extrêmes
  uniquement ; gamma négatif → breakouts/momentum uniquement. Crypto :
  options Deribit ; CME : OI CBOE maison (approximatif) ou SpotGamma/MenthorQ.
- **v2 — DOM L2** : liquidité passive consommée vs affichée (pondération
  anti-spoofing) comme déclencheur couche 3 supplémentaire. Nécessite la
  collecte depth (extension du Recorder par type d'événement, prévue dès v1).
- **v2 — Kelly live** : après ~100 trades réels, Kelly 1/4 comme PLAFOND du
  risque par trade (le risque fixe reste la consigne par défaut).
- **Migration CME (NQ/ES)** : Databento ou Rithmic quand le setup est validé
  sur crypto. Le pipeline est agnostique du flux : seul `ingestion/` change.

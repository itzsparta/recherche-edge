# Orderflow bot — verdict de recherche (no-edge)

**Date** : 2026-06-13
**Données** : BTCUSDT spot, aggTrades Binance, 2025-12-01 → 2026-06-11 (~6 mois, 1.5 GB).
**Frais de référence** : maker 0.02 % / taker 0.05 % + slippage (grille futures Binance ; le spot réel est pire).
**Unité** : R = multiple du risque initial `|entrée − stop|`. `net` = après frais ; `brut` = avant frais.

## TL;DR

Le signal **stacked-imbalance dans une zone de volume profile** (POC/VAH/VAL/nPOC) n'a **pas d'edge directionnel récoltable** sur cet échantillon. Après avoir épuisé tous les leviers, le **brut plafonne à +0.021R (t = 0.83, indistinguable de zéro)** et le **net reste négatif partout**, bloqué par un mur de frais taker de ~0.16R. Aucun dimensionnement ne sauve une espérance négative. Le projet est gelé sur cette conclusion.

## Méthode

- **Backtest 2-passes** : `PlanGenerator` (signal, equity-invariant → parallélisable) puis `OrderExecutor` (exécution séquentielle, compounding). Équivalence mono/parallèle prouvée.
- **Labeling isolé** (`simulate_isolated`) : outcome intrinsèque de chaque candidat pris seul, qty = 1 → `r/mfe/mae` invariants en taille, même broker que l'exécution réelle, parallèle par jour (EOD-flat). 7974 candidats fade étiquetés en ~70 s.
- **Décomposition brut/net rigoureuse** : le brut se mesure en relabelant à **frais = 0** (`r_multiple = pnl/risk0_réel`), jamais en reconstruisant `net + frais/risk0` (cf. piège ci-dessous).
- **Pré-enregistrement** anti-overfit pour le dernier levier (règle + critère de succès figés avant de voir les résultats).

## Leviers testés

| # | Levier | Résultat | Verdict |
|---|--------|----------|---------|
| 1 | Sortie (exit) | Portefeuille −0.267R ; intrinsèque 7974 candidats −0.306R, **38 % morts-nés** (MFE < 0.5R) à −1.19R | épuisé |
| 2 | Cible cappée (RR ≤ 2/3/4) | −0.306 → −0.27R, morts-nés inchangés | marginal |
| 3 | Trailing 1R | −0.298R (écrête les gros wins) | pire |
| 4 | Force du trigger (`stack_depth`/`stack_vol`) | la force prédit l'**échec**, pas le hold (vol fort → morts-nés 36→40 %) | rejeté |
| 5 | Direction (continuation au lieu de fade) | 14454 candidats −0.291R ≈ fade −0.306R | rejeté → **le stacked imbalance @ zone n'a aucune info directionnelle** |
| 6 | Timeframe (1 min → 15 min HTF) | net −0.184R mais **brut −0.042R** (l'amélioration nette = dilution des frais, pas un edge) | rejeté |
| 7 | **Mécanique d'entrée** (limit-au-trigger → stop sur **confirmation**) | tue des morts-nés (38→30 %), **brut −0.093R → +0.021R** ; mais **net −0.138R** | voir ci-dessous |
| 8 | No-BE (`move_to_be=False`) | net +0.01R (bruit) ; ne touche que la variance (wr 47→24 %, win ×2.3) | match nul |
| 9 | **Filtre régime tendance HTF** (pré-enregistré) | with-trend **PIRE** (brut −0.18R, sur IS *et* OOS) → hypothèse rejetée et inversée | rejeté |

## Le résultat central : un edge brut réel mais sous-marin

La **mécanique d'entrée** est le seul levier qui a bougé le brut. Le fill limit-au-trigger souffrait d'**adverse-selection** : on est rempli pile au niveau quand le prix le traverse à contresens, juste avant qu'il reparte contre nous (les morts-nés à `MFE = 0.00` filent droit au stop — visible sur la viz). Entrer en **stop sur confirmation** (après que le prix a avancé d'un risk0 dans le sens du trade) supprime ce drag :

```
fade, frac de confirmation 0 → 1 :   brut −0.093R → +0.021R   (monotone)
                                      morts-nés 38 % → 30 %, wr 47 % → 52 %
```

**Mais** :
1. Le vrai brut plafonne à **+0.021R, t = 0.83** → statistiquement **zéro**. On retire un négatif (l'adverse-selection), on révèle une pièce équilibrée, pas un profit.
2. Entrer sur confirmation est **structurellement taker** (traverser le spread sur momentum). Le surcoût taker (~0.16R) est supérieur au drag d'adverse-selection retiré (~0.11R). **Net −0.138R**, toujours nettement perdant.

Sensibilité aux frais (même cache) : taker = maker 0.02 % → −0.050R ; VIP+BNB 0.03 % → −0.073R. **Même à frais zéro, le plafond est +0.021R.** Aucun palier de frais réaliste ne croise zéro.

## Pièges méthodologiques (à ne pas répéter)

- **Décomposition du brut fausse en mode stop.** `brut = net + frais/risk0` divise les frais par le risk0 du *plan* (`entrée_plan − stop`). En mode stop, l'entrée réelle est décalée → `risk0_réel ≈ 2× risk0_plan` → terme de frais gonflé ~2× → **faux brut +0.18R « à 7σ »**, pur artefact. Toujours mesurer le brut en relabelant à frais = 0.
- **Cellule trompeuse.** Le filtre régime venait d'un seul jour (2025-12-16, 12/12 longs balayés en marché baissier). En agrégat, l'inverse tient. Une cellule visuelle n'est pas une hypothèse validée → pré-enregistrer.
- **Tentation post-hoc.** Le sous-ensemble counter-trend en mode stop est brut-positif et stable (IS +0.062 / OOS +0.050) — mais non pré-enregistré (= data-mining) **et net −0.100R** de toute façon. Écarté.

## Conclusion

Tous les leviers orderflow-natifs (sortie, features, cible, force, direction, timeframe, mécanique d'entrée, BE, régime) sont épuisés. Le brut est ≈ 0 partout ; le net est négatif partout, **fee-bound**. Le signal n'a pas d'edge directionnel récoltable sur BTCUSDT spot, déc. 2025 – juin 2026.

**Ce qui changerait le verdict** : un taux taker ≈ maker (~0.02 %, irréaliste pour une stratégie taker) ; ou une **autre famille de signal** ; ou un marché à coûts de transaction nettement plus bas.

**La valeur conservée** = l'infrastructure et la méthode (backtest 2-passes + labeling isolé + décomposition brut/net rigoureuse + pré-enregistrement + viz interactive), réutilisables pour tout futur pivot.

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
| 10 | **Filtre tendance locale** (momentum K=15 min à l'entrée, pré-enregistré) | DOUX **PIRE** que raide (brut −0.118 vs −0.068, limit) → hypothèse inversée ; **morts-nés 38 %/38 % identiques** (zéro pouvoir de séparation) → la grappe du 2025-12-16 était une cellule trompeuse, pas un pattern | rejeté |
| 11 | **Découpage temporel** (session UTC / jour de semaine / NFP, pré-test IS/OOS) | aucune session brut>0 (**NY 13-21 = moins pire ≈0, déjà la fenêtre live** 13-17) ; jeudi brut +0.164 = **mirage** (IS net −0.195, edge 100 % en OOS) ; **tous les jours moins-pires IS→OOS = décalage de régime H2**, pas un effet jour ; NFP **pire** (brut −0.158 vs −0.088) = filtre d'évitement, pas edge | rejeté |

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
- **Cellule trompeuse (×2).** Le filtre régime (#9) venait d'un seul jour (2025-12-16, 12/12 longs balayés en marché baissier) ; le filtre tendance locale (#10) de la même journée (grappes de fades qui plongent au même stop). Les deux fois, en agrégat l'inverse tient et les morts-nés ne bougent pas. Une cellule visuelle n'est pas une hypothèse validée → pré-enregistrer.
- **Tentation post-hoc.** Le sous-ensemble counter-trend en mode stop est brut-positif et stable (IS +0.062 / OOS +0.050) — mais non pré-enregistré (= data-mining) **et net −0.100R** de toute façon. Écarté.

## Audit anti-overfitting (López de Prado) — capstone

Après ~50 variantes/leviers testés, la question honnête : la moins-pire config a-t-elle la moindre chance d'être réelle, ou est-ce du bruit sélectionné ? Outil = **Deflated Sharpe Ratio** (`scripts/overfit_audit.py`, self-test validé : PBO bruit→0.5, dominante→0). Sur 14 configs (sessions/jours/tendance), meilleur Sharpe net = **+1.28 annualisé** ; seuil de bruit SR0 (Sharpe max attendu de N essais de hasard) = **+3.59 (N=14) / +4.70 (N=50)**. Le best est très en-dessous → **DSR = 0.052 (N=14), 0.008 (N=50)** : probabilité d'un vrai edge après correction multiple-testing ≈ **zéro**. Même en gonflant le best (biais d'exposition, cf. ci-dessous), il échoue → conclusion conservatrice.

**Caveat PBO (=0.24, non retenu).** CSCV suppose N stratégies à exposition comparable ; mes configs sont des *filtres* (un « mardi seulement » est flat 6 j/7 → paraît faussement persistant car flat ≈ moins négatif que perdre tous les jours). Le PBO est donc contaminé ici ; un PBO propre exige une grille de params à exposition égale. Le DSR n'a pas ce défaut (il déflate le meilleur Sharpe quoi qu'il arrive) → on tranche sur le DSR.

**Note sizing.** Purged/embargoed CV : nos trades sont EOD-flat (zéro overnight) → pas de chevauchement de labels inter-jours → purge quasi-moot ici (embargo implémenté dans le CSCV par rigueur, utile pour un pivot à hold long). Vol-targeting (EWMA) : module le sizing, **ne crée pas d'edge** (Kelly d'une espérance ≤0 = 0) → infra pour un futur signal, pas un sauvetage.

## Phase 0 DOM/L2 — la cécité-tape mise à l'épreuve (KILL, 2026-06-14)

Hypothèse de dégel : le tape est *aveugle aux ordres limites au repos*. L'absorption vraie (un mur de bids qui encaisse et tient) et le spoofing (un mur retiré avant l'impact) sont invisibles au tape mais lisibles au **carnet L2** — peut-être séparent-ils les fades morts-nés (MFE < 0.5R) que le tape confond. Test **pré-enregistré** sur 7 jours `book_snapshot_25` Tardis gratuits (BTCUSDT, déc. 2025 → juin 2026) : 4 features carnet — `book_defense` (liq défensive normalisée), `touch_imbalance` (déséquilibre defend/oppose dans la bande), `replenish` (recharge iceberg), `pull_rate` (annulations type spoof) — jointes au carnet à l'instant du fill, **sans lookahead**. Greenlight anti-mirage à 4 conditions : c1 meilleure AUC carnet ≥ 0.60 ; c2 lift par quartile monotone ; c3 signe stable ≥ 6/7 jours ; c4 bat le meilleur tape de ΔAUC ≥ 0.05.

```
n = 312 candidats (7 jours) | base mort-né = 0.474
carnet  book_defense 0.504 | touch_imbalance 0.535 | replenish 0.473 | pull_rate 0.524
tape    stack_vol 0.512 | stack_depth 0.521
best carnet touch_imbalance 0.535  vs  best tape 0.521  (ΔAUC +0.014)
c1=False  c2=True  c3=False (4/7)  c4=False        →  KILL thèse L2
```

Le carnet ne sépare **pas** les morts-nés mieux que le tape : meilleure feature L2 = 0.535 AUC ≈ aléatoire (0.5), +0.014 vs tape ≈ zéro. La cécité-tape n'était **pas** le facteur manquant — l'information des ordres au repos n'ajoute aucun signal orthogonal pour ce signal sur ce marché. *Caveat* : n=312, 7 jours premier-du-mois (tier gratuit Tardis) = sous-puissant ; mais l'écart à franchir (0.535 → 0.60 ; ΔAUC 0.014 → 0.05) est large, pas borderline — un effet réel mais ténu resterait sous le seuil de récolte nette de toute façon. Infra réutilisable pour un pivot signal : `features/book.py` (loader + 4 features sans lookahead), `backtest/separation.py` (AUC tie-aware + lift + verdict pré-enregistré), `scripts/dom_separation.py`.

## Conclusion

Tous les leviers orderflow-natifs (sortie, features, cible, force, direction, timeframe, mécanique d'entrée, BE, régime HTF, tendance locale, découpage temporel session/jour/calendrier) sont épuisés. Le brut est ≈ 0 partout ; le net est négatif partout, **fee-bound**. Le signal n'a pas d'edge directionnel récoltable sur BTCUSDT spot, déc. 2025 – juin 2026.

**Ce qui changerait le verdict** : un taux taker ≈ maker (~0.02 %, irréaliste pour une stratégie taker) ; ou une **autre famille de signal** ; ou un marché à coûts de transaction nettement plus bas.

**La valeur conservée** = l'infrastructure et la méthode (backtest 2-passes + labeling isolé + décomposition brut/net rigoureuse + pré-enregistrement + viz interactive + audit anti-overfit DSR/PBO/CSCV + séparation DOM/L2 (AUC tie-aware / lift / greenlight pré-enregistré)), réutilisables pour tout futur pivot.

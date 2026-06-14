# Spec — Features DOM/L2 (Phase 0) : séparer les morts-nés

**Date :** 2026-06-14
**Statut :** design validé, prêt pour plan d'implémentation
**Track :** option (b) — tester si le L2 (order book) débloque un edge que le tape seul a manqué.

## Contexte

La v1 a été bâtie sur le **tape spot seul** (trades) et prouvée **no-edge** jusqu'à
l'audit anti-overfit López de Prado (DSR(N=50)=0.008, PBO contaminé écarté). L'audit
data 2026-06-14 confirme que ce no-edge **n'est pas un artefact** : 220 M rows, 0 gap
>60 s, 0 ts hors-ordre, dupes 2,53 % bénins (bot-splitting, pas re-DL).

Mais le gap-audit v1 montre que le no-edge a été établi sur la surface **la plus pauvre**
des couches 1–3 : `absorption.py` **infère** l'absorption des trades (gros volume + range
serré + delta), **aveugle à l'ordre limite au repos qui absorbe**. La logique DOM du spec
v1 (*liquidité réellement consommée vs affichée, anti-spoofing*) n'a jamais été testée —
impossible sans order book.

Phase 0 acquise ($0) : `scripts/download_tardis_l2.py` a téléchargé 7 jours
`book_snapshot_25` BTCUSDT (1er-du-mois gratuit Tardis, 2025-12-01 → 2026-06-01) dans
`data/l2/BTCUSDT/`. Ces 7 jours **chevauchent le tape** → cross-check possible.

## Objectif & critère de succès

**Question Phase 0 :** une feature book, calculée à l'entrée d'un fade, **sépare-t-elle
les morts-nés** (fade rempli puis qui file droit au stop, `mfe_r < 0.5`) des fades qui
tiennent — **mieux que les features tape actuelles** ?

Les **38 % de morts-nés uniformes** sont la cause racine du no-edge (adverse-selection au
fill limit : on est rempli pile quand le prix continue dans l'autre sens). Si le book
révèle, à l'entrée, que le niveau fadé a une liquidité défensive **réelle** (tient) vs
**fine/spoofée** (casse), c'est le signal manquant.

**Non-objectif Phase 0 :** prédire le R final (sortie déjà épuisée, dilue le signal),
backtester (7 jours non-contigus → impossible), intégrer au live. Phase 0 = **signal-of-life**.

## Périmètre

- **Dans le scope :** loader `book_snapshot_25`, 4 features book+tape, mesure de séparation
  des morts-nés sur les 7 jours, rapport + greenlight pré-enregistré.
- **Hors scope :** reconstruction `incremental_book_L2` (inutile, on a les snapshots),
  intégration `ConfluenceEngine`, sizing, backtest, live.

## Architecture

| Fichier | Rôle |
|---|---|
| `src/orderflow_bot/features/book.py` | **NEUF** — loader `book_snapshot_25` (µs→ms centralisé) + les 4 features. Pur, sans I/O réseau, testable. |
| `scripts/dom_separation.py` | **NEUF** — orchestration : génère+labelle les candidats des 7 jours, joint le book, calcule les features, sort le rapport. |
| `tests/test_book.py` | **NEUF** — unit tests sur books synthétiques. |

### Flux (par jour, ×7)

```
tape Parquet (continu déc→juin) ──> generate_plans(cfg, jour, warmup 20j depuis tape)
                                       └─ warmup dispo car tape contigu
                                       ▼
                                   candidats (OrderPlan: ts, entry, stop, side)
                                       │
                                   simulate_isolated(jour) ──> ClosedTrade (mfe_r)
                                       │                         └─ label mort-né = mfe_r < 0.5
book_snapshot_25(jour) ──> Book ──> book_at(t) / book_window(t0,t1)  (bisect sur ts ms)
                                       │
                                   4 features(candidat, book, tape)  [fenêtre finissant au fill opened_ts]
                                       ▼
                                   rapport séparation (AUC + lift + check par-jour)
```

- `book_snapshot_25` = **déjà des snapshots** (top 25 niveaux/ligne, ~100 ms ou sur
  changement) → **zéro reconstruction**. `book_at(t)` = dernier snapshot ≤ t (bisect).
- Config réutilisée = `config.yaml` (le fade qui a donné le no-edge), pour que la
  population de candidats soit **identique** à celle déjà étudiée.
- Un jour en mémoire à la fois (≈ 700 k snapshots × arrays price/amount ; 7 jours = 624–815 k).

## Les 4 features

**Conventions.** `side = plan.side` (+1 long / −1 short). Fade-long → bounce attendu →
**défenseurs = BIDS** ; fade-short → défenseurs = ASKS. `oppose` = l'autre côté.
Bande = `entry ± band_ticks` (défaut 10). Fenêtre dynamique `W` finit au **fill `opened_ts`**
(défaut 2 s). Tout est mesuré **sans lookahead** (fenêtre finissant au fill).

| # | Feature | Type | Formule | Sens pré-enregistré |
|---|---|---|---|---|
| 1 | `book_defense` | statique @fill | Σ amount défenseur dans la bande ÷ médiane **trailing** du book total (fenêtre glissante causale, pas de lookahead intra-jour) | **haut → tient** |
| 2 | `touch_imbalance` | statique @fill | (défend − oppose)/(défend + oppose) dans la bande, ∈ [−1,1] | **haut → tient** |
| 3 | `replenish` (iceberg) | dynamique W | volume tape traversant la bande défenseur sur W ÷ taille défenseur affichée au début de W (>1 = plus mangé qu'affiché = recharge cachée) | **haut → tient** |
| 4 | `pull_rate` (spoof) | dynamique W | baisses de taille défenseur affichée **non** expliquées par le volume tape (annulations) ÷ taille initiale | **haut → meurt** |

Le couple **3/4 = le cœur real-vs-fake** : mur mangé puis rechargé (3 haut) = vrai
défenseur iceberg → tient ; mur qui disparaît sans trades (4 haut) = spoof retiré → casse.
1/2 = baseline statique cheap, mais piégeable par le spoof — c'est 4 qui le démasque.

**Causalité / tradeable :** `pull`/`replenish` sur l'approche sont observables avant/au fill
(un bot pourrait annuler le limit) ; `book_defense`/`touch` au fill = observables au fill.
Zéro info future.

## Validation & greenlight (PRÉ-ENREGISTRÉ)

**Label :** mort-né = `mfe_r < 0.5` (déf projet). Taux de base ≈ 38 %.

**Mesure par feature :** AUC(feature → mort-né) ; table de lift par quartile (Q1→Q4 →
taux de morts-nés) ; baseline = AUC des features tape `stack_vol`, `stack_depth`
(déjà dans `plan.meta`).

Vu l'historique du projet (jeudi +0,164 / cellule US 14-21 = **mirages post-hoc**), les
critères sont **figés avant de regarder les résultats**. Greenlight Phase 1 ⇔ **les 4** :

1. ≥ 1 feature book avec **AUC ≥ 0,60**.
2. Son **lift monotone** sur les quartiles, dans le **sens pré-enregistré** ci-dessus.
3. **Signe de l'effet stable sur ≥ 6/7 jours** (pas porté par 1 jour — ce qui a tué #9/#10/#11).
4. Bat la **meilleure feature tape** d'une marge nette (**ΔAUC ≥ 0,05**).

- **Tout vrai** → greenlight : payer/collecter l'historique L2 complet (Tardis Academic
  ou self-record `@depth` gratuit en avant), puis vrai test edge (DSR/PBO) sur grand échantillon.
- **Sinon** → kill la thèse L2, $0 dépensé.

**Honnête :** 7 jours = IC large sur l'AUC. La barre est volontairement **fort + stable
par-jour**, pas signif marginale. Phase 0 ne prouve pas un edge ; elle décide si ça vaut
le coût de la Phase 1.

## Error handling

- Jour sans candidat → skip.
- Feature NaN (entry hors des top-25 niveaux, ou trou de snapshot près de t) → candidat
  exclu, **taux d'exclusion loggé** (taux élevé = book trop peu profond pour ce niveau = info).
- µs→ms : conversion centralisée dans le loader.

## Tests (`tests/test_book.py`, synthétiques, .venv pytest)

- `book_at` / `book_window` : bisect correct (avant 1er snapshot → None ; pile sur ts ; entre deux).
- `book_defense` : book connu → somme/normalisation attendues.
- `touch_imbalance` : book symétrique → 0 ; bid-lourd → positif (long) et négatif (short).
- `replenish` : séquence mangé-puis-rechargé + trades → >1 ; book statique sans trade → 0.
- `pull_rate` : taille disparue sans trade → haut ; taille mangée par trades → 0 (consommation ≠ pull).

## Sortie

`dom_separation.html` (Plotly dark, cohérent avec les autres viz) : table AUC (book vs
tape), barres de lift par quartile/feature, bande signe par-jour, + résumé stdout avec le
verdict greenlight (4 conditions cochées ou non).

## Phase 1 (ce que le greenlight débloque)

Hors scope ici. Si greenlight : acquérir l'historique L2 contigu (Tardis payant Academic
OU self-record `@depth` Binance gratuit en avant), ré-générer les features sur T ~ 100+
jours, et trancher l'edge avec le toolkit existant (DSR/PBO/walkforward). Aucun sizing ne
sauve une espérance ≤ 0 — le greenlight est nécessaire, pas suffisant.

# Étage 2a — Ingestion klines (fondation data) — Design

> Sous-projet du redeploy swing. Étage 2 = swing-CONTINUATION sur klines multi-années,
> découpé en **2a** (cette fondation data) puis **2b** (trigger VA-breakout + drift gate + verdict).
> Pré-requis : étage 1 (fade-vers-value) KILL gate 1 — miroir +0.271R = drift pur (BTC −29.6 %,
> mono-régime). Leçon : un échantillon mono-régime ne sépare pas l'edge-de-niveau du drift.

## 1. Contexte et objectif

L'étage 2 teste le hint *continuation* (breakout du bord de value area) sur **9 ans de
BTCUSDT 1m** — assez de régimes (bull 2020-21, bear 2022, reprise 2023-25) pour que le drift
directionnel s'annule, condition sine qua non pour isoler un edge de niveau.

Le moteur backtest consomme un flux de `Trade` (ticks). Les klines sont des barres OHLCV 1m.
**2a** bâtit le pont : télécharger, parser et **adapter** les klines en ticks synthétiques qui
pilotent le moteur **existant intact** (VP, zones, agrégateur 4h, `simulate_isolated`), puis
vérifier par un **smoke-plomberie** que la chaîne klines→zones→plans→labels tourne sainement.

**2a ne fait AUCUNE prétention d'edge.** Pas de signal nouveau, pas de gate de drift, pas de
verdict. Pur plombage de données. Le smoke est une sanité mécanique — **à ne PAS relire comme
une mesure d'edge** (ce serait re-fabriquer un mirage sur sous-échantillon).

## 2. Architecture

**Adaptateur kline → ticks synthétiques** (approche retenue ; bar-native VP et vrais aggTrades
9 ans rejetés : réécriture du cœur pour la 1re, centaines de Go pour la 2de).

Insight porteur : le **footprint/delta est mort** pour la thèse VA-breakout (elle lit VP +
OHLC de barre, jamais le delta/imbalance par niveau). Donc les ticks synthétiques **n'ont pas
besoin d'un buy/sell fidèle** — `is_buyer_maker` est arbitraire et jamais lu par le chemin
swing. L'adaptateur reste trivial et honnête : on ne fabrique aucun delta qu'on utiliserait.

```
zip mensuel data.binance.vision  →  parser  →  Parquet (ts,O,H,L,C,V)
                                                      │
                                       read_klines_as_ticks  (4 Trade synthétiques / kline)
                                                      │
                              read_market(cfg)  ─dispatch trades|klines─┐
                                                      │                  │
                          generate_plans_parallel (passe-1)      simulate_isolated(eod_flat=False)
                                  (VP, zones, trigger)                 (labeling séquentiel)
```

## 3. Contrat tick-synthétique (figé)

Chaque kline 1m `(open_time, O, H, L, C, V)` → **exactement 4** `Trade` :

| # | price | qty | ts (offset depuis open_time) | kind |
|---|-------|-----|------------------------------|------|
| 1 | O     | V/4 | +0 ms        | open  |
| 2 | H     | V/4 | +20 000 ms   | high  |
| 3 | L     | V/4 | +40 000 ms   | low   |
| 4 | C     | V/4 | +59 999 ms   | close |

`is_buyer_maker = False` (jamais lu sur le chemin swing).

**Invariants garantis** (la raison du choix à 4 ticks) :
- La barre 4h reconstruite par `BarAggregator` (bucket `ts // bar_ms`) a `open` = 1er tick,
  `high` = max, `low` = min, `close` = **dernier** tick → exactement `O/H/L/C` agrégés sur la
  fenêtre. Le trigger de niveau (qui lit l'OHLC de barre) reçoit donc la bonne géométrie.
- Le `VolumeProfile` reçoit `V/4` aux 4 prix → volume-au-prix étalé sur `[L, H]`. L'ordre
  H-avant-L est sans effet (VP order-agnostic ; high/low = max/min).
- `ts` strictement croissant entre klines (open_time + 60 000 par minute) → `read_trades`
  fast-path par bornes de footer reste valide ; au sein d'une kline les ts sont distincts
  (offsets 0/20k/40k/59999) → aucun cas d'égalité de ts.
- **Aucune kline ne chevauche une frontière de bloc** (garantit l'équivalence
  parallèle≡séquentiel de `generate_plans_parallel`) : les 4 ticks d'une kline restent dans
  la même minute, et `start_ms` minute-aligné (un open_time) ⇒ bornes `start_ms + k·DAY`
  minute-alignées (DAY = 86 400 000 est multiple de 60 000). La kline `open_time == b_end`
  part au bloc suivant, celle d'avant (ticks ≤ b_end−1) reste — partition propre.

**Approximation assumée** : un VP construit sur O/H/L/C sur-pondère les extrêmes (H et L de
chaque barre) vs un VP tick-réel. Agrégé sur des milliers de klines (profil multi-jours) la
value area émerge quand même de la distribution des prix ; le smoke-plomberie (§7) vérifie la
non-dégénérescence. Le signal VA-breakout (2b) lit les **bords** de VA, eux-mêmes définis par
cette même construction → biais cohérent, pas contaminant. Raffinement (distribution sur N
bins) reporté si le smoke révèle des zones dégénérées.

## 4. Composants et interfaces

### 4.1 Config (`src/orderflow_bot/config.py`)
Ajouts à `BotConfig` (chemin trades par défaut → **comportement existant inchangé**) :
```python
data_format: Literal["trades", "klines"] = "trades"

@property
def kline_data_dir(self) -> str:
    """Racine des klines : data_dir/klines/market. Distinct des trades
    (data_dir/market) — schémas Parquet incompatibles, jamais mélangés."""
    return f"{self.data_dir}/klines/{self.market}"
```

### 4.2 Downloader (`scripts/download_klines.py`, nouveau)
Télécharge les zips mensuels `data.binance.vision/data/spot/monthly/klines/{SYMBOL}/1m/
{SYMBOL}-1m-{YYYY}-{MM}.zip` (URL confirmée par la 1re tâche), vérifie le `.CHECKSUM` SHA256,
extrait le CSV, écrit un Parquet/mois. **Idempotent** : un mois déjà présent est sauté (comme
`ingestion/importer.py`). Couverture mensuelle ≈ T−1 mois ; le mois courant (dumps *daily*)
est hors-périmètre 2a.

### 4.3 Parser (`src/orderflow_bot/ingestion/klines.py`, nouveau)
`parse_kline_csv(path) -> pyarrow.Table` (colonnes `ts,open,high,low,close,volume`).
Colonnes CSV Binance : `open_time, open, high, low, close, volume, close_time, quote_volume,
count, taker_buy_base, taker_buy_quote, ignore` → on retient `open_time→ts` + OHLCV.
**Normalisation `ts`** : Binance a publié certains dumps récents en microsecondes (16 chiffres).
Si `ts > 10^15`, diviser par 1000 → ms. Garde-fou explicite, testé.

### 4.4 Reader (`src/orderflow_bot/ingestion/reader.py`, ajout)
```python
def read_klines_as_ticks(
    data_dir: str | Path, symbol: str,
    start_ms: int | None = None, end_ms: int | None = None,
) -> Iterator[Trade]:
    """Streame les klines Parquet (ordonnées par ts) et yield 4 Trade
    synthétiques/kline (contrat §3). Signature drop-in de read_trades."""
```
Réutilise le même streaming DuckDB/ordonnancement par footer que `read_trades`. La fenêtre
`[start_ms, end_ms)` filtre sur `open_time` (la kline dont l'open est dans la fenêtre).

### 4.5 Résolveur (`src/orderflow_bot/ingestion/reader.py`, ajout)
```python
def read_market(cfg, start_ms=None, end_ms=None) -> Iterator[Trade]:
    """Dispatch unique trades|klines selon cfg.data_format. Point d'entrée
    du chemin swing parallèle/séquentiel."""
    if cfg.data_format == "klines":
        return read_klines_as_ticks(cfg.kline_data_dir, cfg.symbol, start_ms, end_ms)
    return read_trades(cfg.market_data_dir, cfg.symbol, start_ms, end_ms)
```

### 4.6 Câblage (`src/orderflow_bot/pipeline.py`, modif minimale)
`_block_worker` (passe-1 parallèle) : `read_trades(cfg.market_data_dir, cfg.symbol, …)` →
`read_market(cfg, …)`. **Behavior-preserving** pour les trades (`data_format` défaut `trades`).
- `_isolated_block_worker` / `simulate_isolated_parallel` : **NON touchés** (tail_days=1
  inutilisable pour holds swing multi-jours ; le labeling swing reste séquentiel).
- `live.py`, `__main__.py`, `scripts/plot_*`, `dom_separation.py` : **NON touchés** (outils
  trades intraday, hors-périmètre).

### 4.7 Orchestrateur smoke (`scripts/klines_smoke.py`, nouveau)
Mince : charge `config.klines.yaml`, `generate_plans_parallel` (klines, trigger
`level_rejection` existant), `simulate_isolated(eod_flat=False)`, applique les asserts §7,
imprime PASS/FAIL. Les helpers vérifiables vivent dans le package (cf. §10), pas dans le script.
Les bornes `[start_ms, end_ms]` passées à `generate_plans_parallel` sont dérivées de l'étendue
réelle des klines (open_times) → minute-alignées par construction (cf. invariant §3).

### 4.8 Config run (`config.klines.yaml`, nouveau)
`data_format: klines`, `symbol: BTCUSDT`, `bar_minutes: 240`, `eod_flat: false`,
`trigger: level_rejection`, `tick_size: 0.01`, caps risque détendus (comme `config.swing.yaml`).

## 5. Flux de données
1. `download_klines.py` → `data/klines/spot/BTCUSDT/BTCUSDT-1m-YYYY-MM.parquet` (×~108 mois).
2. `read_market(cfg)` (klines) → flux `Trade` synthétiques ordonné par ts.
3. `generate_plans_parallel` : un process/bloc de jours, chacun lit ses Parquet (warmup inclus),
   bâtit VP/zones, tire `level_rejection` → plans candidats.
4. `simulate_isolated(eod_flat=False)` : labeling séquentiel, holds multi-jours, censure des
   queues ouvertes en fin de data (`kind="eod"`).

## 6. Smoke-plomberie (gate 2a — PASS/FAIL, zéro edge)

Sur une fenêtre réelle téléchargée (≥ 2 mois, assez pour ≥ 1 profil composite + zones) :

**A. Zones saines** (sur ≥ 1 jour finalisé) :
- `VAL ≤ POC ≤ VAH` pour chaque `DailyLevels`.
- POC dans `[day_low, day_high]`.
- Largeur VA `(VAH−VAL)` ∈ `]0, day_high−day_low]` (non nulle, non aberrante).
- Au moins 1 zone construite par `build_zones`.

**B. Plans cohérents** (`generate_plans` + `level_rejection`) :
- ≥ 1 plan produit sur la fenêtre.
- Géométrie : long → `stop < entry < target` ; short → `target < entry < stop`.
- `RR ≥ cfg.risk.min_rr` pour chaque plan (déjà garanti par `ConfluenceEngine`, on l'assert).

**C. Labels finis** (`simulate_isolated(eod_flat=False)`) :
- Tout `r_multiple` fini (pas de NaN/inf).
- La censure tire : ≥ 1 label `kind=="eod"` si une position reste ouverte en fin de data,
  OU tous résolus stop/target (les deux sont des PASS — on vérifie l'absence de plantage).

**PASS** = A ∧ B ∧ C. **FAIL** = klines ne pilotent pas le moteur sainement → stop, diagnostic
avant d'engager 2b. Aucun seuil de performance ici.

## 7. Hors-périmètre (→ 2b)
- Trigger VA-breakout (clôture au-delà de VAH/VAL + cible niveau suivant).
- Drift gate : symétrie long/short (`brut_long>0 ∧ brut_short>0`), split régime (trailing 90 j),
  miroir battu, t>2, DSR, CV purged+embargo, **net>0**.
- Pré-enregistrement des critères d'edge.
- Parallélisation du labeling (reste séquentiel ; suffisant car VA-breakouts rares → peu de
  positions concurrentes).
- Dumps *daily* / mois courant ; multi-symboles.

## 8. Limitations connues
- VP O/H/L/C coarse vs tick-réel (§3) — assumé, vérifié non-dégénéré par le smoke.
- Couverture klines jusqu'à T−1 mois (monthly only).
- `read_market` ne couvre que le chemin swing parallèle ; les outils trades gardent
  `read_trades` en direct (intacts).

## 9. Stratégie de test
- **Unitaires** (tmp Parquet synthétiques) : parser (mapping colonnes + normalisation µs→ms) ;
  `read_klines_as_ticks` (4 ticks/kline, ts/offsets, V/4, ordre close-last, fenêtre `[start,end)`,
  reconstruction barre 4h exacte via `BarAggregator`) ; `read_market` (dispatch trades vs klines) ;
  `kline_data_dir`.
- **Helpers smoke** (`backtest/`, vérifiables hors script) : asserts A/B/C en fonctions pures
  testées sur fixtures.
- **Intégration** : `_block_worker`/`generate_plans_parallel` inchangés sur trades (régression :
  un run trades existant donne le même résultat).

## 10. Frontière de code
- **Réutilisé intact** : `VolumeProfile`, `BarAggregator`, `build_zones`, `ConfluenceEngine`,
  `level_rejection_triggers`, `PaperBroker`, `simulate_isolated`, `generate_plans[_parallel]`,
  `read_trades`, métriques/DSR.
- **Nouveau** : `download_klines.py`, `ingestion/klines.py`, `read_klines_as_ticks`,
  `read_market`, `klines_smoke.py`, helpers smoke, `config.klines.yaml`.
- **Modifié** : `config.py` (+`data_format`, +`kline_data_dir`), `pipeline.py` (`_block_worker`
  → `read_market`).

## 11. Condition de succès 2a
Le smoke-plomberie PASS sur ≥ 2 mois de klines réels téléchargés, les tests trades existants
restent verts (zéro régression), et la chaîne klines→VP→zones→plans→labels tourne de bout en
bout. Alors → greenlight 2b (trigger VA-breakout + drift gate). FAIL → diagnostic data avant
tout signal.

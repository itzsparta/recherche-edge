# Étage 2a — Ingestion klines (fondation data) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bâtir le pont klines→ticks synthétiques pour piloter le moteur backtest existant intact sur 9 ans de BTCUSDT 1m, puis vérifier par un smoke-plomberie PASS/FAIL que la chaîne klines→VP→zones→plans→labels tourne sainement.

**Architecture:** Chaque kline 1m devient 4 `Trade` synthétiques {O,H,L,C} (close-last, V/4) qui reconstruisent exactement la barre 4h et étalent le volume-au-prix. Un résolveur `read_market` dispatch trades|klines selon `cfg.data_format` ; seul `_block_worker` (passe-1 parallèle) est recâblé, le reste intact. **Aucune prétention d'edge** : le smoke est une sanité mécanique (pas une mesure de performance).

**Tech Stack:** Python 3.11, pydantic v2, DuckDB, pyarrow, pytest. Spec : `docs/superpowers/specs/2026-06-17-klines-ingestion-design.md`.

**Contraintes projet (IMPÉRATIF) :**
- Python = `.venv/Scripts/python.exe` (le `python` nu est un autre venv sans pytest).
- Le repo git est enraciné à `C:\Projets` (multi-projets). **Jamais `git add .` / `git add -A`** — toujours `git add <chemins spécifiques>` (natif, pas `rtk git add`), puis vérifier `git diff --cached --stat`.
- Branche de travail : `feat/orderflow-klines-ingestion` (déjà créée, spec déjà commitée dessus).
- `brut` ne se mesure jamais ici (2a = zéro edge) ; pas de pré-enregistrement nécessaire.

---

## File Structure

| Fichier | Rôle | Action |
|---|---|---|
| `src/orderflow_bot/config.py` | `data_format` + `kline_data_dir` | Modifier |
| `src/orderflow_bot/ingestion/klines.py` | CSV kline Binance → Parquet (ts,O,H,L,C,V) | Créer |
| `src/orderflow_bot/ingestion/reader.py` | `_ordered_parquet`/`_window_sql` (extraits), `read_klines_as_ticks`, `read_market` | Modifier |
| `src/orderflow_bot/pipeline.py` | `_block_worker` → `read_market` | Modifier |
| `scripts/download_klines.py` | Téléchargement mensuel idempotent | Créer |
| `src/orderflow_bot/backtest/plumbing_checks.py` | Helpers PASS/FAIL purs (zones/plans/labels) | Créer |
| `scripts/klines_smoke.py` | Orchestrateur smoke (le gate 2a) | Créer |
| `config.klines.yaml` | Config run klines | Créer |
| `tests/test_klines_parser.py`, `tests/test_klines_reader.py`, `tests/test_read_market.py`, `tests/test_klines_download.py`, `tests/test_plumbing_checks.py` | Tests | Créer |

---

### Task 1: Config — `data_format` + `kline_data_dir`

**Files:**
- Modify: `src/orderflow_bot/config.py` (classe `BotConfig`, après `market` ligne ~86 et la property `market_data_dir`)
- Test: `tests/test_config.py` (ajout)

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/test_config.py` :
```python
def test_kline_data_dir_distinct_from_trades():
    cfg = BotConfig(data_dir="data", market="spot")
    assert cfg.market_data_dir == "data/spot"
    assert cfg.kline_data_dir == "data/klines/spot"

def test_data_format_defaults_to_trades():
    assert BotConfig().data_format == "trades"

def test_data_format_klines_accepted():
    assert BotConfig(data_format="klines").data_format == "klines"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_config.py::test_kline_data_dir_distinct_from_trades -v`
Expected: FAIL (`AttributeError: 'BotConfig' object has no attribute 'kline_data_dir'`)

- [ ] **Step 3: Write minimal implementation**

Dans `src/orderflow_bot/config.py`, classe `BotConfig`, ajouter le champ après `market: Literal["spot", "futures"] = "spot"` :
```python
    data_format: Literal["trades", "klines"] = "trades"
```
Et ajouter la property après `market_data_dir` :
```python
    @property
    def kline_data_dir(self) -> str:
        """Racine des klines : data_dir/klines/market. Distincte des trades
        (data_dir/market) — schemas Parquet incompatibles, jamais melanges."""
        return f"{self.data_dir}/klines/{self.market}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_config.py -v`
Expected: PASS (tous, dont les 3 nouveaux)

- [ ] **Step 5: Commit**

```bash
git add src/orderflow_bot/config.py tests/test_config.py
git commit -m "feat(orderflow): config data_format + kline_data_dir [2a]"
```

---

### Task 2: Parser CSV kline → Parquet

**Files:**
- Create: `src/orderflow_bot/ingestion/klines.py`
- Test: `tests/test_klines_parser.py`

Colonnes CSV Binance klines (12, ordre fixe) : `open_time, open, high, low, close, volume, close_time, quote_volume, count, taker_buy_base, taker_buy_quote, ignore`. On retient `open_time→ts` + OHLCV. Certains dumps récents publient `open_time` en microsecondes (16 chiffres) → normaliser comme `importer.convert_csv` (seuil `1e14`).

- [ ] **Step 1: Write the failing test**

`tests/test_klines_parser.py` :
```python
import pyarrow.parquet as pq

from orderflow_bot.ingestion.klines import convert_kline_csv

# 12 colonnes, sans header (format historique spot)
_MS_ROW = "1577836800000,7195.24,7196.25,7178.64,7179.78,1004.5,1577836859999,7218000,1200,500.0,3600000,0\n"
# meme barre mais open_time en microsecondes (recent) -> doit etre normalise en ms
_US_ROW = "1577836800000000,7195.24,7196.25,7178.64,7179.78,1004.5,1577836859999000,7218000,1200,500.0,3600000,0\n"


def test_parses_ohlcv_and_keeps_ms(tmp_path):
    csv = tmp_path / "k.csv"
    csv.write_text(_MS_ROW, encoding="utf-8")
    out = tmp_path / "k.parquet"
    n = convert_kline_csv(csv, out)
    assert n == 1
    tbl = pq.read_table(out).to_pylist()[0]
    assert tbl == {"ts": 1577836800000, "open": 7195.24, "high": 7196.25,
                   "low": 7178.64, "close": 7179.78, "volume": 1004.5}


def test_normalizes_microseconds_to_ms(tmp_path):
    csv = tmp_path / "k.csv"
    csv.write_text(_US_ROW, encoding="utf-8")
    out = tmp_path / "k.parquet"
    convert_kline_csv(csv, out)
    assert pq.read_table(out).to_pylist()[0]["ts"] == 1577836800000


def test_parses_with_header(tmp_path):
    header = "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_base,taker_buy_quote,ignore\n"
    csv = tmp_path / "k.csv"
    csv.write_text(header + _MS_ROW, encoding="utf-8")
    out = tmp_path / "k.parquet"
    assert convert_kline_csv(csv, out) == 1
    assert pq.read_table(out).to_pylist()[0]["ts"] == 1577836800000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_klines_parser.py -v`
Expected: FAIL (`ModuleNotFoundError: orderflow_bot.ingestion.klines`)

- [ ] **Step 3: Write minimal implementation**

`src/orderflow_bot/ingestion/klines.py` :
```python
"""Import des archives klines 1m data.binance.vision (gratuites).

CSV Binance klines : 12 colonnes, ordre fixe, avec ou sans header. open_time
en ms ou (dumps recents) en microsecondes. Conversion -> schema Parquet
(ts ms, open, high, low, close, volume) consomme par read_klines_as_ticks."""

from pathlib import Path

import duckdb
import pyarrow.parquet as pq

# au-dela de ce seuil open_time est en microsecondes (1e14 ms ~ annee 5138)
_US_THRESHOLD = 100_000_000_000_000

_KLINE_COLS = {
    "open_time": "BIGINT", "open": "DOUBLE", "high": "DOUBLE", "low": "DOUBLE",
    "close": "DOUBLE", "volume": "DOUBLE", "close_time": "BIGINT",
    "quote_volume": "DOUBLE", "count": "BIGINT", "taker_buy_base": "DOUBLE",
    "taker_buy_quote": "DOUBLE", "ignore": "DOUBLE",
}


def _has_header(csv_path: Path) -> bool:
    with open(csv_path, encoding="utf-8") as f:
        return f.readline().startswith("open_time")


def convert_kline_csv(csv_path: str | Path, out_parquet: str | Path) -> int:
    """CSV klines 1m -> un Parquet ordonne par ts (ms). Retourne le nb de barres."""
    csv_path = Path(csv_path)
    has_header = _has_header(csv_path)
    cols_sql = ", ".join(f"'{c}': '{t}'" for c, t in _KLINE_COLS.items())
    con = duckdb.connect()
    try:
        table = con.execute(
            f"""
            SELECT CASE WHEN open_time >= ? THEN open_time // 1000
                        ELSE open_time END AS ts,
                   open, high, low, close, volume
            FROM read_csv(?, header={'true' if has_header else 'false'},
                          columns={{{cols_sql}}})
            ORDER BY ts
            """,
            [_US_THRESHOLD, str(csv_path)],
        ).fetch_arrow_table()
    finally:
        con.close()
    pq.write_table(table, out_parquet)
    return table.num_rows
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_klines_parser.py -v`
Expected: PASS (3)

- [ ] **Step 5: Commit**

```bash
git add src/orderflow_bot/ingestion/klines.py tests/test_klines_parser.py
git commit -m "feat(orderflow): parser CSV klines->Parquet (norm us->ms) [2a]"
```

---

### Task 3: Reader — extraction `_ordered_parquet`/`_window_sql` + `read_klines_as_ticks`

**Files:**
- Modify: `src/orderflow_bot/ingestion/reader.py` (refactor `read_trades` lignes 40-98, ajout reader klines)
- Test: `tests/test_klines_reader.py`
- Régression: `tests/test_storage.py` (doit rester vert — prouve le refactor sans régression)

Le refactor extrait la planification de fichiers (commune trades/klines) en un helper ; `read_trades` garde son comportement (couvert par `test_storage`). Le contrat 4 ticks vient de la spec §3.

- [ ] **Step 1: Write the failing test**

`tests/test_klines_reader.py` :
```python
import pyarrow as pa
import pyarrow.parquet as pq

from orderflow_bot.features.aggregator import BarAggregator
from orderflow_bot.ingestion.reader import read_klines_as_ticks

H4 = 240 * 60_000
T0 = 20_000 * 86_400_000          # minute- et 4h-aligne (multiple de DAY)


def _write_klines(folder, name, rows):
    # rows: (ts, open, high, low, close, volume)
    folder.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table({
        "ts": [r[0] for r in rows], "open": [r[1] for r in rows],
        "high": [r[2] for r in rows], "low": [r[3] for r in rows],
        "close": [r[4] for r in rows], "volume": [r[5] for r in rows],
    }), folder / name)


def test_kline_expands_to_four_ticks(tmp_path):
    _write_klines(tmp_path / "BTCUSDT", "k.parquet", [(T0, 100.0, 105.0, 98.0, 101.0, 8.0)])
    ticks = list(read_klines_as_ticks(tmp_path, "BTCUSDT"))
    assert [(t.ts - T0, t.price, t.qty) for t in ticks] == [
        (0, 100.0, 2.0), (20_000, 105.0, 2.0), (40_000, 98.0, 2.0), (59_999, 101.0, 2.0),
    ]
    assert all(t.is_buyer_maker is False for t in ticks)


def test_klines_reconstruct_4h_bar_ohlc(tmp_path):
    # 2 klines 1m dans la meme fenetre 4h -> une barre 4h
    _write_klines(tmp_path / "BTCUSDT", "k.parquet", [
        (T0,          100.0, 105.0, 98.0, 101.0, 8.0),    # open de fenetre = 100
        (T0 + 60_000, 101.0, 110.0, 99.0, 102.0, 4.0),    # close de fenetre = 102
    ])
    agg = BarAggregator(H4, 1.0)
    for t in read_klines_as_ticks(tmp_path, "BTCUSDT"):
        agg.on_trade(t)
    bar = agg.flush()
    assert bar.open == 100.0      # 1er tick
    assert bar.high == 110.0      # max H
    assert bar.low == 98.0        # min L
    assert bar.close == 102.0     # dernier tick
    assert bar.volume == 12.0     # somme V


def test_klines_window_filters_by_open_time(tmp_path):
    _write_klines(tmp_path / "BTCUSDT", "k.parquet", [
        (T0,           100.0, 101.0, 99.0, 100.5, 4.0),
        (T0 + 60_000,  100.5, 102.0, 100.0, 101.0, 4.0),
        (T0 + 120_000, 101.0, 103.0, 100.5, 102.0, 4.0),
    ])
    ticks = list(read_klines_as_ticks(tmp_path, "BTCUSDT",
                                      start_ms=T0 + 60_000, end_ms=T0 + 120_000))
    # seule la kline du milieu (open_time dans [start,end)) -> 4 ticks @ open 100.5
    assert {t.ts // 60_000 for t in ticks} == {(T0 + 60_000) // 60_000}
    assert ticks[0].price == 100.5


def test_read_klines_empty_dir(tmp_path):
    assert list(read_klines_as_ticks(tmp_path, "BTCUSDT")) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_klines_reader.py -v`
Expected: FAIL (`ImportError: cannot import name 'read_klines_as_ticks'`)

- [ ] **Step 3: Write minimal implementation**

Dans `src/orderflow_bot/ingestion/reader.py` : (a) extraire deux helpers, (b) réécrire `read_trades` pour les utiliser (comportement inchangé), (c) ajouter le streaming klines.

Remplacer le corps de `read_trades` (lignes 40-98) par :
```python
def _ordered_parquet(
    folder: Path, start_ms: int | None, end_ms: int | None
) -> tuple[list[Path], bool]:
    """(fichiers a lire dans l'ordre, global_sort?). global_sort=True => lire
    tous les fichiers en un seul scan trie (stats absentes ou chevauchement).
    Sinon, fichiers hors fenetre sautes, ordonnes par leurs bornes ts."""
    files = sorted(folder.glob("*.parquet")) if folder.exists() else []
    if not files:
        return [], False
    plan: list[tuple[int, int, Path]] = []
    for f in files:
        md = pq.read_metadata(f)
        if md.num_rows == 0:
            continue
        bounds = _ts_bounds(md)
        if bounds is None:
            return files, True
        lo, hi = bounds
        if (start_ms is not None and hi < start_ms) or \
                (end_ms is not None and lo >= end_ms):
            continue
        plan.append((lo, hi, f))
    plan.sort(key=lambda p: p[:2])
    if any(prev[1] > nxt[0] for prev, nxt in zip(plan, plan[1:])):
        return files, True
    return [f for _, _, f in plan], False


def _window_sql(start_ms: int | None, end_ms: int | None) -> tuple[str, list]:
    conds: list[str] = []
    params: list = []
    if start_ms is not None:
        conds.append("ts >= ?")
        params.append(start_ms)
    if end_ms is not None:
        conds.append("ts < ?")
        params.append(end_ms)
    where = (" WHERE " + " AND ".join(conds)) if conds else ""
    return where, params


def read_trades(
    data_dir: str | Path,
    symbol: str,
    start_ms: int | None = None,
    end_ms: int | None = None,
) -> Iterator[Trade]:
    """Relit les Parquet trades du symbole en streaming, ordonnes par ts.
    Chemin rapide par bornes de footer (fichiers non chevauchants) ; repli sur
    tri global DuckDB si stats absentes ou chevauchement."""
    folder = Path(data_dir) / symbol
    files, global_sort = _ordered_parquet(folder, start_ms, end_ms)
    if not files:
        return
    where, params = _window_sql(start_ms, end_ms)
    q = f"SELECT ts, price, qty, is_buyer_maker FROM read_parquet(?){where} ORDER BY ts"
    con = duckdb.connect()
    try:
        if global_sort:
            log.warning("stats absentes ou fichiers chevauchants : tri global")
            yield from _stream(con.execute(q, [[str(f) for f in files], *params]))
        else:
            for i, f in enumerate(files, 1):
                log.info("lecture %d/%d: %s", i, len(files), f.name)
                yield from _stream(con.execute(q, [str(f), *params]))
    finally:
        con.close()
```

Puis ajouter, après `read_trades`, le streaming klines (contrat §3) :
```python
def _stream_klines(cur) -> Iterator[Trade]:
    """Chaque kline (ts,O,H,L,C,V) -> 4 Trade synthetiques {O,H,L,C}, close
    en dernier, V/4 chacun, offsets ts 0/20k/40k/59999 (spec contrat tick)."""
    while batch := cur.fetchmany(_BATCH):
        for ts, o, h, l, c, v in batch:
            q = v / 4.0
            yield Trade(ts=ts, price=o, qty=q, is_buyer_maker=False)
            yield Trade(ts=ts + 20_000, price=h, qty=q, is_buyer_maker=False)
            yield Trade(ts=ts + 40_000, price=l, qty=q, is_buyer_maker=False)
            yield Trade(ts=ts + 59_999, price=c, qty=q, is_buyer_maker=False)


def read_klines_as_ticks(
    data_dir: str | Path,
    symbol: str,
    start_ms: int | None = None,
    end_ms: int | None = None,
) -> Iterator[Trade]:
    """Streame les klines Parquet (ordonnees par ts = open_time) et yield 4
    Trade synthetiques/kline. Signature drop-in de read_trades. La fenetre
    [start_ms, end_ms) filtre sur open_time."""
    folder = Path(data_dir) / symbol
    files, global_sort = _ordered_parquet(folder, start_ms, end_ms)
    if not files:
        return
    where, params = _window_sql(start_ms, end_ms)
    q = f"SELECT ts, open, high, low, close, volume FROM read_parquet(?){where} ORDER BY ts"
    con = duckdb.connect()
    try:
        if global_sort:
            yield from _stream_klines(con.execute(q, [[str(f) for f in files], *params]))
        else:
            for f in files:
                yield from _stream_klines(con.execute(q, [str(f), *params]))
    finally:
        con.close()
```

- [ ] **Step 4: Run new tests + regression**

Run: `.venv/Scripts/python.exe -m pytest tests/test_klines_reader.py tests/test_storage.py -v`
Expected: PASS (5 nouveaux + tous ceux de test_storage — le refactor ne régresse pas read_trades)

- [ ] **Step 5: Commit**

```bash
git add src/orderflow_bot/ingestion/reader.py tests/test_klines_reader.py
git commit -m "feat(orderflow): read_klines_as_ticks (contrat 4 ticks) + extract planning [2a]"
```

---

### Task 4: Résolveur `read_market`

**Files:**
- Modify: `src/orderflow_bot/ingestion/reader.py` (ajout en fin de fichier)
- Test: `tests/test_read_market.py`

- [ ] **Step 1: Write the failing test**

`tests/test_read_market.py` :
```python
import pyarrow as pa
import pyarrow.parquet as pq

from orderflow_bot.config import BotConfig
from orderflow_bot.ingestion.reader import read_market

T0 = 20_000 * 86_400_000


def _write(folder, name, table):
    folder.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, folder / name)


def test_read_market_trades(tmp_path):
    _write(tmp_path / "spot" / "BTCUSDT", "t.parquet", pa.table({
        "ts": [T0, T0 + 100], "price": [100.0, 101.0],
        "qty": [1.0, 2.0], "is_buyer_maker": [False, True],
    }))
    cfg = BotConfig(data_dir=str(tmp_path), market="spot", data_format="trades")
    ticks = list(read_market(cfg))
    assert [t.price for t in ticks] == [100.0, 101.0]


def test_read_market_klines(tmp_path):
    _write(tmp_path / "klines" / "spot" / "BTCUSDT", "k.parquet", pa.table({
        "ts": [T0], "open": [100.0], "high": [105.0],
        "low": [98.0], "close": [101.0], "volume": [8.0],
    }))
    cfg = BotConfig(data_dir=str(tmp_path), market="spot", data_format="klines")
    ticks = list(read_market(cfg))
    assert [t.price for t in ticks] == [100.0, 105.0, 98.0, 101.0]   # 4 ticks synthetiques
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_read_market.py -v`
Expected: FAIL (`ImportError: cannot import name 'read_market'`)

- [ ] **Step 3: Write minimal implementation**

Ajouter en fin de `src/orderflow_bot/ingestion/reader.py`. Import `BotConfig` au niveau module (les imports existants sont en tête de fichier) :
```python
from orderflow_bot.config import BotConfig
```
(à placer avec les imports existants, après `from orderflow_bot.models import Trade`).

Puis la fonction :
```python
def read_market(
    cfg: BotConfig, start_ms: int | None = None, end_ms: int | None = None
) -> Iterator[Trade]:
    """Dispatch unique trades|klines selon cfg.data_format. Point d'entree du
    chemin swing (parallele et sequentiel) ; les outils trades intraday gardent
    read_trades en direct."""
    if cfg.data_format == "klines":
        return read_klines_as_ticks(cfg.kline_data_dir, cfg.symbol, start_ms, end_ms)
    return read_trades(cfg.market_data_dir, cfg.symbol, start_ms, end_ms)
```

Vérifier l'absence d'import circulaire : `config.py` n'importe pas `reader.py` (confirmé — `config.py` n'importe que `pathlib`, `typing`, `yaml`, `pydantic`). OK.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_read_market.py -v`
Expected: PASS (2)

- [ ] **Step 5: Commit**

```bash
git add src/orderflow_bot/ingestion/reader.py tests/test_read_market.py
git commit -m "feat(orderflow): resolveur read_market (dispatch trades|klines) [2a]"
```

---

### Task 5: Câblage `_block_worker` → `read_market`

**Files:**
- Modify: `src/orderflow_bot/pipeline.py` (`_block_worker` lignes 305-310)
- Test: régression existante (`tests/` qui couvrent `generate_plans_parallel`)

Changement behavior-preserving : `data_format` défaut `trades` → `read_market` retombe sur `read_trades`. Seul `_block_worker` change ; `_isolated_block_worker` reste sur `read_trades` (tail_days=1 inutilisable pour holds swing — labeling swing séquentiel uniquement).

- [ ] **Step 1: Identifier le test de régression existant**

Run: `.venv/Scripts/python.exe -m pytest tests/ -k "parallel or blocked or equiv" -v`
Expected: une suite verte couvrant `generate_plans_parallel` ≡ `generate_plans_blocked` ≡ global. Noter les noms (servent de garde anti-régression).

- [ ] **Step 2: Modifier `_block_worker`**

Dans `src/orderflow_bot/pipeline.py`, remplacer le corps de `_block_worker` :
```python
def _block_worker(args: tuple[BotConfig, int, int, int]) -> list[OrderPlan]:
    cfg, read_from, b_start, b_end = args
    from orderflow_bot.ingestion.reader import read_market
    trades = read_market(cfg, start_ms=max(0, read_from), end_ms=b_end)
    return generate_plans(cfg, trades, b_start, b_end)
```
(seules les 2 lignes du milieu changent : `read_market(cfg, …)` au lieu de
`read_trades(cfg.market_data_dir, cfg.symbol, …)`.)

- [ ] **Step 3: Run regression to verify trades path unchanged**

Run: `.venv/Scripts/python.exe -m pytest tests/ -k "parallel or blocked or equiv" -v`
Expected: PASS (identique au Step 1 — chemin trades inchangé)

- [ ] **Step 4: Full suite**

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS (zéro régression sur tout le repo)

- [ ] **Step 5: Commit**

```bash
git add src/orderflow_bot/pipeline.py
git commit -m "feat(orderflow): cable _block_worker sur read_market (klines passe-1) [2a]"
```

---

### Task 6: Downloader mensuel idempotent

**Files:**
- Create: `scripts/download_klines.py`
- Test: `tests/test_klines_download.py` (parties pures : URL + itération mois)

Le téléchargement réseau lui-même n'est pas testé unitairement (comme `import_range`) ; il est exercé par le smoke (Task 8). On teste le constructeur d'URL et l'itérateur de mois.

- [ ] **Step 1: Write the failing test**

`tests/test_klines_download.py` :
```python
from orderflow_bot.config import BotConfig

from scripts.download_klines import kline_archive_url, month_range


def test_kline_url_spot():
    assert kline_archive_url("spot", "BTCUSDT", 2020, 1) == (
        "https://data.binance.vision/data/spot/monthly/klines/"
        "BTCUSDT/1m/BTCUSDT-1m-2020-01.zip"
    )


def test_kline_url_futures():
    assert kline_archive_url("futures", "BTCUSDT", 2023, 12) == (
        "https://data.binance.vision/data/futures/um/monthly/klines/"
        "BTCUSDT/1m/BTCUSDT-1m-2023-12.zip"
    )


def test_month_range_inclusive():
    assert month_range(2019, 11, 2020, 2) == [(2019, 11), (2019, 12), (2020, 1), (2020, 2)]


def test_month_range_single():
    assert month_range(2020, 5, 2020, 5) == [(2020, 5)]
```

`scripts/` n'a pas de `__init__.py` (convention repo). Pour l'import en test, ajouter en tête du test :
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
```
(placer AVANT `from scripts.download_klines import ...`).

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_klines_download.py -v`
Expected: FAIL (`ModuleNotFoundError: scripts.download_klines`)

- [ ] **Step 3: Write minimal implementation**

`scripts/download_klines.py` :
```python
"""Telecharge les archives klines 1m mensuelles data.binance.vision (gratuites)
-> un Parquet/mois dans kline_data_dir/symbol. Idempotent : un mois deja present
est saute. Usage: python scripts/download_klines.py 2017 8 2026 5"""

import io
import logging
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from orderflow_bot.config import load_config
from orderflow_bot.ingestion.klines import convert_kline_csv

log = logging.getLogger(__name__)
_BASE = "https://data.binance.vision/data"


def kline_archive_url(market: str, symbol: str, year: int, month: int) -> str:
    root = "spot" if market == "spot" else "futures/um"
    return (f"{_BASE}/{root}/monthly/klines/{symbol}/1m/"
            f"{symbol}-1m-{year:04d}-{month:02d}.zip")


def month_range(y0: int, m0: int, y1: int, m1: int) -> list[tuple[int, int]]:
    """Liste [(annee, mois)] de (y0,m0) a (y1,m1) inclus."""
    out, y, m = [], y0, m0
    while (y, m) <= (y1, m1):
        out.append((y, m))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def download_klines(config_path: str, y0: int, m0: int, y1: int, m1: int) -> dict:
    cfg = load_config(config_path)
    out_dir = Path(cfg.kline_data_dir) / cfg.symbol
    out_dir.mkdir(parents=True, exist_ok=True)
    got = skipped = missing = bars = 0
    for y, m in month_range(y0, m0, y1, m1):
        out = out_dir / f"{cfg.symbol}-1m-{y:04d}-{m:02d}.parquet"
        if out.exists():
            skipped += 1
            continue
        url = kline_archive_url(cfg.market, cfg.symbol, y, m)
        try:
            with urlopen(url, timeout=180) as resp:
                blob = resp.read()
        except HTTPError as e:
            if e.code == 404:
                log.warning("archive absente: %s", url)
                missing += 1
                continue
            raise
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            name = z.namelist()[0]
            with tempfile.TemporaryDirectory() as td:
                bars += convert_kline_csv(z.extract(name, td), out)
        got += 1
        log.info("%04d-%02d importe", y, m)
    return {"months_imported": got, "months_skipped": skipped,
            "months_missing": missing, "bars": bars}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cfg_path = sys.argv[1] if len(sys.argv) >= 6 else "config.klines.yaml"
    args = [int(a) for a in sys.argv[-4:]]
    print(download_klines(cfg_path, *args))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_klines_download.py -v`
Expected: PASS (4)

- [ ] **Step 5: Commit**

```bash
git add scripts/download_klines.py tests/test_klines_download.py
git commit -m "feat(orderflow): downloader klines mensuel idempotent [2a]"
```

---

### Task 7: Helpers smoke-plomberie (purs, testables)

**Files:**
- Create: `src/orderflow_bot/backtest/plumbing_checks.py`
- Test: `tests/test_plumbing_checks.py`

Chaque helper renvoie une **liste de violations** (vide = PASS). Critères = spec §6 (A zones, B plans, C labels). Le contrôle RR utilise une tolérance flottante (`1e-9`) — leçon étage 1 : `reward/risk` au ras de `min_rr` est knife-edge en float.

- [ ] **Step 1: Write the failing test**

`tests/test_plumbing_checks.py` :
```python
from orderflow_bot.backtest.plumbing_checks import (
    label_violations, plan_violations, zone_violations,
)
from orderflow_bot.models import ClosedTrade, Fill, OrderPlan
from orderflow_bot.strategy.context import DailyLevels


def _lv(poc, vah, val, hi, lo, day=1):
    return DailyLevels(day=day, poc=poc, vah=vah, val=val, high=hi, low=lo)


def _ct(r, kind="target"):
    p = OrderPlan(1, 1, 100.0, 99.0, 102.0, {})
    return ClosedTrade(plan=p, qty=1.0,
                       fills=[Fill(1, 100.0, 1.0, "entry"), Fill(2, 102.0, 1.0, kind)],
                       pnl=r, r_multiple=r, opened_ts=1, closed_ts=2)


def test_zone_violations_pass():
    assert zone_violations([_lv(100.0, 102.0, 98.0, 103.0, 97.0)]) == []


def test_zone_violations_poc_outside_va():
    v = zone_violations([_lv(105.0, 102.0, 98.0, 103.0, 97.0)])   # POC > VAH
    assert len(v) >= 1


def test_zone_violations_empty_levels():
    assert zone_violations([]) == ["aucun DailyLevels"]


def test_plan_violations_pass_long():
    p = OrderPlan(1, 1, 100.0, 99.0, 103.0, {})    # stop<entry<target, RR=3
    assert plan_violations([p], min_rr=2.0) == []


def test_plan_violations_bad_geometry():
    p = OrderPlan(1, 1, 100.0, 101.0, 103.0, {})   # long mais stop>entry
    assert len(plan_violations([p], min_rr=2.0)) >= 1


def test_plan_violations_rr_too_low():
    p = OrderPlan(1, 1, 100.0, 99.0, 100.5, {})    # RR=0.5
    assert any("RR" in m for m in plan_violations([p], min_rr=2.0))


def test_label_violations_pass():
    assert label_violations([_ct(2.0), _ct(-1.0, "stop")]) == []


def test_label_violations_nan():
    assert len(label_violations([_ct(float("nan"))])) >= 1


def test_label_violations_empty():
    assert label_violations([]) == ["aucun label"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_plumbing_checks.py -v`
Expected: FAIL (`ModuleNotFoundError: orderflow_bot.backtest.plumbing_checks`)

- [ ] **Step 3: Write minimal implementation**

`src/orderflow_bot/backtest/plumbing_checks.py` :
```python
"""Smoke-plomberie etage 2a : asserts PASS/FAIL purs sur la chaine
klines->zones->plans->labels. AUCUNE mesure d'edge (spec etage 2a). Chaque
fonction renvoie une liste de violations ; vide = PASS."""

import math

from orderflow_bot.models import ClosedTrade, OrderPlan
from orderflow_bot.strategy.context import DailyLevels


def zone_violations(levels: list[DailyLevels]) -> list[str]:
    """A : VAL<=POC<=VAH, POC dans le range, largeur VA dans ]0, range]."""
    out: list[str] = []
    if not levels:
        return ["aucun DailyLevels"]
    for lv in levels:
        if not (lv.val <= lv.poc <= lv.vah):
            out.append(f"jour {lv.day}: VAL<=POC<=VAH viole "
                       f"({lv.val}, {lv.poc}, {lv.vah})")
        if not (lv.low <= lv.poc <= lv.high):
            out.append(f"jour {lv.day}: POC hors range "
                       f"({lv.low}, {lv.poc}, {lv.high})")
        w = lv.vah - lv.val
        if not (0 < w <= lv.high - lv.low):
            out.append(f"jour {lv.day}: largeur VA aberrante ({w})")
    return out


def plan_violations(plans: list[OrderPlan], min_rr: float) -> list[str]:
    """B : geometrie reversal coherente + RR>=min_rr (tolerance flottante)."""
    out: list[str] = []
    if not plans:
        return ["aucun plan"]
    for p in plans:
        if p.side == 1 and not (p.stop < p.entry < p.target):
            out.append(f"long incoherent: stop {p.stop} entry {p.entry} "
                       f"target {p.target}")
        elif p.side == -1 and not (p.target < p.entry < p.stop):
            out.append(f"short incoherent: stop {p.stop} entry {p.entry} "
                       f"target {p.target}")
        risk = abs(p.entry - p.stop)
        reward = abs(p.target - p.entry)
        if risk <= 0 or reward / risk < min_rr - 1e-9:
            out.append(f"RR < {min_rr}: risk {risk} reward {reward}")
    return out


def label_violations(labels: list[ClosedTrade]) -> list[str]:
    """C : r_multiple fini pour tout label realise."""
    out: list[str] = []
    if not labels:
        return ["aucun label"]
    for ct in labels:
        if not math.isfinite(ct.r_multiple):
            out.append(f"r non fini: {ct.r_multiple} (ouvert {ct.opened_ts})")
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_plumbing_checks.py -v`
Expected: PASS (9)

- [ ] **Step 5: Commit**

```bash
git add src/orderflow_bot/backtest/plumbing_checks.py tests/test_plumbing_checks.py
git commit -m "feat(orderflow): helpers smoke-plomberie 2a (zones/plans/labels) [2a]"
```

---

### Task 8: Orchestrateur smoke + config + run réel (le GATE 2a)

**Files:**
- Create: `config.klines.yaml`
- Create: `scripts/klines_smoke.py`

Cette tâche produit le **verdict 2a**. Elle nécessite des klines réels téléchargés (Task 6).

- [ ] **Step 1: Écrire `config.klines.yaml`**

`config.klines.yaml` :
```yaml
symbol: BTCUSDT
market: spot
data_format: klines
data_dir: data
tick_size: 0.01
bin_size: 1.0
profile_bin_size: 10.0
bar_minutes: 240
eod_flat: false
journal_path: journal.klines.jsonl
strategy:
  trigger: level_rejection
  zone_margin_pct: 0.002
  stop_buffer_ticks: 20
  entry_expire_minutes: 600
  profile_days: 5
  npoc_lookback_days: 20
risk:
  min_rr: 2.0
  min_stop_friction_mult: 0.0
  max_trades_per_day: 999
  max_consecutive_losses: 999
  daily_stop_pct: 1.0
sessions: []
```

- [ ] **Step 2: Écrire l'orchestrateur**

`scripts/klines_smoke.py` :
```python
"""Smoke-plomberie etage 2a : verifie que les klines pilotent le moteur de bout
en bout (zones saines, plans coherents, labels finis) + que le chemin parallele
klines tourne. PASS/FAIL, AUCUNE mesure d'edge. Usage: python scripts/klines_smoke.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from orderflow_bot.backtest.plumbing_checks import (
    label_violations, plan_violations, zone_violations,
)
from orderflow_bot.config import load_config
from orderflow_bot.ingestion.reader import available_days, read_klines_as_ticks
from orderflow_bot.pipeline import PlanGenerator, generate_plans_parallel, simulate_isolated

_DAY_MS = 86_400_000


def _collect_levels_and_plans(cfg):
    """Passe sequentielle : collecte les DailyLevels finalises ET les plans
    (level_rejection) sur tout l'historique klines."""
    gen = PlanGenerator(cfg)
    plans = []
    for t in read_klines_as_ticks(cfg.kline_data_dir, cfg.symbol):
        plans.extend(gen.on_trade(t))
    return gen._levels, plans


def main() -> int:
    cfg = load_config("config.klines.yaml")
    days = available_days(cfg.kline_data_dir, cfg.symbol)
    if not days:
        print("FAIL: aucune kline dans", cfg.kline_data_dir, "/", cfg.symbol)
        return 1

    levels, plans = _collect_levels_and_plans(cfg)
    labels = simulate_isolated(
        cfg, plans,
        read_klines_as_ticks(cfg.kline_data_dir, cfg.symbol),
        eod_flat=cfg.eod_flat,
    )

    problems = (zone_violations(levels)
                + plan_violations(plans, cfg.risk.min_rr)
                + label_violations(labels))

    # chemin parallele klines (la vraie preuve du cablage _block_worker->read_market)
    start, end = days[0] * _DAY_MS, (days[-1] + 1) * _DAY_MS
    par = generate_plans_parallel(cfg, start, end)
    if not par:
        problems.append("generate_plans_parallel (klines) ne produit aucun plan")

    print(f"jours={len(days)} levels={len(levels)} plans={len(plans)} "
          f"labels={len(labels)} plans_par={len(par)}")
    if problems:
        print("FAIL — violations:")
        for p in problems[:20]:
            print("  -", p)
        return 1
    print("PASS — klines pilotent le moteur de bout en bout (zero edge mesure)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Télécharger ≥ 2 mois de klines réels**

Run: `.venv/Scripts/python.exe scripts/download_klines.py config.klines.yaml 2022 1 2022 3`
Expected: `{'months_imported': 3, 'months_skipped': 0, 'months_missing': 0, 'bars': ...}` et 3 Parquet dans `data/klines/spot/BTCUSDT/`.
(2022 Q1 = fenêtre bear, ≥ 2 mois → ≥ 1 profil composite + zones. Si réseau indisponible, choisir tout autre trimestre présent sur data.binance.vision.)

- [ ] **Step 4: Lancer le smoke (le gate 2a)**

Run: `.venv/Scripts/python.exe scripts/klines_smoke.py`
Expected: ligne de stats puis **`PASS — klines pilotent le moteur de bout en bout`**.
- Si **FAIL zones** : VP klines dégénéré → revoir le contrat tick (spec §3, distribution volume).
- Si **FAIL plans** (« aucun plan ») : `level_rejection` ne tire pas sur klines → vérifier zones/seuils, pas un bug data en soi (peut être un trimestre sans rejet net ; élargir la fenêtre).
- Si **FAIL labels** : NaN/inf → bug broker/censure sur eod_flat=False.

- [ ] **Step 5: Commit**

```bash
git add config.klines.yaml scripts/klines_smoke.py
git commit -m "feat(orderflow): orchestrateur smoke-plomberie klines + config [2a]"
```

(Les Parquet `data/klines/**` ne sont PAS commités — vérifier qu'ils sont ignorés par `.gitignore` comme `data/` l'est déjà ; sinon ne pas les ajouter.)

---

## Verification

Après les 8 tâches :
- [ ] `.venv/Scripts/python.exe -m pytest tests/ -q` → toute la suite verte (zéro régression trades).
- [ ] `scripts/klines_smoke.py` → **PASS** sur ≥ 2 mois réels.
- [ ] Chemin trades intact (live/__main__/plots non touchés).
- [ ] Si PASS → greenlight **étage 2b** (trigger VA-breakout + drift gate). Si FAIL → diagnostic data avant tout signal.

Puis : **REQUIRED SUB-SKILL** superpowers:finishing-a-development-branch (vérifier tests, présenter les options de merge).

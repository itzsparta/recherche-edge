# Import Historique + Multi-Marché Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Importer l'historique aggTrades gratuit de `data.binance.vision` (spot ET futures USDT-M) en Parquet compatible avec le pipeline existant, et router le bot par marché (`spot` | `futures`) — le live websocket futures est géo-bloqué depuis la France (stream muet vérifié le 2026-06-12), seul le spot diffuse.

**Architecture:** Un champ `market` en config pilote trois choses : le chemin des données (`data_dir/market/symbol` — spot et futures du même symbole ne se mélangent jamais), l'URL websocket live, et l'URL d'archive pour l'import. `reader.py`, `recorder.py` et leurs tests sont INTOUCHÉS : les call sites passent simplement `cfg.market_data_dir` (propriété) au lieu de `cfg.data_dir` aux mêmes APIs. L'importeur télécharge les zips quotidiens, convertit le CSV en Parquet via DuckDB→Arrow (normalisation des deux formats), et est idempotent (un fichier par jour, skip si présent).

**Formats CSV réels (vérifiés sur les archives du 2026-06-10) :**

| | Spot | Futures UM |
|---|---|---|
| Header | non | oui (`agg_trade_id,price,...`) |
| Colonnes | 8 (`...,is_buyer_maker,is_best_match`) | 7 |
| `transact_time` | **microsecondes** (16 chiffres) | millisecondes (13 chiffres) |
| Booléens | `False`/`True` | `false`/`true` |
| URL | `data/spot/daily/aggTrades/{S}/{S}-aggTrades-{D}.zip` | `data/futures/um/daily/aggTrades/{S}/{S}-aggTrades-{D}.zip` |

**Tech Stack:** stdlib (`urllib.request`, `zipfile`, `tempfile`, `datetime`), DuckDB (déjà dépendance) pour parser le CSV, pyarrow pour écrire le Parquet. Pas de pandas (YAGNI).

**Racine projet :** `C:\Projets\code python\orderflow-bot`. Python : `.venv\Scripts\python`. Repo git enraciné à `C:\Projets`.

**Préliminaire :** créer la branche : `git checkout -b feat/orderflow-import` (depuis `C:\Projets`).

**Données existantes :** `data/BTCUSDT` est vide — aucune migration nécessaire.

---

### Task 1: Config `market` + chemins par marché + URL websocket par marché

**Files:**
- Modify: `src/orderflow_bot/config.py`
- Modify: `src/orderflow_bot/ingestion/binance_ws.py`
- Modify: `src/orderflow_bot/live.py`
- Modify: `src/orderflow_bot/__main__.py` (branche backtest)
- Modify: `src/orderflow_bot/backtest/walkforward.py`
- Modify: `config.yaml`
- Test: `tests/test_config.py`, `tests/test_binance_ws.py` (si absent : créer), `tests/test_walkforward.py`, `tests/test_live_bootstrap.py`

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `tests/test_config.py` :

```python
def test_market_default_and_path():
    cfg = BotConfig()
    assert cfg.market == "spot"
    assert cfg.market_data_dir.replace("\\", "/") == "data/spot"


def test_market_rejects_unknown():
    import pytest
    with pytest.raises(Exception):
        BotConfig(market="forex")
```

(`BotConfig` est déjà importé en tête de ce fichier ; ne pas dupliquer l'import.)

Ajouter à `tests/test_binance_ws.py` (créer le fichier si besoin — vérifier d'abord s'il existe ; s'il existe, ajouter le test à la fin) :

```python
from orderflow_bot.ingestion.binance_ws import FUTURES_WS, SPOT_WS, ws_url


def test_ws_url_by_market():
    assert ws_url("spot") == SPOT_WS
    assert ws_url("futures") == FUTURES_WS
    assert "stream.binance.com" in SPOT_WS
    assert "fstream.binance.com" in FUTURES_WS
```

Dans `tests/test_walkforward.py`, adapter `_write_parquet` (les données vivent maintenant sous `market/symbol`) :

```python
def _write_parquet(tmp_path, symbol="BTCUSDT"):
    folder = tmp_path / "spot" / symbol
    folder.mkdir(parents=True)
    t = pa.table({
        "ts": [5 * _DAY + 1, 5 * _DAY + 2, 7 * _DAY + 1],
        "price": [100.0, 101.0, 102.0],
        "qty": [1.0, 1.0, 1.0],
        "is_buyer_maker": [False, True, False],
    })
    pq.write_table(t, folder / "x.parquet")
```

et adapter les deux tests `available_days` (l'API de `available_days` ne change pas — c'est le data_dir passé qui inclut le marché) :

```python
def test_available_days(tmp_path):
    _write_parquet(tmp_path)
    assert available_days(tmp_path / "spot", "BTCUSDT") == [5, 7]


def test_available_days_empty(tmp_path):
    assert available_days(tmp_path / "spot", "BTCUSDT") == []
```

(les tests `walk_forward` eux ne changent PAS : ils passent `data_dir=str(tmp_path)` et `walk_forward` résout désormais `market_data_dir` en interne — `market` par défaut est `spot`, le chemin résolu est donc `tmp/spot/BTCUSDT`, là où `_write_parquet` écrit).

Dans `tests/test_live_bootstrap.py`, remplacer la construction du recorder :

```python
    rec = TradeRecorder(cfg.market_data_dir, cfg.symbol)
```

- [ ] **Step 2: Vérifier l'échec**

Run: `.venv\Scripts\python -m pytest tests/test_config.py tests/test_binance_ws.py tests/test_walkforward.py tests/test_live_bootstrap.py -v`
Expected: FAIL — `AttributeError: 'BotConfig' object has no attribute 'market'` / `ImportError: cannot import name 'SPOT_WS'` / échecs de chemin.

- [ ] **Step 3: Implémenter la config**

Dans `src/orderflow_bot/config.py` :

En tête, compléter les imports :

```python
from pathlib import Path
from typing import Literal
```

Dans `BotConfig`, ajouter après `symbol` :

```python
    market: Literal["spot", "futures"] = "spot"
```

et ajouter la propriété (dans la classe, après les champs) :

```python
    @property
    def market_data_dir(self) -> str:
        """Racine des donnees du marche courant : data_dir/market.
        Spot et futures du meme symbole ne se melangent jamais."""
        return str(Path(self.data_dir) / self.market)
```

- [ ] **Step 4: Implémenter l'URL websocket par marché**

Dans `src/orderflow_bot/ingestion/binance_ws.py`, remplacer la constante seule par :

```python
FUTURES_WS = "wss://fstream.binance.com/ws"
SPOT_WS = "wss://stream.binance.com:9443/ws"


def ws_url(market: str) -> str:
    """URL websocket par marche. ATTENTION : le flux futures est geo-bloque
    depuis la France (connexion acceptee mais aucun message diffuse)."""
    return SPOT_WS if market == "spot" else FUTURES_WS
```

(la signature de `stream_trades` garde son `url_base: str = FUTURES_WS` — inchangée.)

- [ ] **Step 5: Brancher les call sites**

Dans `src/orderflow_bot/live.py` :

```python
from orderflow_bot.ingestion.binance_ws import stream_trades, ws_url
```

`run_record` :

```python
async def run_record(cfg: BotConfig) -> None:
    """Enregistre le flux tick en Parquet. Ctrl+C -> flush propre."""
    rec = TradeRecorder(cfg.market_data_dir, cfg.symbol)
    try:
        await stream_trades(cfg.symbol, rec.append, url_base=ws_url(cfg.market))
    finally:
        rec.flush()
        log.info("flush final ok")
```

`bootstrap_pipeline` — remplacer la ligne de lecture :

```python
    for t in read_trades(cfg.market_data_dir, cfg.symbol):
```

`run_paper` — remplacer le recorder et le stream :

```python
    rec = TradeRecorder(cfg.market_data_dir, cfg.symbol)
```

```python
        await stream_trades(cfg.symbol, handle, url_base=ws_url(cfg.market))
```

Dans `src/orderflow_bot/__main__.py`, branche backtest — remplacer l'appel :

```python
        trades = read_trades(cfg.market_data_dir, cfg.symbol,
                             start_ms=_ms(args.start), end_ms=_ms(args.end))
```

Dans `src/orderflow_bot/backtest/walkforward.py`, dans `walk_forward` — remplacer les deux accès données :

```python
    days = available_days(cfg.market_data_dir, cfg.symbol)
```

```python
        trades = read_trades(cfg.market_data_dir, cfg.symbol,
                             start_ms=(start_day - warmup_days) * _DAY_MS,
                             end_ms=end_day * _DAY_MS)
```

Dans `config.yaml`, ajouter `market` sous `symbol` et passer le tick spot :

```yaml
symbol: BTCUSDT
market: spot          # spot | futures — live futures geo-bloque depuis la France
tick_size: 0.01       # tick spot BTCUSDT (futures : 0.1)
```

- [ ] **Step 6: Vérifier le passage**

Run: `.venv\Scripts\python -m pytest -q`
Expected: PASS (94 tests : 92 + 2 nouveaux config + 1 ws si fichier neuf — compter le total réel).

- [ ] **Step 7: Commit**

```bash
git add src/orderflow_bot/config.py src/orderflow_bot/ingestion/binance_ws.py src/orderflow_bot/live.py src/orderflow_bot/__main__.py src/orderflow_bot/backtest/walkforward.py config.yaml tests/test_config.py tests/test_binance_ws.py tests/test_walkforward.py tests/test_live_bootstrap.py
git commit -m "feat(orderflow): routage par marche spot/futures (donnees, websocket)"
```

---

### Task 2: Importeur — conversion CSV → Parquet

**Files:**
- Create: `src/orderflow_bot/ingestion/importer.py`
- Test: `tests/test_importer.py`

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `tests/test_importer.py` :

```python
from orderflow_bot.ingestion.importer import convert_csv
from orderflow_bot.ingestion.reader import read_trades

# format spot reel : 8 colonnes, PAS de header, transact_time en MICROsecondes,
# booleens True/False
SPOT_CSV = """3984971527,61730.00000000,0.00008000,6394149873,6394149873,1781049600078441,False,True
3984971528,61730.00000000,0.03666000,6394149874,6394149907,1781049600137111,True,True
"""

# format futures reel : 7 colonnes, header, transact_time en MILLIsecondes,
# booleens true/false
FUTURES_CSV = """agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker
3333403793,61694.9,0.023,7771002125,7771002137,1781049600065,true
3333403794,61695.0,0.896,7771002138,7771002163,1781049600132,false
"""


def _convert(tmp_path, content: str):
    csv_path = tmp_path / "in.csv"
    csv_path.write_text(content, encoding="utf-8")
    out_dir = tmp_path / "spot" / "BTCUSDT"
    out_dir.mkdir(parents=True)
    out = out_dir / "day.parquet"
    n = convert_csv(csv_path, out)
    return n, list(read_trades(tmp_path / "spot", "BTCUSDT"))


def test_convert_spot_format(tmp_path):
    n, trades = _convert(tmp_path, SPOT_CSV)
    assert n == 2
    # microsecondes -> millisecondes
    assert trades[0].ts == 1781049600078
    assert trades[1].ts == 1781049600137
    assert trades[0].price == 61730.0
    assert trades[0].qty == 0.00008
    assert trades[0].is_buyer_maker is False
    assert trades[1].is_buyer_maker is True


def test_convert_futures_format(tmp_path):
    n, trades = _convert(tmp_path, FUTURES_CSV)
    assert n == 2
    # deja en millisecondes : inchange
    assert trades[0].ts == 1781049600065
    assert trades[0].is_buyer_maker is True
    assert trades[1].is_buyer_maker is False


def test_convert_orders_by_ts(tmp_path):
    shuffled = """agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker
2,101.0,1.0,2,2,1781049600200,false
1,100.0,1.0,1,1,1781049600100,true
"""
    n, trades = _convert(tmp_path, shuffled)
    assert n == 2
    assert [t.ts for t in trades] == [1781049600100, 1781049600200]
```

- [ ] **Step 2: Vérifier l'échec**

Run: `.venv\Scripts\python -m pytest tests/test_importer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'orderflow_bot.ingestion.importer'`.

- [ ] **Step 3: Implémenter**

Créer `src/orderflow_bot/ingestion/importer.py` :

```python
"""Import des archives historiques data.binance.vision (gratuites).

Deux formats CSV cohabitent (verifies sur les archives reelles) :
- spot : 8 colonnes, pas de header, transact_time en MICROsecondes, True/False
- futures um : 7 colonnes, header, transact_time en millisecondes, true/false
La conversion normalise tout vers le schema Parquet du TradeRecorder
(ts ms, price, qty, is_buyer_maker)."""

from pathlib import Path

import duckdb
import pyarrow.parquet as pq

_COLS = ["agg_trade_id", "price", "qty", "first_id", "last_id",
         "transact_time", "is_buyer_maker", "is_best_match"]
# au-dela de ce seuil le timestamp est en microsecondes (1e14 ms ~ annee 5138)
_US_THRESHOLD = 100_000_000_000_000


def _sniff(csv_path: Path) -> tuple[bool, int]:
    """(header present, nombre de colonnes) depuis la premiere ligne."""
    with open(csv_path, encoding="utf-8") as f:
        first = f.readline()
    return first.startswith("agg_trade_id"), first.count(",") + 1


_COL_TYPES = {"price": "DOUBLE", "qty": "DOUBLE",
              "is_buyer_maker": "VARCHAR", "is_best_match": "VARCHAR"}


def convert_csv(csv_path: str | Path, out_parquet: str | Path) -> int:
    """CSV aggTrades (spot ou futures) -> un fichier Parquet ordonne par ts.
    Retourne le nombre de trades ecrits."""
    csv_path = Path(csv_path)
    has_header, ncols = _sniff(csv_path)
    # header/columns ne sont pas parametrables en prepared statement DuckDB :
    # inline, valeurs issues de _COLS/_COL_TYPES en dur (aucune entree externe)
    cols_sql = ", ".join(f"'{c}': '{_COL_TYPES.get(c, 'BIGINT')}'"
                         for c in _COLS[:ncols])
    con = duckdb.connect()
    try:
        table = con.execute(
            f"""
            SELECT CASE WHEN transact_time >= ? THEN transact_time // 1000
                        ELSE transact_time END AS ts,
                   price, qty,
                   lower(is_buyer_maker) IN ('true', '1') AS is_buyer_maker
            FROM read_csv(?, header={'true' if has_header else 'false'},
                          columns={{{cols_sql}}})
            ORDER BY ts
            """,
            [_US_THRESHOLD, str(csv_path)],
        ).arrow()
    finally:
        con.close()
    pq.write_table(table, out_parquet)
    return table.num_rows
```

- [ ] **Step 4: Vérifier le passage**

Run: `.venv\Scripts\python -m pytest tests/test_importer.py -v` → PASS, puis suite complète `.venv\Scripts\python -m pytest -q` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/orderflow_bot/ingestion/importer.py tests/test_importer.py
git commit -m "feat(orderflow): conversion CSV aggTrades -> Parquet (spot us + futures ms)"
```

---

### Task 3: Importeur — téléchargement + import par plage de dates

**Files:**
- Modify: `src/orderflow_bot/ingestion/importer.py`
- Test: `tests/test_importer.py`

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `tests/test_importer.py` :

```python
import io
import zipfile
from datetime import date
from urllib.error import HTTPError

from orderflow_bot.config import BotConfig
from orderflow_bot.ingestion.importer import archive_url, import_range
from orderflow_bot.ingestion.reader import available_days


def test_archive_url():
    d = date(2026, 6, 10)
    assert archive_url("spot", "BTCUSDT", d) == (
        "https://data.binance.vision/data/spot/daily/aggTrades/"
        "BTCUSDT/BTCUSDT-aggTrades-2026-06-10.zip")
    assert archive_url("futures", "BTCUSDT", d) == (
        "https://data.binance.vision/data/futures/um/daily/aggTrades/"
        "BTCUSDT/BTCUSDT-aggTrades-2026-06-10.zip")


def _zip_bytes(csv_content: str, name: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name, csv_content)
    return buf.getvalue()


def _fake_download(day_ms: int):
    """Fabrique un downloader qui sert un zip futures-style pour chaque jour."""
    def dl(url: str) -> bytes:
        csv = ("agg_trade_id,price,quantity,first_trade_id,last_trade_id,"
               "transact_time,is_buyer_maker\n"
               f"1,100.0,1.0,1,1,{day_ms},true\n")
        return _zip_bytes(csv, "x.csv")
    return dl


def test_import_range_writes_one_parquet_per_day(tmp_path, monkeypatch):
    import orderflow_bot.ingestion.importer as imp
    day = date(2026, 6, 10)
    day_ms = 1781049600000
    monkeypatch.setattr(imp, "_download", _fake_download(day_ms))
    cfg = BotConfig(data_dir=str(tmp_path))
    report = imp.import_range(cfg, day, day)
    assert report == {"days_imported": 1, "days_skipped": 0,
                      "days_missing": 0, "trades": 1}
    assert available_days(cfg.market_data_dir, cfg.symbol) == [day_ms // 86_400_000]


def test_import_range_idempotent(tmp_path, monkeypatch):
    import orderflow_bot.ingestion.importer as imp
    day = date(2026, 6, 10)
    monkeypatch.setattr(imp, "_download", _fake_download(1781049600000))
    cfg = BotConfig(data_dir=str(tmp_path))
    imp.import_range(cfg, day, day)
    report = imp.import_range(cfg, day, day)          # deuxieme run : skip
    assert report["days_imported"] == 0
    assert report["days_skipped"] == 1


def test_import_range_404_counts_missing(tmp_path, monkeypatch):
    import orderflow_bot.ingestion.importer as imp

    def dl_404(url: str) -> bytes:
        raise HTTPError(url, 404, "Not Found", None, None)

    monkeypatch.setattr(imp, "_download", dl_404)
    cfg = BotConfig(data_dir=str(tmp_path))
    report = imp.import_range(cfg, date(2026, 6, 10), date(2026, 6, 10))
    assert report == {"days_imported": 0, "days_skipped": 0,
                      "days_missing": 1, "trades": 0}
```

- [ ] **Step 2: Vérifier l'échec**

Run: `.venv\Scripts\python -m pytest tests/test_importer.py -v`
Expected: FAIL — `ImportError: cannot import name 'archive_url'`.

- [ ] **Step 3: Implémenter**

Ajouter à `src/orderflow_bot/ingestion/importer.py` (imports en tête, fonctions à la suite) :

```python
import io
import logging
import tempfile
import zipfile
from datetime import date, timedelta
from urllib.error import HTTPError
from urllib.request import urlopen

from orderflow_bot.config import BotConfig
```

```python
log = logging.getLogger(__name__)

_BASE = "https://data.binance.vision/data"


def archive_url(market: str, symbol: str, d: date) -> str:
    """URL de l'archive quotidienne aggTrades (zip) sur data.binance.vision."""
    root = "spot" if market == "spot" else "futures/um"
    return (f"{_BASE}/{root}/daily/aggTrades/{symbol}/"
            f"{symbol}-aggTrades-{d.isoformat()}.zip")


def _download(url: str) -> bytes:
    with urlopen(url, timeout=120) as resp:
        return resp.read()


def import_range(cfg: BotConfig, start: date, end: date) -> dict:
    """Importe [start, end] (bornes incluses) : un Parquet par jour dans
    market_data_dir/symbol. Idempotent : un jour deja present est saute.
    Un jour absent de l'archive (404) est compte, pas fatal."""
    out_dir = Path(cfg.market_data_dir) / cfg.symbol
    out_dir.mkdir(parents=True, exist_ok=True)
    imported = skipped = missing = trades = 0
    d = start
    while d <= end:
        out = out_dir / f"{cfg.symbol}-aggTrades-{d.isoformat()}.parquet"
        if out.exists():
            skipped += 1
            d += timedelta(days=1)
            continue
        url = archive_url(cfg.market, cfg.symbol, d)
        try:
            blob = _download(url)
        except HTTPError as e:
            if e.code == 404:
                log.warning("archive absente: %s", url)
                missing += 1
                d += timedelta(days=1)
                continue
            raise
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            name = z.namelist()[0]
            with tempfile.TemporaryDirectory() as td:
                csv_path = z.extract(name, td)
                n = convert_csv(csv_path, out)
        trades += n
        imported += 1
        log.info("importe %s: %d trades", d.isoformat(), n)
        d += timedelta(days=1)
    return {"days_imported": imported, "days_skipped": skipped,
            "days_missing": missing, "trades": trades}
```

- [ ] **Step 4: Vérifier le passage**

Run: `.venv\Scripts\python -m pytest tests/test_importer.py -v` → PASS, puis `.venv\Scripts\python -m pytest -q` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/orderflow_bot/ingestion/importer.py tests/test_importer.py
git commit -m "feat(orderflow): import par plage de dates depuis data.binance.vision (idempotent)"
```

---

### Task 4: CLI `import` + smoke test réel + ROADMAP

**Files:**
- Modify: `src/orderflow_bot/__main__.py`
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: Implémenter la commande**

Dans `src/orderflow_bot/__main__.py` :

Ajouter `"import"` aux choices :

```python
    ap.add_argument("command",
                    choices=["record", "backtest", "paper", "validate",
                             "walkforward", "import"])
```

Mettre à jour les help de `--start`/`--end` :

```python
    ap.add_argument("--start", default=None, help="YYYY-MM-DD (backtest, import)")
    ap.add_argument("--end", default=None, help="YYYY-MM-DD (backtest, import)")
```

Ajouter la branche AVANT le `else:` final :

```python
    elif args.command == "import":
        from datetime import date

        from orderflow_bot.ingestion.importer import import_range

        if not args.start:
            ap.error("import exige --start (et --end, sinon --start seul)")
        start = date.fromisoformat(args.start)
        end = date.fromisoformat(args.end) if args.end else start
        print(json.dumps(import_range(cfg, start, end), indent=2))
```

- [ ] **Step 2: Smoke test réel (réseau, ~17 Mo)**

Run (depuis `orderflow-bot/`) :

```
.venv\Scripts\python -m orderflow_bot import --start 2026-06-10
```

Expected: JSON `{"days_imported": 1, "days_skipped": 0, "days_missing": 0, "trades": ~1163227}` (spot 2026-06-10 ≈ 1,16 M trades) et un fichier `data/spot/BTCUSDT/BTCUSDT-aggTrades-2026-06-10.parquet`. Relancer la même commande → `days_skipped: 1` (idempotence réelle).

Puis vérifier le chaînage complet :

```
.venv\Scripts\python -m orderflow_bot backtest --start 2026-06-10 --end 2026-06-11
```

Expected: JSON de métriques (probablement `{"trades": 0}` — un seul jour = warmup sans veille, c'est normal ; l'important est zéro exception).

- [ ] **Step 3: Suite complète**

Run: `.venv\Scripts\python -m pytest -q`
Expected: PASS.

- [ ] **Step 4: Mettre à jour la ROADMAP**

Dans `docs/ROADMAP.md`, remplacer l'étape 1 du protocole :

```markdown
1. **Données** : `import --start --end` (historique gratuit data.binance.vision,
   spot et futures) pour le backtest/walk-forward immédiat ; `record` en continu
   pour le flux temps réel. ATTENTION : le websocket live futures est géo-bloqué
   depuis la France (connexion acceptée, zéro message) — le live (record/paper)
   ne fonctionne qu'en `market: spot`.
```

- [ ] **Step 5: Commit**

```bash
git add src/orderflow_bot/__main__.py docs/ROADMAP.md
git commit -m "feat(orderflow): commande CLI import + note geo-blocage futures"
```

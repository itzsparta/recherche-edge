# Orderflow Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bot de trading orderflow Python (qualité > vitesse) : ingestion tick Binance Futures, features orderflow (volume profile, CVD, footprint, absorption, imbalances), signal à confluence 3 couches (contexte HTF → zone → déclencheur), money management codé en dur, backtest par replay du même pipeline que le live, paper trading.

**Architecture:** Pipeline événementiel pur-Python : chaque `Trade` traverse broker (fills) → profil journalier → agrégateur de bougies footprint → détecteurs de triggers → confluence → risque → soumission d'ordre. Le backtest rejoue les ticks Parquet dans exactement le même `Pipeline` que le live (zéro divergence backtest/live). Le risque est vérifié AVANT toute soumission, jamais après.

**Décision v1 — trades only, pas de carnet L2 :** toutes les features de la stratégie (profile, CVD, footprint, absorption, imbalances) se calculent depuis le flux `aggTrade` (prix, qty, côté agresseur). La synchronisation depth L2 est complexe et n'alimente aucune règle de la v1. Extension future possible (détection iceberg/spoof) sans rien casser : le `Recorder` et le `Pipeline` sont extensibles par type d'événement.

**Décision v1 — flat EOD :** position fermée de force au changement de jour UTC (stratégie intraday, une seule position).

**Tech Stack:** Python ≥3.11, `websockets`, `pydantic` v2, `pyyaml`, `pyarrow`, `duckdb`, `pytest`. Pas de pandas/numpy (inutiles ici, YAGNI).

**Racine projet :** `C:\Projets\code python\orderflow-bot` — toutes les commandes ci-dessous s'exécutent depuis ce dossier. Le repo git est enraciné à `C:\Projets`. Python du venv : `.venv\Scripts\python`.

**Conseil d'exécution :** dès la Task 5 terminée, lancer `record` en tâche de fond (terminal séparé) pour accumuler des données réelles — la validation finale sur données réelles (hors plan, nécessite plusieurs jours de collecte) en dépend.

**Structure des fichiers :**

```
orderflow-bot/
├── pyproject.toml
├── config.yaml
├── .gitignore
├── src/orderflow_bot/
│   ├── __init__.py
│   ├── binning.py               # prix ↔ bin entier (clé de tous les dicts de volume)
│   ├── models.py                # Trade, FootprintBar, OrderPlan, Fill, ClosedTrade, Cancelled
│   ├── config.py                # pydantic BotConfig + load_config
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── parser.py            # payload Binance aggTrade → Trade
│   │   ├── recorder.py          # Trade → fichiers Parquet
│   │   ├── reader.py            # Parquet → Iterator[Trade] (DuckDB, ordonné)
│   │   └── binance_ws.py        # websocket + reconnexion backoff
│   ├── features/
│   │   ├── __init__.py
│   │   ├── aggregator.py        # trades → FootprintBar (bougies temps)
│   │   ├── volume_profile.py    # POC, VAH/VAL, LVN/HVN
│   │   ├── cvd.py               # CVD + divergences sur swings
│   │   ├── imbalance.py         # imbalances diagonales empilées
│   │   └── absorption.py        # détection absorption (fenêtre glissante)
│   ├── strategy/
│   │   ├── __init__.py
│   │   ├── context.py           # DailyLevels, biais HTF, naked POCs
│   │   ├── zones.py             # zones tradables du jour
│   │   └── confluence.py        # Trigger, TriggerEngine, ConfluenceEngine → OrderPlan
│   ├── risk/
│   │   ├── __init__.py
│   │   └── manager.py           # sizing, stop journalier, streak, sessions, cap trades/jour
│   ├── execution/
│   │   ├── __init__.py
│   │   ├── paper.py             # PaperBroker : fills conservateurs, partiel 1R + BE
│   │   └── journal.py           # JSONL append + load
│   ├── backtest/
│   │   ├── __init__.py
│   │   └── metrics.py           # win rate, PF, expectancy R, max DD
│   ├── pipeline.py              # assemblage : LE cœur partagé backtest/live
│   ├── live.py                  # run_record / run_paper (asyncio)
│   └── __main__.py              # CLI : record | backtest | paper
└── tests/
    ├── conftest.py
    └── test_*.py                # un fichier par module (voir tâches)
```

---

### Task 1: Scaffolding projet + binning + modèles de base

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `src/orderflow_bot/__init__.py`, `src/orderflow_bot/binning.py`, `src/orderflow_bot/models.py`
- Create: `src/orderflow_bot/{ingestion,features,strategy,risk,execution,backtest}/__init__.py` (vides)
- Create: `tests/__init__.py` (vide — rend `tests` importable pour `from .conftest import ...`)
- Test: `tests/test_binning.py`, `tests/test_models.py`

- [ ] **Step 1: Créer la branche et le squelette**

```bash
rtk git checkout -b feat/orderflow-bot
```

`pyproject.toml` :

```toml
[project]
name = "orderflow-bot"
version = "0.1.0"
description = "Bot trading orderflow - qualite avant vitesse"
requires-python = ">=3.11"
dependencies = [
    "websockets>=12.0",
    "pydantic>=2.5",
    "pyyaml>=6.0",
    "pyarrow>=15.0",
    "duckdb>=0.10",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`.gitignore` :

```
.venv/
__pycache__/
*.egg-info/
data/
*.jsonl
```

Créer `src/orderflow_bot/__init__.py` vide, les `__init__.py` vides des sous-packages `ingestion`, `features`, `strategy`, `risk`, `execution`, `backtest`, et `tests/__init__.py` vide.

- [ ] **Step 2: Installer l'environnement**

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
```

Attendu : install OK. Vérifier : `.venv\Scripts\python -c "import websockets, pydantic, pyarrow, duckdb; print('ok')"` → `ok`.

- [ ] **Step 3: Écrire les tests qui échouent (binning + modèles)**

`tests/test_binning.py` :

```python
from orderflow_bot.binning import bin_of, price_of


def test_bin_roundtrip():
    assert bin_of(117_234.3, 1.0) == 117_234
    assert price_of(117_234, 1.0) == 117_234.0


def test_bin_fractional_size():
    assert bin_of(97.06, 0.1) == 971
    assert price_of(971, 0.1) == 97.1


def test_bin_rounds_to_nearest():
    assert bin_of(100.6, 1.0) == 101
    assert bin_of(100.4, 1.0) == 100
```

`tests/test_models.py` :

```python
from orderflow_bot.models import Trade


def test_aggressor_buy():
    t = Trade(ts=1, price=100.0, qty=0.5, is_buyer_maker=False)
    assert t.aggressor == 1


def test_aggressor_sell():
    t = Trade(ts=1, price=100.0, qty=0.5, is_buyer_maker=True)
    assert t.aggressor == -1
```

- [ ] **Step 4: Vérifier l'échec**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_binning.py tests\test_models.py -q
```

Attendu : FAIL — `ModuleNotFoundError: No module named 'orderflow_bot.binning'`.

- [ ] **Step 5: Implémenter**

`src/orderflow_bot/binning.py` :

```python
"""Conversion prix <-> bin entier. Toutes les structures de volume sont indexees
par bin entier pour eviter les comparaisons de floats."""


def bin_of(price: float, bin_size: float) -> int:
    return int(round(price / bin_size))


def price_of(b: int, bin_size: float) -> float:
    return round(b * bin_size, 10)
```

`src/orderflow_bot/models.py` :

```python
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Trade:
    ts: int                # epoch ms
    price: float
    qty: float
    is_buyer_maker: bool   # True => l'agresseur est vendeur

    @property
    def aggressor(self) -> int:
        """+1 achat agressif, -1 vente agressive."""
        return -1 if self.is_buyer_maker else 1


@dataclass(slots=True)
class FootprintBar:
    open_ts: int
    close_ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    delta: float                       # somme qty * aggressor
    ask_vol: dict[int, float]          # volume achat agressif par bin
    bid_vol: dict[int, float]          # volume vente agressive par bin


@dataclass(frozen=True, slots=True)
class OrderPlan:
    ts: int
    side: int          # +1 long, -1 short
    entry: float       # ordre limit
    stop: float
    target: float
    meta: dict = field(default_factory=dict)   # zone/trigger/bias pour le journal


@dataclass(frozen=True, slots=True)
class Fill:
    ts: int
    price: float
    qty: float
    kind: str          # entry | partial | stop | target | eod


@dataclass(slots=True)
class ClosedTrade:
    plan: OrderPlan
    qty: float
    fills: list[Fill]
    pnl: float
    r_multiple: float
    opened_ts: int
    closed_ts: int


@dataclass(frozen=True, slots=True)
class Cancelled:
    """Ordre d'entree expire sans fill."""
    ts: int
```

- [ ] **Step 6: Vérifier le passage**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_binning.py tests\test_models.py -q
```

Attendu : PASS (5 tests).

- [ ] **Step 7: Commit**

```bash
rtk git add orderflow-bot && rtk git commit -m "feat(orderflow): scaffolding projet, binning et modeles de donnees"
```

---

### Task 2: Configuration pydantic

**Files:**
- Create: `src/orderflow_bot/config.py`, `config.yaml`
- Test: `tests/test_config.py`

- [ ] **Step 1: Test qui échoue**

`tests/test_config.py` :

```python
from orderflow_bot.config import BotConfig, load_config


def test_defaults():
    cfg = BotConfig()
    assert cfg.symbol == "BTCUSDT"
    assert cfg.risk.risk_pct == 0.0075
    assert cfg.risk.daily_stop_pct == 0.02
    assert cfg.risk.max_consecutive_losses == 3
    assert cfg.risk.min_rr == 2.0
    assert cfg.strategy.absorption.window_ms == 30_000


def test_load_yaml(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("symbol: ETHUSDT\nrisk:\n  risk_pct: 0.005\n", encoding="utf-8")
    cfg = load_config(p)
    assert cfg.symbol == "ETHUSDT"
    assert cfg.risk.risk_pct == 0.005
    assert cfg.risk.min_rr == 2.0   # defaut conserve
```

- [ ] **Step 2: Vérifier l'échec**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_config.py -q
```

Attendu : FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implémenter**

`src/orderflow_bot/config.py` :

```python
from pathlib import Path

import yaml
from pydantic import BaseModel


class AbsorptionCfg(BaseModel):
    window_ms: int = 30_000
    vol_factor: float = 3.0          # volume fenetre >= facteur x mediane baseline
    max_range_ticks: int = 15        # le prix ne progresse plus
    min_delta_frac: float = 0.3      # |delta| >= frac x volume fenetre
    baseline_windows: int = 20


class ImbalanceCfg(BaseModel):
    ratio: float = 3.0
    min_stack: int = 3


class StrategyCfg(BaseModel):
    zone_margin_pct: float = 0.001       # demi-largeur de zone, en % du prix
    stop_buffer_ticks: int = 20          # stop derriere la zone
    entry_expire_minutes: int = 15       # ordre limit non rempli -> annule
    profile_days: int = 5                # composite pour LVN
    npoc_lookback_days: int = 20
    absorption: AbsorptionCfg = AbsorptionCfg()
    imbalance: ImbalanceCfg = ImbalanceCfg()


class RiskCfg(BaseModel):
    risk_pct: float = 0.0075             # 0.75 % par trade
    daily_stop_pct: float = 0.02         # -2 % -> stop jusqu'au lendemain
    max_consecutive_losses: int = 3      # 3 pertes -> pause jusqu'au lendemain
    max_trades_per_day: int = 3
    min_rr: float = 2.0
    partial_at_r: float = 1.0            # partiel a 1R
    partial_fraction: float = 0.5        # 50 % de la position
    qty_step: float = 0.001


class SessionCfg(BaseModel):
    start: str   # "HH:MM" UTC
    end: str


class BotConfig(BaseModel):
    symbol: str = "BTCUSDT"
    tick_size: float = 0.1
    bin_size: float = 1.0
    bar_minutes: int = 1
    data_dir: str = "data"
    journal_path: str = "journal.jsonl"
    equity: float = 10_000.0
    risk: RiskCfg = RiskCfg()
    strategy: StrategyCfg = StrategyCfg()
    sessions: list[SessionCfg] = [SessionCfg(start="13:00", end="17:00")]


def load_config(path: str | Path) -> BotConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return BotConfig(**data)
```

`config.yaml` (racine projet) :

```yaml
symbol: BTCUSDT
tick_size: 0.1
bin_size: 1.0
bar_minutes: 1
data_dir: data
journal_path: journal.jsonl
equity: 10000

risk:
  risk_pct: 0.0075
  daily_stop_pct: 0.02
  max_consecutive_losses: 3
  max_trades_per_day: 3
  min_rr: 2.0
  partial_at_r: 1.0
  partial_fraction: 0.5
  qty_step: 0.001

strategy:
  zone_margin_pct: 0.001
  stop_buffer_ticks: 20
  entry_expire_minutes: 15
  profile_days: 5
  npoc_lookback_days: 20
  absorption:
    window_ms: 30000
    vol_factor: 3.0
    max_range_ticks: 15
    min_delta_frac: 0.3
    baseline_windows: 20
  imbalance:
    ratio: 3.0
    min_stack: 3

# Overlap Londres-NY, UTC
sessions:
  - {start: "13:00", end: "17:00"}
```

- [ ] **Step 4: Vérifier le passage**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_config.py -q
```

Attendu : PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add orderflow-bot && rtk git commit -m "feat(orderflow): config pydantic + config.yaml par defaut"
```

---

### Task 3: Parser aggTrade Binance

**Files:**
- Create: `src/orderflow_bot/ingestion/parser.py`
- Test: `tests/test_parser.py`

- [ ] **Step 1: Test qui échoue**

`tests/test_parser.py` (payload réel du stream `@aggTrade` Binance Futures USD-M) :

```python
from orderflow_bot.ingestion.parser import parse_agg_trade

PAYLOAD = {
    "e": "aggTrade", "E": 1718000000123, "s": "BTCUSDT", "a": 26129,
    "p": "117234.30", "q": "0.005", "f": 100, "l": 105,
    "T": 1718000000100, "m": True,
}


def test_parse_valid():
    t = parse_agg_trade(PAYLOAD)
    assert t is not None
    assert t.ts == 1718000000100          # T = trade time, pas E
    assert t.price == 117234.30
    assert t.qty == 0.005
    assert t.is_buyer_maker is True
    assert t.aggressor == -1


def test_parse_ignores_other_events():
    assert parse_agg_trade({"e": "depthUpdate"}) is None
    assert parse_agg_trade({"result": None, "id": 1}) is None
```

- [ ] **Step 2: Vérifier l'échec**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_parser.py -q
```

Attendu : FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implémenter**

`src/orderflow_bot/ingestion/parser.py` :

```python
from orderflow_bot.models import Trade


def parse_agg_trade(msg: dict) -> Trade | None:
    """Stream Binance @aggTrade -> Trade. Ignore tout autre message."""
    if msg.get("e") != "aggTrade":
        return None
    return Trade(
        ts=int(msg["T"]),
        price=float(msg["p"]),
        qty=float(msg["q"]),
        is_buyer_maker=bool(msg["m"]),
    )
```

- [ ] **Step 4: Vérifier le passage**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_parser.py -q
```

Attendu : PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add orderflow-bot && rtk git commit -m "feat(orderflow): parser aggTrade Binance"
```

---

### Task 4: Stockage Parquet — Recorder + Reader

**Files:**
- Create: `src/orderflow_bot/ingestion/recorder.py`, `src/orderflow_bot/ingestion/reader.py`
- Test: `tests/test_storage.py`

- [ ] **Step 1: Test qui échoue (round-trip)**

`tests/test_storage.py` :

```python
from orderflow_bot.ingestion.reader import read_trades
from orderflow_bot.ingestion.recorder import TradeRecorder
from orderflow_bot.models import Trade


def _trades(n: int, t0: int = 1_700_000_000_000) -> list[Trade]:
    return [
        Trade(ts=t0 + i * 100, price=100.0 + i * 0.1, qty=0.01 * (i + 1),
              is_buyer_maker=i % 2 == 0)
        for i in range(n)
    ]


def test_roundtrip(tmp_path):
    rec = TradeRecorder(tmp_path, "BTCUSDT", flush_every=4)
    src = _trades(10)
    for t in src:
        rec.append(t)
    rec.flush()                     # 2 fichiers auto + 1 reste
    got = list(read_trades(tmp_path, "BTCUSDT"))
    assert got == src               # ordre + valeurs exacts


def test_read_time_window(tmp_path):
    rec = TradeRecorder(tmp_path, "BTCUSDT", flush_every=100)
    src = _trades(10)
    for t in src:
        rec.append(t)
    rec.flush()
    t0 = src[0].ts
    got = list(read_trades(tmp_path, "BTCUSDT", start_ms=t0 + 300, end_ms=t0 + 700))
    assert got == src[3:7]


def test_read_empty_dir(tmp_path):
    assert list(read_trades(tmp_path, "BTCUSDT")) == []
```

- [ ] **Step 2: Vérifier l'échec**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_storage.py -q
```

Attendu : FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implémenter**

`src/orderflow_bot/ingestion/recorder.py` :

```python
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from orderflow_bot.models import Trade

_SCHEMA = pa.schema([
    ("ts", pa.int64()),
    ("price", pa.float64()),
    ("qty", pa.float64()),
    ("is_buyer_maker", pa.bool_()),
])


class TradeRecorder:
    """Bufferise puis ecrit des fichiers Parquet immuables nommes par plage de ts.
    Pas d'append Parquet : un fichier par flush, le reader recolle via ORDER BY."""

    def __init__(self, data_dir: str | Path, symbol: str, flush_every: int = 5000):
        self.flush_every = flush_every
        self._dir = Path(data_dir) / symbol
        self._dir.mkdir(parents=True, exist_ok=True)
        self._buf: list[Trade] = []

    def append(self, t: Trade) -> None:
        self._buf.append(t)
        if len(self._buf) >= self.flush_every:
            self.flush()

    def flush(self) -> None:
        if not self._buf:
            return
        table = pa.table(
            {
                "ts": [t.ts for t in self._buf],
                "price": [t.price for t in self._buf],
                "qty": [t.qty for t in self._buf],
                "is_buyer_maker": [t.is_buyer_maker for t in self._buf],
            },
            schema=_SCHEMA,
        )
        name = f"{self._buf[0].ts}_{self._buf[-1].ts}.parquet"
        pq.write_table(table, self._dir / name)
        self._buf.clear()
```

`src/orderflow_bot/ingestion/reader.py` :

```python
from collections.abc import Iterator
from pathlib import Path

import duckdb

from orderflow_bot.models import Trade


def read_trades(
    data_dir: str | Path,
    symbol: str,
    start_ms: int | None = None,
    end_ms: int | None = None,
) -> Iterator[Trade]:
    """Relit tous les Parquet du symbole, ordonnes par ts, en streaming par lots."""
    folder = Path(data_dir) / symbol
    if not folder.exists() or not any(folder.glob("*.parquet")):
        return
    q = "SELECT ts, price, qty, is_buyer_maker FROM read_parquet(?)"
    params: list = [str(folder / "*.parquet")]
    conds = []
    if start_ms is not None:
        conds.append("ts >= ?")
        params.append(start_ms)
    if end_ms is not None:
        conds.append("ts < ?")
        params.append(end_ms)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY ts"
    cur = duckdb.connect().execute(q, params)
    while batch := cur.fetchmany(50_000):
        for ts, price, qty, mkr in batch:
            yield Trade(ts=ts, price=price, qty=qty, is_buyer_maker=mkr)
```

- [ ] **Step 4: Vérifier le passage**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_storage.py -q
```

Attendu : PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add orderflow-bot && rtk git commit -m "feat(orderflow): stockage tick Parquet (recorder + reader DuckDB)"
```

---

### Task 5: Websocket Binance + CLI `record`

**Files:**
- Create: `src/orderflow_bot/ingestion/binance_ws.py`, `src/orderflow_bot/live.py`, `src/orderflow_bot/__main__.py`
- Test: smoke test manuel (réseau requis)

- [ ] **Step 1: Implémenter le client websocket**

`src/orderflow_bot/ingestion/binance_ws.py` :

```python
import asyncio
import json
import logging
from collections.abc import Callable

import websockets

from orderflow_bot.ingestion.parser import parse_agg_trade
from orderflow_bot.models import Trade

log = logging.getLogger(__name__)

FUTURES_WS = "wss://fstream.binance.com/ws"


async def stream_trades(
    symbol: str,
    handler: Callable[[Trade], None],
    url_base: str = FUTURES_WS,
) -> None:
    """Boucle infinie : connecte, pousse chaque Trade au handler, reconnecte
    avec backoff exponentiel (1s -> 60s) sur toute coupure."""
    url = f"{url_base}/{symbol.lower()}@aggTrade"
    backoff = 1.0
    while True:
        try:
            async with websockets.connect(url, ping_interval=180, ping_timeout=60) as ws:
                log.info("connecte a %s", url)
                backoff = 1.0
                async for raw in ws:
                    t = parse_agg_trade(json.loads(raw))
                    if t is not None:
                        handler(t)
        except (websockets.WebSocketException, OSError) as e:
            log.warning("deconnexion ws (%s), reconnexion dans %.0fs", e, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60.0)
```

- [ ] **Step 2: Implémenter `run_record` et le CLI**

`src/orderflow_bot/live.py` :

```python
import asyncio
import logging

from orderflow_bot.config import BotConfig
from orderflow_bot.ingestion.binance_ws import stream_trades
from orderflow_bot.ingestion.recorder import TradeRecorder

log = logging.getLogger(__name__)


async def run_record(cfg: BotConfig) -> None:
    """Enregistre le flux tick en Parquet. Ctrl+C -> flush propre."""
    rec = TradeRecorder(cfg.data_dir, cfg.symbol)
    try:
        await stream_trades(cfg.symbol, rec.append)
    finally:
        rec.flush()
        log.info("flush final ok")
```

`src/orderflow_bot/__main__.py` :

```python
import argparse
import asyncio
import logging

from orderflow_bot.config import load_config


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(prog="orderflow_bot")
    ap.add_argument("command", choices=["record", "backtest", "paper"])
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--start", default=None, help="YYYY-MM-DD (backtest)")
    ap.add_argument("--end", default=None, help="YYYY-MM-DD (backtest)")
    args = ap.parse_args()
    cfg = load_config(args.config)

    if args.command == "record":
        from orderflow_bot.live import run_record
        asyncio.run(run_record(cfg))
    elif args.command == "backtest":
        raise SystemExit("backtest: implemente en Task 17")
    else:
        raise SystemExit("paper: implemente en Task 18")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Vérifier que la suite existante passe toujours**

```powershell
rtk test .venv\Scripts\python -m pytest -q
```

Attendu : PASS.

- [ ] **Step 4: Smoke test manuel (réseau requis)**

```powershell
.venv\Scripts\python -m orderflow_bot record
```

Laisser tourner ~30 s, Ctrl+C. Vérifier qu'au moins un fichier existe :

```powershell
ls data\BTCUSDT
```

Attendu : ≥1 fichier `<ts>_<ts>.parquet` (le flush final écrit le buffer partiel). Si la machine n'a pas accès réseau, noter SKIP et continuer.

- [ ] **Step 5: Commit**

```bash
rtk git add orderflow-bot && rtk git commit -m "feat(orderflow): websocket Binance avec reconnexion + CLI record"
```

> **Note exécuteur :** à partir d'ici, laisser `record` tourner en tâche de fond dans un terminal séparé pour accumuler des données réelles.

---

### Task 6: Agrégateur de bougies footprint

**Files:**
- Create: `src/orderflow_bot/features/aggregator.py`
- Test: `tests/test_aggregator.py`, `tests/conftest.py`

- [ ] **Step 1: Helper de test partagé**

`tests/conftest.py` :

```python
from orderflow_bot.models import FootprintBar, Trade


def make_trade(ts: int, price: float, qty: float = 1.0, sell: bool = False) -> Trade:
    return Trade(ts=ts, price=price, qty=qty, is_buyer_maker=sell)


def make_bar(low: float, high: float, delta: float, open_: float = 0.0,
             close: float = 0.0, open_ts: int = 0) -> FootprintBar:
    o = open_ or low
    c = close or high
    return FootprintBar(open_ts=open_ts, close_ts=open_ts + 60_000, open=o, high=high,
                        low=low, close=c, volume=abs(delta) or 1.0, delta=delta,
                        ask_vol={}, bid_vol={})
```

- [ ] **Step 2: Test qui échoue**

`tests/test_aggregator.py` :

```python
from orderflow_bot.features.aggregator import BarAggregator

from .conftest import make_trade


def test_bar_closes_on_window_boundary():
    agg = BarAggregator(bar_ms=60_000, bin_size=1.0)
    assert agg.on_trade(make_trade(0, 100.0, 2.0)) is None
    assert agg.on_trade(make_trade(10_000, 101.5, 1.0, sell=True)) is None
    bar = agg.on_trade(make_trade(60_000, 102.0, 1.0))   # nouvelle fenetre
    assert bar is not None
    assert (bar.open, bar.high, bar.low, bar.close) == (100.0, 101.5, 100.0, 101.5)
    assert bar.volume == 3.0
    assert bar.delta == 2.0 - 1.0
    assert bar.ask_vol == {100: 2.0}
    assert bar.bid_vol == {102: 1.0}    # 101.5 -> bin 102 (round)


def test_flush_returns_partial_bar():
    agg = BarAggregator(bar_ms=60_000, bin_size=1.0)
    agg.on_trade(make_trade(5_000, 100.0))
    bar = agg.flush()
    assert bar is not None and bar.close == 100.0
    assert agg.flush() is None
```

- [ ] **Step 3: Vérifier l'échec**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_aggregator.py -q
```

Attendu : FAIL — `ModuleNotFoundError`.

- [ ] **Step 4: Implémenter**

`src/orderflow_bot/features/aggregator.py` :

```python
from orderflow_bot.binning import bin_of
from orderflow_bot.models import FootprintBar, Trade


class BarAggregator:
    """Agrege les trades en bougies temps avec footprint bid/ask par bin.
    on_trade retourne la bougie precedente quand une nouvelle fenetre demarre."""

    def __init__(self, bar_ms: int, bin_size: float):
        self.bar_ms = bar_ms
        self.bin_size = bin_size
        self._cur: FootprintBar | None = None

    def on_trade(self, t: Trade) -> FootprintBar | None:
        start = t.ts - t.ts % self.bar_ms
        closed = None
        if self._cur is not None and start > self._cur.open_ts:
            closed = self._cur
            self._cur = None
        if self._cur is None:
            self._cur = FootprintBar(
                open_ts=start, close_ts=start + self.bar_ms,
                open=t.price, high=t.price, low=t.price, close=t.price,
                volume=0.0, delta=0.0, ask_vol={}, bid_vol={},
            )
        b = self._cur
        b.high = max(b.high, t.price)
        b.low = min(b.low, t.price)
        b.close = t.price
        b.volume += t.qty
        b.delta += t.qty * t.aggressor
        side = b.ask_vol if t.aggressor > 0 else b.bid_vol
        k = bin_of(t.price, self.bin_size)
        side[k] = side.get(k, 0.0) + t.qty
        return closed

    def flush(self) -> FootprintBar | None:
        closed, self._cur = self._cur, None
        return closed
```

- [ ] **Step 5: Vérifier le passage**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_aggregator.py -q
```

Attendu : PASS.

- [ ] **Step 6: Commit**

```bash
rtk git add orderflow-bot && rtk git commit -m "feat(orderflow): agregateur bougies footprint"
```

---

### Task 7: Volume profile — POC, value area, LVN/HVN

**Files:**
- Create: `src/orderflow_bot/features/volume_profile.py`
- Test: `tests/test_volume_profile.py`

- [ ] **Step 1: Test qui échoue**

`tests/test_volume_profile.py` :

```python
from orderflow_bot.features.volume_profile import VolumeProfile


def _profile(vols: dict[int, float]) -> VolumeProfile:
    p = VolumeProfile(bin_size=1.0)
    for b, q in vols.items():
        p.add(float(b), q)
    return p


def test_poc():
    p = _profile({98: 5, 99: 10, 100: 30, 101: 10, 102: 5})
    assert p.poc() == 100


def test_value_area_70pct():
    # total=60, 70%=42 ; expansion depuis POC : +101(40) puis +99(50) -> VAL=99, VAH=101
    p = _profile({98: 5, 99: 10, 100: 30, 101: 10, 102: 5})
    assert p.value_area(0.70) == (99, 101)


def test_lvn_groups_valley():
    # mean = 86/6 ; seuil 0.3*mean ~ 4.3 ; vallee [97, 98] -> representant 98
    p = _profile({95: 20, 96: 18, 97: 2, 98: 1, 99: 22, 100: 25})
    assert p.lvns(0.3) == [98]


def test_hvn():
    p = _profile({95: 20, 96: 18, 97: 2, 98: 1, 99: 22, 100: 25})
    assert p.hvns(1.5) == [99, 100]   # > 1.5 * (86/6) ~ 21.5


def test_merge():
    a = _profile({100: 10})
    b = _profile({100: 5, 101: 3})
    a.merge(b)
    assert a.vol == {100: 15.0, 101: 3.0}
    assert a.total == 18.0
```

- [ ] **Step 2: Vérifier l'échec**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_volume_profile.py -q
```

Attendu : FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implémenter**

`src/orderflow_bot/features/volume_profile.py` :

```python
from orderflow_bot.binning import bin_of


class VolumeProfile:
    """Volume par bin de prix. POC, value area (expansion depuis le POC),
    LVN/HVN relatifs au volume moyen du range."""

    def __init__(self, bin_size: float):
        self.bin_size = bin_size
        self.vol: dict[int, float] = {}
        self.total = 0.0

    def add(self, price: float, qty: float) -> None:
        b = bin_of(price, self.bin_size)
        self.vol[b] = self.vol.get(b, 0.0) + qty
        self.total += qty

    def merge(self, other: "VolumeProfile") -> None:
        for b, q in other.vol.items():
            self.vol[b] = self.vol.get(b, 0.0) + q
            self.total += q

    def poc(self) -> int:
        return max(self.vol, key=lambda b: self.vol[b])

    def value_area(self, pct: float = 0.70) -> tuple[int, int]:
        """(val_bin, vah_bin) : etend depuis le POC vers le voisin le plus
        volumineux jusqu'a couvrir pct du volume total."""
        bins = sorted(self.vol)
        lo = hi = bins.index(self.poc())
        acc = self.vol[bins[lo]]
        while acc < pct * self.total and (lo > 0 or hi < len(bins) - 1):
            up = self.vol[bins[hi + 1]] if hi < len(bins) - 1 else -1.0
            down = self.vol[bins[lo - 1]] if lo > 0 else -1.0
            if up >= down:
                hi += 1
                acc += up
            else:
                lo -= 1
                acc += down
        return bins[lo], bins[hi]

    def _mean_per_bin(self) -> float:
        lo, hi = min(self.vol), max(self.vol)
        return self.total / (hi - lo + 1)

    def lvns(self, frac: float = 0.3) -> list[int]:
        """Vallees internes (< frac x volume moyen), groupees ; un bin
        representant (centre) par vallee. Bords du range exclus."""
        m = self._mean_per_bin()
        lo, hi = min(self.vol), max(self.vol)
        out: list[int] = []
        run: list[int] = []
        for b in range(lo + 1, hi):
            if self.vol.get(b, 0.0) < frac * m:
                run.append(b)
            elif run:
                out.append(run[len(run) // 2])
                run = []
        if run:
            out.append(run[len(run) // 2])
        return out

    def hvns(self, frac: float = 1.5) -> list[int]:
        m = self._mean_per_bin()
        return sorted(b for b, q in self.vol.items() if q > frac * m)
```

- [ ] **Step 4: Vérifier le passage**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_volume_profile.py -q
```

Attendu : PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add orderflow-bot && rtk git commit -m "feat(orderflow): volume profile (POC, value area, LVN/HVN)"
```

---

### Task 8: CVD + divergences

**Files:**
- Create: `src/orderflow_bot/features/cvd.py`
- Test: `tests/test_cvd.py`

- [ ] **Step 1: Test qui échoue**

`tests/test_cvd.py` :

```python
from orderflow_bot.features.cvd import CvdTracker

from .conftest import make_bar


def _feed(tracker: CvdTracker, lows_deltas: list[tuple[float, float]]) -> None:
    for low, delta in lows_deltas:
        tracker.on_bar(make_bar(low=low, high=low + 2.0, delta=delta))


def test_bullish_divergence():
    t = CvdTracker()
    # swing low 1 : low=100, cvd=-10 ; swing low 2 : low=99 (plus bas), cvd=-5 (plus haut)
    _feed(t, [(101, -4), (100, -6), (101.5, 3), (100.5, -4), (99, 6), (100.5, 1)])
    # cvd cumulatif aux swings : i=1 -> -10 ; i=4 -> -5
    assert t.bullish_divergence() is True
    assert t.bearish_divergence() is False


def test_no_divergence_when_cvd_confirms():
    t = CvdTracker()
    # prix plus bas ET cvd plus bas -> pas de divergence
    _feed(t, [(101, -4), (100, -6), (101.5, 1), (100.5, -8), (99, -2), (100.5, 1)])
    assert t.bullish_divergence() is False


def test_reset():
    t = CvdTracker()
    _feed(t, [(101, -4), (100, -6), (101.5, 3)])
    t.reset()
    assert t.cvd == 0.0
    assert t.bullish_divergence() is False
```

- [ ] **Step 2: Vérifier l'échec**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_cvd.py -q
```

Attendu : FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implémenter**

`src/orderflow_bot/features/cvd.py` :

```python
from orderflow_bot.models import FootprintBar


class CvdTracker:
    """Cumulative Volume Delta par bougie + divergences prix/CVD sur les deux
    derniers swings (fractale 1-1 : extreme strictement au-dela de ses voisins)."""

    def __init__(self):
        self.cvd = 0.0
        self._hist: list[tuple[float, float, float]] = []   # (low, high, cvd_close)

    def reset(self) -> None:
        self.cvd = 0.0
        self._hist.clear()

    def on_bar(self, bar: FootprintBar) -> None:
        self.cvd += bar.delta
        self._hist.append((bar.low, bar.high, self.cvd))

    def _swings(self, key: int, is_low: bool) -> list[tuple[float, float]]:
        h = self._hist
        out = []
        for i in range(1, len(h) - 1):
            if is_low and h[i][key] < h[i - 1][key] and h[i][key] < h[i + 1][key]:
                out.append((h[i][key], h[i][2]))
            if not is_low and h[i][key] > h[i - 1][key] and h[i][key] > h[i + 1][key]:
                out.append((h[i][key], h[i][2]))
        return out

    def bullish_divergence(self) -> bool:
        s = self._swings(0, is_low=True)
        if len(s) < 2:
            return False
        (p1, c1), (p2, c2) = s[-2], s[-1]
        return p2 < p1 and c2 > c1

    def bearish_divergence(self) -> bool:
        s = self._swings(1, is_low=False)
        if len(s) < 2:
            return False
        (p1, c1), (p2, c2) = s[-2], s[-1]
        return p2 > p1 and c2 < c1
```

- [ ] **Step 4: Vérifier le passage**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_cvd.py -q
```

Attendu : PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add orderflow-bot && rtk git commit -m "feat(orderflow): CVD et divergences prix/delta"
```

---

### Task 9: Imbalances diagonales empilées

**Files:**
- Create: `src/orderflow_bot/features/imbalance.py`
- Test: `tests/test_imbalance.py`

- [ ] **Step 1: Test qui échoue**

`tests/test_imbalance.py` :

```python
from orderflow_bot.features.imbalance import stacked_imbalances
from orderflow_bot.models import FootprintBar


def _bar(ask: dict[int, float], bid: dict[int, float]) -> FootprintBar:
    return FootprintBar(open_ts=0, close_ts=60_000, open=100.0, high=101.0,
                        low=99.0, close=100.0, volume=1.0, delta=0.0,
                        ask_vol=ask, bid_vol=bid)


def test_stacked_buy_imbalances():
    # diagonale : ask(b) vs bid(b-1) ; ratio 3 atteint sur 100,101,102
    bar = _bar(ask={100: 30, 101: 24, 102: 18}, bid={99: 5, 100: 8, 101: 6})
    st = stacked_imbalances(bar, ratio=3.0, min_stack=3)
    assert st["buy"] == [100, 101, 102]
    assert st["sell"] == []


def test_no_stack_below_min():
    bar = _bar(ask={100: 30, 101: 24}, bid={99: 5, 100: 8})
    st = stacked_imbalances(bar, ratio=3.0, min_stack=3)
    assert st["buy"] == []


def test_zero_denominator_counts_as_imbalance():
    bar = _bar(ask={100: 5, 101: 5, 102: 5}, bid={})
    st = stacked_imbalances(bar, ratio=3.0, min_stack=3)
    assert st["buy"] == [100, 101, 102]
```

- [ ] **Step 2: Vérifier l'échec**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_imbalance.py -q
```

Attendu : FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implémenter**

`src/orderflow_bot/features/imbalance.py` :

```python
from orderflow_bot.models import FootprintBar


def stacked_imbalances(
    bar: FootprintBar, ratio: float = 3.0, min_stack: int = 3
) -> dict[str, list[int]]:
    """Imbalances diagonales footprint : achat = ask(b) >= ratio x bid(b-1),
    vente = bid(b) >= ratio x ask(b+1). Denominateur nul + numerateur > 0 compte.
    Retourne uniquement les bins appartenant a une pile >= min_stack consecutifs."""

    def imb(num: float, den: float) -> bool:
        if num <= 0:
            return False
        return den == 0 or num / den >= ratio

    buys, sells = [], []
    for b in set(bar.ask_vol) | set(bar.bid_vol):
        if imb(bar.ask_vol.get(b, 0.0), bar.bid_vol.get(b - 1, 0.0)):
            buys.append(b)
        if imb(bar.bid_vol.get(b, 0.0), bar.ask_vol.get(b + 1, 0.0)):
            sells.append(b)

    def stacks(xs: list[int]) -> list[int]:
        out: list[int] = []
        run: list[int] = []
        for b in sorted(xs):
            run = run + [b] if run and b == run[-1] + 1 else [b]
            if len(run) == min_stack:
                out.extend(run)
            elif len(run) > min_stack:
                out.append(b)
        return out

    return {"buy": stacks(buys), "sell": stacks(sells)}
```

- [ ] **Step 4: Vérifier le passage**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_imbalance.py -q
```

Attendu : PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add orderflow-bot && rtk git commit -m "feat(orderflow): imbalances diagonales empilees"
```

---

### Task 10: Détection d'absorption

**Files:**
- Create: `src/orderflow_bot/features/absorption.py`
- Test: `tests/test_absorption.py`

- [ ] **Step 1: Test qui échoue**

`tests/test_absorption.py` :

```python
from orderflow_bot.config import AbsorptionCfg
from orderflow_bot.features.absorption import AbsorptionDetector

from .conftest import make_trade

CFG = AbsorptionCfg(window_ms=30_000, vol_factor=3.0, max_range_ticks=15,
                    min_delta_frac=0.3, baseline_windows=8)


def _baseline(det: AbsorptionDetector, t0: int) -> int:
    """8 fenetres calmes de 30s, 1 trade de qty 1.0 chacune. Retourne ts suivant."""
    ts = t0
    for i in range(8):
        assert det.on_trade(make_trade(ts, 100.0 + (i % 2) * 0.1, 1.0, sell=i % 2 == 0)) is None
        ts += 30_000
    return ts


def test_detects_sell_absorption():
    det = AbsorptionDetector(CFG, tick_size=0.1)
    ts = _baseline(det, 1_000_000)
    # choc : ventes massives, range 1 tick, le prix ne baisse plus (last >= first)
    hits = []
    for i in range(10):
        px = 97.0 if i % 2 == 0 else 97.1
        a = det.on_trade(make_trade(ts, px, 0.5, sell=True))
        if a:
            hits.append(a)
        ts += 1_500
    assert hits, "absorption attendue"
    assert hits[0].side == 1            # vente absorbee -> signal bullish


def test_no_absorption_when_price_keeps_falling():
    det = AbsorptionDetector(CFG, tick_size=0.1)
    ts = _baseline(det, 1_000_000)
    # meme volume vendeur mais le prix degringole (range > 15 ticks)
    px = 100.0
    for _ in range(10):
        assert det.on_trade(make_trade(ts, round(px, 1), 0.5, sell=True)) is None
        px -= 0.4
        ts += 1_500


def test_needs_baseline():
    det = AbsorptionDetector(CFG, tick_size=0.1)
    # gros volume immediat mais aucune baseline -> jamais de signal
    ts = 1_000_000
    for i in range(10):
        assert det.on_trade(make_trade(ts, 97.0 if i % 2 else 97.1, 0.5, sell=True)) is None
        ts += 1_500
```

- [ ] **Step 2: Vérifier l'échec**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_absorption.py -q
```

Attendu : FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implémenter**

`src/orderflow_bot/features/absorption.py` :

```python
import statistics
from collections import deque
from dataclasses import dataclass

from orderflow_bot.config import AbsorptionCfg
from orderflow_bot.models import Trade


@dataclass(frozen=True, slots=True)
class Absorption:
    ts: int
    side: int     # +1 : ventes absorbees (bullish) ; -1 : achats absorbes (bearish)
    price: float


class AbsorptionDetector:
    """Fenetre glissante de window_ms. Absorption si, simultanement :
    volume >= vol_factor x mediane des fenetres baseline (tumbling),
    range prix <= max_range_ticks, delta directionnel >= min_delta_frac x volume,
    et le prix ne progresse plus dans le sens du delta."""

    def __init__(self, cfg: AbsorptionCfg, tick_size: float):
        self.cfg = cfg
        self.tick = tick_size
        self._win: deque[Trade] = deque()
        self._baseline: deque[float] = deque(maxlen=cfg.baseline_windows)
        self._slot: int | None = None
        self._slot_vol = 0.0

    def on_trade(self, t: Trade) -> Absorption | None:
        c = self.cfg
        slot = t.ts // c.window_ms
        if self._slot is None:
            self._slot = slot
        while self._slot < slot:
            self._baseline.append(self._slot_vol)
            self._slot_vol = 0.0
            self._slot += 1
        self._slot_vol += t.qty

        self._win.append(t)
        cutoff = t.ts - c.window_ms
        while self._win and self._win[0].ts < cutoff:
            self._win.popleft()

        if len(self._baseline) < 3:
            return None
        med = statistics.median(self._baseline)
        vol = sum(x.qty for x in self._win)
        if med <= 0 or vol < c.vol_factor * med:
            return None
        prices = [x.price for x in self._win]
        if max(prices) - min(prices) > c.max_range_ticks * self.tick:
            return None
        delta = sum(x.qty * x.aggressor for x in self._win)
        first, last = self._win[0].price, self._win[-1].price
        if delta <= -c.min_delta_frac * vol and last >= first:
            self._win.clear()
            return Absorption(ts=t.ts, side=1, price=t.price)
        if delta >= c.min_delta_frac * vol and last <= first:
            self._win.clear()
            return Absorption(ts=t.ts, side=-1, price=t.price)
        return None
```

- [ ] **Step 4: Vérifier le passage**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_absorption.py -q
```

Attendu : PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add orderflow-bot && rtk git commit -m "feat(orderflow): detecteur d'absorption sur fenetre glissante"
```

---

### Task 11: Contexte HTF — DailyLevels, biais, naked POCs

**Files:**
- Create: `src/orderflow_bot/strategy/context.py`
- Test: `tests/test_context.py`

- [ ] **Step 1: Test qui échoue**

`tests/test_context.py` :

```python
from orderflow_bot.features.volume_profile import VolumeProfile
from orderflow_bot.strategy.context import (
    Bias, DailyLevels, levels_from_profile, market_bias, naked_pocs,
)


def _levels(day: int, poc: float, lo: float = 0.0, hi: float = 1e9) -> DailyLevels:
    return DailyLevels(day=day, poc=poc, vah=poc + 3, val=poc - 3, high=hi, low=lo)


def test_levels_from_profile():
    p = VolumeProfile(bin_size=1.0)
    for b, q in {98: 5, 99: 10, 100: 30, 101: 10, 102: 5}.items():
        p.add(float(b), q)
    lv = levels_from_profile(day=10, profile=p, high=103.0, low=97.0)
    assert lv.poc == 100.0
    assert (lv.val, lv.vah) == (99.0, 101.0)
    assert (lv.low, lv.high) == (97.0, 103.0)


def test_bias_long_on_rising_pocs():
    assert market_bias([_levels(1, 100), _levels(2, 101), _levels(3, 102)]) is Bias.LONG
    assert market_bias([_levels(1, 102), _levels(2, 101), _levels(3, 100)]) is Bias.SHORT
    assert market_bias([_levels(1, 100), _levels(2, 103), _levels(3, 101)]) is Bias.BOTH
    assert market_bias([_levels(1, 100)]) is Bias.BOTH   # historique insuffisant


def test_naked_pocs():
    lv = [
        _levels(1, 100.0),                      # retouche au jour 2 -> pas naked
        _levels(2, 95.0, lo=94.0, hi=101.0),    # jour 2 : range couvre 100
        _levels(3, 97.0, lo=96.0, hi=98.0),     # ne couvre pas 95 -> 95 naked
    ]
    assert naked_pocs(lv) == [95.0]             # dernier jour exclu par definition
```

- [ ] **Step 2: Vérifier l'échec**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_context.py -q
```

Attendu : FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implémenter**

`src/orderflow_bot/strategy/context.py` :

```python
from dataclasses import dataclass
from enum import Enum

from orderflow_bot.binning import price_of
from orderflow_bot.features.volume_profile import VolumeProfile


class Bias(Enum):
    LONG = "long"
    SHORT = "short"
    BOTH = "both"


@dataclass(frozen=True, slots=True)
class DailyLevels:
    day: int        # epoch days (ts // 86_400_000)
    poc: float
    vah: float
    val: float
    high: float
    low: float


def levels_from_profile(
    day: int, profile: VolumeProfile, high: float, low: float
) -> DailyLevels:
    val_b, vah_b = profile.value_area()
    s = profile.bin_size
    return DailyLevels(day=day, poc=price_of(profile.poc(), s),
                       vah=price_of(vah_b, s), val=price_of(val_b, s),
                       high=high, low=low)


def market_bias(levels: list[DailyLevels]) -> Bias:
    """POC strictement montants sur 3 jours -> LONG ; descendants -> SHORT ;
    sinon range -> BOTH (les deux sens aux extremes de la value area)."""
    if len(levels) < 3:
        return Bias.BOTH
    a, b, c = levels[-3:]
    if a.poc < b.poc < c.poc:
        return Bias.LONG
    if a.poc > b.poc > c.poc:
        return Bias.SHORT
    return Bias.BOTH


def naked_pocs(levels: list[DailyLevels]) -> list[float]:
    """POC des jours passes jamais retraverses par le range d'un jour ulterieur.
    Le dernier jour est exclu (aucun jour ulterieur pour le tester)."""
    out = []
    for i, lv in enumerate(levels[:-1]):
        if all(not (nxt.low <= lv.poc <= nxt.high) for nxt in levels[i + 1:]):
            out.append(lv.poc)
    return out
```

- [ ] **Step 4: Vérifier le passage**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_context.py -q
```

Attendu : PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add orderflow-bot && rtk git commit -m "feat(orderflow): contexte HTF (daily levels, biais, naked POC)"
```

---

### Task 12: Zones tradables du jour

**Files:**
- Create: `src/orderflow_bot/strategy/zones.py`
- Test: `tests/test_zones.py`

- [ ] **Step 1: Test qui échoue**

`tests/test_zones.py` :

```python
from orderflow_bot.strategy.context import DailyLevels
from orderflow_bot.strategy.zones import Zone, build_zones, zone_at

PREV = DailyLevels(day=1, poc=100.0, vah=103.0, val=97.0, high=105.0, low=95.0)


def test_build_zones_val_vah():
    zones = build_zones(PREV, npocs=[], lvn_prices=[], margin_pct=0.002)
    val = next(z for z in zones if z.kind == "val")
    vah = next(z for z in zones if z.kind == "vah")
    m = 100.0 * 0.002
    assert (val.lo, val.hi, val.side, val.target) == (97.0 - m, 97.0 + m, 1, 100.0)
    assert (vah.lo, vah.hi, vah.side, vah.target) == (103.0 - m, 103.0 + m, -1, 100.0)


def test_build_zones_npoc_lvn_both_sides():
    zones = build_zones(PREV, npocs=[92.0], lvn_prices=[99.0], margin_pct=0.002)
    npoc = next(z for z in zones if z.kind == "npoc")
    lvn = next(z for z in zones if z.kind == "lvn")
    assert npoc.side == 0 and npoc.target == 100.0
    assert lvn.side == 0


def test_zone_at():
    zones = build_zones(PREV, npocs=[], lvn_prices=[], margin_pct=0.002)
    z = zone_at(zones, 97.1)
    assert z is not None and z.kind == "val"
    assert zone_at(zones, 100.0) is None
```

- [ ] **Step 2: Vérifier l'échec**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_zones.py -q
```

Attendu : FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implémenter**

`src/orderflow_bot/strategy/zones.py` :

```python
from dataclasses import dataclass

from orderflow_bot.strategy.context import DailyLevels


@dataclass(frozen=True, slots=True)
class Zone:
    lo: float
    hi: float
    side: int      # +1 long only (VAL), -1 short only (VAH), 0 selon trigger (nPOC/LVN)
    kind: str      # val | vah | npoc | lvn
    target: float


def build_zones(
    prev: DailyLevels,
    npocs: list[float],
    lvn_prices: list[float],
    margin_pct: float,
) -> list[Zone]:
    """Zones du jour depuis les niveaux de la veille. Target v1 = POC veille
    (bord conservateur de la rotation attendue)."""
    m = prev.poc * margin_pct
    zones = [
        Zone(prev.val - m, prev.val + m, 1, "val", prev.poc),
        Zone(prev.vah - m, prev.vah + m, -1, "vah", prev.poc),
    ]
    zones += [Zone(p - m, p + m, 0, "npoc", prev.poc) for p in npocs]
    zones += [Zone(p - m, p + m, 0, "lvn", prev.poc) for p in lvn_prices]
    return zones


def zone_at(zones: list[Zone], price: float) -> Zone | None:
    for z in zones:
        if z.lo <= price <= z.hi:
            return z
    return None
```

- [ ] **Step 4: Vérifier le passage**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_zones.py -q
```

Attendu : PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add orderflow-bot && rtk git commit -m "feat(orderflow): zones tradables (VAL/VAH, naked POC, LVN)"
```

---

### Task 13: Triggers + Confluence → OrderPlan

**Files:**
- Create: `src/orderflow_bot/strategy/confluence.py`
- Test: `tests/test_confluence.py`

- [ ] **Step 1: Test qui échoue**

`tests/test_confluence.py` :

```python
from orderflow_bot.config import ImbalanceCfg
from orderflow_bot.strategy.confluence import ConfluenceEngine, Trigger
from orderflow_bot.strategy.context import Bias, DailyLevels
from orderflow_bot.strategy.zones import build_zones

PREV = DailyLevels(day=1, poc=100.0, vah=103.0, val=97.0, high=105.0, low=95.0)


def _engine(bias: Bias = Bias.BOTH) -> ConfluenceEngine:
    eng = ConfluenceEngine(min_rr=2.0, stop_buffer_ticks=10, tick_size=0.1)
    zones = build_zones(PREV, npocs=[], lvn_prices=[], margin_pct=0.002)
    eng.update_day(zones, bias)
    return eng


def test_long_in_val_zone():
    eng = _engine()
    plan = eng.evaluate(Trigger(ts=1, side=1, kind="absorption", price=97.1))
    assert plan is not None
    assert plan.side == 1
    assert plan.entry == 97.1
    assert plan.stop == (97.0 - 0.2) - 1.0      # zone.lo - buffer 10 ticks
    assert plan.target == 100.0
    assert plan.meta == {"zone": "val", "trigger": "absorption", "bias": "both"}


def test_rejects_outside_zone():
    eng = _engine()
    assert eng.evaluate(Trigger(ts=1, side=1, kind="absorption", price=99.0)) is None


def test_rejects_wrong_zone_side():
    eng = _engine()
    # trigger short dans la zone VAL (long only) -> rejet
    assert eng.evaluate(Trigger(ts=1, side=-1, kind="absorption", price=97.1)) is None


def test_rejects_against_bias():
    eng = _engine(Bias.SHORT)
    assert eng.evaluate(Trigger(ts=1, side=1, kind="absorption", price=97.1)) is None


def test_rejects_poor_rr():
    # entry colle au target : reward ~1.4 / risk ~1.3 -> RR < 2 (97.1 est bien DANS la zone)
    eng = ConfluenceEngine(min_rr=2.0, stop_buffer_ticks=10, tick_size=0.1)
    near = DailyLevels(day=1, poc=98.5, vah=103.0, val=97.0, high=105.0, low=95.0)
    eng.update_day(build_zones(near, [], [], 0.002), Bias.BOTH)
    assert eng.evaluate(Trigger(ts=1, side=1, kind="absorption", price=97.1)) is None


def test_trigger_engine_emits_on_bar_signals():
    from orderflow_bot.config import AbsorptionCfg
    from orderflow_bot.features.absorption import AbsorptionDetector
    from orderflow_bot.features.cvd import CvdTracker
    from orderflow_bot.models import FootprintBar
    from orderflow_bot.strategy.confluence import TriggerEngine

    eng = TriggerEngine(
        absorption=AbsorptionDetector(AbsorptionCfg(), tick_size=0.1),
        cvd=CvdTracker(),
        imb_cfg=ImbalanceCfg(ratio=3.0, min_stack=3),
    )
    # bougie baissiere avec pile d'imbalances achat -> trigger long contre le mouvement
    bar = FootprintBar(open_ts=0, close_ts=60_000, open=101.0, high=101.0, low=99.0,
                       close=99.5, volume=10.0, delta=2.0,
                       ask_vol={99: 9, 100: 9, 101: 9}, bid_vol={98: 1, 99: 2, 100: 2})
    trigs = eng.on_bar(bar)
    assert any(t.kind == "stacked_imbalance" and t.side == 1 for t in trigs)
```

- [ ] **Step 2: Vérifier l'échec**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_confluence.py -q
```

Attendu : FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implémenter**

`src/orderflow_bot/strategy/confluence.py` :

```python
from dataclasses import dataclass

from orderflow_bot.config import ImbalanceCfg
from orderflow_bot.features.absorption import AbsorptionDetector
from orderflow_bot.features.cvd import CvdTracker
from orderflow_bot.features.imbalance import stacked_imbalances
from orderflow_bot.models import FootprintBar, OrderPlan, Trade
from orderflow_bot.strategy.context import Bias
from orderflow_bot.strategy.zones import Zone, zone_at


@dataclass(frozen=True, slots=True)
class Trigger:
    ts: int
    side: int
    kind: str     # absorption | cvd_divergence | stacked_imbalance
    price: float


class TriggerEngine:
    """Couche 3 : transforme les sorties des detecteurs en Triggers dates."""

    def __init__(self, absorption: AbsorptionDetector, cvd: CvdTracker,
                 imb_cfg: ImbalanceCfg):
        self.absorption = absorption
        self.cvd = cvd
        self.imb_cfg = imb_cfg

    def on_trade(self, t: Trade) -> list[Trigger]:
        a = self.absorption.on_trade(t)
        if a is None:
            return []
        return [Trigger(ts=a.ts, side=a.side, kind="absorption", price=a.price)]

    def on_bar(self, bar: FootprintBar) -> list[Trigger]:
        self.cvd.on_bar(bar)
        out: list[Trigger] = []
        if self.cvd.bullish_divergence():
            out.append(Trigger(bar.close_ts, 1, "cvd_divergence", bar.close))
        if self.cvd.bearish_divergence():
            out.append(Trigger(bar.close_ts, -1, "cvd_divergence", bar.close))
        st = stacked_imbalances(bar, self.imb_cfg.ratio, self.imb_cfg.min_stack)
        # imbalances empilees CONTRE le mouvement de la bougie = renversement
        if st["buy"] and bar.close < bar.open:
            out.append(Trigger(bar.close_ts, 1, "stacked_imbalance", bar.close))
        if st["sell"] and bar.close > bar.open:
            out.append(Trigger(bar.close_ts, -1, "stacked_imbalance", bar.close))
        return out


class ConfluenceEngine:
    """Confluence des 3 couches : bias (contexte) x zone x trigger.
    Emet un OrderPlan complet (entry limit, stop structurel, target, R:R>=min)."""

    def __init__(self, min_rr: float, stop_buffer_ticks: int, tick_size: float):
        self.min_rr = min_rr
        self.buffer = stop_buffer_ticks * tick_size
        self.zones: list[Zone] = []
        self.bias = Bias.BOTH

    def update_day(self, zones: list[Zone], bias: Bias) -> None:
        self.zones = zones
        self.bias = bias

    def evaluate(self, trig: Trigger) -> OrderPlan | None:
        z = zone_at(self.zones, trig.price)
        if z is None:
            return None
        if z.side not in (0, trig.side):
            return None
        if self.bias is Bias.LONG and trig.side != 1:
            return None
        if self.bias is Bias.SHORT and trig.side != -1:
            return None
        entry = trig.price
        stop = z.lo - self.buffer if trig.side == 1 else z.hi + self.buffer
        risk = (entry - stop) * trig.side
        reward = (z.target - entry) * trig.side
        if risk <= 0 or reward / risk < self.min_rr:
            return None
        return OrderPlan(
            ts=trig.ts, side=trig.side, entry=entry, stop=stop, target=z.target,
            meta={"zone": z.kind, "trigger": trig.kind, "bias": self.bias.value},
        )
```

- [ ] **Step 4: Vérifier le passage**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_confluence.py -q
```

Attendu : PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add orderflow-bot && rtk git commit -m "feat(orderflow): triggers orderflow + moteur de confluence 3 couches"
```

---

### Task 14: RiskManager

**Files:**
- Create: `src/orderflow_bot/risk/manager.py`
- Test: `tests/test_risk.py`

- [ ] **Step 1: Test qui échoue**

`tests/test_risk.py` :

```python
from orderflow_bot.config import RiskCfg, SessionCfg
from orderflow_bot.models import OrderPlan
from orderflow_bot.risk.manager import RiskManager

DAY_MS = 86_400_000
TS_14H = 50 * DAY_MS + 14 * 3_600_000     # 14:00 UTC, jour 50
SESSIONS = [SessionCfg(start="13:00", end="17:00")]


def _rm(equity: float = 10_000.0) -> RiskManager:
    return RiskManager(RiskCfg(), SESSIONS, equity)


def _plan(entry: float = 100.0, stop: float = 98.7) -> OrderPlan:
    return OrderPlan(ts=TS_14H, side=1, entry=entry, stop=stop, target=104.0)


def test_size_from_stop_distance():
    rm = _rm()
    # 10000 * 0.0075 / 1.3 = 57.69... -> floor au step 0.001
    assert rm.size(_plan()) == 57.692


def test_size_none_when_too_small():
    rm = _rm(equity=0.1)
    assert rm.size(_plan()) is None


def test_session_filter():
    rm = _rm()
    assert rm.can_open(TS_14H) is True
    assert rm.can_open(50 * DAY_MS + 9 * 3_600_000) is False    # 09:00 hors session


def test_daily_stop_blocks_until_next_day():
    rm = _rm()
    rm.on_open(TS_14H)
    rm.on_close(TS_14H + 60_000, -250.0)     # -2.5 % > stop journalier 2 %
    assert rm.can_open(TS_14H + 120_000) is False
    assert rm.can_open(TS_14H + DAY_MS) is True    # lendemain : reset


def test_three_losses_pause():
    rm = _rm()
    for i in range(3):
        rm.on_open(TS_14H + i * 3)
        rm.on_close(TS_14H + i * 3 + 1, -10.0)
    assert rm.can_open(TS_14H + 100) is False
    assert rm.can_open(TS_14H + DAY_MS) is True


def test_win_resets_streak():
    # cap trades/jour leve pour isoler le comportement du streak
    rm = RiskManager(RiskCfg(max_trades_per_day=10), SESSIONS, 10_000.0)
    for pnl in (-10.0, -10.0, 50.0, -10.0):
        rm.on_open(TS_14H)
        rm.on_close(TS_14H + 1, pnl)
    assert rm.can_open(TS_14H + 100) is True


def test_single_position_and_daily_cap():
    rm = _rm()
    rm.on_open(TS_14H)
    assert rm.can_open(TS_14H + 1) is False        # position deja ouverte
    rm.on_close(TS_14H + 2, 5.0)
    rm.on_open(TS_14H + 3)
    rm.on_close(TS_14H + 4, 5.0)
    rm.on_open(TS_14H + 5)
    rm.on_close(TS_14H + 6, 5.0)
    assert rm.can_open(TS_14H + 7) is False        # cap 3 trades/jour


def test_cancel_refunds_trade_slot():
    rm = _rm()
    rm.on_open(TS_14H)
    rm.on_cancel()
    assert rm.can_open(TS_14H + 1) is True
```

- [ ] **Step 2: Vérifier l'échec**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_risk.py -q
```

Attendu : FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implémenter**

`src/orderflow_bot/risk/manager.py` :

```python
import math

from orderflow_bot.config import RiskCfg, SessionCfg
from orderflow_bot.models import OrderPlan

_DAY_MS = 86_400_000


def _mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


class RiskManager:
    """Garde-fous codes en dur, verifies AVANT toute soumission :
    risque fixe par trade, stop journalier, pertes consecutives,
    sessions UTC, position unique, cap trades/jour."""

    def __init__(self, cfg: RiskCfg, sessions: list[SessionCfg], equity: float):
        self.cfg = cfg
        self._sessions = [(_mins(s.start), _mins(s.end)) for s in sessions]
        self.equity = equity
        self.position_open = False
        self._day = -1
        self._day_start_equity = equity
        self._daily_pnl = 0.0
        self._streak = 0
        self._trades_today = 0

    def _roll(self, ts: int) -> None:
        day = ts // _DAY_MS
        if day != self._day:
            self._day = day
            self._day_start_equity = self.equity
            self._daily_pnl = 0.0
            self._streak = 0
            self._trades_today = 0

    def in_session(self, ts: int) -> bool:
        mins = (ts // 60_000) % 1440
        return any(a <= mins < b for a, b in self._sessions)

    def can_open(self, ts: int) -> bool:
        self._roll(ts)
        c = self.cfg
        return (
            not self.position_open
            and self.in_session(ts)
            and self._trades_today < c.max_trades_per_day
            and self._streak < c.max_consecutive_losses
            and self._daily_pnl > -c.daily_stop_pct * self._day_start_equity
        )

    def size(self, plan: OrderPlan) -> float | None:
        risk_per_unit = (plan.entry - plan.stop) * plan.side
        if risk_per_unit <= 0:
            return None
        qty = self.equity * self.cfg.risk_pct / risk_per_unit
        qty = math.floor(qty / self.cfg.qty_step) * self.cfg.qty_step
        qty = round(qty, 10)
        return qty if qty >= self.cfg.qty_step else None

    def on_open(self, ts: int) -> None:
        self._roll(ts)
        self.position_open = True
        self._trades_today += 1

    def on_cancel(self) -> None:
        """Entree expiree sans fill : le slot du jour est rendu."""
        self.position_open = False
        self._trades_today = max(0, self._trades_today - 1)

    def on_close(self, ts: int, pnl: float) -> None:
        self._roll(ts)
        self.position_open = False
        self.equity += pnl
        self._daily_pnl += pnl
        self._streak = self._streak + 1 if pnl < 0 else 0
```

- [ ] **Step 4: Vérifier le passage**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_risk.py -q
```

Attendu : PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add orderflow-bot && rtk git commit -m "feat(orderflow): risk manager (sizing, stop journalier, streak, sessions)"
```

---

### Task 15: PaperBroker — fills conservateurs, partiel 1R + breakeven

**Files:**
- Create: `src/orderflow_bot/execution/paper.py`
- Test: `tests/test_paper.py`

- [ ] **Step 1: Test qui échoue**

`tests/test_paper.py` :

```python
from orderflow_bot.config import RiskCfg
from orderflow_bot.execution.paper import PaperBroker
from orderflow_bot.models import Cancelled, ClosedTrade, OrderPlan

from .conftest import make_trade

# long : entry 100, stop 98 (risk 2.0), target 106 (RR 3)
PLAN = OrderPlan(ts=1_000, side=1, entry=100.0, stop=98.0, target=106.0)


def _broker() -> PaperBroker:
    return PaperBroker(RiskCfg(partial_at_r=1.0, partial_fraction=0.5),
                       expire_ms=900_000)


def test_entry_requires_strict_cross():
    br = _broker()
    br.submit(PLAN, qty=1.0, ts=1_000)
    assert br.on_trade(make_trade(2_000, 100.0)) is None      # toucher ne suffit pas
    assert br.on_trade(make_trade(3_000, 99.9)) is None       # fill, position ouverte
    assert br.active is True


def test_full_cycle_partial_then_target():
    br = _broker()
    br.submit(PLAN, qty=1.0, ts=1_000)
    br.on_trade(make_trade(2_000, 99.9))                      # entry @100
    # partiel a 1R = 102 : franchissement strict requis
    assert br.on_trade(make_trade(3_000, 102.0)) is None
    assert br.on_trade(make_trade(4_000, 102.1)) is None      # partiel 0.5 @102, stop -> BE
    # retour a 100 : stop BE sur le reste
    ct = br.on_trade(make_trade(5_000, 100.0))
    assert isinstance(ct, ClosedTrade)
    assert ct.pnl == 0.5 * 2.0 + 0.5 * 0.0                    # +1.0
    assert ct.r_multiple == 1.0 / (2.0 * 1.0)                 # 0.5 R
    kinds = [f.kind for f in ct.fills]
    assert kinds == ["entry", "partial", "stop"]
    assert br.active is False


def test_target_fill():
    br = _broker()
    br.submit(PLAN, qty=1.0, ts=1_000)
    br.on_trade(make_trade(2_000, 99.9))
    br.on_trade(make_trade(3_000, 102.1))                     # partiel
    ct = br.on_trade(make_trade(4_000, 106.1))                # target strict
    assert isinstance(ct, ClosedTrade)
    assert ct.pnl == 0.5 * 2.0 + 0.5 * 6.0                    # +4.0
    assert ct.fills[-1].kind == "target"
    assert ct.fills[-1].price == 106.0


def test_stop_with_gap_fills_worse():
    br = _broker()
    br.submit(PLAN, qty=1.0, ts=1_000)
    br.on_trade(make_trade(2_000, 99.9))
    ct = br.on_trade(make_trade(3_000, 97.5))                 # gap sous le stop
    assert isinstance(ct, ClosedTrade)
    assert ct.fills[-1].price == 97.5                          # fill au pire prix
    assert ct.pnl == (97.5 - 100.0) * 1.0


def test_entry_expires():
    br = _broker()
    br.submit(PLAN, qty=1.0, ts=1_000)
    ev = br.on_trade(make_trade(1_000 + 900_001, 101.0))
    assert isinstance(ev, Cancelled)
    assert br.active is False


def test_short_cycle():
    plan = OrderPlan(ts=1_000, side=-1, entry=100.0, stop=102.0, target=94.0)
    br = _broker()
    br.submit(plan, qty=1.0, ts=1_000)
    br.on_trade(make_trade(2_000, 100.1))                     # fill short @100
    br.on_trade(make_trade(3_000, 97.9))                      # partiel @98, stop -> BE
    ct = br.on_trade(make_trade(4_000, 93.9))                 # target @94
    assert isinstance(ct, ClosedTrade)
    assert ct.pnl == 0.5 * 2.0 + 0.5 * 6.0


def test_force_close():
    br = _broker()
    br.submit(PLAN, qty=1.0, ts=1_000)
    br.on_trade(make_trade(2_000, 99.9))
    ct = br.force_close(make_trade(5_000, 101.0))
    assert isinstance(ct, ClosedTrade)
    assert ct.fills[-1].kind == "eod"
    assert ct.pnl == 1.0
```

- [ ] **Step 2: Vérifier l'échec**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_paper.py -q
```

Attendu : FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implémenter**

`src/orderflow_bot/execution/paper.py` :

```python
from dataclasses import dataclass, field

from orderflow_bot.config import RiskCfg
from orderflow_bot.models import Cancelled, ClosedTrade, Fill, OrderPlan, Trade


@dataclass(slots=True)
class _Position:
    plan: OrderPlan
    qty: float
    submit_ts: int
    state: str = "pending"          # pending | open
    opened_ts: int = 0
    remaining: float = 0.0
    stop: float = 0.0               # stop courant (deplace a BE apres partiel)
    partial_done: bool = False
    fills: list[Fill] = field(default_factory=list)


class PaperBroker:
    """Simulateur de fills conservateur : tout franchissement de niveau doit etre
    STRICT (un trade imprime au-dela). Le stop accepte les gaps au pire prix.
    Au plus une position. Verifications dans l'ordre du pire cas : stop d'abord."""

    def __init__(self, cfg: RiskCfg, expire_ms: int):
        self.cfg = cfg
        self.expire_ms = expire_ms
        self._pos: _Position | None = None

    @property
    def active(self) -> bool:
        return self._pos is not None

    def submit(self, plan: OrderPlan, qty: float, ts: int) -> None:
        assert self._pos is None, "une seule position a la fois"
        self._pos = _Position(plan=plan, qty=qty, submit_ts=ts, stop=plan.stop)

    def on_trade(self, t: Trade) -> ClosedTrade | Cancelled | None:
        p = self._pos
        if p is None:
            return None
        s = p.plan.side
        if p.state == "pending":
            if t.ts - p.submit_ts > self.expire_ms:
                self._pos = None
                return Cancelled(ts=t.ts)
            if (p.plan.entry - t.price) * s > 0:               # franchissement strict
                p.state = "open"
                p.opened_ts = t.ts
                p.remaining = p.qty
                p.fills.append(Fill(ts=t.ts, price=p.plan.entry, qty=p.qty, kind="entry"))
            return None

        # position ouverte : pire cas d'abord
        if (t.price - p.stop) * s <= 0:
            worst = min(p.stop, t.price) if s == 1 else max(p.stop, t.price)
            return self._close(t.ts, worst, "stop")
        risk0 = (p.plan.entry - p.plan.stop) * s
        partial_level = p.plan.entry + s * self.cfg.partial_at_r * risk0
        if not p.partial_done and (t.price - partial_level) * s > 0:
            part_qty = round(p.qty * self.cfg.partial_fraction, 10)
            p.fills.append(Fill(ts=t.ts, price=partial_level, qty=part_qty, kind="partial"))
            p.remaining = round(p.remaining - part_qty, 10)
            p.partial_done = True
            p.stop = p.plan.entry                              # breakeven
            return None
        if (t.price - p.plan.target) * s > 0:
            return self._close(t.ts, p.plan.target, "target")
        return None

    def force_close(self, t: Trade) -> ClosedTrade | None:
        """Flat EOD : ferme le restant au prix courant."""
        p = self._pos
        if p is None:
            return None
        if p.state == "pending":
            self._pos = None
            return None
        return self._close(t.ts, t.price, "eod")

    def _close(self, ts: int, price: float, kind: str) -> ClosedTrade:
        p = self._pos
        assert p is not None
        p.fills.append(Fill(ts=ts, price=price, qty=p.remaining, kind=kind))
        s = p.plan.side
        entry = p.plan.entry
        pnl = sum((f.price - entry) * s * f.qty for f in p.fills if f.kind != "entry")
        risk0 = (entry - p.plan.stop) * s
        r = pnl / (risk0 * p.qty) if risk0 > 0 and p.qty > 0 else 0.0
        ct = ClosedTrade(plan=p.plan, qty=p.qty, fills=p.fills, pnl=round(pnl, 10),
                         r_multiple=round(r, 10), opened_ts=p.opened_ts, closed_ts=ts)
        self._pos = None
        return ct
```

- [ ] **Step 4: Vérifier le passage**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_paper.py -q
```

Attendu : PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add orderflow-bot && rtk git commit -m "feat(orderflow): paper broker (fills stricts, partiel 1R, breakeven, EOD)"
```

---

### Task 16: Journal de trades + métriques

**Files:**
- Create: `src/orderflow_bot/execution/journal.py`, `src/orderflow_bot/backtest/metrics.py`
- Test: `tests/test_journal_metrics.py`

- [ ] **Step 1: Test qui échoue**

`tests/test_journal_metrics.py` :

```python
from orderflow_bot.backtest.metrics import compute_metrics
from orderflow_bot.execution.journal import TradeJournal
from orderflow_bot.models import ClosedTrade, Fill, OrderPlan


def _ct(pnl: float, r: float) -> ClosedTrade:
    plan = OrderPlan(ts=1, side=1, entry=100.0, stop=98.0, target=106.0,
                     meta={"zone": "val", "trigger": "absorption", "bias": "both"})
    fills = [Fill(ts=1, price=100.0, qty=1.0, kind="entry"),
             Fill(ts=2, price=100.0 + pnl, qty=1.0, kind="target")]
    return ClosedTrade(plan=plan, qty=1.0, fills=fills, pnl=pnl, r_multiple=r,
                       opened_ts=1, closed_ts=2)


def test_journal_roundtrip(tmp_path):
    path = tmp_path / "j.jsonl"
    j = TradeJournal(path)
    j.record(_ct(4.0, 2.0))
    j.record(_ct(-2.0, -1.0))
    rows = TradeJournal.load(path)
    assert len(rows) == 2
    assert rows[0]["pnl"] == 4.0
    assert rows[0]["plan"]["meta"]["trigger"] == "absorption"
    assert rows[0]["fills"][0]["kind"] == "entry"


def test_metrics():
    rows = [
        {"pnl": 4.0, "r_multiple": 2.0},
        {"pnl": -2.0, "r_multiple": -1.0},
        {"pnl": 4.0, "r_multiple": 2.0},
    ]
    m = compute_metrics(rows)
    assert m["trades"] == 3
    assert m["win_rate"] == 2 / 3
    assert m["profit_factor"] == 8.0 / 2.0
    assert m["expectancy_r"] == 1.0
    assert m["total_pnl"] == 6.0
    assert m["max_drawdown"] == 2.0


def test_metrics_empty():
    assert compute_metrics([]) == {"trades": 0}
```

- [ ] **Step 2: Vérifier l'échec**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_journal_metrics.py -q
```

Attendu : FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implémenter**

`src/orderflow_bot/execution/journal.py` :

```python
import json
from dataclasses import asdict
from pathlib import Path

from orderflow_bot.models import ClosedTrade


class TradeJournal:
    """JSONL append-only : un trade ferme par ligne, avec tout son contexte
    (plan, meta zone/trigger/bias, fills detailles)."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, ct: ClosedTrade) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(ct)) + "\n")

    @staticmethod
    def load(path: str | Path) -> list[dict]:
        p = Path(path)
        if not p.exists():
            return []
        return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines()
                if line.strip()]
```

`src/orderflow_bot/backtest/metrics.py` :

```python
def compute_metrics(rows: list[dict]) -> dict:
    """Metriques de performance depuis les lignes du journal."""
    if not rows:
        return {"trades": 0}
    pnls = [r["pnl"] for r in rows]
    rs = [r["r_multiple"] for r in rows]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    eq = peak = dd = 0.0
    for p in pnls:
        eq += p
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return {
        "trades": len(rows),
        "win_rate": len(wins) / len(rows),
        "profit_factor": sum(wins) / abs(sum(losses)) if losses else float("inf"),
        "expectancy_r": sum(rs) / len(rs),
        "total_pnl": sum(pnls),
        "max_drawdown": dd,
    }
```

- [ ] **Step 4: Vérifier le passage**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_journal_metrics.py -q
```

Attendu : PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add orderflow-bot && rtk git commit -m "feat(orderflow): journal JSONL + metriques de performance"
```

---

### Task 17: Pipeline + moteur de backtest (intégration)

**Files:**
- Create: `src/orderflow_bot/pipeline.py`
- Modify: `src/orderflow_bot/__main__.py` (brancher `backtest`)
- Test: `tests/test_backtest.py`

- [ ] **Step 1: Test d'intégration qui échoue**

`tests/test_backtest.py` — scénario synthétique 2 jours : jour 1 construit un profil pyramidal (POC 100, VAL 97, VAH 103) ; jour 2 descend dans la zone VAL, absorption vendeuse, rotation vers le POC → exactement 1 trade gagnant via partiel + target :

```python
from orderflow_bot.config import (
    AbsorptionCfg, BotConfig, RiskCfg, SessionCfg, StrategyCfg,
)
from orderflow_bot.execution.journal import TradeJournal
from orderflow_bot.models import Trade
from orderflow_bot.pipeline import Pipeline, run_backtest

DAY_MS = 86_400_000
DAY1 = 20_000 * DAY_MS          # minuit UTC, jour epoch 20000


def _cfg(tmp_path) -> BotConfig:
    return BotConfig(
        tick_size=0.1, bin_size=1.0, bar_minutes=1, equity=10_000.0,
        journal_path=str(tmp_path / "journal.jsonl"),
        risk=RiskCfg(),
        strategy=StrategyCfg(
            zone_margin_pct=0.002, stop_buffer_ticks=10, profile_days=1,
            entry_expire_minutes=15,
            absorption=AbsorptionCfg(window_ms=30_000, vol_factor=3.0,
                                     max_range_ticks=15, min_delta_frac=0.3,
                                     baseline_windows=8),
        ),
        sessions=[SessionCfg(start="00:00", end="23:59")],
    )


def synth_trades() -> list[Trade]:
    out: list[Trade] = []
    # --- jour 1 : profil pyramidal 95..105, POC=100, VAL=97, VAH=103
    ts = DAY1
    for p in range(95, 106):
        for _ in range(10 - abs(p - 100)):
            out.append(Trade(ts=ts, price=float(p), qty=1.0,
                             is_buyer_maker=ts % 2 == 0))
            ts += 1_000
    # --- jour 2
    ts = DAY1 + DAY_MS
    # descente calme 100 -> 97.5 : baseline (~10 fenetres de 30 s, vol 0.5/fenetre)
    p = 100.0
    while p > 97.5:
        out.append(Trade(ts=ts, price=round(p, 1), qty=0.05, is_buyer_maker=True))
        ts += 3_000
        p -= 0.025
    # accalmie > window_ms : vide la fenetre glissante du detecteur, pour que
    # first/last de la fenetre choc soient les prix du choc lui-meme
    ts += 35_000
    # absorption dans la zone VAL (96.8..97.2) : 12 ventes 0.5, range 1 tick,
    # dernier prix >= premier
    for i in range(12):
        px = 97.0 if i % 2 == 0 else 97.1
        out.append(Trade(ts=ts, price=px, qty=0.5, is_buyer_maker=True))
        ts += 1_700
    # meche sous l'entry pour remplir l'ordre limit (franchissement strict)
    for _ in range(2):
        out.append(Trade(ts=ts, price=96.9, qty=0.3, is_buyer_maker=True))
        ts += 1_000
    # rotation vers le POC : 97.2 -> 100.6 (partiel ~1R puis target 100)
    p = 97.2
    while p <= 100.6:
        out.append(Trade(ts=ts, price=round(p, 1), qty=0.3, is_buyer_maker=False))
        ts += 2_000
        p += 0.2
    return out


def test_backtest_end_to_end(tmp_path):
    cfg = _cfg(tmp_path)
    report = run_backtest(cfg, synth_trades())
    assert report["trades"] == 1
    assert report["total_pnl"] > 50.0
    assert report["win_rate"] == 1.0
    rows = TradeJournal.load(cfg.journal_path)
    assert rows[0]["plan"]["meta"]["trigger"] == "absorption"
    assert rows[0]["plan"]["meta"]["zone"] == "val"
    kinds = [f["kind"] for f in rows[0]["fills"]]
    assert kinds[0] == "entry" and "partial" in kinds and kinds[-1] == "target"


def test_no_trading_during_warmup(tmp_path):
    cfg = _cfg(tmp_path)
    trades = [t for t in synth_trades() if t.ts < DAY1 + DAY_MS]   # jour 1 seul
    report = run_backtest(cfg, trades)
    assert report["trades"] == 0


def test_trading_disabled_flag(tmp_path):
    cfg = _cfg(tmp_path)
    pipe = Pipeline(cfg, TradeJournal(cfg.journal_path))
    pipe.trading_enabled = False
    for t in synth_trades():
        pipe.on_trade(t)
    assert TradeJournal.load(cfg.journal_path) == []
```

- [ ] **Step 2: Vérifier l'échec**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_backtest.py -q
```

Attendu : FAIL — `ModuleNotFoundError: No module named 'orderflow_bot.pipeline'`.

- [ ] **Step 3: Implémenter le pipeline**

`src/orderflow_bot/pipeline.py` :

```python
"""Coeur partage backtest/live : chaque Trade traverse, dans cet ordre,
broker (fills) -> rollover journalier -> profil du jour -> bougies/triggers ->
confluence -> risque -> soumission. Le risque est verifie AVANT la soumission."""

import logging
from collections.abc import Iterable
from pathlib import Path

from orderflow_bot.backtest.metrics import compute_metrics
from orderflow_bot.config import BotConfig
from orderflow_bot.execution.journal import TradeJournal
from orderflow_bot.execution.paper import PaperBroker
from orderflow_bot.features.absorption import AbsorptionDetector
from orderflow_bot.features.aggregator import BarAggregator
from orderflow_bot.features.cvd import CvdTracker
from orderflow_bot.features.volume_profile import VolumeProfile
from orderflow_bot.models import Cancelled, ClosedTrade, Trade
from orderflow_bot.risk.manager import RiskManager
from orderflow_bot.strategy.confluence import ConfluenceEngine, TriggerEngine
from orderflow_bot.strategy.context import (
    DailyLevels, levels_from_profile, market_bias, naked_pocs,
)
from orderflow_bot.strategy.zones import build_zones
from orderflow_bot.binning import price_of

log = logging.getLogger(__name__)

_DAY_MS = 86_400_000


class Pipeline:
    def __init__(self, cfg: BotConfig, journal: TradeJournal):
        self.cfg = cfg
        self.journal = journal
        self.trading_enabled = True
        st = cfg.strategy
        self.aggregator = BarAggregator(cfg.bar_minutes * 60_000, cfg.bin_size)
        self.triggers = TriggerEngine(
            absorption=AbsorptionDetector(st.absorption, cfg.tick_size),
            cvd=CvdTracker(),
            imb_cfg=st.imbalance,
        )
        self.confluence = ConfluenceEngine(
            min_rr=cfg.risk.min_rr,
            stop_buffer_ticks=st.stop_buffer_ticks,
            tick_size=cfg.tick_size,
        )
        self.risk = RiskManager(cfg.risk, cfg.sessions, cfg.equity)
        self.broker = PaperBroker(cfg.risk, st.entry_expire_minutes * 60_000)
        self._day = -1
        self._levels: list[DailyLevels] = []
        self._profiles: list[VolumeProfile] = []
        self._day_profile = VolumeProfile(cfg.bin_size)
        self._day_high = float("-inf")
        self._day_low = float("inf")

    def on_trade(self, t: Trade) -> None:
        self._maybe_rollover(t)
        self._handle(self.broker.on_trade(t), t.ts)
        self._day_profile.add(t.price, t.qty)
        self._day_high = max(self._day_high, t.price)
        self._day_low = min(self._day_low, t.price)
        trigs = []
        bar = self.aggregator.on_trade(t)
        if bar is not None:
            trigs += self.triggers.on_bar(bar)
        trigs += self.triggers.on_trade(t)
        for trig in trigs:
            if not self.trading_enabled or not self.risk.can_open(trig.ts):
                continue
            plan = self.confluence.evaluate(trig)
            if plan is None:
                continue
            qty = self.risk.size(plan)
            if qty is None:
                continue
            self.broker.submit(plan, qty, trig.ts)
            self.risk.on_open(trig.ts)
            log.info("ordre soumis: %s", plan)
            break   # une seule position

    def _maybe_rollover(self, t: Trade) -> None:
        day = t.ts // _DAY_MS
        if day == self._day:
            return
        if self._day >= 0 and self._day_profile.total > 0:
            self._handle(self.broker.force_close(t), t.ts)     # flat EOD
            bar = self.aggregator.flush()
            if bar is not None:
                self.triggers.on_bar(bar)
            self._finalize_day()
        self._day = day
        self._day_profile = VolumeProfile(self.cfg.bin_size)
        self._day_high = float("-inf")
        self._day_low = float("inf")
        self.triggers.cvd.reset()

    def _finalize_day(self) -> None:
        st = self.cfg.strategy
        self._levels.append(levels_from_profile(
            self._day, self._day_profile, self._day_high, self._day_low))
        self._levels = self._levels[-st.npoc_lookback_days:]
        self._profiles.append(self._day_profile)
        self._profiles = self._profiles[-st.profile_days:]
        composite = VolumeProfile(self.cfg.bin_size)
        for p in self._profiles:
            composite.merge(p)
        lvn_prices = [price_of(b, self.cfg.bin_size) for b in composite.lvns()]
        prev = self._levels[-1]
        zones = build_zones(prev, naked_pocs(self._levels), lvn_prices,
                            st.zone_margin_pct)
        self.confluence.update_day(zones, market_bias(self._levels))
        log.info("nouveau jour: bias=%s zones=%d", self.confluence.bias.value, len(zones))

    def _handle(self, ev: ClosedTrade | Cancelled | None, ts: int) -> None:
        if ev is None:
            return
        if isinstance(ev, Cancelled):
            self.risk.on_cancel()
            return
        self.risk.on_close(ts, ev.pnl)
        self.journal.record(ev)
        log.info("trade ferme: pnl=%.2f r=%.2f", ev.pnl, ev.r_multiple)


def run_backtest(cfg: BotConfig, trades: Iterable[Trade]) -> dict:
    # journal purge en debut de run : le rapport ne doit refleter que ce replay
    Path(cfg.journal_path).unlink(missing_ok=True)
    journal = TradeJournal(cfg.journal_path)
    pipe = Pipeline(cfg, journal)
    for t in trades:
        pipe.on_trade(t)
    return compute_metrics(TradeJournal.load(cfg.journal_path))
```

- [ ] **Step 4: Brancher le CLI backtest**

Dans `src/orderflow_bot/__main__.py`, remplacer la branche `backtest` :

```python
    elif args.command == "backtest":
        import json as _json
        from datetime import datetime, timezone

        from orderflow_bot.ingestion.reader import read_trades
        from orderflow_bot.pipeline import run_backtest

        def _ms(d: str | None) -> int | None:
            if d is None:
                return None
            dt = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)

        trades = read_trades(cfg.data_dir, cfg.symbol,
                             start_ms=_ms(args.start), end_ms=_ms(args.end))
        report = run_backtest(cfg, trades)
        print(_json.dumps(report, indent=2))
```

- [ ] **Step 5: Vérifier le passage (suite complète)**

```powershell
rtk test .venv\Scripts\python -m pytest -q
```

Attendu : PASS — tous les tests, y compris `test_backtest_end_to_end`.

- [ ] **Step 6: Commit**

```bash
rtk git add orderflow-bot && rtk git commit -m "feat(orderflow): pipeline partage + moteur de backtest par replay"
```

---

### Task 18: Paper trading live + bootstrap historique

**Files:**
- Modify: `src/orderflow_bot/live.py` (ajouter `run_paper`)
- Modify: `src/orderflow_bot/__main__.py` (brancher `paper`)
- Test: `tests/test_live_bootstrap.py`

- [ ] **Step 1: Test qui échoue (bootstrap)**

`tests/test_live_bootstrap.py` :

```python
from orderflow_bot.config import BotConfig, SessionCfg, StrategyCfg
from orderflow_bot.execution.journal import TradeJournal
from orderflow_bot.ingestion.recorder import TradeRecorder
from orderflow_bot.live import bootstrap_pipeline
from orderflow_bot.models import Trade
from orderflow_bot.pipeline import Pipeline

DAY_MS = 86_400_000
DAY1 = 20_000 * DAY_MS


def test_bootstrap_replays_history_without_trading(tmp_path):
    cfg = BotConfig(
        data_dir=str(tmp_path / "data"),
        journal_path=str(tmp_path / "journal.jsonl"),
        strategy=StrategyCfg(profile_days=1),
        sessions=[SessionCfg(start="00:00", end="23:59")],
    )
    rec = TradeRecorder(cfg.data_dir, cfg.symbol)
    ts = DAY1
    for p in range(95, 106):
        for _ in range(10 - abs(p - 100)):
            rec.append(Trade(ts=ts, price=float(p), qty=1.0, is_buyer_maker=False))
            ts += 1_000
    # premier trade du jour 2 : declenche le rollover -> zones construites
    rec.append(Trade(ts=DAY1 + DAY_MS, price=100.0, qty=0.1, is_buyer_maker=False))
    rec.flush()

    pipe = Pipeline(cfg, TradeJournal(cfg.journal_path))
    n = bootstrap_pipeline(pipe, cfg)
    assert n > 0
    assert pipe.trading_enabled is True            # reactive apres replay
    assert len(pipe.confluence.zones) >= 2         # VAL + VAH au minimum
    assert TradeJournal.load(cfg.journal_path) == []   # aucun trade fictif
```

- [ ] **Step 2: Vérifier l'échec**

```powershell
rtk test .venv\Scripts\python -m pytest tests\test_live_bootstrap.py -q
```

Attendu : FAIL — `ImportError: cannot import name 'bootstrap_pipeline'`.

- [ ] **Step 3: Implémenter**

Remplacer `src/orderflow_bot/live.py` par :

```python
import asyncio
import logging

from orderflow_bot.config import BotConfig
from orderflow_bot.execution.journal import TradeJournal
from orderflow_bot.ingestion.binance_ws import stream_trades
from orderflow_bot.ingestion.reader import read_trades
from orderflow_bot.ingestion.recorder import TradeRecorder
from orderflow_bot.pipeline import Pipeline

log = logging.getLogger(__name__)


async def run_record(cfg: BotConfig) -> None:
    """Enregistre le flux tick en Parquet. Ctrl+C -> flush propre."""
    rec = TradeRecorder(cfg.data_dir, cfg.symbol)
    try:
        await stream_trades(cfg.symbol, rec.append)
    finally:
        rec.flush()
        log.info("flush final ok")


def bootstrap_pipeline(pipe: Pipeline, cfg: BotConfig) -> int:
    """Rejoue l'historique Parquet local AVANT le live pour amorcer niveaux,
    zones et biais — trading desactive pendant le replay. Retourne le nombre
    de trades rejoues."""
    pipe.trading_enabled = False
    n = 0
    for t in read_trades(cfg.data_dir, cfg.symbol):
        pipe.on_trade(t)
        n += 1
    pipe.trading_enabled = True
    log.info("bootstrap: %d trades rejoues, %d zones", n, len(pipe.confluence.zones))
    return n


async def run_paper(cfg: BotConfig) -> None:
    """Paper trading live : bootstrap historique puis stream temps reel.
    Enregistre aussi les ticks recus (les donnees s'accumulent en continu)."""
    journal = TradeJournal(cfg.journal_path)
    pipe = Pipeline(cfg, journal)
    bootstrap_pipeline(pipe, cfg)
    rec = TradeRecorder(cfg.data_dir, cfg.symbol)

    def handle(t) -> None:
        rec.append(t)
        pipe.on_trade(t)

    try:
        await stream_trades(cfg.symbol, handle)
    finally:
        rec.flush()
```

Dans `src/orderflow_bot/__main__.py`, remplacer la branche `paper` :

```python
    else:
        from orderflow_bot.live import run_paper
        asyncio.run(run_paper(cfg))
```

(et la branche `record` reste : `from orderflow_bot.live import run_record` / `asyncio.run(run_record(cfg))`.)

- [ ] **Step 4: Vérifier le passage (suite complète)**

```powershell
rtk test .venv\Scripts\python -m pytest -q
```

Attendu : PASS — suite complète.

- [ ] **Step 5: Smoke test manuel (réseau requis)**

```powershell
.venv\Scripts\python -m orderflow_bot paper
```

Attendu dans les logs : `bootstrap: N trades rejoues` puis `connecte a wss://fstream.binance.com/...`. Laisser ~1 min, Ctrl+C. Hors session (13:00–17:00 UTC) aucun trade ne s'ouvre — comportement voulu.

- [ ] **Step 6: Commit final**

```bash
rtk git add orderflow-bot && rtk git commit -m "feat(orderflow): paper trading live avec bootstrap historique"
```

---

## Validation finale (hors plan, après quelques jours de collecte)

1. `record` tourne ≥ `profile_days + 3` jours (idéalement 2–4 semaines).
2. `backtest --start ... --end ...` → examiner `journal.jsonl` trade par trade : chaque entrée doit être explicable (zone + trigger + bias cohérents).
3. Critères avant d'envisager quoi que ce soit en réel : expectancy_r > 0 sur ≥ 30 trades, max_drawdown < stop journalier cumulé plausible, 1–3 trades/jour observés (sinon les seuils filtrent mal).
4. Paper live ≥ 2 semaines en parallèle du backtest continu.
5. Extensions naturelles ensuite : depth L2 (iceberg/spoof), volume bars, exécution testnet Binance.

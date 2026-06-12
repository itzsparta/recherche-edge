"""Import des archives historiques data.binance.vision (gratuites).

Deux formats CSV cohabitent (verifies sur les archives reelles) :
- spot : 8 colonnes, pas de header, transact_time en MICROsecondes, True/False
- futures um : 7 colonnes, header, transact_time en millisecondes, true/false
La conversion normalise tout vers le schema Parquet du TradeRecorder
(ts ms, price, qty, is_buyer_maker)."""

import io
import logging
import tempfile
import zipfile
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import duckdb
import pyarrow.parquet as pq

from orderflow_bot.config import BotConfig

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
        ).fetch_arrow_table()
    finally:
        con.close()
    pq.write_table(table, out_parquet)
    return table.num_rows


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

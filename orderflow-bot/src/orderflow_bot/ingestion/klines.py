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
        ).to_arrow_table()
    finally:
        con.close()
    pq.write_table(table, out_parquet)
    return table.num_rows

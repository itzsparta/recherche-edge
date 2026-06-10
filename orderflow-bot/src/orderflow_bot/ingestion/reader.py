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

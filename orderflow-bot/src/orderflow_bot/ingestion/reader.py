import logging
from collections.abc import Iterator
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

from orderflow_bot.models import Trade

log = logging.getLogger(__name__)

_BATCH = 50_000


def _ts_bounds(md: pq.FileMetaData) -> tuple[int, int] | None:
    """(min_ts, max_ts) du fichier via les stats du footer Parquet, sans
    scanner les donnees. None si les stats manquent."""
    lo: int | None = None
    hi: int | None = None
    for i in range(md.num_row_groups):
        rg = md.row_group(i)
        for j in range(rg.num_columns):
            col = rg.column(j)
            if col.path_in_schema != "ts":
                continue
            st = col.statistics
            if st is None or not st.has_min_max:
                return None
            lo = st.min if lo is None else min(lo, st.min)
            hi = st.max if hi is None else max(hi, st.max)
    return None if lo is None or hi is None else (lo, hi)


def _stream(cur) -> Iterator[Trade]:
    while batch := cur.fetchmany(_BATCH):
        for ts, price, qty, mkr in batch:
            yield Trade(ts=ts, price=price, qty=qty, is_buyer_maker=mkr)


def read_trades(
    data_dir: str | Path,
    symbol: str,
    start_ms: int | None = None,
    end_ms: int | None = None,
) -> Iterator[Trade]:
    """Relit les Parquet du symbole en streaming, ordonnes par ts.

    Chemin rapide : les fichiers sont ordonnes par leurs bornes de ts (stats
    du footer Parquet, lues sans scan), ceux entierement hors fenetre sont
    sautes, puis chacun est lu et trie individuellement -- pas de tri global
    du dataset. Ce chemin n'est valide que si les fichiers ne se chevauchent
    pas dans le temps ; en cas de chevauchement ou de stats absentes, repli
    sur le tri global DuckDB, plus lent mais toujours correct."""
    folder = Path(data_dir) / symbol
    files = sorted(folder.glob("*.parquet")) if folder.exists() else []
    if not files:
        return
    plan: list[tuple[int, int, Path]] | None = []
    for f in files:
        md = pq.read_metadata(f)
        if md.num_rows == 0:
            continue
        bounds = _ts_bounds(md)
        if bounds is None:
            plan = None
            break
        lo, hi = bounds
        if (start_ms is not None and hi < start_ms) or \
                (end_ms is not None and lo >= end_ms):
            continue                    # fichier entierement hors fenetre
        plan.append((lo, hi, f))
    if plan is not None:
        plan.sort(key=lambda p: p[:2])
        if any(prev[1] > nxt[0] for prev, nxt in zip(plan, plan[1:])):
            plan = None                 # chevauchement -> ordre par fichier invalide

    conds: list[str] = []
    params: list = []
    if start_ms is not None:
        conds.append("ts >= ?")
        params.append(start_ms)
    if end_ms is not None:
        conds.append("ts < ?")
        params.append(end_ms)
    where = (" WHERE " + " AND ".join(conds)) if conds else ""
    q = f"SELECT ts, price, qty, is_buyer_maker FROM read_parquet(?){where} ORDER BY ts"

    con = duckdb.connect()
    try:
        if plan is None:
            log.warning("stats absentes ou fichiers chevauchants : tri global")
            yield from _stream(con.execute(q, [[str(f) for f in files], *params]))
        else:
            for i, (_, _, f) in enumerate(plan, 1):
                log.info("lecture %d/%d: %s", i, len(plan), f.name)
                yield from _stream(con.execute(q, [str(f), *params]))
    finally:
        con.close()


def available_days(data_dir: str | Path, symbol: str) -> list[int]:
    """Jours (epoch ms // 86_400_000) presents dans les Parquet, tries."""
    folder = Path(data_dir) / symbol
    if not folder.exists() or not any(folder.glob("*.parquet")):
        return []
    con = duckdb.connect()
    try:
        rows = con.execute(
            "SELECT DISTINCT ts // 86400000 AS d FROM read_parquet(?) ORDER BY d",
            [str(folder / "*.parquet")],
        ).fetchall()
    finally:
        con.close()
    return [int(r[0]) for r in rows]

import logging
from collections.abc import Iterator
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

from orderflow_bot.config import BotConfig
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


def read_market(
    cfg: BotConfig, start_ms: int | None = None, end_ms: int | None = None
) -> Iterator[Trade]:
    """Dispatch unique trades|klines selon cfg.data_format. Point d'entree du
    chemin swing (parallele et sequentiel) ; les outils trades intraday gardent
    read_trades en direct."""
    if cfg.data_format == "klines":
        return read_klines_as_ticks(cfg.kline_data_dir, cfg.symbol, start_ms, end_ms)
    return read_trades(cfg.market_data_dir, cfg.symbol, start_ms, end_ms)


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

"""Features DOM/L2 a partir des snapshots book_snapshot_25 (Tardis).

Phase 0 : tester si le book separe les fades morts-nes (mfe_r<0.5) mieux que le
tape. Loader des CSV gzip Tardis (timestamp en MICROSECONDES -> ms). Les 4
features fusionnent book (affiche) + tape (consomme), sans lookahead (fenetres
finissant au fill).

book_snapshot_25 : 104 col = exchange,symbol,timestamp,local_timestamp puis pour
chaque niveau i in 0..24 : asks[i].price, asks[i].amount, bids[i].price, bids[i].amount.
"""
from __future__ import annotations

from dataclasses import dataclass
from os import PathLike

import duckdb
import numpy as np

LEVELS = 25


@dataclass(slots=True)
class BookDay:
    ts: np.ndarray        # int64 ms, croissant
    ask_px: np.ndarray    # (N, 25) float64
    ask_amt: np.ndarray
    bid_px: np.ndarray
    bid_amt: np.ndarray
    total: np.ndarray     # (N,) somme amount des 2 cotes, pre-calc

    def idx_at(self, t: int) -> int:
        """Index du dernier snapshot avec ts <= t, ou -1 si aucun."""
        return int(np.searchsorted(self.ts, t, side="right")) - 1

    def window_idx(self, t0: int, t1: int) -> tuple[int, int]:
        """[lo, hi) des snapshots avec t0 <= ts <= t1."""
        lo = int(np.searchsorted(self.ts, t0, side="left"))
        hi = int(np.searchsorted(self.ts, t1, side="right"))
        return lo, hi

    def trailing_median_total(self, t: int, window_ms: int) -> float:
        lo, hi = self.window_idx(t - window_ms, t)
        if hi <= lo:
            return float("nan")
        return float(np.median(self.total[lo:hi]))


def load_book_day(path: str | PathLike[str]) -> BookDay:
    """Charge un CSV.gz book_snapshot_25 -> BookDay (timestamp us -> ms)."""
    sql_path = str(path).replace("'", "''")               # echappe ' pour le SQL
    con = duckdb.connect()
    try:
        d = con.execute(
            f"SELECT * FROM read_csv_auto('{sql_path}', header=true)"
        ).fetchnumpy()
    finally:
        con.close()

    def _filled(name: str) -> np.ndarray:
        a = d[name]
        a = np.ma.filled(a, np.nan) if np.ma.isMaskedArray(a) else np.asarray(a)
        return a.astype("float64")

    def col_amt(name: str) -> np.ndarray:
        # niveau absent -> 0.0 (pas de volume affiche)
        return np.nan_to_num(_filled(name), nan=0.0)

    def col_px(name: str) -> np.ndarray:
        # niveau absent -> NaN preserve (un prix manquant n'est pas un prix de 0)
        return _filled(name)

    ts = np.asarray(d["timestamp"], dtype="int64") // 1000        # us -> ms
    ask_px = np.column_stack([col_px(f"asks[{i}].price") for i in range(LEVELS)])
    ask_amt = np.column_stack([col_amt(f"asks[{i}].amount") for i in range(LEVELS)])
    bid_px = np.column_stack([col_px(f"bids[{i}].price") for i in range(LEVELS)])
    bid_amt = np.column_stack([col_amt(f"bids[{i}].amount") for i in range(LEVELS)])
    total = ask_amt.sum(1) + bid_amt.sum(1)
    order = np.argsort(ts, kind="stable")
    return BookDay(ts[order], ask_px[order], ask_amt[order],
                   bid_px[order], bid_amt[order], total[order])

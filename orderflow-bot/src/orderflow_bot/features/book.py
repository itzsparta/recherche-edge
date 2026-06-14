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


def load_book_day(path: str) -> BookDay:
    """Charge un CSV.gz book_snapshot_25 -> BookDay (timestamp us -> ms)."""
    con = duckdb.connect()
    try:
        d = con.execute(
            f"SELECT * FROM read_csv_auto('{path}', header=true)"
        ).fetchnumpy()
    finally:
        con.close()

    def col(name: str) -> np.ndarray:
        a = d[name]
        a = np.ma.filled(a, np.nan) if np.ma.isMaskedArray(a) else np.asarray(a)
        return np.nan_to_num(a.astype("float64"), nan=0.0)

    ts = np.asarray(d["timestamp"], dtype="int64") // 1000        # us -> ms
    ask_px = np.column_stack([col(f"asks[{i}].price") for i in range(LEVELS)])
    ask_amt = np.column_stack([col(f"asks[{i}].amount") for i in range(LEVELS)])
    bid_px = np.column_stack([col(f"bids[{i}].price") for i in range(LEVELS)])
    bid_amt = np.column_stack([col(f"bids[{i}].amount") for i in range(LEVELS)])
    total = ask_amt.sum(1) + bid_amt.sum(1)
    order = np.argsort(ts, kind="stable")
    return BookDay(ts[order], ask_px[order], ask_amt[order],
                   bid_px[order], bid_amt[order], total[order])

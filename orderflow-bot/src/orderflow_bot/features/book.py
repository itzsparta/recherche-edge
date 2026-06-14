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


def _defend_oppose(book: BookDay, i: int, side: int):
    """Retourne (defend_px, defend_amt, oppose_px, oppose_amt) au snapshot i.
    Fade long (+1) -> defenseurs = bids ; fade short (-1) -> defenseurs = asks."""
    if side > 0:
        return book.bid_px[i], book.bid_amt[i], book.ask_px[i], book.ask_amt[i]
    return book.ask_px[i], book.ask_amt[i], book.bid_px[i], book.bid_amt[i]


def _band_sum(px: np.ndarray, amt: np.ndarray, entry: float, band: float) -> float:
    return float(amt[np.abs(px - entry) <= band].sum())


def book_defense(book: BookDay, i: int, entry: float, side: int,
                 band: float, norm_total: float) -> float:
    """Liq defensive dans la bande / mediane trailing du book total. Haut -> tient."""
    if not (norm_total > 0):
        return float("nan")
    dpx, damt, _, _ = _defend_oppose(book, i, side)
    return _band_sum(dpx, damt, entry, band) / norm_total


def touch_imbalance(book: BookDay, i: int, entry: float, side: int,
                    band: float) -> float:
    """(defend - oppose)/(defend + oppose) dans la bande, in [-1, 1]. Haut -> tient."""
    dpx, damt, opx, oamt = _defend_oppose(book, i, side)
    d = _band_sum(dpx, damt, entry, band)
    o = _band_sum(opx, oamt, entry, band)
    tot = d + o
    return (d - o) / tot if tot > 0 else float("nan")


def tape_vol_in_band(tape_ts: np.ndarray, tape_px: np.ndarray, tape_qty: np.ndarray,
                     t0: int, t1: int, entry: float, band: float) -> float:
    """Volume tape avec t0 <= ts <= t1 et |price - entry| <= band."""
    if tape_ts.size == 0:
        return 0.0
    m = (tape_ts >= t0) & (tape_ts <= t1) & (np.abs(tape_px - entry) <= band)
    return float(tape_qty[m].sum())


def replenish(book: BookDay, tape_ts, tape_px, tape_qty, entry: float, side: int,
              opened_ts: int, W: int, band: float) -> float:
    """Volume tape consomme dans la bande sur W / liq defensive affichee au debut
    de W. >1 = plus mange qu'affiche = recharge cachee (iceberg). Haut -> tient."""
    i0 = book.idx_at(opened_ts - W)
    if i0 < 0:
        return float("nan")
    dpx, damt, _, _ = _defend_oppose(book, i0, side)
    displayed = _band_sum(dpx, damt, entry, band)
    if displayed <= 0:
        return float("nan")
    traded = tape_vol_in_band(tape_ts, tape_px, tape_qty,
                              opened_ts - W, opened_ts, entry, band)
    return traded / displayed


def pull_rate(book: BookDay, tape_ts, tape_px, tape_qty, entry: float, side: int,
              opened_ts: int, W: int, band: float) -> float:
    """Baisses de liq defensive affichee NON expliquees par le tape (annulations)
    sur W / liq affichee au debut. Haut -> spoof retire -> meurt."""
    lo, hi = book.window_idx(opened_ts - W, opened_ts)
    if hi - lo < 2:
        return float("nan")

    def defend_band(j: int) -> float:
        dpx, damt, _, _ = _defend_oppose(book, j, side)
        return _band_sum(dpx, damt, entry, band)

    start = defend_band(lo)
    if start <= 0:
        return float("nan")
    pull = 0.0
    prev = start
    for j in range(lo + 1, hi):
        cur = defend_band(j)
        drop = prev - cur
        if drop > 0:
            traded = tape_vol_in_band(tape_ts, tape_px, tape_qty,
                                      int(book.ts[j - 1]), int(book.ts[j]),
                                      entry, band)
            pull += max(0.0, drop - traded)
        prev = cur
    return pull / start

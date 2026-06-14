# DOM/L2 Features (Phase 0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mesurer si le book (L2) sépare les fades morts-nés (`mfe_r<0.5`) mieux que le tape, sur les 7 jours `book_snapshot_25` gratuits, avec un greenlight pré-enregistré.

**Architecture:** Loader numpy des snapshots Tardis + 4 features book/tape pures (`features/book.py`), stats de séparation pures (`backtest/separation.py`), orchestration qui génère+labelle les candidats (réutilise `generate_plans`/`simulate_isolated`), joint le book au fill, et sort un rapport HTML + verdict (`scripts/dom_separation.py`). Tout sans lookahead (fenêtres finissant au fill).

**Tech Stack:** Python 3.11, numpy, duckdb (lecture CSV.gz), plotly (viz), pytest. Venv : `.venv\Scripts\python`.

**Spec :** `docs/superpowers/specs/2026-06-14-dom-features-design.md`

---

## File Structure

| Fichier | Responsabilité |
|---|---|
| `src/orderflow_bot/features/book.py` | **Create** — `BookDay` (arrays + bisect), `load_book_day`, 4 features (`book_defense`, `touch_imbalance`, `replenish`, `pull_rate`), helpers privés. Pur, pas d'I/O réseau. |
| `src/orderflow_bot/backtest/separation.py` | **Create** — `auc` (tie-aware), `quartile_lift`, `evaluate_greenlight`. Pur, sans I/O. |
| `scripts/dom_separation.py` | **Create** — orchestration : `collect` (gen+label+join), agrégation, viz Plotly, verdict. |
| `tests/test_book.py` | **Create** — unit tests loader + 4 features (BookDay construit en direct). |
| `tests/test_separation.py` | **Create** — unit tests auc/lift/greenlight. |

Convention projet : tests dans `tests/test_*.py`, features pures dans `src/orderflow_bot/features/`, exécutées via `.venv\Scripts\python -m pytest`.

---

## Task 1 : Loader book + BookDay (bisect)

**Files:**
- Create: `src/orderflow_bot/features/book.py`
- Test: `tests/test_book.py`

- [ ] **Step 1 : Écrire le test du loader + bisect**

```python
# tests/test_book.py
import gzip
import numpy as np
from orderflow_bot.features import book as bk


def _write_book_csv(path, rows):
    """rows = list de (ts_us, [(ask_px, ask_amt), ...], [(bid_px, bid_amt), ...]).
    Pad a 25 niveaux avec des cellules vides (NaN cote Tardis)."""
    cols = ["exchange", "symbol", "timestamp", "local_timestamp"]
    for i in range(25):
        cols += [f"asks[{i}].price", f"asks[{i}].amount",
                 f"bids[{i}].price", f"bids[{i}].amount"]
    lines = [",".join(cols)]
    for ts, asks, bids in rows:
        cells = ["binance", "BTCUSDT", str(ts), str(ts)]
        for i in range(25):
            ap, aa = asks[i] if i < len(asks) else ("", "")
            bp, ba = bids[i] if i < len(bids) else ("", "")
            cells += [str(ap), str(aa), str(bp), str(ba)]
        lines.append(",".join(cells))
    with gzip.open(path, "wt") as f:
        f.write("\n".join(lines) + "\n")


def test_load_book_day_converts_us_to_ms_and_sorts(tmp_path):
    p = tmp_path / "book.csv.gz"
    # ts en microsecondes ; volontairement non trie pour verifier le tri
    _write_book_csv(p, [
        (2_000_000, [(101.0, 1.5)], [(100.0, 2.0)]),
        (1_000_000, [(101.0, 0.5)], [(100.0, 1.0)]),
    ])
    book = bk.load_book_day(str(p))
    assert list(book.ts) == [1000, 2000]            # us -> ms, trie
    assert book.bid_amt[0, 0] == 1.0                 # snapshot ts=1000
    assert book.ask_amt[1, 0] == 1.5                 # snapshot ts=2000
    # niveaux absents -> amount 0
    assert book.ask_amt[0, 1] == 0.0
    # total = somme des 2 cotes
    assert book.total[0] == 0.5 + 1.0


def test_idx_at_and_window():
    ts = np.array([100, 200, 300], dtype="int64")
    z = np.zeros((3, 25))
    book = bk.BookDay(ts, z.copy(), z.copy(), z.copy(), z.copy(), np.zeros(3))
    assert book.idx_at(50) == -1                      # avant le 1er
    assert book.idx_at(200) == 1                       # pile
    assert book.idx_at(250) == 1                       # entre deux -> dernier <=
    assert book.window_idx(150, 300) == (1, 3)
```

- [ ] **Step 2 : Lancer le test, vérifier l'échec**

Run: `.venv\Scripts\python -m pytest tests/test_book.py -v`
Expected: FAIL — `ModuleNotFoundError` / `AttributeError: module ... has no attribute 'load_book_day'`.

- [ ] **Step 3 : Implémenter le loader + BookDay**

```python
# src/orderflow_bot/features/book.py
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
        ).fetch_numpy()
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
```

- [ ] **Step 4 : Lancer le test, vérifier le succès**

Run: `.venv\Scripts\python -m pytest tests/test_book.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5 : Commit**

```bash
git add src/orderflow_bot/features/book.py tests/test_book.py
git commit -m "feat(orderflow): loader book_snapshot_25 (BookDay + bisect)"
```

---

## Task 2 : Features statiques (book_defense, touch_imbalance)

**Files:**
- Modify: `src/orderflow_bot/features/book.py`
- Test: `tests/test_book.py`

- [ ] **Step 1 : Écrire les tests des features statiques**

```python
# tests/test_book.py  (ajouter)
def _one_level_book(ts, ask, bid):
    """ask/bid = (price, amount) au niveau 0 ; reste 0. ts = liste ms."""
    n = len(ts)
    ax = np.zeros((n, 25)); aa = np.zeros((n, 25))
    bx = np.zeros((n, 25)); ba = np.zeros((n, 25))
    for k in range(n):
        ax[k, 0], aa[k, 0] = ask[k]
        bx[k, 0], ba[k, 0] = bid[k]
    total = aa.sum(1) + ba.sum(1)
    return bk.BookDay(np.array(ts, dtype="int64"), ax, aa, bx, ba, total)


def test_book_defense_normalised():
    # long -> defenseurs = bids ; entry=100, band large
    book = _one_level_book([0], ask=[(101.0, 1.0)], bid=[(100.0, 4.0)])
    # defense brute = 4.0 ; normalisee par norm_total=2.0 -> 2.0
    assert bk.book_defense(book, 0, entry=100.0, side=1, band=5.0, norm_total=2.0) == 2.0
    # norm_total invalide -> NaN
    assert np.isnan(bk.book_defense(book, 0, 100.0, 1, 5.0, 0.0))


def test_touch_imbalance_sign():
    book = _one_level_book([0], ask=[(101.0, 1.0)], bid=[(100.0, 4.0)])
    # long : defend(bids)=4, oppose(asks)=1 -> (4-1)/5 = 0.6
    assert bk.touch_imbalance(book, 0, entry=100.5, side=1, band=5.0) == 0.6
    # short : defend(asks)=1, oppose(bids)=4 -> (1-4)/5 = -0.6
    assert bk.touch_imbalance(book, 0, entry=100.5, side=-1, band=5.0) == -0.6
    # bande trop etroite -> rien -> NaN
    assert np.isnan(bk.touch_imbalance(book, 0, entry=200.0, side=1, band=0.5))
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run: `.venv\Scripts\python -m pytest tests/test_book.py::test_book_defense_normalised tests/test_book.py::test_touch_imbalance_sign -v`
Expected: FAIL — `AttributeError: ... has no attribute 'book_defense'`.

- [ ] **Step 3 : Implémenter les helpers + features statiques**

```python
# src/orderflow_bot/features/book.py  (ajouter en bas)
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
```

- [ ] **Step 4 : Lancer, vérifier le succès**

Run: `.venv\Scripts\python -m pytest tests/test_book.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5 : Commit**

```bash
git add src/orderflow_bot/features/book.py tests/test_book.py
git commit -m "feat(orderflow): features book statiques (defense + touch imbalance)"
```

---

## Task 3 : Features dynamiques (replenish, pull_rate)

**Files:**
- Modify: `src/orderflow_bot/features/book.py`
- Test: `tests/test_book.py`

- [ ] **Step 1 : Écrire les tests des features dynamiques**

```python
# tests/test_book.py  (ajouter)
def test_replenish_ratio():
    # snapshot a t=0 : bid niveau0 = (100, 2.0). fill a opened_ts=2000, W=2000.
    book = _one_level_book([0, 1000, 2000], ask=[(101.0, 1.0)] * 3,
                           bid=[(100.0, 2.0)] * 3)
    # tape : 5.0 de volume traverse dans la bande sur [0, 2000]
    t_ts = np.array([500, 1500], dtype="int64")
    t_px = np.array([100.0, 100.0])
    t_qty = np.array([3.0, 2.0])
    # affiche au debut W = 2.0 ; mange = 5.0 -> 2.5 (recharge cachee)
    r = bk.replenish(book, t_ts, t_px, t_qty, entry=100.0, side=1,
                     opened_ts=2000, W=2000, band=5.0)
    assert abs(r - 2.5) < 1e-9
    # pas de tape -> 0
    r0 = bk.replenish(book, np.array([], "int64"), np.array([]), np.array([]),
                      100.0, 1, 2000, 2000, 5.0)
    assert r0 == 0.0


def test_pull_rate_cancel_vs_consumed():
    # bid niveau0 : 4.0 -> 1.0 entre deux snapshots (chute de 3.0)
    book = _one_level_book([0, 1000, 2000],
                           ask=[(101.0, 1.0)] * 3,
                           bid=[(100.0, 4.0), (100.0, 1.0), (100.0, 1.0)])
    # CAS spoof : aucun trade -> toute la chute = annulation. pull = 3.0/4.0 = 0.75
    pull = bk.pull_rate(book, np.array([], "int64"), np.array([]), np.array([]),
                        entry=100.0, side=1, opened_ts=2000, W=2000, band=5.0)
    assert abs(pull - 0.75) < 1e-9
    # CAS consomme : 3.0 de tape entre snapshot 0 et 1 -> chute expliquee -> pull = 0
    t_ts = np.array([500], dtype="int64"); t_px = np.array([100.0]); t_qty = np.array([3.0])
    pull0 = bk.pull_rate(book, t_ts, t_px, t_qty, 100.0, 1, 2000, 2000, 5.0)
    assert pull0 == 0.0
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run: `.venv\Scripts\python -m pytest tests/test_book.py::test_replenish_ratio tests/test_book.py::test_pull_rate_cancel_vs_consumed -v`
Expected: FAIL — `AttributeError: ... has no attribute 'replenish'`.

- [ ] **Step 3 : Implémenter le helper tape + features dynamiques**

```python
# src/orderflow_bot/features/book.py  (ajouter en bas)
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
```

- [ ] **Step 4 : Lancer, vérifier le succès**

Run: `.venv\Scripts\python -m pytest tests/test_book.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5 : Commit**

```bash
git add src/orderflow_bot/features/book.py tests/test_book.py
git commit -m "feat(orderflow): features book dynamiques (replenish iceberg + pull spoof)"
```

---

## Task 4 : Stats de séparation (auc + quartile_lift)

**Files:**
- Create: `src/orderflow_bot/backtest/separation.py`
- Test: `tests/test_separation.py`

- [ ] **Step 1 : Écrire les tests auc/lift**

```python
# tests/test_separation.py
import math
from orderflow_bot.backtest.separation import auc, quartile_lift


def test_auc_perfect_and_random():
    # positifs (True) ont les scores les plus hauts -> AUC = 1.0
    scores = [0.1, 0.2, 0.8, 0.9]
    labels = [False, False, True, True]
    assert auc(scores, labels) == 1.0
    # inverse -> 0.0
    assert auc([0.9, 0.8, 0.2, 0.1], labels) == 0.0
    # une seule classe -> NaN
    assert math.isnan(auc([1.0, 2.0], [True, True]))


def test_auc_ties_half():
    # tous egaux -> AUC = 0.5 (rangs moyens)
    assert auc([1.0, 1.0, 1.0, 1.0], [True, False, True, False]) == 0.5


def test_auc_drops_nan():
    # NaN exclus, le reste est un separateur parfait
    scores = [float("nan"), 0.1, 0.9]
    labels = [True, False, True]
    assert auc(scores, labels) == 1.0


def test_quartile_lift_monotone():
    # score = label parfait -> lift croissant 0,0,1,1 sur 4 quartiles
    scores = [0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9]
    labels = [False, False, False, False, True, True, True, True]
    assert quartile_lift(scores, labels, q=4) == [0.0, 0.0, 1.0, 1.0]
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run: `.venv\Scripts\python -m pytest tests/test_separation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'orderflow_bot.backtest.separation'`.

- [ ] **Step 3 : Implémenter auc + quartile_lift**

```python
# src/orderflow_bot/backtest/separation.py
"""Stats de separation (Phase 0 DOM) : AUC tie-aware + lift par quantile +
verdict greenlight pre-enregistre. Pur, sans I/O. Classe positive = mort-ne."""
from __future__ import annotations

import math


def auc(scores: list[float], labels: list[bool]) -> float:
    """AUC pour predire label=True a partir du score (haut score -> positif),
    via Mann-Whitney (rangs moyens sur les ex aequo). NaN exclus. NaN si une
    seule classe presente."""
    pairs = [(s, l) for s, l in zip(scores, labels) if not math.isnan(s)]
    n_pos = sum(1 for _, l in pairs if l)
    n_neg = len(pairs) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = sorted(range(len(pairs)), key=lambda k: pairs[k][0])
    ranks = [0.0] * len(pairs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and pairs[order[j + 1]][0] == pairs[order[i]][0]:
            j += 1
        avg = (i + j) / 2.0 + 1.0                 # rangs 1-based, moyenne sur ties
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    sum_pos = sum(ranks[k] for k in range(len(pairs)) if pairs[k][1])
    u = sum_pos - n_pos * (n_pos + 1) / 2.0
    return u / (n_pos * n_neg)


def quartile_lift(scores: list[float], labels: list[bool], q: int = 4) -> list[float]:
    """Taux de positifs par quantile croissant du score. NaN exclus."""
    pairs = sorted(((s, l) for s, l in zip(scores, labels) if not math.isnan(s)),
                   key=lambda x: x[0])
    n = len(pairs)
    if n == 0:
        return [float("nan")] * q
    out = []
    for b in range(q):
        chunk = pairs[b * n // q:(b + 1) * n // q]
        out.append(sum(1 for _, l in chunk if l) / len(chunk)
                   if chunk else float("nan"))
    return out
```

- [ ] **Step 4 : Lancer, vérifier le succès**

Run: `.venv\Scripts\python -m pytest tests/test_separation.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5 : Commit**

```bash
git add src/orderflow_bot/backtest/separation.py tests/test_separation.py
git commit -m "feat(orderflow): stats separation AUC tie-aware + quartile lift"
```

---

## Task 5 : Verdict greenlight pré-enregistré

**Files:**
- Modify: `src/orderflow_bot/backtest/separation.py`
- Test: `tests/test_separation.py`

- [ ] **Step 1 : Écrire le test du verdict**

```python
# tests/test_separation.py  (ajouter)
from orderflow_bot.backtest.separation import evaluate_greenlight


def _rows_strong_separator():
    """7 jours, 8 candidats/jour. 'good' (oriente) separe parfaitement les
    morts-nes ; tape 'noise' = bruit constant."""
    rows = []
    for d in range(7):
        for k in range(8):
            mort = k >= 4
            rows.append({"day": f"d{d}", "mort_ne": mort,
                         "good": float(k), "noise": 0.0})
    return rows


def test_greenlight_passes_on_strong_separator():
    rows = _rows_strong_separator()
    days = [f"d{d}" for d in range(7)]
    v = evaluate_greenlight(rows, days, orient={"good": +1}, tape_feats=["noise"])
    assert v["best_feat"] == "good"
    assert v["best_auc"] >= 0.60
    assert v["c1"] and v["c2"] and v["c3"] and v["c4"]
    assert v["green"] is True


def test_greenlight_fails_when_no_book_signal():
    # book = bruit, tape = bruit -> pas de separation
    rows = [{"day": f"d{d}", "mort_ne": (k % 2 == 0), "good": 0.0, "noise": 0.0}
            for d in range(7) for k in range(8)]
    days = [f"d{d}" for d in range(7)]
    v = evaluate_greenlight(rows, days, orient={"good": +1}, tape_feats=["noise"])
    assert v["green"] is False
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run: `.venv\Scripts\python -m pytest tests/test_separation.py::test_greenlight_passes_on_strong_separator -v`
Expected: FAIL — `ImportError: cannot import name 'evaluate_greenlight'`.

- [ ] **Step 3 : Implémenter evaluate_greenlight**

```python
# src/orderflow_bot/backtest/separation.py  (ajouter en bas)
def evaluate_greenlight(rows, days, orient, tape_feats, *, auc_min=0.60,
                        delta_min=0.05, day_min=6, day_min_n=5):
    """Applique les 4 conditions pre-enregistrees (cf. spec). orient = {feat: +/-1}
    (signe tel que haut -> plus de morts-nes). tape_feats = liste de features tape
    baseline (sens libre -> on prend max(auc, 1-auc)). Retourne un dict de verdict."""
    labels = [r["mort_ne"] for r in rows]

    def oriented(rs, feat):
        sign = orient[feat]
        return [sign * r[feat] for r in rs], [r["mort_ne"] for r in rs]

    book_auc = {f: auc(*oriented(rows, f)) for f in orient}
    best_feat = max(book_auc, key=lambda f: book_auc[f] if not math.isnan(book_auc[f]) else -1.0)
    best_auc = book_auc[best_feat]

    tape_auc = {}
    for f in tape_feats:
        a = auc([r[f] for r in rows], labels)
        tape_auc[f] = max(a, 1 - a) if not math.isnan(a) else float("nan")
    best_tape = max((v for v in tape_auc.values() if not math.isnan(v)), default=0.5)

    lift = quartile_lift(*oriented(rows, best_feat))
    clean = [x for x in lift if not math.isnan(x)]
    monotone = all(clean[k] <= clean[k + 1] for k in range(len(clean) - 1)) and len(clean) >= 2

    by_day_ok = 0
    for day in days:
        dr = [r for r in rows if r["day"] == day]
        if len(dr) < day_min_n:
            continue
        a = auc(*oriented(dr, best_feat))
        if not math.isnan(a) and a > 0.5:
            by_day_ok += 1

    c1 = (not math.isnan(best_auc)) and best_auc >= auc_min
    c2 = monotone
    c3 = by_day_ok >= day_min
    c4 = (not math.isnan(best_auc)) and (best_auc - best_tape) >= delta_min
    return {"best_feat": best_feat, "best_auc": best_auc, "best_tape": best_tape,
            "book_auc": book_auc, "tape_auc": tape_auc, "lift": lift,
            "by_day_ok": by_day_ok, "c1": c1, "c2": c2, "c3": c3, "c4": c4,
            "green": bool(c1 and c2 and c3 and c4)}
```

- [ ] **Step 4 : Lancer, vérifier le succès**

Run: `.venv\Scripts\python -m pytest tests/test_separation.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5 : Commit**

```bash
git add src/orderflow_bot/backtest/separation.py tests/test_separation.py
git commit -m "feat(orderflow): verdict greenlight pre-enregistre (4 conditions)"
```

---

## Task 6 : Orchestration + viz + run réel

**Files:**
- Create: `scripts/dom_separation.py`

Pas de TDD unitaire ici (I/O + viz) : la logique pure est déjà testée (Tasks 1–5). On valide par un **smoke run** sur les 7 jours.

- [ ] **Step 1 : Écrire le script d'orchestration**

```python
# scripts/dom_separation.py
"""Phase 0 DOM : le book separe-t-il les fades morts-nes mieux que le tape ?

Pour chaque jour L2 (7 premiers-du-mois gratuits), genere les candidats fade
(meme config.yaml que le no-edge), les labelle (simulate_isolated -> mort-ne si
mfe_r<0.5), joint le book a l'instant du fill, calcule les 4 features DOM, et
mesure la separation (AUC + lift par quartile) vs les features tape stack_vol/
stack_depth. Verdict greenlight PRE-ENREGISTRE -> rapport HTML.

Usage: python scripts/dom_separation.py [config.yaml] [data/l2/BTCUSDT] [--no-open]
"""
import datetime as dt
import glob
import sys
from pathlib import Path

import numpy as np

from orderflow_bot.backtest.separation import evaluate_greenlight, quartile_lift
from orderflow_bot.config import load_config
from orderflow_bot.features import book as bk
from orderflow_bot.ingestion.reader import read_trades
from orderflow_bot.pipeline import generate_plans, simulate_isolated

_DAY = 86_400_000
ORIENT = {"book_defense": -1, "touch_imbalance": -1, "replenish": -1, "pull_rate": +1}
TAPE_FEATS = ["stack_vol", "stack_depth"]
BAND_TICKS = 20
W_MS = 2_000
NORM_WINDOW_MS = 60_000


def days_from_dir(l2dir: str):
    out = []
    for p in sorted(glob.glob(f"{l2dir}/book_snapshot_25_*.csv.gz")):
        date_s = Path(p).name.replace("book_snapshot_25_", "").replace(".csv.gz", "")
        out.append((date_s, p))
    return out


def _day_ms(date_s: str) -> int:
    return int(dt.datetime.strptime(date_s, "%Y-%m-%d")
               .replace(tzinfo=dt.timezone.utc).timestamp() * 1000)


def collect(cfg, date_s: str, l2_path: str) -> list[dict]:
    day = _day_ms(date_s)
    band = BAND_TICKS * cfg.tick_size
    warm = day - cfg.strategy.npoc_lookback_days * _DAY
    gen_ticks = read_trades(cfg.market_data_dir, cfg.symbol, start_ms=warm, end_ms=day + _DAY)
    plans = generate_plans(cfg, gen_ticks, day, day + _DAY)
    if not plans:
        return []
    lab_ticks = read_trades(cfg.market_data_dir, cfg.symbol,
                            start_ms=day, end_ms=day + _DAY + 3_600_000)
    trades = simulate_isolated(cfg, plans, lab_ticks)

    book = bk.load_book_day(l2_path)
    tp = list(read_trades(cfg.market_data_dir, cfg.symbol, start_ms=day, end_ms=day + _DAY))
    t_ts = np.fromiter((t.ts for t in tp), dtype="int64", count=len(tp))
    t_px = np.fromiter((t.price for t in tp), dtype="float64", count=len(tp))
    t_qty = np.fromiter((t.qty for t in tp), dtype="float64", count=len(tp))

    rows, excluded = [], 0
    for ct in trades:
        p = ct.plan
        ot = ct.opened_ts
        i = book.idx_at(ot)
        if i < 0:
            excluded += 1
            continue
        norm = book.trailing_median_total(ot, NORM_WINDOW_MS)
        rows.append({
            "day": date_s,
            "mort_ne": ct.mfe_r < 0.5,
            "book_defense": bk.book_defense(book, i, p.entry, p.side, band, norm),
            "touch_imbalance": bk.touch_imbalance(book, i, p.entry, p.side, band),
            "replenish": bk.replenish(book, t_ts, t_px, t_qty, p.entry, p.side, ot, W_MS, band),
            "pull_rate": bk.pull_rate(book, t_ts, t_px, t_qty, p.entry, p.side, ot, W_MS, band),
            "stack_vol": float(p.meta.get("stack_vol", float("nan"))),
            "stack_depth": float(p.meta.get("stack_depth", float("nan"))),
        })
    print(f"{date_s}: {len(rows)} joints, {excluded} exclus (pas de snapshot <= fill)")
    return rows


def viz(verdict, n, base, out="dom_separation.html", do_open=True):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    feats = list(ORIENT)
    fig = make_subplots(rows=1, cols=2, column_widths=[0.45, 0.55],
                        subplot_titles=("AUC oriente (>0.5 = separe)", f"Lift quartile — {verdict['best_feat']}"),
                        specs=[[{"type": "bar"}, {"type": "bar"}]])
    aucs = [verdict["book_auc"][f] for f in feats]
    cols = ["#26a69a" if a >= 0.60 else "#ef5350" for a in aucs]
    fig.add_bar(x=feats, y=aucs, marker_color=cols, row=1, col=1, name="book")
    fig.add_bar(x=list(verdict["tape_auc"]), y=list(verdict["tape_auc"].values()),
                marker_color="#888", row=1, col=1, name="tape")
    fig.add_hline(y=0.60, line=dict(color="#fff", dash="dash"), row=1, col=1)
    lift = verdict["lift"]
    fig.add_bar(x=[f"Q{k+1}" for k in range(len(lift))], y=lift,
                marker_color="#ffb74d", row=1, col=2, name="taux mort-ne")
    fig.add_hline(y=base, line=dict(color="#fff", dash="dash"), row=1, col=2)
    cks = "".join("✅" if verdict[c] else "❌" for c in ("c1", "c2", "c3", "c4"))
    verdict_txt = "GREENLIGHT ✅" if verdict["green"] else "KILL ❌"
    fig.update_layout(
        template="plotly_dark", height=600, showlegend=True,
        title=f"PHASE 0 DOM — {verdict_txt}  |  best '{verdict['best_feat']}' "
              f"AUC={verdict['best_auc']:.3f} (tape {verdict['best_tape']:.3f})  |  "
              f"n={n}, base mort-ne={base:.2f}  |  c1c2c3c4={cks} "
              f"(jours OK {verdict['by_day_ok']}/7)")
    fig.write_html(out, include_plotlyjs=True)
    print(f"-> {out}")
    if do_open:
        import webbrowser
        webbrowser.open(Path(out).resolve().as_uri())


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cfg_path = next((a for a in args if a.endswith(".yaml")), "config.yaml")
    l2dir = next((a for a in args if "l2" in a.replace("\\", "/")), "data/l2/BTCUSDT")
    cfg = load_config(cfg_path)
    days = days_from_dir(l2dir)
    if not days:
        print(f"aucun book_snapshot_25_*.csv.gz dans {l2dir}")
        return
    rows = []
    for date_s, p in days:
        rows += collect(cfg, date_s, p)
    if not rows:
        print("aucun candidat joint")
        return
    n = len(rows)
    base = sum(r["mort_ne"] for r in rows) / n
    print(f"\n=== {n} candidats | base mort-ne = {base:.3f} ===")
    verdict = evaluate_greenlight(rows, [d for d, _ in days], ORIENT, TAPE_FEATS)
    for f in ORIENT:
        print(f"  {f:16s} AUC={verdict['book_auc'][f]:.3f}")
    for f, a in verdict["tape_auc"].items():
        print(f"  [tape] {f:10s} AUC={a:.3f}")
    print(f"\nbest book = {verdict['best_feat']} ({verdict['best_auc']:.3f}) "
          f"vs tape {verdict['best_tape']:.3f}")
    print(f"c1 AUC>=0.60={verdict['c1']} | c2 lift monotone={verdict['c2']} | "
          f"c3 jours>=6/7={verdict['c3']} ({verdict['by_day_ok']}) | c4 dAUC>=0.05={verdict['c4']}")
    print(f"\n=== VERDICT : {'GREENLIGHT (Phase 1)' if verdict['green'] else 'KILL thèse L2'} ===")
    viz(verdict, n, base, do_open="--no-open" not in sys.argv)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2 : Smoke run sur les 7 jours**

Run: `.venv\Scripts\python scripts/dom_separation.py config.yaml data/l2/BTCUSDT --no-open`
Expected: une ligne par jour (`AAAA-MM-JJ: N joints, M exclus`), puis le bloc AUC par feature, les 4 conditions, le VERDICT, et `-> dom_separation.html`. Aucune exception. `n` total attendu ~200–300.

- [ ] **Step 3 : Vérifier le HTML**

Run: `.venv\Scripts\python scripts/dom_separation.py config.yaml data/l2/BTCUSDT`
Expected: ouvre `dom_separation.html` (barres AUC book vs tape, lift quartile, titre = verdict). Vérifier visuellement que les barres et le verdict cohèrent avec le stdout.

- [ ] **Step 4 : Lancer toute la suite de tests**

Run: `.venv\Scripts\python -m pytest -q`
Expected: tous les tests passent (existants + 12 neufs).

- [ ] **Step 5 : Commit**

```bash
git add scripts/dom_separation.py
git commit -m "feat(orderflow): orchestration Phase 0 DOM (join book + verdict greenlight + viz)"
```

---

## Self-Review

**Spec coverage :**
- Loader `book_snapshot_25` (µs→ms, top-25) → Task 1.
- 4 features (book_defense, touch_imbalance, replenish, pull_rate) avec sens pré-enregistré → Tasks 2–3.
- Join book au fill `opened_ts`, exclusion hors-snapshot loggée → Task 6 (`collect`).
- Séparation AUC + quartile lift vs tape → Tasks 4, 6.
- Greenlight 4 conditions (AUC≥0.60, lift monotone, ≥6/7 jours, ΔAUC≥0.05) → Task 5.
- Sortie HTML Plotly + verdict → Task 6.
- Warmup nPOC depuis tape contigu → Task 6 (`collect`, `npoc_lookback_days`).
- Tests synthétiques (bisect, defense, imbalance, replenish, pull) → Tasks 1–3.

**Cohérence des types :** `BookDay` (Task 1) consommé par toutes les features (Tasks 2–3) et `collect` (Task 6) avec les mêmes signatures. `evaluate_greenlight` (Task 5) consomme les `rows` dict produits par `collect` (mêmes clés : `day`, `mort_ne`, 4 features book, 2 tape). `ORIENT` (Task 6) = clés des features book = clés testées (Task 5).

**Placeholders :** aucun — code complet à chaque étape.

**Non couvert volontairement (hors scope spec) :** intégration ConfluenceEngine, backtest, Phase 1.

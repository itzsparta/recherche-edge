import gzip
import math

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


def test_trailing_median_total():
    ts = np.array([100, 200, 300, 400], dtype="int64")
    total = np.array([10.0, 20.0, 30.0, 100.0])
    z = np.zeros((4, 25))
    book = bk.BookDay(ts, z.copy(), z.copy(), z.copy(), z.copy(), total)
    # fenetre vide (aucun snapshot dans [50, 99]) -> NaN
    assert math.isnan(book.trailing_median_total(99, 49))
    # fenetre a un seul element [200, 200] -> ce total
    assert book.trailing_median_total(200, 0) == 20.0
    # impair, 3 elements dans [100, 300] -> mediane de {10, 20, 30} = 20
    assert book.trailing_median_total(300, 200) == 20.0
    # pair, 4 elements dans [100, 400] -> moyenne des 2 centraux {20, 30} = 25
    assert book.trailing_median_total(400, 300) == 25.0


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


def test_pull_rate_boundary_trade_counted_once():
    # bid niveau0 : 4 -> 3 -> 1 (drop 1 puis 2). trade pile sur le snapshot interieur t=1000.
    book = _one_level_book([0, 1000, 2000],
                           ask=[(101.0, 1.0)] * 3,
                           bid=[(100.0, 4.0), (100.0, 3.0), (100.0, 1.0)])
    t_ts = np.array([1000], dtype="int64"); t_px = np.array([100.0]); t_qty = np.array([1.0])
    # le trade (qty 1) explique le drop de l'etape 1 (4->3) UNE fois ; etape 2 (3->1) = pull pur = 2
    # pull = 2 / start 4 = 0.5  (avant le fix il etait double-compte -> 0.25, faux)
    pull = bk.pull_rate(book, t_ts, t_px, t_qty, entry=100.0, side=1,
                        opened_ts=2000, W=2000, band=5.0)
    assert abs(pull - 0.5) < 1e-9

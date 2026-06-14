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

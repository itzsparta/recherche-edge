import pyarrow as pa
import pyarrow.parquet as pq

from orderflow_bot.ingestion.reader import read_trades
from orderflow_bot.ingestion.recorder import TradeRecorder
from orderflow_bot.models import Trade


def _write_parquet(folder, name: str, trades: list[Trade]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table({
        "ts": [t.ts for t in trades],
        "price": [t.price for t in trades],
        "qty": [t.qty for t in trades],
        "is_buyer_maker": [t.is_buyer_maker for t in trades],
    }), folder / name)


def _trades(n: int, t0: int = 1_700_000_000_000) -> list[Trade]:
    return [
        Trade(ts=t0 + i * 100, price=100.0 + i * 0.1, qty=0.01 * (i + 1),
              is_buyer_maker=i % 2 == 0)
        for i in range(n)
    ]


def test_roundtrip(tmp_path):
    rec = TradeRecorder(tmp_path, "BTCUSDT", flush_every=4)
    src = _trades(10)
    for t in src:
        rec.append(t)
    rec.flush()                     # 2 fichiers auto + 1 reste
    got = list(read_trades(tmp_path, "BTCUSDT"))
    assert got == src               # ordre + valeurs exacts


def test_read_time_window(tmp_path):
    rec = TradeRecorder(tmp_path, "BTCUSDT", flush_every=100)
    src = _trades(10)
    for t in src:
        rec.append(t)
    rec.flush()
    t0 = src[0].ts
    got = list(read_trades(tmp_path, "BTCUSDT", start_ms=t0 + 300, end_ms=t0 + 700))
    assert got == src[3:7]


def test_read_empty_dir(tmp_path):
    assert list(read_trades(tmp_path, "BTCUSDT")) == []


def test_read_symbol_folder_without_parquet(tmp_path):
    (tmp_path / "BTCUSDT").mkdir()
    assert list(read_trades(tmp_path, "BTCUSDT")) == []


def test_read_order_independent_of_filenames(tmp_path):
    # noms tries a l'envers du temps (mix recorder/importer) : l'ordre doit
    # venir des bornes ts des fichiers, jamais du tri des noms
    src = _trades(10)
    _write_parquet(tmp_path / "BTCUSDT", "AAA.parquet", src[5:])
    _write_parquet(tmp_path / "BTCUSDT", "ZZZ.parquet", src[:5])
    assert list(read_trades(tmp_path, "BTCUSDT")) == src


def test_read_overlapping_files_fall_back_to_global_sort(tmp_path):
    src = _trades(10)
    _write_parquet(tmp_path / "BTCUSDT", "even.parquet", src[::2])
    _write_parquet(tmp_path / "BTCUSDT", "odd.parquet", src[1::2])
    assert list(read_trades(tmp_path, "BTCUSDT")) == src


def test_read_window_skips_out_of_range_files(tmp_path):
    src = _trades(10)
    _write_parquet(tmp_path / "BTCUSDT", "a.parquet", src[:5])
    _write_parquet(tmp_path / "BTCUSDT", "b.parquet", src[5:])
    t0 = src[0].ts
    got = list(read_trades(tmp_path, "BTCUSDT", start_ms=t0 + 500, end_ms=t0 + 800))
    assert got == src[5:8]


def test_flush_never_overwrites(tmp_path):
    rec = TradeRecorder(tmp_path, "BTCUSDT", flush_every=100)
    t = Trade(ts=1_700_000_000_000, price=100.0, qty=1.0, is_buyer_maker=False)
    rec.append(t)
    rec.flush()
    rec.append(t)
    rec.flush()                     # memes bornes ts -> suffixe, pas d'ecrasement
    assert len(list((tmp_path / "BTCUSDT").glob("*.parquet"))) == 2
    assert list(read_trades(tmp_path, "BTCUSDT")) == [t, t]

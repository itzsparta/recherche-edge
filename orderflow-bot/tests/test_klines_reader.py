import pyarrow as pa
import pyarrow.parquet as pq

from orderflow_bot.features.aggregator import BarAggregator
from orderflow_bot.ingestion.reader import read_klines_as_ticks

H4 = 240 * 60_000
T0 = 20_000 * 86_400_000          # minute- et 4h-aligne (multiple de DAY)


def _write_klines(folder, name, rows):
    # rows: (ts, open, high, low, close, volume)
    folder.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table({
        "ts": [r[0] for r in rows], "open": [r[1] for r in rows],
        "high": [r[2] for r in rows], "low": [r[3] for r in rows],
        "close": [r[4] for r in rows], "volume": [r[5] for r in rows],
    }), folder / name)


def test_kline_expands_to_four_ticks(tmp_path):
    _write_klines(tmp_path / "BTCUSDT", "k.parquet", [(T0, 100.0, 105.0, 98.0, 101.0, 8.0)])
    ticks = list(read_klines_as_ticks(tmp_path, "BTCUSDT"))
    assert [(t.ts - T0, t.price, t.qty) for t in ticks] == [
        (0, 100.0, 2.0), (20_000, 105.0, 2.0), (40_000, 98.0, 2.0), (59_999, 101.0, 2.0),
    ]
    assert all(t.is_buyer_maker is False for t in ticks)


def test_klines_reconstruct_4h_bar_ohlc(tmp_path):
    # 2 klines 1m dans la meme fenetre 4h -> une barre 4h
    _write_klines(tmp_path / "BTCUSDT", "k.parquet", [
        (T0,          100.0, 105.0, 98.0, 101.0, 8.0),    # open de fenetre = 100
        (T0 + 60_000, 101.0, 110.0, 99.0, 102.0, 4.0),    # close de fenetre = 102
    ])
    agg = BarAggregator(H4, 1.0)
    for t in read_klines_as_ticks(tmp_path, "BTCUSDT"):
        agg.on_trade(t)
    bar = agg.flush()
    assert bar.open == 100.0      # 1er tick
    assert bar.high == 110.0      # max H
    assert bar.low == 98.0        # min L
    assert bar.close == 102.0     # dernier tick
    assert bar.volume == 12.0     # somme V


def test_klines_window_filters_by_open_time(tmp_path):
    _write_klines(tmp_path / "BTCUSDT", "k.parquet", [
        (T0,           100.0, 101.0, 99.0, 100.5, 4.0),
        (T0 + 60_000,  100.5, 102.0, 100.0, 101.0, 4.0),
        (T0 + 120_000, 101.0, 103.0, 100.5, 102.0, 4.0),
    ])
    ticks = list(read_klines_as_ticks(tmp_path, "BTCUSDT",
                                      start_ms=T0 + 60_000, end_ms=T0 + 120_000))
    # seule la kline du milieu (open_time dans [start,end)) -> 4 ticks @ open 100.5
    assert {t.ts // 60_000 for t in ticks} == {(T0 + 60_000) // 60_000}
    assert ticks[0].price == 100.5


def test_read_klines_empty_dir(tmp_path):
    assert list(read_klines_as_ticks(tmp_path, "BTCUSDT")) == []

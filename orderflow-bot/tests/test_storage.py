from orderflow_bot.ingestion.reader import read_trades
from orderflow_bot.ingestion.recorder import TradeRecorder
from orderflow_bot.models import Trade


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

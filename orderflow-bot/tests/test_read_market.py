import pyarrow as pa
import pyarrow.parquet as pq

from orderflow_bot.config import BotConfig
from orderflow_bot.ingestion.reader import read_market

T0 = 20_000 * 86_400_000


def _write(folder, name, table):
    folder.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, folder / name)


def test_read_market_trades(tmp_path):
    _write(tmp_path / "spot" / "BTCUSDT", "t.parquet", pa.table({
        "ts": [T0, T0 + 100], "price": [100.0, 101.0],
        "qty": [1.0, 2.0], "is_buyer_maker": [False, True],
    }))
    cfg = BotConfig(data_dir=str(tmp_path), market="spot", data_format="trades")
    ticks = list(read_market(cfg))
    assert [t.price for t in ticks] == [100.0, 101.0]


def test_read_market_klines(tmp_path):
    _write(tmp_path / "klines" / "spot" / "BTCUSDT", "k.parquet", pa.table({
        "ts": [T0], "open": [100.0], "high": [105.0],
        "low": [98.0], "close": [101.0], "volume": [8.0],
    }))
    cfg = BotConfig(data_dir=str(tmp_path), market="spot", data_format="klines")
    ticks = list(read_market(cfg))
    assert [t.price for t in ticks] == [100.0, 105.0, 98.0, 101.0]   # 4 ticks synthetiques

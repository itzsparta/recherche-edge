import io
import zipfile
from datetime import date
from urllib.error import HTTPError

from orderflow_bot.config import BotConfig
from orderflow_bot.ingestion.importer import archive_url, convert_csv, import_range
from orderflow_bot.ingestion.reader import available_days, read_trades

# format spot reel : 8 colonnes, PAS de header, transact_time en MICROsecondes,
# booleens True/False
SPOT_CSV = """3984971527,61730.00000000,0.00008000,6394149873,6394149873,1781049600078441,False,True
3984971528,61730.00000000,0.03666000,6394149874,6394149907,1781049600137111,True,True
"""

# format futures reel : 7 colonnes, header, transact_time en MILLIsecondes,
# booleens true/false
FUTURES_CSV = """agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker
3333403793,61694.9,0.023,7771002125,7771002137,1781049600065,true
3333403794,61695.0,0.896,7771002138,7771002163,1781049600132,false
"""


def _convert(tmp_path, content: str):
    csv_path = tmp_path / "in.csv"
    csv_path.write_text(content, encoding="utf-8")
    out_dir = tmp_path / "spot" / "BTCUSDT"
    out_dir.mkdir(parents=True)
    out = out_dir / "day.parquet"
    n = convert_csv(csv_path, out)
    return n, list(read_trades(tmp_path / "spot", "BTCUSDT"))


def test_convert_spot_format(tmp_path):
    n, trades = _convert(tmp_path, SPOT_CSV)
    assert n == 2
    # microsecondes -> millisecondes
    assert trades[0].ts == 1781049600078
    assert trades[1].ts == 1781049600137
    assert trades[0].price == 61730.0
    assert trades[0].qty == 0.00008
    assert trades[0].is_buyer_maker is False
    assert trades[1].is_buyer_maker is True


def test_convert_futures_format(tmp_path):
    n, trades = _convert(tmp_path, FUTURES_CSV)
    assert n == 2
    # deja en millisecondes : inchange
    assert trades[0].ts == 1781049600065
    assert trades[0].is_buyer_maker is True
    assert trades[1].is_buyer_maker is False


def test_convert_orders_by_ts(tmp_path):
    shuffled = """agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker
2,101.0,1.0,2,2,1781049600200,false
1,100.0,1.0,1,1,1781049600100,true
"""
    n, trades = _convert(tmp_path, shuffled)
    assert n == 2
    assert [t.ts for t in trades] == [1781049600100, 1781049600200]


def test_archive_url():
    d = date(2026, 6, 10)
    assert archive_url("spot", "BTCUSDT", d) == (
        "https://data.binance.vision/data/spot/daily/aggTrades/"
        "BTCUSDT/BTCUSDT-aggTrades-2026-06-10.zip")
    assert archive_url("futures", "BTCUSDT", d) == (
        "https://data.binance.vision/data/futures/um/daily/aggTrades/"
        "BTCUSDT/BTCUSDT-aggTrades-2026-06-10.zip")


def _zip_bytes(csv_content: str, name: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name, csv_content)
    return buf.getvalue()


def _fake_download(day_ms: int):
    """Fabrique un downloader qui sert un zip futures-style pour chaque jour."""
    def dl(url: str) -> bytes:
        csv = ("agg_trade_id,price,quantity,first_trade_id,last_trade_id,"
               "transact_time,is_buyer_maker\n"
               f"1,100.0,1.0,1,1,{day_ms},true\n")
        return _zip_bytes(csv, "x.csv")
    return dl


def test_import_range_writes_one_parquet_per_day(tmp_path, monkeypatch):
    import orderflow_bot.ingestion.importer as imp
    day = date(2026, 6, 10)
    day_ms = 1781049600000
    monkeypatch.setattr(imp, "_download", _fake_download(day_ms))
    cfg = BotConfig(data_dir=str(tmp_path))
    report = imp.import_range(cfg, day, day)
    assert report == {"days_imported": 1, "days_skipped": 0,
                      "days_missing": 0, "trades": 1}
    assert available_days(cfg.market_data_dir, cfg.symbol) == [day_ms // 86_400_000]


def test_import_range_idempotent(tmp_path, monkeypatch):
    import orderflow_bot.ingestion.importer as imp
    day = date(2026, 6, 10)
    monkeypatch.setattr(imp, "_download", _fake_download(1781049600000))
    cfg = BotConfig(data_dir=str(tmp_path))
    imp.import_range(cfg, day, day)
    report = imp.import_range(cfg, day, day)          # deuxieme run : skip
    assert report["days_imported"] == 0
    assert report["days_skipped"] == 1


def test_import_range_404_counts_missing(tmp_path, monkeypatch):
    import orderflow_bot.ingestion.importer as imp

    def dl_404(url: str) -> bytes:
        raise HTTPError(url, 404, "Not Found", None, None)

    monkeypatch.setattr(imp, "_download", dl_404)
    cfg = BotConfig(data_dir=str(tmp_path))
    report = imp.import_range(cfg, date(2026, 6, 10), date(2026, 6, 10))
    assert report == {"days_imported": 0, "days_skipped": 0,
                      "days_missing": 1, "trades": 0}

import pyarrow.parquet as pq

from orderflow_bot.ingestion.klines import convert_kline_csv

# 12 colonnes, sans header (format historique spot)
_MS_ROW = "1577836800000,7195.24,7196.25,7178.64,7179.78,1004.5,1577836859999,7218000,1200,500.0,3600000,0\n"
# meme barre mais open_time en microsecondes (recent) -> doit etre normalise en ms
_US_ROW = "1577836800000000,7195.24,7196.25,7178.64,7179.78,1004.5,1577836859999000,7218000,1200,500.0,3600000,0\n"


def test_parses_ohlcv_and_keeps_ms(tmp_path):
    csv = tmp_path / "k.csv"
    csv.write_text(_MS_ROW, encoding="utf-8")
    out = tmp_path / "k.parquet"
    n = convert_kline_csv(csv, out)
    assert n == 1
    tbl = pq.read_table(out).to_pylist()[0]
    assert tbl == {"ts": 1577836800000, "open": 7195.24, "high": 7196.25,
                   "low": 7178.64, "close": 7179.78, "volume": 1004.5}


def test_normalizes_microseconds_to_ms(tmp_path):
    csv = tmp_path / "k.csv"
    csv.write_text(_US_ROW, encoding="utf-8")
    out = tmp_path / "k.parquet"
    convert_kline_csv(csv, out)
    assert pq.read_table(out).to_pylist()[0]["ts"] == 1577836800000


def test_parses_with_header(tmp_path):
    header = "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_base,taker_buy_quote,ignore\n"
    csv = tmp_path / "k.csv"
    csv.write_text(header + _MS_ROW, encoding="utf-8")
    out = tmp_path / "k.parquet"
    assert convert_kline_csv(csv, out) == 1
    assert pq.read_table(out).to_pylist()[0]["ts"] == 1577836800000

from orderflow_bot.ingestion.importer import convert_csv
from orderflow_bot.ingestion.reader import read_trades

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

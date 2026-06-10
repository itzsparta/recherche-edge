from orderflow_bot.ingestion.parser import parse_agg_trade

PAYLOAD = {
    "e": "aggTrade", "E": 1718000000123, "s": "BTCUSDT", "a": 26129,
    "p": "117234.30", "q": "0.005", "f": 100, "l": 105,
    "T": 1718000000100, "m": True,
}


def test_parse_valid():
    t = parse_agg_trade(PAYLOAD)
    assert t is not None
    assert t.ts == 1718000000100          # T = trade time, pas E
    assert t.price == 117234.30
    assert t.qty == 0.005
    assert t.is_buyer_maker is True
    assert t.aggressor == -1


def test_parse_ignores_other_events():
    assert parse_agg_trade({"e": "depthUpdate"}) is None
    assert parse_agg_trade({"result": None, "id": 1}) is None

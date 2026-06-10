from orderflow_bot.models import Trade


def test_aggressor_buy():
    t = Trade(ts=1, price=100.0, qty=0.5, is_buyer_maker=False)
    assert t.aggressor == 1


def test_aggressor_sell():
    t = Trade(ts=1, price=100.0, qty=0.5, is_buyer_maker=True)
    assert t.aggressor == -1

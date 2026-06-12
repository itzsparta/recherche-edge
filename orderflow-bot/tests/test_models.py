from orderflow_bot.models import Trade, ClosedTrade, OrderPlan


def test_aggressor_buy():
    t = Trade(ts=1, price=100.0, qty=0.5, is_buyer_maker=False)
    assert t.aggressor == 1


def test_aggressor_sell():
    t = Trade(ts=1, price=100.0, qty=0.5, is_buyer_maker=True)
    assert t.aggressor == -1


def test_closed_trade_fees_default():
    from orderflow_bot.models import ClosedTrade, OrderPlan
    plan = OrderPlan(ts=0, side=1, entry=100.0, stop=98.0, target=106.0)
    ct = ClosedTrade(plan=plan, qty=1.0, fills=[], pnl=0.0, r_multiple=0.0,
                     opened_ts=0, closed_ts=0)
    assert ct.fees == 0.0

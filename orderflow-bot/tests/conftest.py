from orderflow_bot.models import FootprintBar, Trade


def make_trade(ts: int, price: float, qty: float = 1.0, sell: bool = False) -> Trade:
    return Trade(ts=ts, price=price, qty=qty, is_buyer_maker=sell)


def make_bar(low: float, high: float, delta: float, open_: float = 0.0,
             close: float = 0.0, open_ts: int = 0) -> FootprintBar:
    o = open_ or low
    c = close or high
    return FootprintBar(open_ts=open_ts, close_ts=open_ts + 60_000, open=o, high=high,
                        low=low, close=c, volume=abs(delta) or 1.0, delta=delta,
                        ask_vol={}, bid_vol={})

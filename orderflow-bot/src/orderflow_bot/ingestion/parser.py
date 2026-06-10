from orderflow_bot.models import Trade


def parse_agg_trade(msg: dict) -> Trade | None:
    """Stream Binance @aggTrade -> Trade. Ignore tout autre message."""
    if msg.get("e") != "aggTrade":
        return None
    return Trade(
        ts=int(msg["T"]),
        price=float(msg["p"]),
        qty=float(msg["q"]),
        is_buyer_maker=bool(msg["m"]),
    )

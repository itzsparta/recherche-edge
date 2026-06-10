import asyncio
import json
import logging
from collections.abc import Callable

import websockets

from orderflow_bot.ingestion.parser import parse_agg_trade
from orderflow_bot.models import Trade

log = logging.getLogger(__name__)

FUTURES_WS = "wss://fstream.binance.com/ws"


class HandlerError(Exception):
    """Le handler a echoue (ex: disque plein). Distincte des erreurs transport :
    une erreur handler doit ARRETER le stream, pas declencher une reconnexion
    silencieuse qui perdrait tous les trades suivants."""


async def stream_trades(
    symbol: str,
    handler: Callable[[Trade], None],
    url_base: str = FUTURES_WS,
) -> None:
    """Boucle infinie : connecte, pousse chaque Trade au handler, reconnecte
    avec backoff exponentiel (1s -> 60s) sur toute coupure transport."""
    url = f"{url_base}/{symbol.lower()}@aggTrade"
    backoff = 1.0
    while True:
        try:
            async with websockets.connect(url, ping_interval=180, ping_timeout=60) as ws:
                log.info("connecte a %s", url)
                backoff = 1.0
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        log.warning("trame non-JSON ignoree: %.200r", raw)
                        continue
                    t = parse_agg_trade(msg)
                    if t is None:
                        continue
                    try:
                        handler(t)
                    except Exception as e:
                        raise HandlerError("handler en echec, arret du stream") from e
        except (websockets.WebSocketException, OSError) as e:
            log.warning("deconnexion ws (%s), reconnexion dans %.0fs", e, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60.0)

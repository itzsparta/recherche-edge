import logging

from orderflow_bot.config import BotConfig
from orderflow_bot.ingestion.binance_ws import stream_trades
from orderflow_bot.ingestion.recorder import TradeRecorder

log = logging.getLogger(__name__)


async def run_record(cfg: BotConfig) -> None:
    """Enregistre le flux tick en Parquet. Ctrl+C -> flush propre."""
    rec = TradeRecorder(cfg.data_dir, cfg.symbol)
    try:
        await stream_trades(cfg.symbol, rec.append)
    finally:
        rec.flush()
        log.info("flush final ok")

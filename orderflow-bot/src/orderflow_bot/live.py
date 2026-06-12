import logging

from orderflow_bot.config import BotConfig
from orderflow_bot.execution.journal import TradeJournal
from orderflow_bot.ingestion.binance_ws import stream_trades, ws_url
from orderflow_bot.ingestion.reader import read_trades
from orderflow_bot.ingestion.recorder import TradeRecorder
from orderflow_bot.pipeline import Pipeline

log = logging.getLogger(__name__)


async def run_record(cfg: BotConfig) -> None:
    """Enregistre le flux tick en Parquet. Ctrl+C -> flush propre."""
    rec = TradeRecorder(cfg.market_data_dir, cfg.symbol)
    try:
        await stream_trades(cfg.symbol, rec.append, url_base=ws_url(cfg.market))
    finally:
        rec.flush()
        log.info("flush final ok")


def bootstrap_pipeline(pipe: Pipeline, cfg: BotConfig) -> int:
    """Rejoue l'historique Parquet local AVANT le live pour amorcer niveaux,
    zones et biais — trading desactive pendant le replay. Retourne le nombre
    de trades rejoues."""
    pipe.trading_enabled = False
    n = 0
    for t in read_trades(cfg.market_data_dir, cfg.symbol):
        pipe.on_trade(t)
        n += 1
    pipe.trading_enabled = True
    log.info("bootstrap: %d trades rejoues, %d zones", n, len(pipe.confluence.zones))
    return n


async def run_paper(cfg: BotConfig) -> None:
    """Paper trading live : bootstrap historique puis stream temps reel.
    Enregistre aussi les ticks recus (les donnees s'accumulent en continu)."""
    journal = TradeJournal(cfg.journal_path)
    pipe = Pipeline(cfg, journal)
    bootstrap_pipeline(pipe, cfg)
    rec = TradeRecorder(cfg.market_data_dir, cfg.symbol)

    def handle(t) -> None:
        rec.append(t)
        pipe.on_trade(t)

    try:
        await stream_trades(cfg.symbol, handle, url_base=ws_url(cfg.market))
    finally:
        rec.flush()

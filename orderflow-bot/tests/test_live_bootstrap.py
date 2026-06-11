from orderflow_bot.config import BotConfig, SessionCfg, StrategyCfg
from orderflow_bot.execution.journal import TradeJournal
from orderflow_bot.ingestion.recorder import TradeRecorder
from orderflow_bot.live import bootstrap_pipeline
from orderflow_bot.models import Trade
from orderflow_bot.pipeline import Pipeline

DAY_MS = 86_400_000
DAY1 = 20_000 * DAY_MS


def test_bootstrap_replays_history_without_trading(tmp_path):
    cfg = BotConfig(
        data_dir=str(tmp_path / "data"),
        journal_path=str(tmp_path / "journal.jsonl"),
        strategy=StrategyCfg(profile_days=1),
        sessions=[SessionCfg(start="00:00", end="23:59")],
    )
    rec = TradeRecorder(cfg.data_dir, cfg.symbol)
    ts = DAY1
    for p in range(95, 106):
        for _ in range(10 - abs(p - 100)):
            rec.append(Trade(ts=ts, price=float(p), qty=1.0, is_buyer_maker=False))
            ts += 1_000
    # premier trade du jour 2 : declenche le rollover -> zones construites
    rec.append(Trade(ts=DAY1 + DAY_MS, price=100.0, qty=0.1, is_buyer_maker=False))
    rec.flush()

    pipe = Pipeline(cfg, TradeJournal(cfg.journal_path))
    n = bootstrap_pipeline(pipe, cfg)
    assert n > 0
    assert pipe.trading_enabled is True            # reactive apres replay
    assert len(pipe.confluence.zones) >= 2         # VAL + VAH au minimum
    assert TradeJournal.load(cfg.journal_path) == []   # aucun trade fictif

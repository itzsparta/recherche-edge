from orderflow_bot.config import (
    AbsorptionCfg, BotConfig, RiskCfg, SessionCfg, StrategyCfg,
)
from orderflow_bot.execution.journal import TradeJournal
from orderflow_bot.models import Trade
from orderflow_bot.pipeline import Pipeline, run_backtest

DAY_MS = 86_400_000
DAY1 = 20_000 * DAY_MS          # minuit UTC, jour epoch 20000


def _cfg(tmp_path) -> BotConfig:
    return BotConfig(
        tick_size=0.1, bin_size=1.0, bar_minutes=1, equity=10_000.0,
        journal_path=str(tmp_path / "journal.jsonl"),
        risk=RiskCfg(),
        strategy=StrategyCfg(
            zone_margin_pct=0.002, stop_buffer_ticks=10, profile_days=1,
            entry_expire_minutes=15,
            absorption=AbsorptionCfg(window_ms=30_000, vol_factor=3.0,
                                     max_range_ticks=15, min_delta_frac=0.3,
                                     baseline_windows=8),
        ),
        sessions=[SessionCfg(start="00:00", end="23:59")],
    )


def synth_trades() -> list[Trade]:
    out: list[Trade] = []
    # --- jour 1 : profil pyramidal 95..105, POC=100, VAL=97, VAH=103
    ts = DAY1
    for p in range(95, 106):
        for _ in range(10 - abs(p - 100)):
            out.append(Trade(ts=ts, price=float(p), qty=1.0,
                             is_buyer_maker=ts % 2 == 0))
            ts += 1_000
    # --- jour 2
    ts = DAY1 + DAY_MS
    # descente calme 100 -> 97.5 : baseline (~10 fenetres de 30 s, vol 0.5/fenetre)
    p = 100.0
    while p > 97.5:
        out.append(Trade(ts=ts, price=round(p, 1), qty=0.05, is_buyer_maker=True))
        ts += 3_000
        p -= 0.025
    # accalmie > window_ms : vide la fenetre glissante du detecteur, pour que
    # first/last de la fenetre choc soient les prix du choc lui-meme
    ts += 35_000
    # absorption dans la zone VAL (96.8..97.2) : 12 ventes 0.5, range 1 tick,
    # dernier prix >= premier
    for i in range(12):
        px = 97.0 if i % 2 == 0 else 97.1
        out.append(Trade(ts=ts, price=px, qty=0.5, is_buyer_maker=True))
        ts += 1_700
    # meche sous l'entry pour remplir l'ordre limit (franchissement strict)
    for _ in range(2):
        out.append(Trade(ts=ts, price=96.9, qty=0.3, is_buyer_maker=True))
        ts += 1_000
    # rotation vers le POC : 97.2 -> 100.6 (partiel ~1R puis target 100)
    p = 97.2
    while p <= 100.6:
        out.append(Trade(ts=ts, price=round(p, 1), qty=0.3, is_buyer_maker=False))
        ts += 2_000
        p += 0.2
    return out


def test_backtest_end_to_end(tmp_path):
    cfg = _cfg(tmp_path)
    report = run_backtest(cfg, synth_trades())
    assert report["trades"] == 1
    assert report["total_pnl"] > 50.0
    assert report["win_rate"] == 1.0
    rows = TradeJournal.load(cfg.journal_path)
    assert rows[0]["plan"]["meta"]["trigger"] == "absorption"
    assert rows[0]["plan"]["meta"]["zone"] == "val"
    kinds = [f["kind"] for f in rows[0]["fills"]]
    assert kinds[0] == "entry" and "partial" in kinds and kinds[-1] == "target"


def test_no_trading_during_warmup(tmp_path):
    cfg = _cfg(tmp_path)
    trades = [t for t in synth_trades() if t.ts < DAY1 + DAY_MS]   # jour 1 seul
    report = run_backtest(cfg, trades)
    assert report["trades"] == 0


def test_trading_disabled_flag(tmp_path):
    cfg = _cfg(tmp_path)
    pipe = Pipeline(cfg, TradeJournal(cfg.journal_path))
    pipe.trading_enabled = False
    for t in synth_trades():
        pipe.on_trade(t)
    assert TradeJournal.load(cfg.journal_path) == []

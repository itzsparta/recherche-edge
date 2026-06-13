"""Coeur partage backtest/live : chaque Trade traverse, dans cet ordre,
broker (fills) -> rollover journalier -> profil du jour -> bougies/triggers ->
confluence -> risque -> soumission. Le risque est verifie AVANT la soumission."""

import logging
from collections.abc import Iterable
from pathlib import Path

from orderflow_bot.backtest.metrics import compute_metrics
from orderflow_bot.binning import price_of
from orderflow_bot.config import BotConfig
from orderflow_bot.execution.journal import TradeJournal
from orderflow_bot.execution.paper import PaperBroker
from orderflow_bot.features.absorption import AbsorptionDetector
from orderflow_bot.features.aggregator import BarAggregator
from orderflow_bot.features.cvd import CvdTracker
from orderflow_bot.features.volume_profile import VolumeProfile
from orderflow_bot.models import Cancelled, ClosedTrade, Trade
from orderflow_bot.risk.manager import RiskManager
from orderflow_bot.strategy.confluence import ConfluenceEngine, TriggerEngine
from orderflow_bot.strategy.context import (
    DailyLevels, levels_from_profile, market_bias, naked_pocs,
)
from orderflow_bot.strategy.zones import build_zones

log = logging.getLogger(__name__)

_DAY_MS = 86_400_000


class Pipeline:
    def __init__(self, cfg: BotConfig, journal: TradeJournal):
        self.cfg = cfg
        self.journal = journal
        self.trading_enabled = True
        st = cfg.strategy
        self.aggregator = BarAggregator(cfg.bar_minutes * 60_000, cfg.bin_size)
        self.triggers = TriggerEngine(
            absorption=AbsorptionDetector(st.absorption, cfg.tick_size),
            cvd=CvdTracker(),
            imb_cfg=st.imbalance,
        )
        self.confluence = ConfluenceEngine(
            min_rr=cfg.risk.min_rr,
            stop_buffer_ticks=st.stop_buffer_ticks,
            tick_size=cfg.tick_size,
            fees=cfg.fees,
            min_stop_friction_mult=cfg.risk.min_stop_friction_mult,
        )
        self.risk = RiskManager(cfg.risk, cfg.sessions, cfg.equity)
        self.broker = PaperBroker(cfg.risk, st.entry_expire_minutes * 60_000,
                                  cfg.fees, cfg.tick_size)
        # bins des profils decouples des footprint bars : zones larges
        # sans degrader la detection d'imbalances par niveau
        self.profile_bin = cfg.profile_bin_size or cfg.bin_size
        self._day = -1
        self._levels: list[DailyLevels] = []
        self._profiles: list[VolumeProfile] = []
        self._day_profile = VolumeProfile(self.profile_bin)
        self._day_high = float("-inf")
        self._day_low = float("inf")

    def on_trade(self, t: Trade) -> None:
        self._maybe_rollover(t)
        self._handle(self.broker.on_trade(t), t.ts)
        self._day_profile.add(t.price, t.qty)
        self._day_high = max(self._day_high, t.price)
        self._day_low = min(self._day_low, t.price)
        trigs = []
        bar = self.aggregator.on_trade(t)
        if bar is not None:
            trigs += self.triggers.on_bar(bar)
        trigs += self.triggers.on_trade(t)
        for trig in trigs:
            if not self.trading_enabled or not self.risk.can_open(trig.ts):
                continue
            plan = self.confluence.evaluate(trig)
            if plan is None:
                continue
            qty = self.risk.size(plan)
            if qty is None:
                continue
            self.broker.submit(plan, qty, trig.ts)
            self.risk.on_open(trig.ts)
            log.info("ordre soumis: %s", plan)
            break   # une seule position

    def _maybe_rollover(self, t: Trade) -> None:
        day = t.ts // _DAY_MS
        if day == self._day:
            return
        if self._day >= 0 and self._day_profile.total > 0:
            self._handle(self.broker.force_close(t), t.ts)     # flat EOD
            bar = self.aggregator.flush()
            if bar is not None:
                self.triggers.on_bar(bar)
            self._finalize_day()
        self._day = day
        self._day_profile = VolumeProfile(self.profile_bin)
        self._day_high = float("-inf")
        self._day_low = float("inf")
        self.triggers.cvd.reset()

    def _finalize_day(self) -> None:
        st = self.cfg.strategy
        self._levels.append(levels_from_profile(
            self._day, self._day_profile, self._day_high, self._day_low))
        self._levels = self._levels[-st.npoc_lookback_days:]
        self._profiles.append(self._day_profile)
        self._profiles = self._profiles[-st.profile_days:]
        composite = VolumeProfile(self.profile_bin)
        for p in self._profiles:
            composite.merge(p)
        lvn_prices = [price_of(b, self.profile_bin) for b in composite.lvns()]
        prev = self._levels[-1]
        zones = build_zones(prev, naked_pocs(self._levels), lvn_prices,
                            st.zone_margin_pct)
        self.confluence.update_day(zones, market_bias(self._levels))
        log.info("nouveau jour: bias=%s zones=%d", self.confluence.bias.value, len(zones))

    def _handle(self, ev: ClosedTrade | Cancelled | None, ts: int) -> None:
        if ev is None:
            return
        if isinstance(ev, Cancelled):
            self.risk.on_cancel()
            return
        self.risk.on_close(ts, ev.pnl)
        self.journal.record(ev)
        log.info("trade ferme: pnl=%.2f r=%.2f", ev.pnl, ev.r_multiple)


def window_active(ts: int, from_ts: int | None, to_ts: int | None) -> bool:
    """Fenetre [from_ts, to_ts) pendant laquelle les ENTREES sont autorisees."""
    return (from_ts is None or ts >= from_ts) and (to_ts is None or ts < to_ts)


def run_backtest_window(
    cfg: BotConfig,
    trades: Iterable[Trade],
    trade_from_ts: int | None = None,
    trade_to_ts: int | None = None,
) -> dict:
    """Replay du pipeline complet. Les trades AVANT trade_from_ts servent de
    warmup : profils, zones et CVD s'alimentent mais aucune entree n'est prise.
    Une position ouverte dans la fenetre se gere normalement (stop/target/EOD)
    meme apres la fin de la fenetre."""
    # journal purge en debut de run : le rapport ne doit refleter que ce replay
    Path(cfg.journal_path).unlink(missing_ok=True)
    journal = TradeJournal(cfg.journal_path)
    pipe = Pipeline(cfg, journal)
    for t in trades:
        pipe.trading_enabled = window_active(t.ts, trade_from_ts, trade_to_ts)
        pipe.on_trade(t)
    return compute_metrics(TradeJournal.load(cfg.journal_path))


def run_backtest(cfg: BotConfig, trades: Iterable[Trade]) -> dict:
    return run_backtest_window(cfg, trades)

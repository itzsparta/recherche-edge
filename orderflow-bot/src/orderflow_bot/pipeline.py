"""Coeur partage backtest/live, decoupe en deux etages :

- PlanGenerator (signal) : Trade -> plans candidats. Profil, zones, features,
  confluence. Aucune execution ni risque -> etat invariant a l'equity, donc
  parallelisable par blocs de jours (passe 1).
- OrderExecutor (execution) : applique les plans -> broker, risque, journal,
  flat EOD. Sequentiel (l'equity compose).

Pipeline les enchaine tick par tick (live + reference mono-passe). Le backtest
2-passes les separe : generate_plans (passe 1) puis execute_plans (passe 2).
Le risque est verifie AVANT la soumission, comme avant le decoupage."""

import logging
import math
import os
from collections.abc import Callable, Iterable
from concurrent.futures import ProcessPoolExecutor
from itertools import chain
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
from orderflow_bot.models import Cancelled, ClosedTrade, OrderPlan, Trade
from orderflow_bot.risk.manager import RiskManager
from orderflow_bot.strategy.confluence import ConfluenceEngine, TriggerEngine
from orderflow_bot.strategy.context import (
    DailyLevels, levels_from_profile, market_bias, naked_pocs,
)
from orderflow_bot.strategy.zones import build_zones

log = logging.getLogger(__name__)

_DAY_MS = 86_400_000


class PlanGenerator:
    """Etage signal : profil/zones/features/confluence -> plans candidats.
    Pas de broker ni de risque. on_trade renvoie les plans nes a ce tick."""

    def __init__(self, cfg: BotConfig):
        self.cfg = cfg
        st = cfg.strategy
        self.aggregator = BarAggregator(cfg.bar_minutes * 60_000, cfg.bin_size)
        self.triggers = TriggerEngine(
            absorption=AbsorptionDetector(st.absorption, cfg.tick_size),
            cvd=CvdTracker(),
            imb_cfg=st.imbalance,
            continuation=st.signal_mode == "continuation",
        )
        self.confluence = ConfluenceEngine(
            min_rr=cfg.risk.min_rr,
            stop_buffer_ticks=st.stop_buffer_ticks,
            tick_size=cfg.tick_size,
            fees=cfg.fees,
            min_stop_friction_mult=cfg.risk.min_stop_friction_mult,
            mode=st.signal_mode,
        )
        # bins des profils decouples des footprint bars : zones larges
        # sans degrader la detection d'imbalances par niveau
        self.profile_bin = cfg.profile_bin_size or cfg.bin_size
        self._day = -1
        self._levels: list[DailyLevels] = []
        self._profiles: list[VolumeProfile] = []
        self._day_profile = VolumeProfile(self.profile_bin)
        self._day_high = float("-inf")
        self._day_low = float("inf")

    def on_trade(self, t: Trade) -> list[OrderPlan]:
        self._maybe_rollover(t)
        self._day_profile.add(t.price, t.qty)
        self._day_high = max(self._day_high, t.price)
        self._day_low = min(self._day_low, t.price)
        trigs = []
        bar = self.aggregator.on_trade(t)
        if bar is not None:
            trigs += self.triggers.on_bar(bar)
        trigs += self.triggers.on_trade(t)
        plans = []
        for trig in trigs:
            plan = self.confluence.evaluate(trig)
            if plan is not None:
                plans.append(plan)
        return plans

    def _maybe_rollover(self, t: Trade) -> None:
        day = t.ts // _DAY_MS
        if day == self._day:
            return
        if self._day >= 0 and self._day_profile.total > 0:
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
        self.confluence.update_day(zones, market_bias(self._levels),
                                   day_high=prev.high, day_low=prev.low)
        log.info("nouveau jour: bias=%s zones=%d", self.confluence.bias.value, len(zones))


class OrderExecutor:
    """Etage execution : applique des plans candidats -> broker, risque,
    journal, flat EOD au changement de jour. Sequentiel (compounding)."""

    def __init__(self, cfg: BotConfig, journal: TradeJournal):
        self.cfg = cfg
        self.journal = journal
        self.risk = RiskManager(cfg.risk, cfg.sessions, cfg.equity)
        self.broker = PaperBroker(cfg.risk, cfg.strategy.entry_expire_minutes * 60_000,
                                  cfg.fees, cfg.tick_size,
                                  entry_mode=cfg.strategy.entry_mode,
                                  confirm_frac=cfg.strategy.entry_confirm_frac)
        self.trading_enabled = True
        self._day = -1

    def step(self, t: Trade, plans: list[OrderPlan]) -> None:
        self._maybe_eod(t)
        self._handle(self.broker.on_trade(t), t.ts)
        for plan in plans:
            if not self.trading_enabled or not self.risk.can_open(plan.ts):
                continue
            qty = self.risk.size(plan)
            if qty is None:
                continue
            self.broker.submit(plan, qty, plan.ts)
            self.risk.on_open(plan.ts)
            log.info("ordre soumis: %s", plan)
            break   # une seule position

    def _maybe_eod(self, t: Trade) -> None:
        day = t.ts // _DAY_MS
        if day == self._day:
            return
        if self._day >= 0:
            self._handle(self.broker.force_close(t), t.ts)     # flat EOD
        self._day = day

    def _handle(self, ev: ClosedTrade | Cancelled | None, ts: int) -> None:
        if ev is None:
            return
        if isinstance(ev, Cancelled):
            self.risk.on_cancel()
            return
        self.risk.on_close(ts, ev.pnl)
        self.journal.record(ev)
        log.info("trade ferme: pnl=%.2f r=%.2f", ev.pnl, ev.r_multiple)


class Pipeline:
    """Compose les deux etages tick par tick : live et reference mono-passe.
    Expose les attributs des etages que le live et les tests inspectent."""

    def __init__(self, cfg: BotConfig, journal: TradeJournal):
        self.gen = PlanGenerator(cfg)
        self.exe = OrderExecutor(cfg, journal)

    @property
    def confluence(self) -> ConfluenceEngine:
        return self.gen.confluence

    @property
    def aggregator(self) -> BarAggregator:
        return self.gen.aggregator

    @property
    def _day_profile(self) -> VolumeProfile:
        return self.gen._day_profile

    @property
    def trading_enabled(self) -> bool:
        return self.exe.trading_enabled

    @trading_enabled.setter
    def trading_enabled(self, value: bool) -> None:
        self.exe.trading_enabled = value

    def on_trade(self, t: Trade) -> None:
        self.exe.step(t, self.gen.on_trade(t))


def window_active(ts: int, from_ts: int | None, to_ts: int | None) -> bool:
    """Fenetre [from_ts, to_ts) pendant laquelle les ENTREES sont autorisees."""
    return (from_ts is None or ts >= from_ts) and (to_ts is None or ts < to_ts)


def run_backtest_window(
    cfg: BotConfig,
    trades: Iterable[Trade],
    trade_from_ts: int | None = None,
    trade_to_ts: int | None = None,
) -> dict:
    """Replay mono-passe du pipeline complet (reference). Les trades AVANT
    trade_from_ts servent de warmup : profils, zones et CVD s'alimentent mais
    aucune entree n'est prise. Une position ouverte dans la fenetre se gere
    normalement (stop/target/EOD) meme apres la fin de la fenetre."""
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


def generate_plans(
    cfg: BotConfig,
    trades: Iterable[Trade],
    trade_from_ts: int | None = None,
    trade_to_ts: int | None = None,
) -> list[OrderPlan]:
    """Passe 1 : signal seul -> plans candidats ordonnes par ts. Les plans
    hors fenetre [from, to) sont du warmup et ne sont pas collectes (mais
    alimentent profil/zones/CVD). Invariant a l'execution et a l'equity."""
    gen = PlanGenerator(cfg)
    out: list[OrderPlan] = []
    for t in trades:
        plans = gen.on_trade(t)
        if plans and window_active(t.ts, trade_from_ts, trade_to_ts):
            out.extend(plans)
    return out


def _day_blocks(
    start_ms: int, end_ms: int, n_blocks: int, warmup_ms: int
) -> list[tuple[int, int, int]]:
    """Decoupe [start, end) en <= n_blocks blocs de jours ~egaux. Chaque bloc
    (read_from, block_start, block_end) : read_from = block_start - warmup pour
    rejouer l'historique (profils/zones/nPOC/bias) avant de collecter les plans.
    Le dernier bloc absorbe le reste."""
    span_days = math.ceil((end_ms - start_ms) / _DAY_MS)
    base = max(1, math.ceil(span_days / n_blocks))
    out: list[tuple[int, int, int]] = []
    i = 0
    while True:
        b_start = start_ms + i * base * _DAY_MS
        if b_start >= end_ms:
            break
        b_end = min(end_ms, start_ms + (i + 1) * base * _DAY_MS)
        out.append((b_start - warmup_ms, b_start, b_end))
        i += 1
    return out


def _warmup_ms(cfg: BotConfig, warmup_days: int | None) -> int:
    days = warmup_days if warmup_days is not None else cfg.strategy.npoc_lookback_days
    return days * _DAY_MS


def generate_plans_blocked(
    cfg: BotConfig,
    start_ms: int,
    end_ms: int,
    reader: Callable[[int, int], Iterable[Trade]],
    n_blocks: int,
    warmup_days: int | None = None,
) -> list[OrderPlan]:
    """Passe 1 sequentielle decoupee en blocs (reference testable du parallele).
    `reader(from_ms, to_ms)` fournit les trades d'un intervalle. Identique a
    generate_plans global car chaque bloc rejoue warmup_days en amont (le warmup
    capture exactement ce que la strategie regarde : profile_days et nPOC borne
    a npoc_lookback_days)."""
    blocks = _day_blocks(start_ms, end_ms, n_blocks, _warmup_ms(cfg, warmup_days))
    out: list[OrderPlan] = []
    for read_from, b_start, b_end in blocks:
        out.extend(generate_plans(cfg, reader(max(0, read_from), b_end), b_start, b_end))
    return sorted(out, key=lambda p: p.ts)


def _block_worker(args: tuple[BotConfig, int, int, int]) -> list[OrderPlan]:
    cfg, read_from, b_start, b_end = args
    from orderflow_bot.ingestion.reader import read_trades
    trades = read_trades(cfg.market_data_dir, cfg.symbol,
                         start_ms=max(0, read_from), end_ms=b_end)
    return generate_plans(cfg, trades, b_start, b_end)


def generate_plans_parallel(
    cfg: BotConfig,
    start_ms: int,
    end_ms: int,
    n_blocks: int | None = None,
    warmup_days: int | None = None,
) -> list[OrderPlan]:
    """Passe 1 parallele : un process par bloc de jours (ProcessPoolExecutor),
    chacun lit ses Parquet et rejoue son warmup. Contourne le GIL -> exploite
    les coeurs. Resultat identique a generate_plans global (memes zones)."""
    n_blocks = n_blocks or os.cpu_count() or 4
    blocks = _day_blocks(start_ms, end_ms, n_blocks, _warmup_ms(cfg, warmup_days))
    args = [(cfg, rf, bs, be) for rf, bs, be in blocks]
    with ProcessPoolExecutor() as ex:
        results = ex.map(_block_worker, args)
    return sorted(chain.from_iterable(results), key=lambda p: p.ts)


def execute_plans(
    cfg: BotConfig, plans: list[OrderPlan], trades: Iterable[Trade]
) -> dict:
    """Passe 2 : rejoue les ticks (sans recalcul de signal) et applique les
    plans candidats deja generes -> broker, risque, journal. Sequentiel donc
    l'equity compose exactement. Un plan est soumis au premier tick dont le ts
    atteint celui du plan, apres le traitement broker de ce tick (le tick
    declencheur ne remplit pas l'ordre, comme en mono-passe)."""
    Path(cfg.journal_path).unlink(missing_ok=True)
    journal = TradeJournal(cfg.journal_path)
    exe = OrderExecutor(cfg, journal)
    pending = sorted(plans, key=lambda p: p.ts)
    i, n = 0, len(pending)
    for t in trades:
        due = []
        while i < n and pending[i].ts <= t.ts:
            due.append(pending[i])
            i += 1
        exe.step(t, due)
    return compute_metrics(TradeJournal.load(cfg.journal_path))


def simulate_isolated(
    cfg: BotConfig, plans: list[OrderPlan], trades: Iterable[Trade]
) -> list[ClosedTrade]:
    """Outcome intrinseque de chaque plan candidat, pris isolement : un broker
    independant par plan, sans contrainte de slot ni de risque, qty=1 (r/mfe/mae
    invariants en qty). Meme mecanique d'exit/EOD que l'execution reelle, meme
    ordre par tick (EOD -> on_trade -> submit), donc un plan seul donne le meme
    label qu'en portefeuille. Renvoie un ClosedTrade par plan rempli ; les
    ordres expires sans fill sont omis. Sert a etiqueter les candidats (morts-nes
    vs gagnants) pour le filtre d'entree, sans re-streamer par plan."""
    pending = sorted(plans, key=lambda p: p.ts)
    i, n = 0, len(pending)
    expire = cfg.strategy.entry_expire_minutes * 60_000
    active: list[PaperBroker] = []
    out: list[ClosedTrade] = []
    day = -1
    for t in trades:
        d = t.ts // _DAY_MS
        if d != day:
            if day >= 0:                       # flat EOD : ferme/annule tout l'actif
                for b in active:
                    ct = b.force_close(t)
                    if ct is not None:
                        out.append(ct)
                active = []
            day = d
        still: list[PaperBroker] = []
        for b in active:
            ev = b.on_trade(t)
            if isinstance(ev, ClosedTrade):
                out.append(ev)
            elif ev is None:                   # toujours pending/ouvert -> garder
                still.append(b)
            # Cancelled (expire sans fill) -> abandonne
        active = still
        while i < n and pending[i].ts <= t.ts:
            b = PaperBroker(cfg.risk, expire, cfg.fees, cfg.tick_size,
                            entry_mode=cfg.strategy.entry_mode,
                            confirm_frac=cfg.strategy.entry_confirm_frac)
            b.submit(pending[i], 1.0, pending[i].ts)
            active.append(b)
            i += 1
    return out


def _iso_sort(rows: list[ClosedTrade]) -> list[ClosedTrade]:
    return sorted(rows, key=lambda ct: (ct.opened_ts, ct.closed_ts))


def simulate_isolated_blocked(
    cfg: BotConfig,
    start_ms: int,
    end_ms: int,
    plans: list[OrderPlan],
    reader: Callable[[int, int], Iterable[Trade]],
    n_blocks: int,
    tail_days: int = 1,
) -> list[ClosedTrade]:
    """simulate_isolated decoupe par blocs de jours (reference testable du
    parallele). Sans warmup (les outcomes ne dependent pas de l'historique),
    mais chaque bloc lit +tail_days en queue : une position ouverte le dernier
    jour du bloc se ferme a l'EOD = premier tick du lendemain, qui doit etre
    present. La queue ne soumet rien (les plans du bloc ont tous ts < b_end)."""
    tail = tail_days * _DAY_MS
    out: list[ClosedTrade] = []
    for _, b_start, b_end in _day_blocks(start_ms, end_ms, n_blocks, 0):
        bp = [p for p in plans if b_start <= p.ts < b_end]
        out.extend(simulate_isolated(cfg, bp, reader(b_start, b_end + tail)))
    return _iso_sort(out)


def _isolated_block_worker(
    args: tuple[BotConfig, int, int, int, list[OrderPlan]]
) -> list[ClosedTrade]:
    cfg, b_start, b_end, tail, block_plans = args
    from orderflow_bot.ingestion.reader import read_trades
    ticks = read_trades(cfg.market_data_dir, cfg.symbol,
                        start_ms=b_start, end_ms=b_end + tail)
    return simulate_isolated(cfg, block_plans, ticks)


def simulate_isolated_parallel(
    cfg: BotConfig,
    start_ms: int,
    end_ms: int,
    plans: list[OrderPlan],
    n_blocks: int | None = None,
    tail_days: int = 1,
) -> list[ClosedTrade]:
    """simulate_isolated parallele : un process par bloc de jours, chacun relit
    ses Parquet (+tail) et etiquette ses plans. Pas de warmup -> speedup ~lineaire
    (vs la passe 1 plafonnee par le warmup). Identique a simulate_isolated."""
    n_blocks = n_blocks or os.cpu_count() or 4
    tail = tail_days * _DAY_MS
    args = [(cfg, b_start, b_end, tail, [p for p in plans if b_start <= p.ts < b_end])
            for _, b_start, b_end in _day_blocks(start_ms, end_ms, n_blocks, 0)]
    with ProcessPoolExecutor() as ex:
        results = ex.map(_isolated_block_worker, args)
    return _iso_sort(chain.from_iterable(results))

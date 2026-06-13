import statistics
from collections import deque
from dataclasses import dataclass

from orderflow_bot.config import AbsorptionCfg
from orderflow_bot.models import Trade


@dataclass(frozen=True, slots=True)
class Absorption:
    ts: int
    side: int     # +1 : ventes absorbees (bullish) ; -1 : achats absorbes (bearish)
    price: float


class AbsorptionDetector:
    """Fenetre glissante de window_ms. Absorption si, simultanement :
    volume >= vol_factor x mediane des fenetres baseline (tumbling),
    range prix <= max_range_ticks, delta directionnel >= min_delta_frac x volume,
    et le prix ne progresse plus dans le sens du delta."""

    def __init__(self, cfg: AbsorptionCfg, tick_size: float):
        self.cfg = cfg
        self.tick = tick_size
        self._win: deque[Trade] = deque()
        self._baseline: deque[float] = deque(maxlen=cfg.baseline_windows)
        self._slot: int | None = None
        self._slot_vol = 0.0
        # sommes glissantes maintenues en O(1) (append/popleft/clear) au lieu
        # de re-sommer toute la fenetre a chaque tick : ~90 % du temps pipeline
        self._win_vol = 0.0                 # sum(x.qty for x in _win)
        self._win_delta = 0.0               # sum(x.qty * x.aggressor for x in _win)
        self._med: float | None = None      # mediane baseline, recalculee au slot

    def _clear_window(self) -> None:
        self._win.clear()
        self._win_vol = 0.0
        self._win_delta = 0.0

    def on_trade(self, t: Trade) -> Absorption | None:
        c = self.cfg
        slot = t.ts // c.window_ms
        if self._slot is None:
            self._slot = slot
        while self._slot < slot:
            self._baseline.append(self._slot_vol)
            self._slot_vol = 0.0
            self._slot += 1
            self._med = None                # la baseline a change -> cache invalide
        self._slot_vol += t.qty

        self._win.append(t)
        self._win_vol += t.qty
        self._win_delta += t.qty * t.aggressor
        cutoff = t.ts - c.window_ms
        while self._win and self._win[0].ts < cutoff:
            old = self._win.popleft()
            self._win_vol -= old.qty
            self._win_delta -= old.qty * old.aggressor

        if len(self._baseline) < 3:
            return None
        if self._med is None:
            self._med = statistics.median(self._baseline)
        med = self._med
        vol = self._win_vol
        if med <= 0 or vol < c.vol_factor * med:
            return None
        prices = [x.price for x in self._win]
        if max(prices) - min(prices) > c.max_range_ticks * self.tick:
            return None
        delta = self._win_delta
        first, last = self._win[0].price, self._win[-1].price
        if delta <= -c.min_delta_frac * vol and last >= first:
            self._clear_window()
            return Absorption(ts=t.ts, side=1, price=t.price)
        if delta >= c.min_delta_frac * vol and last <= first:
            self._clear_window()
            return Absorption(ts=t.ts, side=-1, price=t.price)
        return None

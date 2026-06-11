import math

from orderflow_bot.config import RiskCfg, SessionCfg
from orderflow_bot.models import OrderPlan

_DAY_MS = 86_400_000


def _mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


class RiskManager:
    """Garde-fous codes en dur, verifies AVANT toute soumission :
    risque fixe par trade, stop journalier, pertes consecutives,
    sessions UTC, position unique, cap trades/jour."""

    def __init__(self, cfg: RiskCfg, sessions: list[SessionCfg], equity: float):
        self.cfg = cfg
        self._sessions = [(_mins(s.start), _mins(s.end)) for s in sessions]
        self.equity = equity
        self.position_open = False
        self._day = -1
        self._day_start_equity = equity
        self._daily_pnl = 0.0
        self._streak = 0
        self._trades_today = 0

    def _roll(self, ts: int) -> None:
        day = ts // _DAY_MS
        if day != self._day:
            self._day = day
            self._day_start_equity = self.equity
            self._daily_pnl = 0.0
            self._streak = 0
            self._trades_today = 0

    def in_session(self, ts: int) -> bool:
        mins = (ts // 60_000) % 1440
        return any(a <= mins < b for a, b in self._sessions)

    def can_open(self, ts: int) -> bool:
        self._roll(ts)
        c = self.cfg
        return (
            not self.position_open
            and self.in_session(ts)
            and self._trades_today < c.max_trades_per_day
            and self._streak < c.max_consecutive_losses
            and self._daily_pnl > -c.daily_stop_pct * self._day_start_equity
        )

    def size(self, plan: OrderPlan) -> float | None:
        risk_per_unit = (plan.entry - plan.stop) * plan.side
        if risk_per_unit <= 0:
            return None
        qty = self.equity * self.cfg.risk_pct / risk_per_unit
        qty = math.floor(qty / self.cfg.qty_step) * self.cfg.qty_step
        qty = round(qty, 10)
        return qty if qty >= self.cfg.qty_step else None

    def on_open(self, ts: int) -> None:
        self._roll(ts)
        self.position_open = True
        self._trades_today += 1

    def on_cancel(self) -> None:
        """Entree expiree sans fill : le slot du jour est rendu."""
        self.position_open = False
        self._trades_today = max(0, self._trades_today - 1)

    def on_close(self, ts: int, pnl: float) -> None:
        self._roll(ts)
        self.position_open = False
        self.equity += pnl
        self._daily_pnl += pnl
        self._streak = self._streak + 1 if pnl < 0 else 0

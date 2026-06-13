from dataclasses import dataclass, field

from orderflow_bot.config import FeesCfg, RiskCfg
from orderflow_bot.models import Cancelled, ClosedTrade, Fill, OrderPlan, Trade


@dataclass(slots=True)
class _Position:
    plan: OrderPlan
    qty: float
    submit_ts: int
    state: str = "pending"          # pending | open
    opened_ts: int = 0
    remaining: float = 0.0
    stop: float = 0.0               # stop courant (deplace a BE apres partiel)
    partial_done: bool = False
    fills: list[Fill] = field(default_factory=list)
    best: float = 0.0               # excursion max favorable depuis l'entry (points)
    worst: float = 0.0              # excursion max defavorable (points, negatif)
    entry_px: float = 0.0           # prix de fill reel (= plan.entry en limit, decale en stop)
    confirm_dist: float = 0.0       # stop : distance de confirmation requise (points)
    entry_taker: bool = False       # stop : entree marche -> taker (vs maker en limit)


class PaperBroker:
    """Simulateur de fills conservateur : tout franchissement de niveau doit etre
    STRICT (un trade imprime au-dela). Le stop accepte les gaps au pire prix.
    Au plus une position. Verifications dans l'ordre du pire cas : stop d'abord."""

    def __init__(self, cfg: RiskCfg, expire_ms: int, fees: FeesCfg, tick_size: float,
                 entry_mode: str = "limit", confirm_frac: float = 0.0):
        self.cfg = cfg
        self.expire_ms = expire_ms
        self.fees = fees
        self.tick_size = tick_size
        self.entry_mode = entry_mode
        self.confirm_frac = confirm_frac
        self._pos: _Position | None = None

    @property
    def active(self) -> bool:
        return self._pos is not None

    @property
    def opened(self) -> bool:
        # rempli (vs pending non rempli ou aucune position)
        return self._pos is not None and self._pos.state == "open"

    def submit(self, plan: OrderPlan, qty: float, ts: int) -> None:
        assert self._pos is None, "une seule position a la fois"
        confirm = self.confirm_frac * abs(plan.entry - plan.stop)
        self._pos = _Position(plan=plan, qty=qty, submit_ts=ts, stop=plan.stop,
                              entry_px=plan.entry, confirm_dist=confirm)

    def on_trade(self, t: Trade) -> ClosedTrade | Cancelled | None:
        p = self._pos
        if p is None:
            return None
        s = p.plan.side
        if p.state == "pending":
            if t.ts - p.submit_ts > self.expire_ms:
                self._pos = None
                return Cancelled(ts=t.ts)
            if self.entry_mode == "stop":
                # confirmation : le prix doit avancer confirm_dist DANS le sens du
                # trade. Fill marche au prix courant + slippage (taker).
                if (t.price - p.plan.entry) * s > p.confirm_dist:
                    p.entry_px = t.price + s * self._slip()
                    p.entry_taker = True
                    self._open(p, t.ts)
            elif (p.plan.entry - t.price) * s > 0:             # limit : franchissement strict
                p.entry_px = p.plan.entry
                self._open(p, t.ts)
            return None

        # position ouverte : excursion d'abord (le tick declencheur en fait partie)
        fav = (t.price - p.entry_px) * s
        p.best = max(p.best, fav)
        p.worst = min(p.worst, fav)
        risk0 = (p.entry_px - p.plan.stop) * s
        # trailing apres le partiel : stop a trail_r derriere le plus-haut, plancher BE.
        # best inclut ce tick mais reste >= trail au-dessus du prix -> pas d'auto-declenchement.
        if p.partial_done and self.cfg.trail_r is not None:
            trail = max(0.0, p.best - self.cfg.trail_r * risk0)
            cand = p.entry_px + s * trail
            p.stop = max(p.stop, cand) if s == 1 else min(p.stop, cand)
        # pire cas d'abord
        if (t.price - p.stop) * s <= 0:
            worst = min(p.stop, t.price) if s == 1 else max(p.stop, t.price)
            return self._close(t.ts, worst - s * self._slip(), "stop")
        partial_level = p.entry_px + s * self.cfg.partial_at_r * risk0
        if not p.partial_done and (t.price - partial_level) * s > 0:
            part_qty = round(p.qty * self.cfg.partial_fraction, 10)
            p.fills.append(Fill(ts=t.ts, price=partial_level, qty=part_qty, kind="partial"))
            p.remaining = round(p.remaining - part_qty, 10)
            p.partial_done = True
            if self.cfg.move_to_be:
                p.stop = p.entry_px                            # breakeven
            return None
        if (t.price - p.plan.target) * s > 0:
            return self._close(t.ts, p.plan.target, "target")
        return None

    def _open(self, p: _Position, ts: int) -> None:
        p.state = "open"
        p.opened_ts = ts
        p.remaining = p.qty
        p.fills.append(Fill(ts=ts, price=p.entry_px, qty=p.qty, kind="entry"))

    def force_close(self, t: Trade) -> ClosedTrade | None:
        """Flat EOD : ferme le restant au prix courant avec slippage."""
        p = self._pos
        if p is None:
            return None
        if p.state == "pending":
            self._pos = None
            return None
        fav = (t.price - p.entry_px) * p.plan.side
        p.best = max(p.best, fav)
        p.worst = min(p.worst, fav)
        return self._close(t.ts, t.price - p.plan.side * self._slip(), "eod")

    def _slip(self) -> float:
        return self.fees.slippage_ticks * self.tick_size

    def _fee_rate(self, kind: str) -> float:
        # limit (entry/partial/target) = maker ; market (stop/eod) = taker
        return self.fees.taker_pct if kind in ("stop", "eod") else self.fees.maker_pct

    def _entry_or_fee_rate(self, f: Fill, p: _Position) -> float:
        # entree marche (stop mode) -> taker ; sinon regle standard
        if f.kind == "entry" and p.entry_taker:
            return self.fees.taker_pct
        return self._fee_rate(f.kind)

    def _close(self, ts: int, price: float, kind: str) -> ClosedTrade:
        p = self._pos
        assert p is not None
        p.fills.append(Fill(ts=ts, price=price, qty=p.remaining, kind=kind))
        s = p.plan.side
        entry = p.entry_px
        gross = sum((f.price - entry) * s * f.qty for f in p.fills if f.kind != "entry")
        # somme sur TOUS les fills ; entry marche (stop mode) = taker, sinon maker
        fees = sum(f.price * f.qty * self._entry_or_fee_rate(f, p) for f in p.fills)
        pnl = gross - fees
        risk0 = (entry - p.plan.stop) * s
        r = pnl / (risk0 * p.qty) if risk0 > 0 and p.qty > 0 else 0.0
        mfe = p.best / risk0 if risk0 > 0 else 0.0
        mae = p.worst / risk0 if risk0 > 0 else 0.0
        ct = ClosedTrade(plan=p.plan, qty=p.qty, fills=p.fills, pnl=round(pnl, 10),
                         r_multiple=round(r, 10), opened_ts=p.opened_ts, closed_ts=ts,
                         fees=round(fees, 10),
                         mfe_r=round(mfe, 10), mae_r=round(mae, 10))
        self._pos = None
        return ct

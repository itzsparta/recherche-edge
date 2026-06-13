from dataclasses import dataclass

from orderflow_bot.config import FeesCfg, ImbalanceCfg
from orderflow_bot.features.absorption import AbsorptionDetector
from orderflow_bot.features.cvd import CvdTracker
from orderflow_bot.features.imbalance import stacked_imbalances
from orderflow_bot.models import FootprintBar, OrderPlan, Trade
from orderflow_bot.strategy.context import Bias
from orderflow_bot.strategy.zones import Zone, zone_at


@dataclass(frozen=True, slots=True)
class Trigger:
    ts: int
    side: int
    kind: str     # absorption | cvd_divergence | stacked_imbalance
    price: float


class TriggerEngine:
    """Couche 3 : transforme les sorties des detecteurs en Triggers dates."""

    def __init__(self, absorption: AbsorptionDetector, cvd: CvdTracker,
                 imb_cfg: ImbalanceCfg):
        self.absorption = absorption
        self.cvd = cvd
        self.imb_cfg = imb_cfg

    def on_trade(self, t: Trade) -> list[Trigger]:
        a = self.absorption.on_trade(t)
        if a is None:
            return []
        return [Trigger(ts=a.ts, side=a.side, kind="absorption", price=a.price)]

    def on_bar(self, bar: FootprintBar) -> list[Trigger]:
        self.cvd.on_bar(bar)
        out: list[Trigger] = []
        if self.cvd.bullish_divergence():
            out.append(Trigger(bar.close_ts, 1, "cvd_divergence", bar.close))
        if self.cvd.bearish_divergence():
            out.append(Trigger(bar.close_ts, -1, "cvd_divergence", bar.close))
        st = stacked_imbalances(bar, self.imb_cfg.ratio, self.imb_cfg.min_stack)
        # imbalances empilees CONTRE le mouvement de la bougie = renversement
        if st["buy"] and bar.close < bar.open:
            out.append(Trigger(bar.close_ts, 1, "stacked_imbalance", bar.close))
        if st["sell"] and bar.close > bar.open:
            out.append(Trigger(bar.close_ts, -1, "stacked_imbalance", bar.close))
        return out


class ConfluenceEngine:
    """Confluence des 3 couches : bias (contexte) x zone x trigger.
    Emet un OrderPlan complet (entry limit, stop structurel, target, R:R>=min)."""

    def __init__(self, min_rr: float, stop_buffer_ticks: int, tick_size: float,
                 fees: FeesCfg | None = None, min_stop_friction_mult: float = 0.0):
        self.min_rr = min_rr
        self.buffer = stop_buffer_ticks * tick_size
        self.tick_size = tick_size
        self.fees = fees
        self.friction_mult = min_stop_friction_mult
        self.zones: list[Zone] = []
        self.bias = Bias.BOTH

    def _friction(self, entry: float) -> float:
        """Cout incompressible par unite : frais maker (entree limit) + taker
        (sortie stop, pire cas) + slippage du fill market."""
        assert self.fees is not None
        return (entry * (self.fees.maker_pct + self.fees.taker_pct)
                + self.fees.slippage_ticks * self.tick_size)

    def update_day(self, zones: list[Zone], bias: Bias) -> None:
        self.zones = zones
        self.bias = bias

    def evaluate(self, trig: Trigger) -> OrderPlan | None:
        z = zone_at(self.zones, trig.price)
        if z is None:
            return None
        if z.side not in (0, trig.side):
            return None
        if self.bias is Bias.LONG and trig.side != 1:
            return None
        if self.bias is Bias.SHORT and trig.side != -1:
            return None
        entry = trig.price
        stop = z.lo - self.buffer if trig.side == 1 else z.hi + self.buffer
        risk = (entry - stop) * trig.side
        reward = (z.target - entry) * trig.side
        if risk <= 0 or reward / risk < self.min_rr:
            return None
        # stop trop serre vs frais+slippage : trade mathematiquement perdant
        # (la friction fixe vaudrait plusieurs R), et sizing inverse au risque
        # -> position geante. Rejet a la source.
        if (self.fees is not None and self.friction_mult > 0
                and risk < self.friction_mult * self._friction(entry)):
            return None
        return OrderPlan(
            ts=trig.ts, side=trig.side, entry=entry, stop=stop, target=z.target,
            meta={"zone": z.kind, "trigger": trig.kind, "bias": self.bias.value},
        )

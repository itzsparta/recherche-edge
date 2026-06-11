from dataclasses import dataclass

from orderflow_bot.config import ImbalanceCfg
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

    def __init__(self, min_rr: float, stop_buffer_ticks: int, tick_size: float):
        self.min_rr = min_rr
        self.buffer = stop_buffer_ticks * tick_size
        self.zones: list[Zone] = []
        self.bias = Bias.BOTH

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
        return OrderPlan(
            ts=trig.ts, side=trig.side, entry=entry, stop=stop, target=z.target,
            meta={"zone": z.kind, "trigger": trig.kind, "bias": self.bias.value},
        )

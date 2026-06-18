from dataclasses import dataclass, field

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
    features: dict = field(default_factory=dict)   # force quantitative -> meta du plan


def _stack_features(vol: dict[int, float], bins: list[int]) -> dict:
    """Force d'une pile d'imbalances : profondeur (bins consecutifs) et volume
    agressif total qui la soutient. Plus profond/lourd = niveau plus defendu."""
    return {"stack_depth": len(bins),
            "stack_vol": round(sum(vol.get(b, 0.0) for b in bins), 8)}


class TriggerEngine:
    """Couche 3 : transforme les sorties des detecteurs en Triggers dates."""

    def __init__(self, absorption: AbsorptionDetector, cvd: CvdTracker,
                 imb_cfg: ImbalanceCfg, continuation: bool = False):
        self.absorption = absorption
        self.cvd = cvd
        self.imb_cfg = imb_cfg
        self.continuation = continuation

    def on_trade(self, t: Trade) -> list[Trigger]:
        # absorption = signal de renversement -> hors-sujet en continuation
        if self.continuation:
            return []
        a = self.absorption.on_trade(t)
        if a is None:
            return []
        return [Trigger(ts=a.ts, side=a.side, kind="absorption", price=a.price)]

    def on_bar(self, bar: FootprintBar) -> list[Trigger]:
        self.cvd.on_bar(bar)
        st = stacked_imbalances(bar, self.imb_cfg.ratio, self.imb_cfg.min_stack)
        if self.continuation:
            # momentum : pile DANS le sens de la bougie = cassure qui s'etend
            out: list[Trigger] = []
            if st["buy"] and bar.close > bar.open:
                out.append(Trigger(bar.close_ts, 1, "stacked_imbalance", bar.close,
                                   _stack_features(bar.ask_vol, st["buy"])))
            if st["sell"] and bar.close < bar.open:
                out.append(Trigger(bar.close_ts, -1, "stacked_imbalance", bar.close,
                                   _stack_features(bar.bid_vol, st["sell"])))
            return out
        out = []
        if self.cvd.bullish_divergence():
            out.append(Trigger(bar.close_ts, 1, "cvd_divergence", bar.close))
        if self.cvd.bearish_divergence():
            out.append(Trigger(bar.close_ts, -1, "cvd_divergence", bar.close))
        # imbalances empilees CONTRE le mouvement de la bougie = renversement
        if st["buy"] and bar.close < bar.open:
            out.append(Trigger(bar.close_ts, 1, "stacked_imbalance", bar.close,
                               _stack_features(bar.ask_vol, st["buy"])))
        if st["sell"] and bar.close > bar.open:
            out.append(Trigger(bar.close_ts, -1, "stacked_imbalance", bar.close,
                               _stack_features(bar.bid_vol, st["sell"])))
        return out


class ConfluenceEngine:
    """Confluence des 3 couches : bias (contexte) x zone x trigger.
    Emet un OrderPlan complet (entry limit, stop structurel, target, R:R>=min)."""

    def __init__(self, min_rr: float, stop_buffer_ticks: int, tick_size: float,
                 fees: FeesCfg | None = None, min_stop_friction_mult: float = 0.0,
                 mode: str = "reversal"):
        self.min_rr = min_rr
        self.buffer = stop_buffer_ticks * tick_size
        self.tick_size = tick_size
        self.fees = fees
        self.friction_mult = min_stop_friction_mult
        self.mode = mode
        self.zones: list[Zone] = []
        self.bias = Bias.BOTH
        self.day_high: float | None = None
        self.day_low: float | None = None
        self.struct_levels: list[float] = []
        self.va_width: float | None = None

    def _friction(self, entry: float) -> float:
        """Cout incompressible par unite : frais maker (entree limit) + taker
        (sortie stop, pire cas) + slippage du fill market."""
        assert self.fees is not None
        return (entry * (self.fees.maker_pct + self.fees.taker_pct)
                + self.fees.slippage_ticks * self.tick_size)

    def update_day(self, zones: list[Zone], bias: Bias,
                   day_high: float | None = None, day_low: float | None = None,
                   struct_levels: list[float] | None = None,
                   va_width: float | None = None) -> None:
        self.zones = zones
        self.bias = bias
        self.day_high = day_high
        self.day_low = day_low
        self.struct_levels = struct_levels or []
        self.va_width = va_width

    def _continuation_target(self, entry: float, side: int) -> float | None:
        """Cible swing du breakout : niveau structurel le plus proche AU-DELA de
        l'entree dans le sens du trade ; fallback = mesure de range (entry +
        side*largeur_VA). None si aucun des deux -> pas de plan."""
        beyond = [lv for lv in self.struct_levels if (lv - entry) * side > 0]
        if beyond:
            return min(beyond, key=lambda lv: (lv - entry) * side)
        if self.va_width and self.va_width > 0:
            return entry + side * self.va_width
        return None

    def evaluate(self, trig: Trigger) -> OrderPlan | None:
        z = zone_at(self.zones, trig.price)
        if z is None:
            return None
        if self.mode == "continuation":
            # cassure vers l'EXTERIEUR de la value : VAL casse en bas (short),
            # VAH casse en haut (long) ; nPOC/LVN selon le trigger. Cible =
            # extreme du range, stop = reclaim (formule stop identique au fade).
            eff_side = {"val": -1, "vah": 1}.get(z.kind, 0)
            target = self._continuation_target(trig.price, trig.side)
        else:
            eff_side = z.side
            target = z.target
        if eff_side not in (0, trig.side) or target is None:
            return None
        if self.bias is Bias.LONG and trig.side != 1:
            return None
        if self.bias is Bias.SHORT and trig.side != -1:
            return None
        entry = trig.price
        stop = z.lo - self.buffer if trig.side == 1 else z.hi + self.buffer
        risk = (entry - stop) * trig.side
        reward = (target - entry) * trig.side
        if risk <= 0 or reward / risk < self.min_rr:
            return None
        # stop trop serre vs frais+slippage : trade mathematiquement perdant
        # (la friction fixe vaudrait plusieurs R), et sizing inverse au risque
        # -> position geante. Rejet a la source.
        if (self.fees is not None and self.friction_mult > 0
                and risk < self.friction_mult * self._friction(entry)):
            return None
        meta = {**trig.features, "zone": z.kind, "trigger": trig.kind,
                "bias": self.bias.value}
        if self.mode == "continuation":
            meta["mode"] = "continuation"
        return OrderPlan(ts=trig.ts, side=trig.side, entry=entry, stop=stop,
                         target=target, meta=meta)

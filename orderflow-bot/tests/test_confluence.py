from orderflow_bot.config import ImbalanceCfg
from orderflow_bot.strategy.confluence import ConfluenceEngine, Trigger
from orderflow_bot.strategy.context import Bias, DailyLevels
from orderflow_bot.strategy.zones import build_zones

PREV = DailyLevels(day=1, poc=100.0, vah=103.0, val=97.0, high=105.0, low=95.0)


def _engine(bias: Bias = Bias.BOTH) -> ConfluenceEngine:
    eng = ConfluenceEngine(min_rr=2.0, stop_buffer_ticks=10, tick_size=0.1)
    zones = build_zones(PREV, npocs=[], lvn_prices=[], margin_pct=0.002)
    eng.update_day(zones, bias)
    return eng


def test_long_in_val_zone():
    eng = _engine()
    plan = eng.evaluate(Trigger(ts=1, side=1, kind="absorption", price=97.1))
    assert plan is not None
    assert plan.side == 1
    assert plan.entry == 97.1
    assert plan.stop == (97.0 - 0.2) - 1.0      # zone.lo - buffer 10 ticks
    assert plan.target == 100.0
    assert plan.meta == {"zone": "val", "trigger": "absorption", "bias": "both"}


def test_rejects_outside_zone():
    eng = _engine()
    assert eng.evaluate(Trigger(ts=1, side=1, kind="absorption", price=99.0)) is None


def test_rejects_wrong_zone_side():
    eng = _engine()
    # trigger short dans la zone VAL (long only) -> rejet
    assert eng.evaluate(Trigger(ts=1, side=-1, kind="absorption", price=97.1)) is None


def test_rejects_against_bias():
    eng = _engine(Bias.SHORT)
    assert eng.evaluate(Trigger(ts=1, side=1, kind="absorption", price=97.1)) is None


def test_rejects_poor_rr():
    # entry colle au target : reward ~1.4 / risk ~1.3 -> RR < 2 (97.1 est bien DANS la zone)
    eng = ConfluenceEngine(min_rr=2.0, stop_buffer_ticks=10, tick_size=0.1)
    near = DailyLevels(day=1, poc=98.5, vah=103.0, val=97.0, high=105.0, low=95.0)
    eng.update_day(build_zones(near, [], [], 0.002), Bias.BOTH)
    assert eng.evaluate(Trigger(ts=1, side=1, kind="absorption", price=97.1)) is None


def test_rejects_stop_thinner_than_friction_floor():
    # friction/unite = 97.1x(0.0002+0.0005) + 2 ticks x 0.1 ~ 0.268
    # seuil 3x ~ 0.80 ; buffer 1 tick -> distance stop 0.4 < 0.80 -> rejet
    # (RR brut = 2.9/0.4 = 7.25 > 2 : sans le filtre friction, le plan passerait)
    from orderflow_bot.config import FeesCfg
    eng = ConfluenceEngine(min_rr=2.0, stop_buffer_ticks=1, tick_size=0.1,
                           fees=FeesCfg(), min_stop_friction_mult=3.0)
    eng.update_day(build_zones(PREV, [], [], 0.002), Bias.BOTH)
    assert eng.evaluate(Trigger(ts=1, side=1, kind="absorption", price=97.1)) is None


def test_accepts_stop_wider_than_friction_floor():
    # buffer 10 ticks -> distance stop 1.3 > seuil 0.80 -> plan emis
    from orderflow_bot.config import FeesCfg
    eng = ConfluenceEngine(min_rr=2.0, stop_buffer_ticks=10, tick_size=0.1,
                           fees=FeesCfg(), min_stop_friction_mult=3.0)
    eng.update_day(build_zones(PREV, [], [], 0.002), Bias.BOTH)
    plan = eng.evaluate(Trigger(ts=1, side=1, kind="absorption", price=97.1))
    assert plan is not None


def test_trigger_engine_emits_on_bar_signals():
    from orderflow_bot.config import AbsorptionCfg
    from orderflow_bot.features.absorption import AbsorptionDetector
    from orderflow_bot.features.cvd import CvdTracker
    from orderflow_bot.models import FootprintBar
    from orderflow_bot.strategy.confluence import TriggerEngine

    eng = TriggerEngine(
        absorption=AbsorptionDetector(AbsorptionCfg(), tick_size=0.1),
        cvd=CvdTracker(),
        imb_cfg=ImbalanceCfg(ratio=3.0, min_stack=3),
    )
    # bougie baissiere avec pile d'imbalances achat -> trigger long contre le mouvement
    bar = FootprintBar(open_ts=0, close_ts=60_000, open=101.0, high=101.0, low=99.0,
                       close=99.5, volume=10.0, delta=2.0,
                       ask_vol={99: 9, 100: 9, 101: 9}, bid_vol={98: 1, 99: 2, 100: 2})
    trigs = eng.on_bar(bar)
    assert any(t.kind == "stacked_imbalance" and t.side == 1 for t in trigs)


def test_stacked_imbalance_trigger_carries_strength():
    from orderflow_bot.config import AbsorptionCfg
    from orderflow_bot.features.absorption import AbsorptionDetector
    from orderflow_bot.features.cvd import CvdTracker
    from orderflow_bot.models import FootprintBar
    from orderflow_bot.strategy.confluence import TriggerEngine

    eng = TriggerEngine(
        absorption=AbsorptionDetector(AbsorptionCfg(), tick_size=0.1),
        cvd=CvdTracker(),
        imb_cfg=ImbalanceCfg(ratio=3.0, min_stack=3),
    )
    bar = FootprintBar(open_ts=0, close_ts=60_000, open=101.0, high=101.0, low=99.0,
                       close=99.5, volume=10.0, delta=2.0,
                       ask_vol={99: 9, 100: 9, 101: 9}, bid_vol={98: 1, 99: 2, 100: 2})
    t = next(t for t in eng.on_bar(bar)
             if t.kind == "stacked_imbalance" and t.side == 1)
    assert t.features["stack_depth"] == 3          # bins 99,100,101 empiles
    assert t.features["stack_vol"] == 27.0         # ask_vol 9+9+9


def test_meta_includes_trigger_features():
    eng = _engine()
    t = Trigger(ts=1, side=1, kind="stacked_imbalance", price=97.1,
                features={"stack_depth": 4, "stack_vol": 50.0})
    plan = eng.evaluate(t)
    assert plan is not None
    assert plan.meta["stack_depth"] == 4
    assert plan.meta["stack_vol"] == 50.0
    assert plan.meta["zone"] == "val"
    assert plan.meta["trigger"] == "stacked_imbalance"


# --- mode continuation : trade la CASSURE du niveau, pas le rebond ---

def _cont_engine() -> ConfluenceEngine:
    eng = ConfluenceEngine(min_rr=1.5, stop_buffer_ticks=10, tick_size=0.1,
                           mode="continuation")
    zones = build_zones(PREV, npocs=[], lvn_prices=[], margin_pct=0.002)
    eng.update_day(zones, Bias.BOTH, day_high=PREV.high, day_low=PREV.low,
                   struct_levels=[PREV.low, PREV.high])
    return eng


def test_continuation_breaks_val_short_to_day_low():
    # cassure BAS de VAL -> short, stop = reclaim dans la value, cible = low veille
    eng = _cont_engine()
    plan = eng.evaluate(Trigger(ts=1, side=-1, kind="stacked_imbalance", price=97.0))
    assert plan is not None
    assert plan.side == -1
    assert plan.entry == 97.0
    assert plan.stop == (97.0 + 0.2) + 1.0      # z.hi + buffer (retour dans la value)
    assert plan.target == 95.0                  # prev.low (extension du range)


def test_continuation_breaks_vah_long_to_day_high():
    # cassure HAUT de VAH -> long, stop = reclaim, cible = high veille
    eng = _cont_engine()
    plan = eng.evaluate(Trigger(ts=1, side=1, kind="stacked_imbalance", price=103.0))
    assert plan is not None
    assert plan.side == 1
    assert plan.entry == 103.0
    assert plan.stop == (103.0 - 0.2) - 1.0     # z.lo - buffer
    assert plan.target == 105.0                 # prev.high


def test_continuation_rejects_inward_direction():
    # long dans VAL = sens du rebond (reversal) -> rejete en continuation
    eng = _cont_engine()
    assert eng.evaluate(Trigger(ts=1, side=1, kind="stacked_imbalance", price=97.0)) is None


def test_continuation_meta_marks_mode():
    eng = _cont_engine()
    plan = eng.evaluate(Trigger(ts=1, side=-1, kind="stacked_imbalance", price=97.0,
                                features={"stack_depth": 5, "stack_vol": 12.0}))
    assert plan is not None
    assert plan.meta["mode"] == "continuation"
    assert plan.meta["stack_depth"] == 5


def _cont_trigger_engine():
    from orderflow_bot.config import AbsorptionCfg
    from orderflow_bot.features.absorption import AbsorptionDetector
    from orderflow_bot.features.cvd import CvdTracker
    from orderflow_bot.strategy.confluence import TriggerEngine
    return TriggerEngine(
        absorption=AbsorptionDetector(AbsorptionCfg(), tick_size=0.1),
        cvd=CvdTracker(),
        imb_cfg=ImbalanceCfg(ratio=3.0, min_stack=3),
        continuation=True,
    )


def test_continuation_trigger_fires_with_the_move():
    from orderflow_bot.models import FootprintBar
    eng = _cont_trigger_engine()
    # bougie HAUSSIERE avec pile d'imbalances achat -> long DANS le sens (cassure)
    bar = FootprintBar(open_ts=0, close_ts=60_000, open=99.0, high=101.0, low=99.0,
                       close=100.5, volume=10.0, delta=2.0,
                       ask_vol={99: 9, 100: 9, 101: 9}, bid_vol={98: 1, 99: 2, 100: 2})
    t = next(t for t in eng.on_bar(bar) if t.kind == "stacked_imbalance")
    assert t.side == 1
    assert t.features["stack_depth"] == 3
    assert t.features["stack_vol"] == 27.0


def test_continuation_does_not_fire_against_the_move():
    from orderflow_bot.models import FootprintBar
    eng = _cont_trigger_engine()
    # bougie BAISSIERE avec pile achat : le reversal tirerait long, la continuation NON
    bar = FootprintBar(open_ts=0, close_ts=60_000, open=101.0, high=101.0, low=99.0,
                       close=99.5, volume=10.0, delta=2.0,
                       ask_vol={99: 9, 100: 9, 101: 9}, bid_vol={98: 1, 99: 2, 100: 2})
    assert not any(t.kind == "stacked_imbalance" for t in eng.on_bar(bar))

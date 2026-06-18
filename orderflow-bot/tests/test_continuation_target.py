from orderflow_bot.strategy.confluence import ConfluenceEngine, Trigger
from orderflow_bot.strategy.context import Bias
from orderflow_bot.strategy.zones import Zone


def _engine(mode):
    return ConfluenceEngine(min_rr=2.0, stop_buffer_ticks=1, tick_size=1.0,
                            fees=None, min_stop_friction_mult=0.0, mode=mode)


def test_continuation_target_nearest_structural_level():
    eng = _engine("continuation")
    eng.update_day([Zone(99.0, 100.0, -1, "vah", 0.0)], Bias.BOTH,
                   struct_levels=[95.0, 105.0, 110.0], va_width=8.0)
    plan = eng.evaluate(Trigger(ts=1, side=1, kind="level_breakout", price=100.0))
    assert plan is not None
    assert plan.target == 105.0          # niveau le plus proche AU-DELA de l'entree (100)
    assert plan.side == 1 and plan.meta["mode"] == "continuation"
    assert plan.stop < plan.entry < plan.target


def test_continuation_target_fallback_measured_move():
    eng = _engine("continuation")
    eng.update_day([Zone(99.0, 100.0, -1, "vah", 0.0)], Bias.BOTH,
                   struct_levels=[95.0], va_width=8.0)   # aucun niveau au-dela de 100
    plan = eng.evaluate(Trigger(ts=1, side=1, kind="level_breakout", price=100.0))
    assert plan is not None
    assert plan.target == 108.0          # entry + side * va_width = 100 + 8


def test_continuation_no_plan_when_no_target():
    eng = _engine("continuation")
    eng.update_day([Zone(99.0, 100.0, -1, "vah", 0.0)], Bias.BOTH,
                   struct_levels=[95.0], va_width=None)   # ni niveau au-dela ni measured-move
    assert eng.evaluate(Trigger(ts=1, side=1, kind="level_breakout", price=100.0)) is None


def test_reversal_target_unchanged():
    eng = _engine("reversal")
    eng.update_day([Zone(98.5, 99.0, 1, "val", 103.0)], Bias.BOTH)  # struct_levels absents
    plan = eng.evaluate(Trigger(ts=1, side=1, kind="level_rejection", price=99.0))
    assert plan is not None
    assert plan.target == 103.0          # reversal cible toujours z.target (POC), inchange

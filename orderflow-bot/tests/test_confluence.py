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

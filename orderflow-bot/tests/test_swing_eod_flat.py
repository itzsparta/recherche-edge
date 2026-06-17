import pytest

from orderflow_bot.config import BotConfig, FeesCfg, RiskCfg, StrategyCfg
from orderflow_bot.models import OrderPlan, Trade
from orderflow_bot.pipeline import simulate_isolated

DAY = 86_400_000


def _cfg() -> BotConfig:
    # fees=0 -> r exact ; partial desactive (partial_at_r enorme) -> exit plein au target
    return BotConfig(
        tick_size=0.1,
        fees=FeesCfg(maker_pct=0.0, taker_pct=0.0, slippage_ticks=0),
        risk=RiskCfg(partial_at_r=999.0, move_to_be=False, trail_r=None,
                     min_stop_friction_mult=0.0),
        strategy=StrategyCfg(entry_expire_minutes=600),
    )


def test_eod_flat_false_runs_past_day_to_target():
    cfg = _cfg()
    t0 = 20_000 * DAY
    plan = OrderPlan(ts=t0, side=1, entry=100.0, stop=99.0, target=102.0, meta={})
    trades = [
        Trade(t0, 100.0, 1.0, False),               # cree le broker (submit)
        Trade(t0 + 1_000, 99.9, 1.0, False),        # limit fill (franchissement strict) -> entry_px=100
        Trade(t0 + 2_000, 100.5, 1.0, False),       # ni stop ni target
        Trade(t0 + DAY, 100.8, 1.0, False),         # jour+1 : PAS de flat (eod_flat=False)
        Trade(t0 + DAY + 1_000, 102.1, 1.0, False), # target @102 -> r=+2
        Trade(t0 + DAY + 2_000, 102.0, 1.0, False),
    ]
    out = simulate_isolated(cfg, [plan], trades, eod_flat=False)
    assert len(out) == 1
    assert out[0].fills[-1].kind == "target"
    assert out[0].r_multiple == pytest.approx(2.0)


def test_eod_flat_true_default_force_closes_at_day_boundary():
    cfg = _cfg()
    t0 = 20_000 * DAY
    plan = OrderPlan(ts=t0, side=1, entry=100.0, stop=99.0, target=102.0, meta={})
    trades = [
        Trade(t0, 100.0, 1.0, False),
        Trade(t0 + 1_000, 99.9, 1.0, False),
        Trade(t0 + DAY, 100.8, 1.0, False),         # jour+1 : flat EOD @100.8 -> r=+0.8
        Trade(t0 + DAY + 1_000, 102.1, 1.0, False),
    ]
    out = simulate_isolated(cfg, [plan], trades)     # eod_flat=True par defaut
    assert out[0].fills[-1].kind == "eod"
    assert out[0].r_multiple == pytest.approx(0.8)


def test_eod_flat_false_censors_position_open_at_data_end():
    cfg = _cfg()
    t0 = 20_000 * DAY
    plan = OrderPlan(ts=t0, side=1, entry=100.0, stop=99.0, target=110.0, meta={})  # target jamais atteint
    trades = [
        Trade(t0, 100.0, 1.0, False),
        Trade(t0 + 1_000, 99.9, 1.0, False),         # fill
        Trade(t0 + DAY, 101.0, 1.0, False),          # court toujours
        Trade(t0 + 2 * DAY, 101.5, 1.0, False),      # fin des donnees -> censure
    ]
    out = simulate_isolated(cfg, [plan], trades, eod_flat=False)
    assert len(out) == 1
    assert out[0].fills[-1].kind == "eod"            # censure = fermeture forcee en fin de data
    assert out[0].r_multiple == pytest.approx(1.5)

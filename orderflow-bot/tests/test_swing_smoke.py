import pytest

from orderflow_bot.backtest.swing_gate import (
    both_halves_positive, brut, dead_born_rate, gate1, mirror_plan,
)
from orderflow_bot.models import ClosedTrade, Fill, OrderPlan


def _ct(r, mfe, opened, kind="target") -> ClosedTrade:
    return ClosedTrade(
        plan=OrderPlan(opened, 1, 100.0, 99.0, 102.0, {}), qty=1.0,
        fills=[Fill(opened, 100.0, 1.0, "entry"), Fill(opened + 1, 102.0, 1.0, kind)],
        pnl=r, r_multiple=r, opened_ts=opened, closed_ts=opened + 1,
        mfe_r=mfe, mae_r=0.0,
    )


def test_brut_excludes_censored_labels():
    labels = [_ct(2.0, 2.0, 1, "target"), _ct(-1.0, 0.2, 2, "stop"), _ct(5.0, 5.0, 3, "eod")]
    assert brut(labels) == pytest.approx((2.0 - 1.0) / 2)   # le 'eod' (censure) est exclu


def test_dead_born_rate_excludes_censored():
    labels = [_ct(2.0, 2.0, 1), _ct(-1.0, 0.2, 2, "stop"), _ct(5.0, 5.0, 3, "eod")]
    assert dead_born_rate(labels) == pytest.approx(0.5)     # 1 mort-ne (mfe 0.2) sur 2 realises


def test_mirror_plan_reflects_through_entry():
    m = mirror_plan(OrderPlan(1, 1, 100.0, 99.0, 102.0, {}))
    assert m.side == -1 and m.entry == 100.0 and m.stop == 101.0 and m.target == 98.0


def test_gate1_greenlights_directional_positive():
    fade = [_ct(2.0, 2.0, 1), _ct(1.0, 1.5, 2), _ct(2.0, 2.0, 3), _ct(1.0, 1.2, 4)]
    mirror = [_ct(-2.0, 0.1, 1, "stop"), _ct(-1.0, 0.1, 2, "stop"),
              _ct(-1.5, 0.1, 3, "stop"), _ct(-1.0, 0.1, 4, "stop")]
    assert gate1(fade, mirror)["greenlight"] is True


def test_gate1_kills_when_brut_flat():
    fade = [_ct(0.1, 0.6, 1), _ct(-0.1, 0.2, 2, "stop"), _ct(0.05, 0.6, 3), _ct(-0.2, 0.1, 4, "stop")]
    mirror = [_ct(-0.1, 0.1, 1, "stop"), _ct(0.1, 0.6, 2), _ct(-0.05, 0.1, 3, "stop"), _ct(0.2, 0.6, 4)]
    assert gate1(fade, mirror)["greenlight"] is False

from orderflow_bot.backtest.plumbing_checks import (
    label_violations, plan_violations, zone_violations,
)
from orderflow_bot.models import ClosedTrade, Fill, OrderPlan
from orderflow_bot.strategy.context import DailyLevels


def _lv(poc, vah, val, hi, lo, day=1):
    return DailyLevels(day=day, poc=poc, vah=vah, val=val, high=hi, low=lo)


def _ct(r, kind="target"):
    p = OrderPlan(1, 1, 100.0, 99.0, 102.0, {})
    return ClosedTrade(plan=p, qty=1.0,
                       fills=[Fill(1, 100.0, 1.0, "entry"), Fill(2, 102.0, 1.0, kind)],
                       pnl=r, r_multiple=r, opened_ts=1, closed_ts=2)


def test_zone_violations_pass():
    assert zone_violations([_lv(100.0, 102.0, 98.0, 103.0, 97.0)]) == []


def test_zone_violations_poc_outside_va():
    v = zone_violations([_lv(105.0, 102.0, 98.0, 103.0, 97.0)])   # POC > VAH
    assert len(v) >= 1


def test_zone_violations_empty_levels():
    assert zone_violations([]) == ["aucun DailyLevels"]


def test_plan_violations_pass_long():
    p = OrderPlan(1, 1, 100.0, 99.0, 103.0, {})    # stop<entry<target, RR=3
    assert plan_violations([p], min_rr=2.0) == []


def test_plan_violations_bad_geometry():
    p = OrderPlan(1, 1, 100.0, 101.0, 103.0, {})   # long mais stop>entry
    assert len(plan_violations([p], min_rr=2.0)) >= 1


def test_plan_violations_rr_too_low():
    p = OrderPlan(1, 1, 100.0, 99.0, 100.5, {})    # RR=0.5
    assert any("RR" in m for m in plan_violations([p], min_rr=2.0))


def test_label_violations_pass():
    assert label_violations([_ct(2.0), _ct(-1.0, "stop")]) == []


def test_label_violations_nan():
    assert len(label_violations([_ct(float("nan"))])) >= 1


def test_label_violations_empty():
    assert label_violations([]) == ["aucun label"]

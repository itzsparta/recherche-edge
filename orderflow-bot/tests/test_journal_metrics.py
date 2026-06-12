import math

from orderflow_bot.backtest.metrics import compute_metrics
from orderflow_bot.execution.journal import TradeJournal
from orderflow_bot.models import ClosedTrade, Fill, OrderPlan


def _ct(pnl: float, r: float) -> ClosedTrade:
    plan = OrderPlan(ts=1, side=1, entry=100.0, stop=98.0, target=106.0,
                     meta={"zone": "val", "trigger": "absorption", "bias": "both"})
    fills = [Fill(ts=1, price=100.0, qty=1.0, kind="entry"),
             Fill(ts=2, price=100.0 + pnl, qty=1.0, kind="target")]
    return ClosedTrade(plan=plan, qty=1.0, fills=fills, pnl=pnl, r_multiple=r,
                       opened_ts=1, closed_ts=2)


def test_journal_roundtrip(tmp_path):
    path = tmp_path / "j.jsonl"
    j = TradeJournal(path)
    j.record(_ct(4.0, 2.0))
    j.record(_ct(-2.0, -1.0))
    rows = TradeJournal.load(path)
    assert len(rows) == 2
    assert rows[0]["pnl"] == 4.0
    assert rows[0]["plan"]["meta"]["trigger"] == "absorption"
    assert rows[0]["fills"][0]["kind"] == "entry"


def test_metrics():
    rows = [
        {"pnl": 4.0, "r_multiple": 2.0},
        {"pnl": -2.0, "r_multiple": -1.0},
        {"pnl": 4.0, "r_multiple": 2.0},
    ]
    m = compute_metrics(rows)
    assert m["trades"] == 3
    assert m["win_rate"] == 2 / 3
    assert m["profit_factor"] == 8.0 / 2.0
    assert m["expectancy_r"] == 1.0
    assert m["total_pnl"] == 6.0
    assert m["max_drawdown"] == 2.0


def test_metrics_empty():
    assert compute_metrics([]) == {"trades": 0}


def _row(pnl: float, r: float) -> dict:
    return {"pnl": pnl, "r_multiple": r}


def test_sortino_on_r_multiples():
    # rs = [2.0, -1.0] : mean = 0.5, downside dev = sqrt((0 + 1)/2)
    m = compute_metrics([_row(200.0, 2.0), _row(-100.0, -1.0)])
    assert math.isclose(m["sortino_r"], 0.5 / math.sqrt(0.5))


def test_sortino_inf_when_no_loss():
    m = compute_metrics([_row(100.0, 1.0), _row(50.0, 0.5)])
    assert m["sortino_r"] == float("inf")


def test_calmar_total_pnl_over_max_dd():
    # equity 100 -> 50 : peak 100, dd 50, total 50 -> calmar 1.0
    m = compute_metrics([_row(100.0, 1.0), _row(-50.0, -0.5)])
    assert m["calmar"] == 1.0


def test_calmar_inf_when_no_drawdown():
    m = compute_metrics([_row(100.0, 1.0)])
    assert m["calmar"] == float("inf")

import pytest

from orderflow_bot.config import FeesCfg, RiskCfg
from orderflow_bot.execution.paper import PaperBroker
from orderflow_bot.models import Cancelled, ClosedTrade, OrderPlan

from .conftest import make_trade

# long : entry 100, stop 98 (risk 2.0), target 106 (RR 3)
PLAN = OrderPlan(ts=1_000, side=1, entry=100.0, stop=98.0, target=106.0)

ZERO_FEES = FeesCfg(maker_pct=0.0, taker_pct=0.0, slippage_ticks=0)
# frais ronds pour des assertions exactes : maker 0.1 %, taker 0.2 %, slip 10 ticks = 1.0
TEST_FEES = FeesCfg(maker_pct=0.001, taker_pct=0.002, slippage_ticks=10)


def _broker(fees: FeesCfg = ZERO_FEES) -> PaperBroker:
    return PaperBroker(RiskCfg(partial_at_r=1.0, partial_fraction=0.5),
                       expire_ms=900_000, fees=fees, tick_size=0.1)


def test_entry_requires_strict_cross():
    br = _broker()
    br.submit(PLAN, qty=1.0, ts=1_000)
    assert br.on_trade(make_trade(2_000, 100.0)) is None      # toucher ne suffit pas
    assert br.on_trade(make_trade(3_000, 99.9)) is None       # fill, position ouverte
    assert br.active is True


def test_full_cycle_partial_then_target():
    br = _broker()
    br.submit(PLAN, qty=1.0, ts=1_000)
    br.on_trade(make_trade(2_000, 99.9))                      # entry @100
    # partiel a 1R = 102 : franchissement strict requis
    assert br.on_trade(make_trade(3_000, 102.0)) is None
    assert br.on_trade(make_trade(4_000, 102.1)) is None      # partiel 0.5 @102, stop -> BE
    # retour a 100 : stop BE sur le reste
    ct = br.on_trade(make_trade(5_000, 100.0))
    assert isinstance(ct, ClosedTrade)
    assert ct.pnl == 0.5 * 2.0 + 0.5 * 0.0                    # +1.0
    assert ct.r_multiple == 1.0 / (2.0 * 1.0)                 # 0.5 R
    kinds = [f.kind for f in ct.fills]
    assert kinds == ["entry", "partial", "stop"]
    assert br.active is False


def test_target_fill():
    br = _broker()
    br.submit(PLAN, qty=1.0, ts=1_000)
    br.on_trade(make_trade(2_000, 99.9))
    br.on_trade(make_trade(3_000, 102.1))                     # partiel
    ct = br.on_trade(make_trade(4_000, 106.1))                # target strict
    assert isinstance(ct, ClosedTrade)
    assert ct.pnl == 0.5 * 2.0 + 0.5 * 6.0                    # +4.0
    assert ct.fills[-1].kind == "target"
    assert ct.fills[-1].price == 106.0


def test_stop_with_gap_fills_worse():
    br = _broker()
    br.submit(PLAN, qty=1.0, ts=1_000)
    br.on_trade(make_trade(2_000, 99.9))
    ct = br.on_trade(make_trade(3_000, 97.5))                 # gap sous le stop
    assert isinstance(ct, ClosedTrade)
    assert ct.fills[-1].price == 97.5                          # fill au pire prix
    assert ct.pnl == (97.5 - 100.0) * 1.0


def test_entry_expires():
    br = _broker()
    br.submit(PLAN, qty=1.0, ts=1_000)
    ev = br.on_trade(make_trade(1_000 + 900_001, 101.0))
    assert isinstance(ev, Cancelled)
    assert br.active is False


def test_short_cycle():
    plan = OrderPlan(ts=1_000, side=-1, entry=100.0, stop=102.0, target=94.0)
    br = _broker()
    br.submit(plan, qty=1.0, ts=1_000)
    br.on_trade(make_trade(2_000, 100.1))                     # fill short @100
    br.on_trade(make_trade(3_000, 97.9))                      # partiel @98, stop -> BE
    ct = br.on_trade(make_trade(4_000, 93.9))                 # target @94
    assert isinstance(ct, ClosedTrade)
    assert ct.pnl == 0.5 * 2.0 + 0.5 * 6.0


def test_force_close():
    br = _broker()
    br.submit(PLAN, qty=1.0, ts=1_000)
    br.on_trade(make_trade(2_000, 99.9))
    ct = br.force_close(make_trade(5_000, 101.0))
    assert isinstance(ct, ClosedTrade)
    assert ct.fills[-1].kind == "eod"
    assert ct.pnl == 1.0


def test_fees_deducted_on_target():
    br = _broker(TEST_FEES)
    br.submit(PLAN, qty=1.0, ts=1_000)
    br.on_trade(make_trade(2_000, 99.9))                  # entry @100, maker
    br.on_trade(make_trade(3_000, 102.1))                 # partiel 0.5 @102, maker
    ct = br.on_trade(make_trade(4_000, 106.1))            # target 0.5 @106, maker
    assert isinstance(ct, ClosedTrade)
    # brut = 0.5*2 + 0.5*6 = 4.0
    # frais maker : 100*1*0.001 + 102*0.5*0.001 + 106*0.5*0.001 = 0.204
    assert ct.fees == pytest.approx(0.204, rel=1e-9)
    assert ct.pnl == pytest.approx(4.0 - 0.204, rel=1e-9)
    assert ct.r_multiple == pytest.approx((4.0 - 0.204) / 2.0, rel=1e-9)  # risk0 = 2.0, qty = 1


def test_stop_pays_taker_and_slippage():
    br = _broker(TEST_FEES)
    br.submit(PLAN, qty=1.0, ts=1_000)
    br.on_trade(make_trade(2_000, 99.9))                  # entry @100
    ct = br.on_trade(make_trade(3_000, 97.5))             # gap sous le stop
    assert isinstance(ct, ClosedTrade)
    # pire prix 97.5, slip 10 ticks * 0.1 = 1.0 defavorable -> fill @96.5
    assert ct.fills[-1].price == 96.5
    # brut = 96.5 - 100 = -3.5 ; frais = 100*0.001 (maker entry) + 96.5*0.002 (taker stop)
    assert ct.fees == pytest.approx(0.1 + 0.193, rel=1e-9)
    assert ct.pnl == pytest.approx(-3.5 - 0.293, rel=1e-9)


def test_eod_pays_taker_and_slippage():
    br = _broker(TEST_FEES)
    br.submit(PLAN, qty=1.0, ts=1_000)
    br.on_trade(make_trade(2_000, 99.9))                  # entry @100
    ct = br.force_close(make_trade(5_000, 101.0))
    assert isinstance(ct, ClosedTrade)
    assert ct.fills[-1].price == 100.0                     # 101 - slip 1.0
    assert ct.fills[-1].kind == "eod"
    # frais : entry maker 100*1*0.001 + eod taker 100*1*0.002 = 0.3 ; brut = 0
    assert ct.fees == pytest.approx(0.3, rel=1e-9)
    assert ct.pnl == pytest.approx(-0.3, rel=1e-9)


def test_short_stop_slippage_is_adverse():
    plan = OrderPlan(ts=1_000, side=-1, entry=100.0, stop=102.0, target=94.0)
    br = _broker(TEST_FEES)
    br.submit(plan, qty=1.0, ts=1_000)
    br.on_trade(make_trade(2_000, 100.1))                  # fill short @100
    ct = br.on_trade(make_trade(3_000, 102.5))             # gap au-dessus du stop
    assert isinstance(ct, ClosedTrade)
    assert ct.fills[-1].price == 103.5                     # 102.5 + slip 1.0 (racheter plus haut)


def test_zero_fees_keeps_old_behavior():
    br = _broker()                                         # ZERO_FEES
    br.submit(PLAN, qty=1.0, ts=1_000)
    br.on_trade(make_trade(2_000, 99.9))
    br.on_trade(make_trade(3_000, 102.1))
    ct = br.on_trade(make_trade(4_000, 106.1))
    assert ct.pnl == 4.0
    assert ct.fees == 0.0

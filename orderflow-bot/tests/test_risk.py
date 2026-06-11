from orderflow_bot.config import RiskCfg, SessionCfg
from orderflow_bot.models import OrderPlan
from orderflow_bot.risk.manager import RiskManager

DAY_MS = 86_400_000
TS_14H = 50 * DAY_MS + 14 * 3_600_000     # 14:00 UTC, jour 50
SESSIONS = [SessionCfg(start="13:00", end="17:00")]


def _rm(equity: float = 10_000.0) -> RiskManager:
    return RiskManager(RiskCfg(), SESSIONS, equity)


def _plan(entry: float = 100.0, stop: float = 98.7) -> OrderPlan:
    return OrderPlan(ts=TS_14H, side=1, entry=entry, stop=stop, target=104.0)


def test_size_from_stop_distance():
    rm = _rm()
    # 10000 * 0.0075 / 1.3 = 57.69... -> floor au step 0.001
    assert rm.size(_plan()) == 57.692


def test_size_none_when_too_small():
    rm = _rm(equity=0.1)
    assert rm.size(_plan()) is None


def test_session_filter():
    rm = _rm()
    assert rm.can_open(TS_14H) is True
    assert rm.can_open(50 * DAY_MS + 9 * 3_600_000) is False    # 09:00 hors session


def test_daily_stop_blocks_until_next_day():
    rm = _rm()
    rm.on_open(TS_14H)
    rm.on_close(TS_14H + 60_000, -250.0)     # -2.5 % > stop journalier 2 %
    assert rm.can_open(TS_14H + 120_000) is False
    assert rm.can_open(TS_14H + DAY_MS) is True    # lendemain : reset


def test_three_losses_pause():
    rm = _rm()
    for i in range(3):
        rm.on_open(TS_14H + i * 3)
        rm.on_close(TS_14H + i * 3 + 1, -10.0)
    assert rm.can_open(TS_14H + 100) is False
    assert rm.can_open(TS_14H + DAY_MS) is True


def test_win_resets_streak():
    # cap trades/jour leve pour isoler le comportement du streak
    rm = RiskManager(RiskCfg(max_trades_per_day=10), SESSIONS, 10_000.0)
    for pnl in (-10.0, -10.0, 50.0, -10.0):
        rm.on_open(TS_14H)
        rm.on_close(TS_14H + 1, pnl)
    assert rm.can_open(TS_14H + 100) is True


def test_single_position_and_daily_cap():
    rm = _rm()
    rm.on_open(TS_14H)
    assert rm.can_open(TS_14H + 1) is False        # position deja ouverte
    rm.on_close(TS_14H + 2, 5.0)
    rm.on_open(TS_14H + 3)
    rm.on_close(TS_14H + 4, 5.0)
    rm.on_open(TS_14H + 5)
    rm.on_close(TS_14H + 6, 5.0)
    assert rm.can_open(TS_14H + 7) is False        # cap 3 trades/jour


def test_cancel_refunds_trade_slot():
    rm = _rm()
    rm.on_open(TS_14H)
    rm.on_cancel()
    assert rm.can_open(TS_14H + 1) is True

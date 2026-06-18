import pytest

from orderflow_bot.backtest.swing_gate2 import (
    brut_by_side, gate2, regime_fn_from_closes, regime_split, t_stat,
)
from orderflow_bot.models import ClosedTrade, Fill, OrderPlan


def _ct(r, opened, side=1, mfe=2.0, kind="target") -> ClosedTrade:
    return ClosedTrade(
        plan=OrderPlan(opened, side, 100.0, 99.0, 102.0, {}), qty=1.0,
        fills=[Fill(opened, 100.0, 1.0, "entry"), Fill(opened + 1, 102.0, 1.0, kind)],
        pnl=r, r_multiple=r, opened_ts=opened, closed_ts=opened + 1,
        mfe_r=mfe, mae_r=0.0,
    )


def test_brut_by_side_splits_long_short():
    labels = [_ct(2.0, 1, side=1), _ct(1.0, 2, side=1), _ct(-1.0, 3, side=-1)]
    bl, bs = brut_by_side(labels)
    assert bl == pytest.approx(1.5) and bs == pytest.approx(-1.0)


def test_brut_by_side_excludes_censored():
    labels = [_ct(2.0, 1, side=1), _ct(5.0, 2, side=1, kind="eod")]   # 'eod' = censure
    bl, bs = brut_by_side(labels)
    assert bl == pytest.approx(2.0) and bs == 0.0


def test_t_stat_known_value():
    assert t_stat([_ct(2.0, 1), _ct(-1.0, 2)]) == pytest.approx(1 / 3, abs=1e-3)


def test_t_stat_zero_when_no_variance():
    assert t_stat([_ct(1.0, 1), _ct(1.0, 2)]) == 0.0


def test_regime_fn_from_closes_sign_of_90d_return():
    closes = {0: 100.0, 90: 120.0, 200: 80.0, 290: 60.0}
    fn = regime_fn_from_closes(closes, lookback_days=90)
    DAY = 86_400_000
    assert fn(90 * DAY) == 1       # 120 > 100 (J0)
    assert fn(290 * DAY) == -1     # 60 < 80 (J200)
    assert fn(5 * DAY) == 0        # pas de close a J-85 -> regime inconnu


def test_regime_split_buckets_by_regime():
    DAY = 86_400_000
    labels = [_ct(2.0, 1 * DAY, side=1), _ct(1.0, 2 * DAY, side=-1), _ct(-1.0, 9 * DAY, side=1)]
    reg = regime_split(labels, lambda ts: 1 if ts < 5 * DAY else -1)
    assert reg[1]["n"] == 2 and reg[-1]["n"] == 1
    assert reg[1]["brut"] == pytest.approx(1.5)


def test_gate2_core_greenlight_when_both_sides_positive():
    fade = [_ct(2.0, i, side=1) for i in range(1, 8)] + [_ct(1.5, i, side=-1) for i in range(8, 15)]
    mirror = [_ct(-1.5, i, side=-1) for i in range(1, 15)]
    net = [_ct(1.6, i, side=1) for i in range(1, 8)] + [_ct(1.1, i, side=-1) for i in range(8, 15)]
    v = gate2(fade, mirror, net, lambda ts: 1)
    assert v["brut_long"] > 0 and v["brut_short"] > 0 and v["t"] > 2
    assert v["core_greenlight"] is True


def test_gate2_kills_when_one_side_negative_drift():
    # scenario drift : longs gagnent (vent porteur), shorts perdent -> PAS un edge de niveau
    fade = [_ct(2.0, i, side=1) for i in range(1, 8)] + [_ct(-1.0, i, side=-1) for i in range(8, 15)]
    mirror = [_ct(0.0, i, side=1) for i in range(1, 15)]
    net = [_ct(1.6, i, side=1) for i in range(1, 8)] + [_ct(-1.2, i, side=-1) for i in range(8, 15)]
    v = gate2(fade, mirror, net, lambda ts: 1)
    assert v["brut_short"] < 0
    assert v["core_greenlight"] is False


def test_gate2_kill_attributable_to_short_side_alone():
    # Tous les autres conjoncts PASSENT (brut>0, t>2, net>0, brut>miroir) ;
    # seul brut_short<0 doit faire basculer core_greenlight a False.
    # 20 longs +1.0, 4 shorts -0.1 : brut>0, t tres significatif, mais bs<0.
    fade = ([_ct(1.0, i, side=1) for i in range(1, 21)]
            + [_ct(-0.1, i, side=-1) for i in range(21, 25)])
    mirror = [_ct(0.0, i, side=1) for i in range(1, 25)]          # b_mirror=0 < brut
    net = ([_ct(0.8, i, side=1) for i in range(1, 21)]
           + [_ct(-0.05, i, side=-1) for i in range(21, 25)])     # net>0
    v = gate2(fade, mirror, net, lambda ts: 1)
    assert v["brut"] > 0          # agregat positif (le drift "deguise" l'edge)
    assert v["t"] > 2             # significatif
    assert v["net"] > 0           # survit aux frais
    assert v["brut"] > v["brut_mirror"]
    assert v["brut_long"] > 0
    assert v["brut_short"] < 0    # SEUL conjonct qui echoue
    assert v["core_greenlight"] is False   # ... et il suffit a tuer

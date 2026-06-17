import pytest

from orderflow_bot.config import BotConfig, FeesCfg, RiskCfg, StrategyCfg
from orderflow_bot.models import Trade
from orderflow_bot.pipeline import generate_plans

DAY = 86_400_000
H4 = 240 * 60_000


def _swing_synth() -> list[Trade]:
    out: list[Trade] = []
    base = 20_000 * DAY
    # jour 1 : profil pyramidal POC=100, value autour de 97..103
    ts = base
    for p in range(95, 106):
        for _ in range(10 - abs(p - 100)):
            out.append(Trade(ts, float(p), 1.0, ts % 2 == 0))
            ts += 1_000
    # jour 2, 1ere fenetre 4h : rejet d'un support (dip dans la value puis cloture au-dessus)
    d2 = base + DAY
    out.append(Trade(d2 + 1_000, 96.9, 1.0, False))   # dip dans/sous la value basse
    out.append(Trade(d2 + 2_000, 97.1, 1.0, False))
    out.append(Trade(d2 + 3_000, 99.0, 1.0, False))   # cloture de la fenetre nettement au-dessus
    # 1er trade de la fenetre 4h suivante -> flush du bar precedent -> evaluation du trigger
    out.append(Trade(d2 + H4 + 1_000, 99.2, 1.0, False))
    return out


def test_level_rejection_generates_reversal_plan():
    cfg = BotConfig(
        tick_size=0.1, bar_minutes=240,
        fees=FeesCfg(maker_pct=0.0, taker_pct=0.0, slippage_ticks=0),
        strategy=StrategyCfg(trigger="level_rejection", profile_days=1,
                             npoc_lookback_days=1, zone_margin_pct=0.002,
                             stop_buffer_ticks=5, entry_expire_minutes=600),
        risk=RiskCfg(min_rr=2.0, min_stop_friction_mult=0.0),
    )
    plans = generate_plans(cfg, _swing_synth())
    assert len(plans) >= 1
    p = plans[0]
    assert p.side == 1                              # rejet d'un support -> long
    assert p.target == pytest.approx(100.0)        # target = POC veille
    assert p.meta["trigger"] == "level_rejection"
    assert p.entry < p.target and p.stop < p.entry  # geometrie reversal coherente

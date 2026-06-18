from orderflow_bot.config import BotConfig, FeesCfg, RiskCfg, StrategyCfg
from orderflow_bot.models import Trade
from orderflow_bot.pipeline import generate_plans

DAY = 86_400_000
H4 = 240 * 60_000


def _breakout_synth() -> list[Trade]:
    out: list[Trade] = []
    base = 20_000 * DAY
    ts = base
    # jour 1 : profil pyramidal POC=100, value ~97..103
    for p in range(95, 106):
        for _ in range(10 - abs(p - 100)):
            out.append(Trade(ts, float(p), 1.0, ts % 2 == 0))
            ts += 1_000
    # pic mince a 110 -> prev.high=110 = niveau structurel au-dessus de VAH (cible du breakout)
    out.append(Trade(ts, 110.0, 1.0, False)); ts += 1_000
    # jour 2, 1ere fenetre 4h : corps casse AU-DESSUS de VAH (~103) et cloture nettement au-dessus
    d2 = base + DAY
    out.append(Trade(d2 + 1_000, 102.0, 1.0, False))   # open juste sous VAH
    out.append(Trade(d2 + 2_000, 103.0, 1.0, False))
    out.append(Trade(d2 + 3_000, 106.0, 1.0, False))   # cloture de fenetre au-dessus de VAH
    # 1er trade de la fenetre 4h suivante -> flush du bar precedent -> evaluation du trigger
    out.append(Trade(d2 + H4 + 1_000, 106.2, 1.0, False))
    return out


def test_level_breakout_generates_continuation_plan():
    cfg = BotConfig(
        tick_size=0.1, bar_minutes=240,
        fees=FeesCfg(maker_pct=0.0, taker_pct=0.0, slippage_ticks=0),
        strategy=StrategyCfg(trigger="level_breakout", signal_mode="continuation",
                             profile_days=1, npoc_lookback_days=1, zone_margin_pct=0.002,
                             stop_buffer_ticks=5, entry_expire_minutes=600),
        risk=RiskCfg(min_rr=2.0, min_stop_friction_mult=0.0),
    )
    plans = generate_plans(cfg, _breakout_synth())
    assert len(plans) >= 1
    p = plans[0]
    assert p.side == 1                              # cassure au-dessus de VAH -> long
    assert p.meta["trigger"] == "level_breakout"
    assert p.meta["mode"] == "continuation"
    assert p.entry < p.target and p.stop < p.entry  # geometrie continuation coherente

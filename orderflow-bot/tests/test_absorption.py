from orderflow_bot.config import AbsorptionCfg
from orderflow_bot.features.absorption import AbsorptionDetector

from .conftest import make_trade

CFG = AbsorptionCfg(window_ms=30_000, vol_factor=3.0, max_range_ticks=15,
                    min_delta_frac=0.3, baseline_windows=8)


def _baseline(det: AbsorptionDetector, t0: int) -> int:
    """8 fenetres calmes de 30s, 1 trade de qty 1.0 chacune. Retourne ts suivant."""
    ts = t0
    for i in range(8):
        assert det.on_trade(make_trade(ts, 100.0 + (i % 2) * 0.1, 1.0, sell=i % 2 == 0)) is None
        ts += 30_000
    return ts


def test_detects_sell_absorption():
    det = AbsorptionDetector(CFG, tick_size=0.1)
    ts = _baseline(det, 1_000_000)
    # choc : ventes massives, range 1 tick, le prix ne baisse plus (last >= first)
    hits = []
    for i in range(10):
        px = 97.0 if i % 2 == 0 else 97.1
        a = det.on_trade(make_trade(ts, px, 0.5, sell=True))
        if a:
            hits.append(a)
        ts += 1_500
    assert hits, "absorption attendue"
    assert hits[0].side == 1            # vente absorbee -> signal bullish


def test_no_absorption_when_price_keeps_falling():
    det = AbsorptionDetector(CFG, tick_size=0.1)
    ts = _baseline(det, 1_000_000)
    # meme volume vendeur mais le prix degringole (range > 15 ticks)
    px = 100.0
    for _ in range(10):
        assert det.on_trade(make_trade(ts, round(px, 1), 0.5, sell=True)) is None
        px -= 0.4
        ts += 1_500


def test_needs_baseline():
    det = AbsorptionDetector(CFG, tick_size=0.1)
    # gros volume immediat mais aucune baseline -> jamais de signal
    ts = 1_000_000
    for i in range(10):
        assert det.on_trade(make_trade(ts, 97.0 if i % 2 else 97.1, 0.5, sell=True)) is None
        ts += 1_500

from orderflow_bot.features.cvd import CvdTracker

from .conftest import make_bar


def _feed(tracker: CvdTracker, lows_deltas: list[tuple[float, float]]) -> None:
    for low, delta in lows_deltas:
        tracker.on_bar(make_bar(low=low, high=low + 2.0, delta=delta))


def test_bullish_divergence():
    t = CvdTracker()
    # swing low 1 : low=100, cvd=-10 ; swing low 2 : low=99 (plus bas), cvd=-5 (plus haut)
    _feed(t, [(101, -4), (100, -6), (101.5, 3), (100.5, -4), (99, 6), (100.5, 1)])
    # cvd cumulatif aux swings : i=1 -> -10 ; i=4 -> -5
    assert t.bullish_divergence() is True
    assert t.bearish_divergence() is False


def test_no_divergence_when_cvd_confirms():
    t = CvdTracker()
    # prix plus bas ET cvd plus bas -> pas de divergence
    _feed(t, [(101, -4), (100, -6), (101.5, 1), (100.5, -8), (99, -2), (100.5, 1)])
    assert t.bullish_divergence() is False


def test_reset():
    t = CvdTracker()
    _feed(t, [(101, -4), (100, -6), (101.5, 3)])
    t.reset()
    assert t.cvd == 0.0
    assert t.bullish_divergence() is False

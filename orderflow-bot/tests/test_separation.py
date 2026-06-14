import math
from orderflow_bot.backtest.separation import auc, quartile_lift


def test_auc_perfect_and_random():
    # positifs (True) ont les scores les plus hauts -> AUC = 1.0
    scores = [0.1, 0.2, 0.8, 0.9]
    labels = [False, False, True, True]
    assert auc(scores, labels) == 1.0
    # inverse -> 0.0
    assert auc([0.9, 0.8, 0.2, 0.1], labels) == 0.0
    # une seule classe -> NaN
    assert math.isnan(auc([1.0, 2.0], [True, True]))


def test_auc_ties_half():
    # tous egaux -> AUC = 0.5 (rangs moyens)
    assert auc([1.0, 1.0, 1.0, 1.0], [True, False, True, False]) == 0.5


def test_auc_drops_nan():
    # NaN exclus, le reste est un separateur parfait
    scores = [float("nan"), 0.1, 0.9]
    labels = [True, False, True]
    assert auc(scores, labels) == 1.0


def test_quartile_lift_monotone():
    # score = label parfait -> lift croissant 0,0,1,1 sur 4 quartiles
    scores = [0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9]
    labels = [False, False, False, False, True, True, True, True]
    assert quartile_lift(scores, labels, q=4) == [0.0, 0.0, 1.0, 1.0]


from orderflow_bot.backtest.separation import evaluate_greenlight


def _rows_strong_separator():
    """7 jours, 8 candidats/jour. 'good' (oriente) separe parfaitement les
    morts-nes ; tape 'noise' = bruit constant."""
    rows = []
    for d in range(7):
        for k in range(8):
            mort = k >= 4
            rows.append({"day": f"d{d}", "mort_ne": mort,
                         "good": float(k), "noise": 0.0})
    return rows


def test_greenlight_passes_on_strong_separator():
    rows = _rows_strong_separator()
    days = [f"d{d}" for d in range(7)]
    v = evaluate_greenlight(rows, days, orient={"good": +1}, tape_feats=["noise"])
    assert v["best_feat"] == "good"
    assert v["best_auc"] >= 0.60
    assert v["c1"] and v["c2"] and v["c3"] and v["c4"]
    assert v["green"] is True


def test_greenlight_fails_when_no_book_signal():
    # book = bruit, tape = bruit -> pas de separation
    rows = [{"day": f"d{d}", "mort_ne": (k % 2 == 0), "good": 0.0, "noise": 0.0}
            for d in range(7) for k in range(8)]
    days = [f"d{d}" for d in range(7)]
    v = evaluate_greenlight(rows, days, orient={"good": +1}, tape_feats=["noise"])
    assert v["green"] is False

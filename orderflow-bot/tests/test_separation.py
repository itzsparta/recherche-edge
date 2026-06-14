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

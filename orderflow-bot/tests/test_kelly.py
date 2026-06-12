from orderflow_bot.risk.kelly import kelly_fraction, kelly_quarter


def test_zero_when_no_trades():
    assert kelly_fraction([]) == 0.0


def test_zero_when_negative_expectancy():
    assert kelly_fraction([1.0, -1.0, -1.0]) == 0.0


def test_binary_distribution_matches_theory():
    # p = 0.6 gagne +1R, perd -1R : Kelly theorique = 2p - 1 = 0.2
    rs = [1.0] * 6 + [-1.0] * 4
    f = kelly_fraction(rs)
    assert abs(f - 0.2) < 0.01


def test_quarter_is_quarter():
    rs = [1.0] * 6 + [-1.0] * 4
    assert kelly_quarter(rs) == kelly_fraction(rs) / 4.0


def test_capped_below_blowup():
    # pire trade -2R (slippage) : f doit rester < 0.5 sinon log(1 + f*r) explose
    rs = [3.0, 3.0, 3.0, -2.0]
    f = kelly_fraction(rs)
    assert 0.0 < f < 0.5

from orderflow_bot.binning import bin_of, price_of


def test_bin_roundtrip():
    assert bin_of(117_234.3, 1.0) == 117_234
    assert price_of(117_234, 1.0) == 117_234.0


def test_bin_fractional_size():
    assert bin_of(97.06, 0.1) == 971
    assert price_of(971, 0.1) == 97.1


def test_bin_rounds_to_nearest():
    assert bin_of(100.6, 1.0) == 101
    assert bin_of(100.4, 1.0) == 100

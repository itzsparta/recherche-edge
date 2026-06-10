from orderflow_bot.features.volume_profile import VolumeProfile


def _profile(vols: dict[int, float]) -> VolumeProfile:
    p = VolumeProfile(bin_size=1.0)
    for b, q in vols.items():
        p.add(float(b), q)
    return p


def test_poc():
    p = _profile({98: 5, 99: 10, 100: 30, 101: 10, 102: 5})
    assert p.poc() == 100


def test_value_area_70pct():
    # total=60, 70%=42 ; expansion depuis POC : +101(40) puis +99(50) -> VAL=99, VAH=101
    p = _profile({98: 5, 99: 10, 100: 30, 101: 10, 102: 5})
    assert p.value_area(0.70) == (99, 101)


def test_lvn_groups_valley():
    # mean = 88/6 ~ 14.67 ; seuil 0.3*mean ~ 4.4 ; vallee [97, 98] -> representant 98
    p = _profile({95: 20, 96: 18, 97: 2, 98: 1, 99: 22, 100: 25})
    assert p.lvns(0.3) == [98]


def test_hvn():
    # seuil 1.5 * (88/6) = 22.0 ; inclusif (>=) : 99 (22) et 100 (25) qualifient
    p = _profile({95: 20, 96: 18, 97: 2, 98: 1, 99: 22, 100: 25})
    assert p.hvns(1.5) == [99, 100]


def test_merge():
    a = _profile({100: 10})
    b = _profile({100: 5, 101: 3})
    a.merge(b)
    assert a.vol == {100: 15.0, 101: 3.0}
    assert a.total == 18.0

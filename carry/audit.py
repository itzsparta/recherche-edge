"""Stats anti-overfit portées depuis factor-harvest/audit.py (pur stdlib)."""
import math
from statistics import NormalDist

_N01 = NormalDist()


def sharpe(xs: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    m = sum(xs) / n
    var = sum((x - m) ** 2 for x in xs) / n
    s = math.sqrt(var)
    return m / s if s > 0 else 0.0


def tstat(xs: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    return sharpe(xs) * math.sqrt(n)

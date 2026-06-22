"""Stats minimales (sharpe/tstat). Réutilisé du pattern factor-harvest/forced-flows."""
from __future__ import annotations

import math


def _moments(x: list[float]) -> tuple[float, float, int]:
    n = len(x)
    if n < 2:
        return (x[0] if x else 0.0), 0.0, n
    m = sum(x) / n
    var = sum((v - m) ** 2 for v in x) / (n - 1)
    return m, math.sqrt(var), n


def sharpe(x: list[float]) -> float:
    m, sd, n = _moments(x)
    return m / sd if sd > 0 else 0.0


def tstat(x: list[float]) -> float:
    m, sd, n = _moments(x)
    return m / (sd / math.sqrt(n)) if (sd > 0 and n > 1) else 0.0

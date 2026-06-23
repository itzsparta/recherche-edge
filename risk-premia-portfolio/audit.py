"""Stats anti-overfit portées depuis orderflow-bot/scripts/overfit_audit.py.

Pur stdlib (Bailey & López de Prado 2014). DSR déflate le Sharpe du meilleur
essai par le nombre de variantes + la non-normalité. DSR > 0.95 = significatif
malgré le multiple-testing.
"""
import math
from statistics import NormalDist

_N01 = NormalDist()


def sharpe(xs: list[float]) -> float:
    """Sharpe par période (non annualisé)."""
    n = len(xs)
    if n < 2:
        return 0.0
    m = sum(xs) / n
    var = sum((x - m) ** 2 for x in xs) / n
    s = math.sqrt(var)
    return m / s if s > 0 else 0.0


def tstat(xs: list[float]) -> float:
    """t-stat de la moyenne = SR_période * sqrt(n)."""
    n = len(xs)
    if n < 2:
        return 0.0
    return sharpe(xs) * math.sqrt(n)


def _moments(xs: list[float]) -> tuple[float, float]:
    n = len(xs)
    m = sum(xs) / n
    s = math.sqrt(sum((x - m) ** 2 for x in xs) / n)
    if s == 0:
        return 0.0, 3.0
    sk = sum(((x - m) / s) ** 3 for x in xs) / n
    ku = sum(((x - m) / s) ** 4 for x in xs) / n
    return sk, ku


def deflated_sharpe(rets: list[float], n_trials: int, var_trials: float):
    """Renvoie (DSR, SR_hat, SR0). SR par période (pas annualisé)."""
    T = len(rets)
    sr = sharpe(rets)
    g = 0.5772156649015329  # Euler-Mascheroni
    sr0 = math.sqrt(max(var_trials, 1e-12)) * (
        (1 - g) * _N01.inv_cdf(1 - 1 / n_trials)
        + g * _N01.inv_cdf(1 - 1 / (n_trials * math.e)))
    sk, ku = _moments(rets)
    denom = math.sqrt(max(1e-12, 1 - sk * sr + (ku - 1) / 4 * sr ** 2))
    z = (sr - sr0) * math.sqrt(max(T - 1, 1)) / denom
    return _N01.cdf(z), sr, sr0

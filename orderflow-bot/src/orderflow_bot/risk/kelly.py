import math


def kelly_fraction(rs: list[float], f_max: float = 1.0, steps: int = 500) -> float:
    """Fraction f qui maximise la croissance log E[ln(1 + f*R)] sur la
    distribution EMPIRIQUE des R du journal (aucune hypothese de forme).
    Recherche sur grille. 0 si expectancy <= 0."""
    if not rs or sum(rs) / len(rs) <= 0:
        return 0.0
    worst = min(rs)
    # eviter ln(<= 0) : f * worst > -1 strictement
    cap = f_max if worst >= 0 else min(f_max, -0.999 / worst)
    best_f = best_g = 0.0
    for i in range(1, steps + 1):
        f = cap * i / steps
        g = sum(math.log(1.0 + f * r) for r in rs) / len(rs)
        if g > best_g:
            best_f, best_g = f, g
    return best_f


def kelly_quarter(rs: list[float]) -> float:
    """Kelly 1/4 : PLAFOND offline du risque par trade (v2 de la spec,
    apres ~100 trades reels). Jamais full Kelly, jamais une consigne
    automatique injectee dans le live."""
    return kelly_fraction(rs) / 4.0

import random


def simulate(
    rs: list[float],
    risk_pct: float,
    n_sims: int = 5_000,
    horizon: int | None = None,
    ruin_dd: float = 0.5,
    seed: int = 0,
) -> dict:
    """Monte Carlo par resampling (bootstrap avec remise) des R-multiples
    reels du journal. Equity multiplicative : chaque trade risque risk_pct
    de l'equity courante. Sort la distribution des max drawdowns, la
    probabilite de ruine (DD >= ruin_dd) et la mediane d'equity finale.

    OFFLINE UNIQUEMENT : calibration du Kelly fractionne et comparaison
    d'iterations, jamais en input de decision live."""
    if not rs:
        return {"sims": 0}
    h = horizon or len(rs)
    rng = random.Random(seed)
    dds: list[float] = []
    finals: list[float] = []
    for _ in range(n_sims):
        eq = peak = 1.0
        dd = 0.0
        for _ in range(h):
            eq *= 1.0 + risk_pct * rng.choice(rs)
            peak = max(peak, eq)
            dd = max(dd, 1.0 - eq / peak)
        dds.append(dd)
        finals.append(eq)
    dds.sort()
    finals.sort()

    def q(xs: list[float], p: float) -> float:
        return xs[min(int(p * len(xs)), len(xs) - 1)]

    return {
        "sims": n_sims,
        "horizon": h,
        "risk_pct": risk_pct,
        "dd_p50": q(dds, 0.50),
        "dd_p90": q(dds, 0.90),
        "dd_p99": q(dds, 0.99),
        "ruin_prob": sum(d >= ruin_dd for d in dds) / n_sims,
        "final_p50": q(finals, 0.50),
    }

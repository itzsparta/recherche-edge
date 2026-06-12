import math


def compute_metrics(rows: list[dict]) -> dict:
    """Metriques de performance depuis les lignes du journal.

    Sortino sur les R-multiples (mieux que Sharpe en intraday asymetrique),
    Calmar simplifie sur la periode (pnl total / max drawdown en monnaie).
    Usage : comparaison entre iterations, offline uniquement."""
    if not rows:
        return {"trades": 0}
    pnls = [r["pnl"] for r in rows]
    rs = [r["r_multiple"] for r in rows]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    eq = peak = dd = 0.0
    for p in pnls:
        eq += p
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    mean_r = sum(rs) / len(rs)
    downside = math.sqrt(sum(min(r, 0.0) ** 2 for r in rs) / len(rs))
    return {
        "trades": len(rows),
        "win_rate": len(wins) / len(rows),
        "profit_factor": sum(wins) / abs(sum(losses)) if losses else float("inf"),
        "expectancy_r": mean_r,
        "total_pnl": sum(pnls),
        "max_drawdown": dd,
        "sortino_r": mean_r / downside if downside > 0 else float("inf"),
        "calmar": sum(pnls) / dd if dd > 0 else float("inf"),
    }

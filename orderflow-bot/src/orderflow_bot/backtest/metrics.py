def compute_metrics(rows: list[dict]) -> dict:
    """Metriques de performance depuis les lignes du journal."""
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
    return {
        "trades": len(rows),
        "win_rate": len(wins) / len(rows),
        "profit_factor": sum(wins) / abs(sum(losses)) if losses else float("inf"),
        "expectancy_r": sum(rs) / len(rs),
        "total_pnl": sum(pnls),
        "max_drawdown": dd,
    }

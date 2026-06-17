"""Smoke-plomberie etage 2a : verifie que les klines pilotent le moteur de bout
en bout (zones saines, plans coherents, labels finis) + que le chemin parallele
klines tourne. PASS/FAIL, AUCUNE mesure d'edge. Usage: python scripts/klines_smoke.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from orderflow_bot.backtest.plumbing_checks import (
    label_violations, plan_violations, zone_violations,
)
from orderflow_bot.config import load_config
from orderflow_bot.ingestion.reader import available_days, read_klines_as_ticks
from orderflow_bot.pipeline import PlanGenerator, generate_plans_parallel, simulate_isolated

_DAY_MS = 86_400_000


def _collect_levels_and_plans(cfg):
    """Passe sequentielle : collecte les DailyLevels finalises ET les plans
    (level_rejection) sur tout l'historique klines."""
    gen = PlanGenerator(cfg)
    plans = []
    for t in read_klines_as_ticks(cfg.kline_data_dir, cfg.symbol):
        plans.extend(gen.on_trade(t))
    return gen._levels, plans


def main() -> int:
    cfg = load_config("config.klines.yaml")
    days = available_days(cfg.kline_data_dir, cfg.symbol)
    if not days:
        print("FAIL: aucune kline dans", cfg.kline_data_dir, "/", cfg.symbol)
        return 1

    levels, plans = _collect_levels_and_plans(cfg)
    labels = simulate_isolated(
        cfg, plans,
        read_klines_as_ticks(cfg.kline_data_dir, cfg.symbol),
        eod_flat=cfg.eod_flat,
    )

    problems = (zone_violations(levels)
                + plan_violations(plans, cfg.risk.min_rr)
                + label_violations(labels))

    # chemin parallele klines (la vraie preuve du cablage _block_worker->read_market)
    start, end = days[0] * _DAY_MS, (days[-1] + 1) * _DAY_MS
    par = generate_plans_parallel(cfg, start, end)
    if not par:
        problems.append("generate_plans_parallel (klines) ne produit aucun plan")

    print(f"jours={len(days)} levels={len(levels)} plans={len(plans)} "
          f"labels={len(labels)} plans_par={len(par)}")
    if problems:
        print("FAIL — violations:")
        for p in problems[:20]:
            print("  -", p)
        return 1
    print("PASS — klines pilotent le moteur de bout en bout (zero edge mesure)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import argparse
import asyncio
import json
import logging
from datetime import datetime, timezone

from orderflow_bot.config import load_config


def _ms(d: str | None) -> int | None:
    if d is None:
        return None
    dt = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(prog="orderflow_bot")
    ap.add_argument("command",
                    choices=["record", "backtest", "paper", "validate",
                             "walkforward", "import", "plan-cache", "label-candidates"])
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--start", default=None, help="YYYY-MM-DD (backtest, import, plan-cache, label-candidates)")
    ap.add_argument("--end", default=None, help="YYYY-MM-DD (backtest, import, plan-cache, label-candidates)")
    ap.add_argument("--cache", default="plans_cache.jsonl",
                    help="cache JSONL des plans candidats (plan-cache ecrit, label-candidates lit)")
    ap.add_argument("--labels", default="candidates_outcomes.jsonl",
                    help="JSONL des outcomes isoles par candidat (label-candidates)")
    ap.add_argument("--blocks", type=int, default=None,
                    help="nb de blocs paralleles (plan-cache ; defaut = nb coeurs)")
    ap.add_argument("--journal", default=None, help="journal JSONL (validate)")
    ap.add_argument("--sims", type=int, default=5_000, help="simulations Monte Carlo")
    ap.add_argument("--ruin-dd", type=float, default=0.5,
                    help="drawdown considere comme ruine (fraction)")
    ap.add_argument("--folds", type=int, default=4, help="folds walk-forward")
    ap.add_argument("--warmup-days", type=int, default=20,
                    help="jours de warmup sans trading avant chaque fold")
    args = ap.parse_args()
    cfg = load_config(args.config)

    if args.command == "record":
        from orderflow_bot.live import run_record
        asyncio.run(run_record(cfg))
    elif args.command == "backtest":
        from orderflow_bot.ingestion.reader import read_trades
        from orderflow_bot.pipeline import run_backtest

        trades = read_trades(cfg.market_data_dir, cfg.symbol,
                             start_ms=_ms(args.start), end_ms=_ms(args.end))
        print(json.dumps(run_backtest(cfg, trades), indent=2))
    elif args.command == "plan-cache":
        from orderflow_bot.cache import save_plans
        from orderflow_bot.pipeline import generate_plans_parallel

        if not (args.start and args.end):
            ap.error("plan-cache exige --start et --end (bornes du decoupage)")
        plans = generate_plans_parallel(cfg, _ms(args.start), _ms(args.end),
                                        n_blocks=args.blocks)
        save_plans(args.cache, plans)
        print(json.dumps({"plans": len(plans), "out": args.cache,
                          "start": args.start, "end": args.end,
                          "blocks": args.blocks or "auto"}, indent=2))
    elif args.command == "label-candidates":
        from pathlib import Path

        from orderflow_bot.cache import load_plans
        from orderflow_bot.execution.journal import TradeJournal
        from orderflow_bot.pipeline import (
            simulate_isolated, simulate_isolated_parallel,
        )

        plans = load_plans(args.cache)
        if not plans:
            ap.error(f"cache de plans vide ou absent: {args.cache}")
        s, e = _ms(args.start), _ms(args.end)
        if s is not None and e is not None:        # chemin parallele (par jour, sans warmup)
            outcomes = simulate_isolated_parallel(cfg, s, e, plans, n_blocks=args.blocks)
        else:                                       # repli mono : pas de bornes pour decouper
            from orderflow_bot.ingestion.reader import read_trades
            outcomes = simulate_isolated(
                cfg, plans, read_trades(cfg.market_data_dir, cfg.symbol))
        Path(args.labels).unlink(missing_ok=True)
        j = TradeJournal(args.labels)
        for ct in outcomes:
            j.record(ct)
        print(json.dumps({"candidats": len(plans), "remplis": len(outcomes),
                          "out": args.labels, "blocks": args.blocks or "auto"}, indent=2))
    elif args.command == "validate":
        from orderflow_bot.backtest.metrics import compute_metrics
        from orderflow_bot.backtest.montecarlo import simulate
        from orderflow_bot.execution.journal import TradeJournal
        from orderflow_bot.risk.kelly import kelly_fraction, kelly_quarter

        rows = TradeJournal.load(args.journal or cfg.journal_path)
        rs = [r["r_multiple"] for r in rows]
        report = {
            "metrics": compute_metrics(rows),
            "monte_carlo": simulate(rs, cfg.risk.risk_pct,
                                    n_sims=args.sims, ruin_dd=args.ruin_dd),
            "kelly_full": kelly_fraction(rs),
            "kelly_quarter_cap": kelly_quarter(rs),
            "risk_pct_current": cfg.risk.risk_pct,
        }
        print(json.dumps(report, indent=2))
    elif args.command == "walkforward":
        from orderflow_bot.backtest.walkforward import walk_forward

        print(json.dumps(walk_forward(cfg, n_folds=args.folds,
                                      warmup_days=args.warmup_days), indent=2))
    elif args.command == "import":
        from datetime import date

        from orderflow_bot.ingestion.importer import import_range

        if not args.start:
            ap.error("import exige --start (et --end, sinon --start seul)")
        start = date.fromisoformat(args.start)
        end = date.fromisoformat(args.end) if args.end else start
        print(json.dumps(import_range(cfg, start, end), indent=2))
    else:
        from orderflow_bot.live import run_paper
        asyncio.run(run_paper(cfg))


if __name__ == "__main__":
    main()

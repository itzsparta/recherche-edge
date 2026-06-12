import argparse
import asyncio
import json
import logging

from orderflow_bot.config import load_config


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(prog="orderflow_bot")
    ap.add_argument("command",
                    choices=["record", "backtest", "paper", "validate",
                             "walkforward", "import"])
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--start", default=None, help="YYYY-MM-DD (backtest, import)")
    ap.add_argument("--end", default=None, help="YYYY-MM-DD (backtest, import)")
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
        from datetime import datetime, timezone

        from orderflow_bot.ingestion.reader import read_trades
        from orderflow_bot.pipeline import run_backtest

        def _ms(d: str | None) -> int | None:
            if d is None:
                return None
            dt = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)

        trades = read_trades(cfg.market_data_dir, cfg.symbol,
                             start_ms=_ms(args.start), end_ms=_ms(args.end))
        print(json.dumps(run_backtest(cfg, trades), indent=2))
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

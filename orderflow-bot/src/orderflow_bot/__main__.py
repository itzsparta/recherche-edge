import argparse
import asyncio
import logging

from orderflow_bot.config import load_config


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(prog="orderflow_bot")
    ap.add_argument("command", choices=["record", "backtest", "paper"])
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--start", default=None, help="YYYY-MM-DD (backtest)")
    ap.add_argument("--end", default=None, help="YYYY-MM-DD (backtest)")
    args = ap.parse_args()
    cfg = load_config(args.config)

    if args.command == "record":
        from orderflow_bot.live import run_record
        asyncio.run(run_record(cfg))
    elif args.command == "backtest":
        import json as _json
        from datetime import datetime, timezone

        from orderflow_bot.ingestion.reader import read_trades
        from orderflow_bot.pipeline import run_backtest

        def _ms(d: str | None) -> int | None:
            if d is None:
                return None
            dt = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)

        trades = read_trades(cfg.data_dir, cfg.symbol,
                             start_ms=_ms(args.start), end_ms=_ms(args.end))
        report = run_backtest(cfg, trades)
        print(_json.dumps(report, indent=2))
    else:
        from orderflow_bot.live import run_paper
        asyncio.run(run_paper(cfg))


if __name__ == "__main__":
    main()

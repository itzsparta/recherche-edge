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
        raise SystemExit("backtest: implemente en Task 17")
    else:
        raise SystemExit("paper: implemente en Task 18")


if __name__ == "__main__":
    main()

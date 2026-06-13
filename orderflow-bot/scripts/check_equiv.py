"""Verifie que le backtest 2-passes (generate_plans + execute_plans) produit
le meme resultat que le replay mono-passe (run_backtest) sur donnees reelles.
Garde-fou apres tout refacto perf du pipeline.

Usage: python scripts/check_equiv.py [start YYYY-MM-DD] [end YYYY-MM-DD]
"""
import sys
from datetime import datetime, timezone

from orderflow_bot.config import load_config
from orderflow_bot.ingestion.reader import read_trades
from orderflow_bot.pipeline import execute_plans, generate_plans, run_backtest


def _ms(d: str) -> int:
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def main() -> None:
    start = sys.argv[1] if len(sys.argv) > 1 else "2025-12-01"
    end = sys.argv[2] if len(sys.argv) > 2 else "2025-12-08"
    cfg = load_config("config.yaml")
    s, e = _ms(start), _ms(end)

    def trades():
        return read_trades(cfg.market_data_dir, cfg.symbol, start_ms=s, end_ms=e)

    ref = run_backtest(cfg, trades())               # reference mono-passe
    plans = generate_plans(cfg, trades())           # passe 1
    rep = execute_plans(cfg, plans, trades())       # passe 2

    print(f"fenetre {start}..{end}  plans={len(plans)}")
    print(f"mono-passe : {ref}")
    print(f"2-passes   : {rep}")
    print(f"IDENTIQUE  : {ref == rep}")
    if ref != rep:
        for k in ref:
            if ref[k] != rep.get(k):
                print(f"  diff {k}: {ref[k]} != {rep.get(k)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

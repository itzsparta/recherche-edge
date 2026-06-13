"""Verifie que generate_plans_parallel (passe 1 multi-process) produit les
memes plans que generate_plans (mono-process), et mesure le speedup.

Usage: python scripts/check_parallel.py [start] [end] [n_blocks]
"""
import sys
import time
from datetime import datetime, timezone

from orderflow_bot.config import load_config
from orderflow_bot.ingestion.reader import read_trades
from orderflow_bot.pipeline import generate_plans, generate_plans_parallel


def _ms(d: str) -> int:
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def _key(plans):
    return [(p.ts, p.side, round(p.entry, 6), round(p.stop, 6), round(p.target, 6),
             tuple(sorted(p.meta.items()))) for p in plans]


def main() -> None:
    start = sys.argv[1] if len(sys.argv) > 1 else "2025-12-01"
    end = sys.argv[2] if len(sys.argv) > 2 else "2025-12-08"
    n_blocks = int(sys.argv[3]) if len(sys.argv) > 3 else None
    cfg = load_config("config.yaml")
    s, e = _ms(start), _ms(end)

    t0 = time.time()
    seq = generate_plans(cfg, read_trades(cfg.market_data_dir, cfg.symbol, start_ms=s, end_ms=e))
    t1 = time.time()
    par = generate_plans_parallel(cfg, s, e, n_blocks=n_blocks)
    t2 = time.time()

    seq_t, par_t = t1 - t0, t2 - t1
    print(f"fenetre {start}..{end}  n_blocks={n_blocks or 'auto'}")
    print(f"mono-process : {len(seq):4d} plans en {seq_t:6.1f}s")
    print(f"multi-process: {len(par):4d} plans en {par_t:6.1f}s   speedup x{seq_t / par_t:.1f}")
    print(f"IDENTIQUE    : {_key(seq) == _key(par)}")
    if _key(seq) != _key(par):
        print(f"  seq={len(seq)} par={len(par)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

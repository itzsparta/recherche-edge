"""Sensibilite aux frais de la config gagnante (stop frac=1.0, brut +0.18R).

L'edge brut est reel et positif ; net negatif a cause des frais taker (0.32R).
Question : quel taux taker croise zero ? Re-label le MEME cache sous plusieurs
grilles de frais (mode/frac fixes). Montre le taker de break-even.

Usage: python scripts/test_fees.py [config.yaml] [plans_cache.jsonl] START END [frac]
"""
import statistics as st
import sys

from orderflow_bot.cache import load_plans
from orderflow_bot.config import load_config
from orderflow_bot.pipeline import simulate_isolated_parallel
from orderflow_bot.__main__ import _ms


def deco(label: str, rows: list) -> None:
    net = [c.r_multiple for c in rows]
    fr = [c.fees / ((c.plan.entry - c.plan.stop) * c.plan.side) for c in rows]
    gross = [n + f for n, f in zip(net, fr)]
    print(f"  {label:24s} n={len(rows):5d}  net={st.mean(net):+.3f}R  "
          f"brut={st.mean(gross):+.3f}R  frais={st.mean(fr):.3f}R")


def main() -> None:
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    cache = sys.argv[2] if len(sys.argv) > 2 else "plans_cache.jsonl"
    start, end = _ms(sys.argv[3]), _ms(sys.argv[4])
    frac = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
    base = load_config(cfg_path)
    plans = load_plans(cache)
    print(f"=== {cfg_path} | {cache} | stop frac={frac} ({len(plans)} plans) ===\n")

    # (label, maker, taker) ; slippage inchange
    grids = [
        ("futures actuel .0005",  0.0002,  0.0005),
        ("futures VIP1 .0004",    0.00016, 0.0004),
        ("VIP+BNB .0003",         0.0001,  0.0003),
        ("taker=maker .0002",     0.0002,  0.0002),
        ("zero (plafond brut)",   0.0,     0.0),
    ]
    for label, mk, tk in grids:
        cfg = base.model_copy(deep=True)
        cfg.strategy.entry_mode = "stop"
        cfg.strategy.entry_confirm_frac = frac
        cfg.fees.maker_pct = mk
        cfg.fees.taker_pct = tk
        out = simulate_isolated_parallel(cfg, start, end, plans, n_blocks=16)
        deco(label, out)


if __name__ == "__main__":
    main()

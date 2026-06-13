"""Verifie le VRAI brut de la config stop frac=1.0, sans decomposition.

deco() de test_fees/test_entry_mode calcule fr = frais/risk0_PLAN, mais en mode
stop l'entree est decalee -> risk0_reel != risk0_plan -> fr (et donc brut=net+fr)
gonfle. Ici on n'additionne rien : on lit c.r_multiple, qui vaut toujours
pnl/risk0_reel. A frais=0 -> brut apres slippage. A frais=0 + slip=0 -> signal pur.
Donne mean/std/SE/t pour trancher la significativite.

Usage: python scripts/verify_gross.py [config.yaml] [cache.jsonl] START END [frac]
"""
import statistics as st
import sys

from orderflow_bot.cache import load_plans
from orderflow_bot.config import load_config
from orderflow_bot.pipeline import simulate_isolated_parallel
from orderflow_bot.__main__ import _ms


def stat(label: str, rows: list) -> None:
    r = [c.r_multiple for c in rows]
    if not r:
        print(f"  {label:30s} n=0")
        return
    m = st.mean(r)
    sd = st.stdev(r)
    se = sd / len(r) ** 0.5
    print(f"  {label:30s} n={len(r):5d}  moy={m:+.4f}R  std={sd:.3f}  "
          f"SE={se:.4f}  t={m / se:+.2f}")


def main() -> None:
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    cache = sys.argv[2] if len(sys.argv) > 2 else "plans_cache.jsonl"
    start, end = _ms(sys.argv[3]), _ms(sys.argv[4])
    frac = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
    base = load_config(cfg_path)
    plans = load_plans(cache)
    slip0 = base.fees.slippage_ticks
    print(f"=== stop frac={frac} | {len(plans)} plans "
          f"(r_multiple = pnl/risk0_reel, pas de decompo) ===\n")

    def run(mk: float, tk: float, slip: float) -> list:
        cfg = base.model_copy(deep=True)
        cfg.strategy.entry_mode = "stop"
        cfg.strategy.entry_confirm_frac = frac
        cfg.fees.maker_pct = mk
        cfg.fees.taker_pct = tk
        cfg.fees.slippage_ticks = slip
        return simulate_isolated_parallel(cfg, start, end, plans, n_blocks=16)

    stat("net futures actuel", run(0.0002, 0.0005, slip0))      # sanity ~ -0.138R
    stat("brut (0 frais, slip reel)", run(0.0, 0.0, slip0))     # vrai plafond
    stat("signal pur (0 frais, 0 slip)", run(0.0, 0.0, 0.0))    # edge signal brut


if __name__ == "__main__":
    main()

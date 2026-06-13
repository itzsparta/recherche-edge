"""Teste la mecanique d'entree : limit-au-trigger vs stop-sur-confirmation.

Hypothese : les ~38-40 % de morts-nes (MFE<0.5R) viennent de l'adverse-selection
du fill limit (on est rempli pile quand le prix traverse le niveau a contresens).
En mode stop, on n'entre qu'apres que le prix a avance confirm_frac*risk0 DANS le
sens du trade -> les morts-nes ne confirment jamais -> jamais remplis. Cout : entry
marche (taker+slippage) + RR degrade (entry decalee vers la cible).

Re-label le MEME cache de plans (entry_mode n'affecte que le broker, pas le signal)
avec plusieurs (mode, frac) et compare brut/net/morts-nes/n.

Usage: python scripts/test_entry_mode.py [config.yaml] [plans_cache.jsonl] START END
"""
import statistics as st
import sys

from orderflow_bot.cache import load_plans
from orderflow_bot.config import load_config
from orderflow_bot.pipeline import simulate_isolated_parallel
from orderflow_bot.__main__ import _ms


def deco(label: str, rows: list) -> None:
    if not rows:
        print(f"  {label:18s} n=0")
        return
    net = [c.r_multiple for c in rows]
    fr = [c.fees / ((c.plan.entry - c.plan.stop) * c.plan.side) for c in rows]
    gross = [n + f for n, f in zip(net, fr)]
    born = sum(1 for c in rows if c.mfe_r < 0.5) / len(rows)
    wr = sum(1 for r in net if r > 0) / len(rows)
    print(f"  {label:18s} n={len(rows):5d}  net={st.mean(net):+.3f}R  "
          f"brut={st.mean(gross):+.3f}R  frais={st.mean(fr):.3f}R  "
          f"wr={wr:.0%}  morts-nes={born:.0%}")


def main() -> None:
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    cache = sys.argv[2] if len(sys.argv) > 2 else "plans_cache.jsonl"
    start, end = _ms(sys.argv[3]), _ms(sys.argv[4])
    base = load_config(cfg_path)
    plans = load_plans(cache)
    print(f"=== {cfg_path} | {cache} ({len(plans)} plans) ===\n")

    combos = [("limit", 0.0), ("stop", 0.0), ("stop", 0.25),
              ("stop", 0.5), ("stop", 0.75), ("stop", 1.0)]
    for mode, frac in combos:
        cfg = base.model_copy(deep=True)
        cfg.strategy.entry_mode = mode
        cfg.strategy.entry_confirm_frac = frac
        out = simulate_isolated_parallel(cfg, start, end, plans, n_blocks=16)
        deco(f"{mode} frac={frac}", out)


if __name__ == "__main__":
    main()

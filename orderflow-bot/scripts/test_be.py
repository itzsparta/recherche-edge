"""Impact du passage a BE apres le partiel (move_to_be) sur la config de base
(limit) et la config stop-confirmation. Les morts-nes (MFE<0.5R) meurent AVANT
le partiel -> identiques BE on/off (sanity). Seuls les trades ayant atteint +1R
changent : BE protege le gain pris mais coupe les runners qui mechent sous l'entry.

`>=1R` = fraction ayant atteint le partiel = seuls trades touches par BE.

Usage: python scripts/test_be.py [config.yaml] [cache.jsonl] START END
"""
import statistics as st
import sys

from orderflow_bot.cache import load_plans
from orderflow_bot.config import load_config
from orderflow_bot.pipeline import simulate_isolated_parallel
from orderflow_bot.__main__ import _ms


def deco(label: str, rows: list) -> None:
    if not rows:
        print(f"  {label:28s} n=0")
        return
    r = [c.r_multiple for c in rows]
    wins = [x for x in r if x > 0]
    losses = [x for x in r if x <= 0]
    morts = sum(1 for c in rows if c.mfe_r < 0.5) / len(rows)
    reached = sum(1 for c in rows if c.mfe_r >= 1.0) / len(rows)
    se = st.stdev(r) / len(r) ** 0.5
    print(f"  {label:28s} n={len(rows):5d}  net={st.mean(r):+.3f}R (t={st.mean(r) / se:+.2f})  "
          f"wr={len(wins) / len(rows):.0%}  morts={morts:.0%}  >=1R={reached:.0%}  "
          f"win={st.mean(wins) if wins else 0:+.2f}  loss={st.mean(losses) if losses else 0:+.2f}")


def main() -> None:
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    cache = sys.argv[2] if len(sys.argv) > 2 else "plans_cache.jsonl"
    start, end = _ms(sys.argv[3]), _ms(sys.argv[4])
    base = load_config(cfg_path)
    plans = load_plans(cache)
    print(f"=== {cfg_path} | {cache} ({len(plans)} plans) ===\n")

    combos = [
        ("limit   BE on (actuel)", "limit", 0.0, True),
        ("limit   BE off", "limit", 0.0, False),
        ("stop f=1 BE on", "stop", 1.0, True),
        ("stop f=1 BE off", "stop", 1.0, False),
    ]
    for label, mode, frac, be in combos:
        cfg = base.model_copy(deep=True)
        cfg.strategy.entry_mode = mode
        cfg.strategy.entry_confirm_frac = frac
        cfg.risk.move_to_be = be
        out = simulate_isolated_parallel(cfg, start, end, plans, n_blocks=16)
        deco(label, out)


if __name__ == "__main__":
    main()

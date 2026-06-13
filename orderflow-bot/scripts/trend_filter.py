"""Filtre regime de tendance HTF, PRE-ENREGISTRE (anti-overfit).

Hypothese (du chart 2025-12-16 : 12/12 fades-longs balayes dans un marche
baissier) : le drag se concentre sur les fades A CONTRE-TENDANCE.

Regle figee A PRIORI, zero parametre :
  regime = signe(prix_entree - cloture J-1 UTC)
  with-trend  = side d'accord avec le regime (long si prix>cloture J-1, short si <)
  counter     = side en desaccord
Critere de succes fige A PRIORI : le sous-ensemble with-trend doit montrer
brut > 0 ET meme signe sur les DEUX moities (IS = 1re, OOS = 2e). Sinon -> rejet.

Mesure net (frais reels) ET brut (frais=0, via r_multiple = pnl/risk0_reel, pas
de decompo) sur {tous, with-trend, counter} x {full, IS, OOS}, en limit et stop f=1.

Usage: python scripts/trend_filter.py [config.yaml] [cache.jsonl] START END
"""
import statistics as st
import sys
from pathlib import Path

import duckdb

from orderflow_bot.cache import load_plans
from orderflow_bot.config import load_config
from orderflow_bot.pipeline import simulate_isolated_parallel
from orderflow_bot.__main__ import _ms

_DAY = 86_400_000


def daily_close(cfg) -> dict:
    """Dernier prix de chaque jour UTC -> {jour_index: close}."""
    files = sorted(str(p) for p in (Path(cfg.market_data_dir) / cfg.symbol).glob("*.parquet"))
    con = duckdb.connect()
    try:
        r = con.execute(
            f"SELECT ts // {_DAY} AS d, arg_max(price, ts) AS c "
            "FROM read_parquet(?) GROUP BY d ORDER BY d", [files]).fetchall()
    finally:
        con.close()
    return {int(d): float(c) for d, c in r}


def regime_sign(ct, close: dict):
    """+1 si l'entree est au-dessus de la cloture J-1, -1 sinon. None si J-1 absent."""
    d = ct.plan.ts // _DAY
    pdc = close.get(d - 1)
    if pdc is None:
        return None
    return 1 if ct.plan.entry >= pdc else -1


def line(label: str, net_rows: list, brut_rows: list) -> None:
    if not net_rows:
        print(f"    {label:14s} n=0")
        return
    n = [c.r_multiple for c in net_rows]
    b = [c.r_multiple for c in brut_rows]
    wr = sum(1 for x in n if x > 0) / len(n)
    morts = sum(1 for c in net_rows if c.mfe_r < 0.5) / len(net_rows)
    bt = f"{st.mean(b):+.3f}" if b else "  n/a"
    print(f"    {label:14s} n={len(net_rows):5d}  net={st.mean(n):+.3f}R  brut={bt}R  "
          f"wr={wr:.0%}  morts={morts:.0%}")


def block(title: str, net_rows: list, brut_rows: list, close: dict) -> None:
    def split(rows, kind):
        out = []
        for c in rows:
            r = regime_sign(c, close)
            if r is None:
                continue
            wt = (c.plan.side == r)
            if kind == "all" or (kind == "with" and wt) or (kind == "counter" and not wt):
                out.append(c)
        return out
    print(f"  [{title}]")
    for kind, lab in [("all", "tous"), ("with", "with-trend"), ("counter", "counter-tr")]:
        line(lab, split(net_rows, kind), split(brut_rows, kind))


def main() -> None:
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    cache = sys.argv[2] if len(sys.argv) > 2 else "plans_cache.jsonl"
    start, end = _ms(sys.argv[3]), _ms(sys.argv[4])
    mid = (start + end) // 2
    base = load_config(cfg_path)
    plans = load_plans(cache)
    close = daily_close(base)
    print(f"=== {cfg_path} | {cache} ({len(plans)} plans) | "
          f"IS<{mid} OOS>={mid} ===\n")

    for label, mode, frac in [("LIMIT (base)", "limit", 0.0), ("STOP f=1", "stop", 1.0)]:
        def lab(mk, tk):
            cfg = base.model_copy(deep=True)
            cfg.strategy.entry_mode = mode
            cfg.strategy.entry_confirm_frac = frac
            cfg.fees.maker_pct = mk
            cfg.fees.taker_pct = tk
            return simulate_isolated_parallel(cfg, start, end, plans, n_blocks=16)
        net_rows = lab(base.fees.maker_pct, base.fees.taker_pct)
        brut_rows = lab(0.0, 0.0)
        print(f"### {label}")
        block("FULL", net_rows, brut_rows, close)
        block("IS (1re moitie)", [c for c in net_rows if c.plan.ts < mid],
              [c for c in brut_rows if c.plan.ts < mid], close)
        block("OOS (2e moitie)", [c for c in net_rows if c.plan.ts >= mid],
              [c for c in brut_rows if c.plan.ts >= mid], close)
        print()


if __name__ == "__main__":
    main()

"""Filtre TENDANCE LOCALE (momentum a l'entree), PRE-ENREGISTRE (anti-overfit).

Observation viz (2025-12-16) : grappes de fades-longs qui plongent au meme stop =
on fade un niveau pendant que le prix lui FONCE dedans (momentum adverse). Distinct
du levier #9 (clture J-1, rejete) : ici = pente LOCALE des 15 dernieres minutes.

Regle figee A PRIORI :
  momo_adverse = side * (prix_{t-K} - entry) / risk0     (K = 15 min)
    > 0 = le prix a couru DANS le niveau a contresens du fade (run-into, suspect)
  seuil = mediane sur l'echantillon FULL -> {doux (<=med), raide (>med)}
Hypothese figee : RAIDE = morts-nes = brut pire ; DOUX = brut meilleur.
Critere de succes (dur) : le sous-ensemble DOUX montre brut>0 ET net>0 ET meme
signe sur IS *et* OOS, en LIMIT (maker). Sinon -> rejet.

Mesure net (frais reels) ET brut (frais=0, via r_multiple, pas de decompo) sur
{tous, doux, raide} x {FULL, IS, OOS}, en limit et stop f=1.

Usage: python scripts/local_trend_filter.py [config.yaml] [cache.jsonl] START END
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
_K = 15  # minutes de lookback pour la pente locale (= entry_expire_minutes)


def minute_close(cfg, a: int, b: int) -> dict:
    """Dernier prix de chaque minute UTC sur [a, b) -> {minute_index: close}."""
    files = sorted(str(p) for p in (Path(cfg.market_data_dir) / cfg.symbol).glob("*.parquet"))
    con = duckdb.connect()
    try:
        r = con.execute(
            "SELECT ts // 60000 AS m, arg_max(price, ts) AS c FROM read_parquet(?) "
            "WHERE ts >= ? AND ts < ? GROUP BY m", [files, a, b]).fetchall()
    finally:
        con.close()
    return {int(m): float(c) for m, c in r}


def momo_adverse(ct, close: dict):
    """side*(prix_{t-K} - entry)/risk0. >0 = run-into le niveau. None si manquant."""
    m = ct.plan.ts // 60000
    p0 = close.get(m - _K)
    risk0 = abs(ct.plan.entry - ct.plan.stop)
    if p0 is None or risk0 == 0:
        return None
    return ct.plan.side * (p0 - ct.plan.entry) / risk0


def line(label: str, net_rows: list, brut_rows: list) -> None:
    if not net_rows:
        print(f"    {label:12s} n=0")
        return
    n = [c.r_multiple for c in net_rows]
    b = [c.r_multiple for c in brut_rows]
    wr = sum(1 for x in n if x > 0) / len(n)
    morts = sum(1 for c in net_rows if c.mfe_r < 0.5) / len(net_rows)
    print(f"    {label:12s} n={len(net_rows):5d}  net={st.mean(n):+.3f}R  brut={st.mean(b):+.3f}R  "
          f"wr={wr:.0%}  morts={morts:.0%}")


def block(title: str, net_rows: list, brut_rows: list, close: dict, thr: float) -> None:
    def split(rows, kind):
        out = []
        for c in rows:
            mm = momo_adverse(c, close)
            if mm is None:
                continue
            doux = mm <= thr
            if kind == "all" or (kind == "doux" and doux) or (kind == "raide" and not doux):
                out.append(c)
        return out
    print(f"  [{title}]")
    for kind, lab in [("all", "tous"), ("doux", "doux<=med"), ("raide", "raide>med")]:
        line(lab, split(net_rows, kind), split(brut_rows, kind))


def main() -> None:
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    cache = sys.argv[2] if len(sys.argv) > 2 else "plans_cache.jsonl"
    start, end = _ms(sys.argv[3]), _ms(sys.argv[4])
    mid = (start + end) // 2
    base = load_config(cfg_path)
    plans = load_plans(cache)
    close = minute_close(base, start - _K * 60_000, end)
    print(f"=== {cfg_path} | {cache} ({len(plans)} plans) | K={_K}min | "
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
        vals = [m for c in net_rows if (m := momo_adverse(c, close)) is not None]
        thr = st.median(vals)
        print(f"### {label}   (seuil mediane momo_adverse = {thr:+.3f})")
        block("FULL", net_rows, brut_rows, close, thr)
        block("IS (1re moitie)", [c for c in net_rows if c.plan.ts < mid],
              [c for c in brut_rows if c.plan.ts < mid], close, thr)
        block("OOS (2e moitie)", [c for c in net_rows if c.plan.ts >= mid],
              [c for c in brut_rows if c.plan.ts >= mid], close, thr)
        print()


if __name__ == "__main__":
    main()

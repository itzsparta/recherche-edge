"""Mesure la dilution des frais quand on monte la timeframe / RR.

Compare, sur un cache de plans donne, le brut (relabel frais=0) vs net, et la
distribution du risk0 en points de prix (= largeur de stop). Repond a : "monter
la TF elargit-il le stop assez pour diluer le mur de frais ~0.16R, et reste-t-il
un brut positif ?"

Usage: python scripts/fee_dilution.py CONFIG CACHE START END
"""
import datetime as dt
import math
import sys
from statistics import median

from orderflow_bot.cache import load_plans
from orderflow_bot.config import load_config
from orderflow_bot.pipeline import simulate_isolated_parallel


def _ms(d):
    return int(dt.datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)


def _t(xs):
    n = len(xs)
    if n < 2:
        return 0.0, 0.0
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    return m, (m / (sd / math.sqrt(n)) if sd > 0 else 0.0)


def _risk0(ct):
    entry = next((f.price for f in ct.fills if f.kind == "entry"), ct.plan.entry)
    return abs(entry - ct.plan.stop)


def run(cfg, start, end, plans, label):
    nets = simulate_isolated_parallel(cfg, start, end, plans, n_blocks=16)
    cfg0 = cfg.model_copy(deep=True)
    cfg0.fees.maker_pct = 0.0
    cfg0.fees.taker_pct = 0.0
    cfg0.fees.slippage_ticks = 0
    bruts = simulate_isolated_parallel(cfg0, start, end, plans, n_blocks=16)

    nr = [c.r_multiple for c in nets]
    br = [c.r_multiple for c in bruts]
    r0 = [_risk0(c) for c in nets]
    mae = [c.mae_r for c in nets]
    mfe = [c.mfe_r for c in nets]
    morts = sum(1 for m in mfe if m < 0.5)
    nm, nt = _t(nr)
    bm, bt = _t(br)
    fee_r = bm - nm
    print(f"\n=== {label} : {len(nets)} trades remplis / {len(plans)} plans ===")
    print(f"risk0 (pts prix) : median {median(r0):.1f} | min {min(r0):.1f} | max {max(r0):.1f}")
    print(f"frais-en-R median : {median([c.fees / (_risk0(c) * c.qty) for c in nets if _risk0(c) > 0 and c.qty > 0]):.3f}R")
    print(f"BRUT  R moyen {bm:+.4f}  t={bt:+.2f}")
    print(f"NET   R moyen {nm:+.4f}  t={nm and nt:+.2f}")
    print(f"drag frais     {fee_r:+.4f}R  (brut - net)")
    print(f"morts-nes (MFE<0.5R) : {morts}/{len(nets)} = {100*morts/max(1,len(nets)):.0f}%")
    print(f"MFE median {median(mfe):+.2f}R | MAE median {median(mae):+.2f}R")
    return nm, bm


def main():
    cfg = load_config(sys.argv[1])
    plans = load_plans(sys.argv[2])
    start, end = _ms(sys.argv[3]), _ms(sys.argv[4])
    run(cfg, start, end, plans, f"{sys.argv[1]} x {sys.argv[2]}")


if __name__ == "__main__":
    main()

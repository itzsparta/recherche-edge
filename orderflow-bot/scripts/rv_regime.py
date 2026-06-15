"""Levier #12 (pré-enregistré) : l'espérance du fade est-elle conditionnée par le
RÉGIME DE VOLATILITÉ ? Proxy GRATUIT du régime dealer-gamma (GEX vrai = payant) :

  dealers LONG gamma  -> hedge contre le move -> RV basse  -> mean-reversion -> fade OK
  dealers SHORT gamma -> hedge avec le move   -> RV haute  -> momentum       -> fade meurt

donc low-RV ≈ long-gamma ≈ fade-friendly. C'est un PROXY (la RV est aussi poussée
par les news exogènes), pas le dealer-gamma signé — mais gratuit, n=7974, depuis
notre propre tape.

PRÉ-ENREGISTREMENT (figé AVANT le run, comme #9/#10/#11) :
  - régime = RV trailing 24h à l'entrée (fenêtre PRIMAIRE ; 6h/72h = robustesse seule)
  - split médiane globale -> {low, high}
  - métrique = BRUT (frais=0, relabel direct — JAMAIS net+frais/risk0)
  - hypothèse = fade meilleur en low-RV : brut_low > brut_high ET morts_low < morts_high
  - SUCCÈS = (brut_low - brut_high) >= +0.05R ET même signe en IS ET OOS ET morts_low<morts_high
  - sinon -> pas de gradient sur l'axe gamma-proxy -> rejeté (comme tout le reste)

L'IS/OOS est obligatoire : si « low-RV mieux » n'est que « H2 mieux » repackagé
(décalage de régime H2<H1, le mirage de #11), le signe s'inverse entre moitiés.

Usage: python scripts/rv_regime.py [config.yaml] [cache.jsonl] START END
"""
import math
import statistics as st
import sys

import duckdb
import numpy as np

from orderflow_bot.cache import load_plans
from orderflow_bot.config import load_config
from orderflow_bot.pipeline import simulate_isolated_parallel
from orderflow_bot.__main__ import _ms

_DAY = 86_400_000
BUCKET_MS = 1_800_000          # bars 30 min (last price)
W_PRIMARY = _DAY               # RV trailing 24h (pré-enregistrée)
W_ROBUST = (21_600_000, 3 * _DAY)   # 6h, 72h : robustesse, NON pré-enregistrées


def rv_series(cfg, start: int, end: int):
    """Bars 30min (DuckDB last price) -> (bucket_end_ms[], cumsum returns²[])."""
    glob = f"{cfg.market_data_dir}/{cfg.symbol}/*.parquet"
    con = duckdb.connect()
    try:
        rows = con.execute(
            "SELECT ts//? AS b, last(price ORDER BY ts) AS px FROM read_parquet(?) "
            "WHERE ts >= ? AND ts < ? GROUP BY b ORDER BY b",
            [BUCKET_MS, glob, start - 3 * _DAY, end],   # warmup pour la fenêtre la + longue
        ).fetchall()
    finally:
        con.close()
    b = np.array([r[0] for r in rows], dtype="int64")
    px = np.array([r[1] for r in rows], dtype="float64")
    end_ms = (b + 1) * BUCKET_MS
    lr = np.diff(np.log(px))
    cumsq = np.concatenate([[0.0], np.cumsum(lr * lr)])   # cumsq[i] aligné sur end_ms[i]
    return end_ms, cumsq


def rv_at(end_ms, cumsq, t: int, W: int) -> float:
    """RV (écart-type des log-returns) sur (t-W, t], sans lookahead. NaN si trou."""
    hi = int(np.searchsorted(end_ms, t, side="right")) - 1
    lo = int(np.searchsorted(end_ms, t - W, side="right")) - 1
    if hi < 0 or lo < 0 or hi <= lo:
        return float("nan")
    var = cumsq[hi] - cumsq[lo]
    return math.sqrt(var) if var > 0 else float("nan")


def stats(pairs):
    if not pairs:
        return None
    net = [cn.r_multiple for cn, _ in pairs]
    brut = [cb.r_multiple for _, cb in pairs]
    return {
        "n": len(pairs),
        "net": st.mean(net), "brut": st.mean(brut),
        "wr": sum(1 for x in net if x > 0) / len(net),
        "morts": sum(1 for cn, _ in pairs if cn.mfe_r < 0.5) / len(pairs),
    }


def show(label, s):
    if s is None:
        print(f"  {label:14s} n=0")
        return
    print(f"  {label:14s} n={s['n']:5d}  net={s['net']:+.3f}R  brut={s['brut']:+.3f}R  "
          f"wr={s['wr']:.0%}  morts={s['morts']:.0%}")


def main() -> None:
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    cache = sys.argv[2] if len(sys.argv) > 2 else "plans_cache.jsonl"
    start, end = _ms(sys.argv[3]), _ms(sys.argv[4])
    base = load_config(cfg_path)
    plans = load_plans(cache)

    def lab(mk, tk):
        cfg = base.model_copy(deep=True)
        cfg.fees.maker_pct, cfg.fees.taker_pct = mk, tk
        return simulate_isolated_parallel(cfg, start, end, plans, n_blocks=16)

    net = lab(base.fees.maker_pct, base.fees.taker_pct)
    brut = lab(0.0, 0.0)
    pairs = list(zip(net, brut))
    end_ms, cumsq = rv_series(base, start, end)
    print(__doc__.split("Usage")[0])
    print(f"=== {len(pairs)} candidats remplis | net=frais réels, brut=0 ===")

    def partition(W):
        rv = np.array([rv_at(end_ms, cumsq, cn.opened_ts, W) for cn, _ in pairs])
        ok = ~np.isnan(rv)
        med = float(np.median(rv[ok]))
        low = [pairs[i] for i in range(len(pairs)) if ok[i] and rv[i] <= med]
        high = [pairs[i] for i in range(len(pairs)) if ok[i] and rv[i] > med]
        return low, high, med, int((~ok).sum())

    low, high, med, n_nan = partition(W_PRIMARY)
    sl, sh = stats(low), stats(high)
    print(f"\n### PRIMAIRE — RV trailing 24h (médiane={med:.4f}, {n_nan} sans warmup)")
    show("low-RV", sl)
    show("high-RV", sh)

    # quartiles : un gradient réel doit être ~monotone, pas juste un split binaire
    rv = np.array([rv_at(end_ms, cumsq, cn.opened_ts, W_PRIMARY) for cn, _ in pairs])
    ok = ~np.isnan(rv)
    qs = np.quantile(rv[ok], [0.25, 0.5, 0.75])
    print("\n### quartiles RV 24h (brut monotone croissant->fade meurt avec la vol ?)")
    edges = [-np.inf, *qs, np.inf]
    for q in range(4):
        g = [pairs[i] for i in range(len(pairs)) if ok[i] and edges[q] < rv[i] <= edges[q + 1]]
        show(f"Q{q+1}", stats(g))

    # IS/OOS : le gradient doit tenir DANS chaque moitié (sinon = mirage régime H2)
    mid = (start + end) // 2
    print("\n### IS/OOS (split médiane GLOBALE figée — signe stable obligatoire)")
    deltas = {}
    for half, lo_t, hi_t in (("IS", start, mid), ("OOS", mid, end)):
        hl = [p for p in low if lo_t <= p[0].opened_ts < hi_t]
        hh = [p for p in high if lo_t <= p[0].opened_ts < hi_t]
        a, b = stats(hl), stats(hh)
        da = (a["brut"] - b["brut"]) if a and b else float("nan")
        deltas[half] = da
        print(f"  [{half}] low brut={a['brut']:+.3f}(n{a['n']:4d}) | "
              f"high brut={b['brut']:+.3f}(n{b['n']:4d}) | Δ(low-high)={da:+.3f}R")

    # robustesse (NON pré-enregistré) : autres fenêtres
    print("\n### robustesse autres fenêtres RV (NON pré-enregistré)")
    for W in W_ROBUST:
        lo2, hi2, _, _ = partition(W)
        a, b = stats(lo2), stats(hi2)
        print(f"  RV {W//3_600_000:>2}h  low brut={a['brut']:+.3f} | high brut={b['brut']:+.3f} | "
              f"Δ={a['brut']-b['brut']:+.3f}R")

    # VERDICT pré-enregistré
    d_full = sl["brut"] - sh["brut"]
    morts_ok = sl["morts"] < sh["morts"]
    same_sign = (not math.isnan(deltas["IS"]) and not math.isnan(deltas["OOS"])
                 and math.copysign(1, deltas["IS"]) == math.copysign(1, deltas["OOS"]))
    big = d_full >= 0.05
    green = big and same_sign and morts_ok and deltas["IS"] > 0 and deltas["OOS"] > 0
    print(f"\nΔbrut(low-high)={d_full:+.3f}R (seuil +0.05) | morts low<high={morts_ok} | "
          f"signe stable IS/OOS={same_sign} (IS{deltas['IS']:+.3f} OOS{deltas['OOS']:+.3f})")
    print(f"\n=== VERDICT : {'GRADIENT -> justifie GEX vrai payant' if green else 'PAS DE GRADIENT -> axe gamma rejeté ($0)'} ===")


if __name__ == "__main__":
    main()

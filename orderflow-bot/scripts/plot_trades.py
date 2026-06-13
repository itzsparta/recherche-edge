"""Trace les positions d'un backtest : chemin de prix + niveaux + fills.

Pour une date (ou le jour le plus charge du cache), re-label ce jour via
simulate_isolated (MEME broker que le backtest), puis dessine une grille de
panneaux zoomes : un par trade, prix autour de [entree, sortie], lignes
entry/stop/cible, marqueurs des fills, titre r/mfe/mae. Sert a VOIR pourquoi
les morts-nes meurent (rempli puis demi-tour immediat ?).

Usage:
  python scripts/plot_trades.py [config.yaml] [plans_cache.jsonl] [YYYY-MM-DD]
         [--filter all|morts|wins|loss] [--max N] [--out FICHIER.png]
"""
import math
import sys
from collections import Counter
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from orderflow_bot.cache import load_plans
from orderflow_bot.config import load_config
from orderflow_bot.ingestion.reader import read_trades
from orderflow_bot.pipeline import simulate_isolated
from orderflow_bot.__main__ import _ms

_DAY = 86_400_000


def _arg(flag: str, default):
    if flag in sys.argv:
        return sys.argv[sys.argv.index(flag) + 1]
    return default


def day_price_per_second(cfg, a: int, b: int):
    """Dernier prix par seconde sur [a, b) -> (ts[], price[]), trace leger."""
    files = sorted(str(p) for p in (Path(cfg.market_data_dir) / cfg.symbol).glob("*.parquet"))
    con = duckdb.connect()
    try:
        r = con.execute(
            "SELECT ts // 1000 * 1000 AS s, arg_max(price, ts) AS p "
            "FROM read_parquet(?) WHERE ts >= ? AND ts < ? GROUP BY s ORDER BY s",
            [files, a, b],
        ).fetchnumpy()
    finally:
        con.close()
    return r["s"], r["p"]


def keep(ct, mode: str) -> bool:
    if mode == "morts":
        return ct.mfe_r < 0.5
    if mode == "wins":
        return ct.r_multiple > 0
    if mode == "loss":
        return ct.r_multiple <= 0
    return True


def main() -> None:
    pos = [a for a in sys.argv[1:] if not a.startswith("--")
           and a not in {_arg("--filter", "\0"), _arg("--max", "\0"), _arg("--out", "\0")}]
    cfg_path = pos[0] if len(pos) > 0 else "config.yaml"
    cache = pos[1] if len(pos) > 1 else "plans_cache.jsonl"
    date = pos[2] if len(pos) > 2 else None
    mode = _arg("--filter", "all")
    maxn = int(_arg("--max", "12"))

    cfg = load_config(cfg_path)
    plans = load_plans(cache)
    if date:
        day = (_ms(date) // _DAY) * _DAY
    else:                                   # jour le plus charge du cache
        day = Counter(p.ts // _DAY for p in plans).most_common(1)[0][0] * _DAY
    date_s = date or __import__("datetime").datetime.utcfromtimestamp(day / 1000).strftime("%Y-%m-%d")
    out = _arg("--out", f"trades_{date_s}_{mode}.png")

    day_plans = [p for p in plans if day <= p.ts < day + _DAY]
    if not day_plans:
        print(f"aucun plan le {date_s}")
        return
    ticks = read_trades(cfg.market_data_dir, cfg.symbol,
                        start_ms=day, end_ms=day + _DAY + 3_600_000)  # +1h tail pour EOD
    trades = simulate_isolated(cfg, day_plans, ticks)
    sel = [ct for ct in trades if keep(ct, mode)][:maxn]
    print(f"=== {date_s} | {len(day_plans)} plans, {len(trades)} remplis, "
          f"{len(sel)} affiches (filtre={mode}) ===")
    for ct in sel:
        side = "L" if ct.plan.side == 1 else "S"
        print(f"  {side} r={ct.r_multiple:+.2f}  mfe={ct.mfe_r:.2f}  mae={ct.mae_r:.2f}  "
              f"sortie={ct.fills[-1].kind}")
    if not sel:
        print("rien a tracer")
        return

    ts_s, px_s = day_price_per_second(cfg, day, day + _DAY + 3_600_000)
    ncol = min(3, len(sel))
    nrow = math.ceil(len(sel) / ncol)
    fig, axes = plt.subplots(nrow, ncol, figsize=(5.2 * ncol, 3.3 * nrow), squeeze=False)
    exit_col = {"stop": "tab:red", "target": "tab:green", "eod": "tab:orange", "partial": "tab:blue"}
    for ax, ct in zip(axes.flat, sel):
        p = ct.plan
        a, b = ct.opened_ts, ct.closed_ts
        dur = max(b - a, 60_000)
        lo, hi = a - int(0.4 * dur), b + int(0.4 * dur)
        i0, i1 = np.searchsorted(ts_s, lo), np.searchsorted(ts_s, hi)
        x = (ts_s[i0:i1] - a) / 60_000.0                       # minutes depuis l'entree
        ax.plot(x, px_s[i0:i1], color="0.45", lw=0.8, zorder=1)
        ax.axhline(p.entry, color="tab:blue", lw=0.9, label="entry")
        ax.axhline(p.stop, color="tab:red", ls="--", lw=0.9, label="stop")
        ax.axhline(p.target, color="tab:green", ls="--", lw=0.9, label="cible")
        for f in ct.fills:
            mk = {"entry": "o", "partial": "s", "stop": "x", "target": "*", "eod": "D"}.get(f.kind, ".")
            col = "k" if f.kind == "entry" else exit_col.get(f.kind, "k")
            ax.scatter((f.ts - a) / 60_000.0, f.price, marker=mk, s=55, color=col, zorder=6)
        side = "LONG" if p.side == 1 else "SHORT"
        ax.set_title(f"{side}  r={ct.r_multiple:+.2f}  mfe={ct.mfe_r:.2f}  mae={ct.mae_r:.2f}",
                     fontsize=9)
        ax.set_xlabel("min depuis entree", fontsize=7)
        ax.tick_params(labelsize=7)
    for ax in axes.flat[len(sel):]:
        ax.axis("off")
    fig.suptitle(f"{cfg_path}  |  {date_s}  |  filtre={mode}  "
                 f"(— stop  — cible  | entry=o partiel=□ stop=x cible=★ eod=◆)", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out, dpi=110)
    print(f"-> {out}")


if __name__ == "__main__":
    main()

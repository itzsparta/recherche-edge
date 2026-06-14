"""Phase 0 DOM : le book separe-t-il les fades morts-nes mieux que le tape ?

Pour chaque jour L2 (7 premiers-du-mois gratuits), genere les candidats fade
(meme config.yaml que le no-edge), les labelle (simulate_isolated -> mort-ne si
mfe_r<0.5), joint le book a l'instant du fill, calcule les 4 features DOM, et
mesure la separation (AUC + lift par quartile) vs les features tape stack_vol/
stack_depth. Verdict greenlight PRE-ENREGISTRE -> rapport HTML.

Usage: python scripts/dom_separation.py [config.yaml] [data/l2/BTCUSDT] [--no-open]
"""
import datetime as dt
import glob
import sys
from pathlib import Path

import numpy as np

from orderflow_bot.backtest.separation import evaluate_greenlight, quartile_lift
from orderflow_bot.config import load_config
from orderflow_bot.features import book as bk
from orderflow_bot.ingestion.reader import read_trades
from orderflow_bot.pipeline import generate_plans, simulate_isolated

_DAY = 86_400_000
ORIENT = {"book_defense": -1, "touch_imbalance": -1, "replenish": -1, "pull_rate": +1}
TAPE_FEATS = ["stack_vol", "stack_depth"]
BAND_TICKS = 20
W_MS = 2_000
NORM_WINDOW_MS = 60_000


def days_from_dir(l2dir: str):
    out = []
    for p in sorted(glob.glob(f"{l2dir}/book_snapshot_25_*.csv.gz")):
        date_s = Path(p).name.replace("book_snapshot_25_", "").replace(".csv.gz", "")
        out.append((date_s, p))
    return out


def _day_ms(date_s: str) -> int:
    return int(dt.datetime.strptime(date_s, "%Y-%m-%d")
               .replace(tzinfo=dt.timezone.utc).timestamp() * 1000)


def collect(cfg, date_s: str, l2_path: str) -> list[dict]:
    day = _day_ms(date_s)
    band = BAND_TICKS * cfg.tick_size
    warm = day - cfg.strategy.npoc_lookback_days * _DAY
    gen_ticks = read_trades(cfg.market_data_dir, cfg.symbol, start_ms=warm, end_ms=day + _DAY)
    plans = generate_plans(cfg, gen_ticks, day, day + _DAY)
    if not plans:
        return []
    lab_ticks = read_trades(cfg.market_data_dir, cfg.symbol,
                            start_ms=day, end_ms=day + _DAY + 3_600_000)
    trades = simulate_isolated(cfg, plans, lab_ticks)

    book = bk.load_book_day(l2_path)
    tp = list(read_trades(cfg.market_data_dir, cfg.symbol, start_ms=day, end_ms=day + _DAY))
    t_ts = np.fromiter((t.ts for t in tp), dtype="int64", count=len(tp))
    t_px = np.fromiter((t.price for t in tp), dtype="float64", count=len(tp))
    t_qty = np.fromiter((t.qty for t in tp), dtype="float64", count=len(tp))

    rows, excluded = [], 0
    for ct in trades:
        p = ct.plan
        ot = ct.opened_ts
        i = book.idx_at(ot)
        if i < 0:
            excluded += 1
            continue
        norm = book.trailing_median_total(ot, NORM_WINDOW_MS)
        rows.append({
            "day": date_s,
            "mort_ne": ct.mfe_r < 0.5,
            "book_defense": bk.book_defense(book, i, p.entry, p.side, band, norm),
            "touch_imbalance": bk.touch_imbalance(book, i, p.entry, p.side, band),
            "replenish": bk.replenish(book, t_ts, t_px, t_qty, p.entry, p.side, ot, W_MS, band),
            "pull_rate": bk.pull_rate(book, t_ts, t_px, t_qty, p.entry, p.side, ot, W_MS, band),
            "stack_vol": float(p.meta.get("stack_vol", float("nan"))),
            "stack_depth": float(p.meta.get("stack_depth", float("nan"))),
        })
    print(f"{date_s}: {len(rows)} joints, {excluded} exclus (pas de snapshot <= fill)")
    return rows


def viz(verdict, n, base, out="dom_separation.html", do_open=True):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    feats = list(ORIENT)
    fig = make_subplots(rows=1, cols=2, column_widths=[0.45, 0.55],
                        subplot_titles=("AUC oriente (>0.5 = separe)", f"Lift quartile — {verdict['best_feat']}"),
                        specs=[[{"type": "bar"}, {"type": "bar"}]])
    aucs = [verdict["book_auc"][f] for f in feats]
    cols = ["#26a69a" if a >= 0.60 else "#ef5350" for a in aucs]
    fig.add_bar(x=feats, y=aucs, marker_color=cols, row=1, col=1, name="book")
    fig.add_bar(x=list(verdict["tape_auc"]), y=list(verdict["tape_auc"].values()),
                marker_color="#888", row=1, col=1, name="tape")
    fig.add_hline(y=0.60, line=dict(color="#fff", dash="dash"), row=1, col=1)
    lift = verdict["lift"]
    fig.add_bar(x=[f"Q{k+1}" for k in range(len(lift))], y=lift,
                marker_color="#ffb74d", row=1, col=2, name="taux mort-ne")
    fig.add_hline(y=base, line=dict(color="#fff", dash="dash"), row=1, col=2)
    cks = "".join("✅" if verdict[c] else "❌" for c in ("c1", "c2", "c3", "c4"))
    verdict_txt = "GREENLIGHT ✅" if verdict["green"] else "KILL ❌"
    fig.update_layout(
        template="plotly_dark", height=600, showlegend=True,
        title=f"PHASE 0 DOM — {verdict_txt}  |  best '{verdict['best_feat']}' "
              f"AUC={verdict['best_auc']:.3f} (tape {verdict['best_tape']:.3f})  |  "
              f"n={n}, base mort-ne={base:.2f}  |  c1c2c3c4={cks} "
              f"(jours OK {verdict['by_day_ok']}/7)")
    fig.write_html(out, include_plotlyjs=True)
    print(f"-> {out}")
    if do_open:
        import webbrowser
        webbrowser.open(Path(out).resolve().as_uri())


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cfg_path = next((a for a in args if a.endswith(".yaml")), "config.yaml")
    l2dir = next((a for a in args if "l2" in a.replace("\\", "/")), "data/l2/BTCUSDT")
    cfg = load_config(cfg_path)
    days = days_from_dir(l2dir)
    if not days:
        print(f"aucun book_snapshot_25_*.csv.gz dans {l2dir}")
        return
    rows = []
    for date_s, p in days:
        rows += collect(cfg, date_s, p)
    if not rows:
        print("aucun candidat joint")
        return
    n = len(rows)
    base = sum(r["mort_ne"] for r in rows) / n
    print(f"\n=== {n} candidats | base mort-ne = {base:.3f} ===")
    verdict = evaluate_greenlight(rows, [d for d, _ in days], ORIENT, TAPE_FEATS)
    for f in ORIENT:
        print(f"  {f:16s} AUC={verdict['book_auc'][f]:.3f}")
    for f, a in verdict["tape_auc"].items():
        print(f"  [tape] {f:10s} AUC={a:.3f}")
    print(f"\nbest book = {verdict['best_feat']} ({verdict['best_auc']:.3f}) "
          f"vs tape {verdict['best_tape']:.3f}")
    print(f"c1 AUC>=0.60={verdict['c1']} | c2 lift monotone={verdict['c2']} | "
          f"c3 jours>=6/7={verdict['c3']} ({verdict['by_day_ok']}) | c4 dAUC>=0.05={verdict['c4']}")
    print(f"\n=== VERDICT : {'GREENLIGHT (Phase 1)' if verdict['green'] else 'KILL thèse L2'} ===")
    viz(verdict, n, base, do_open="--no-open" not in sys.argv)


if __name__ == "__main__":
    main()

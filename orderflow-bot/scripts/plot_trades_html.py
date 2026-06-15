"""Graphe INTERACTIF des positions d'un backtest (Plotly, HTML autonome).

Bougies 1-min du jour + marqueurs entree/sortie de chaque trade (zoom, pan,
survol = detail r/mfe/mae/sens/sortie). Outil reutilisable pour n'importe quel
backtest futur. Sur nos donnees Binance (pas besoin de MT5/TradingView, qui
charteraient leur propre flux).

Usage:
  python scripts/plot_trades_html.py [config.yaml] [cache.jsonl] [YYYY-MM-DD]
         [--filter all|morts|wins|loss] [--max N] [--out FICHIER.html] [--no-open]

Ouvre le HTML au navigateur par defaut a la fin (--no-open pour suffire en batch).
"""
import datetime as dt
import sys
import webbrowser
from collections import Counter
from pathlib import Path

import duckdb
import plotly.graph_objects as go

from orderflow_bot.cache import load_plans
from orderflow_bot.config import load_config
from orderflow_bot.ingestion.reader import read_trades
from orderflow_bot.pipeline import simulate_isolated
from orderflow_bot.__main__ import _ms

_DAY = 86_400_000


def _arg(flag: str, default):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def ohlc_1min(cfg, a: int, b: int):
    files = sorted(str(p) for p in (Path(cfg.market_data_dir) / cfg.symbol).glob("*.parquet"))
    con = duckdb.connect()
    try:
        rows = con.execute(
            "SELECT (ts // 60000) * 60000 AS m, arg_min(price, ts) o, max(price) h, "
            "min(price) l, arg_max(price, ts) c FROM read_parquet(?) "
            "WHERE ts >= ? AND ts < ? GROUP BY m ORDER BY m", [files, a, b]).fetchall()
    finally:
        con.close()
    return rows


def keep(ct, mode: str) -> bool:
    if mode == "morts":
        return ct.mfe_r < 0.5
    if mode == "wins":
        return ct.r_multiple > 0
    if mode == "loss":
        return ct.r_multiple <= 0
    return True


def tdt(ms: int) -> dt.datetime:
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc)


def main() -> None:
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    skip = {_arg("--filter", "\0"), _arg("--max", "\0"), _arg("--out", "\0")}
    pos = [a for a in pos if a not in skip]
    cfg_path = pos[0] if len(pos) > 0 else "config.yaml"
    cache = pos[1] if len(pos) > 1 else "plans_cache.jsonl"
    date = pos[2] if len(pos) > 2 else None
    mode = _arg("--filter", "all")
    maxn = int(_arg("--max", "40"))

    cfg = load_config(cfg_path)
    plans = load_plans(cache)
    if date:
        day = (_ms(date) // _DAY) * _DAY
    else:
        day = Counter(p.ts // _DAY for p in plans).most_common(1)[0][0] * _DAY
    date_s = date or tdt(day).strftime("%Y-%m-%d")
    out = _arg("--out", f"trades_{date_s}_{mode}.html")

    day_plans = [p for p in plans if day <= p.ts < day + _DAY]
    if not day_plans:
        print(f"aucun plan le {date_s}")
        return
    ticks = read_trades(cfg.market_data_dir, cfg.symbol,
                        start_ms=day, end_ms=day + _DAY + 3_600_000)
    trades = simulate_isolated(cfg, day_plans, ticks)
    sel = [ct for ct in trades if keep(ct, mode)][:maxn]
    print(f"=== {date_s} | {len(day_plans)} plans, {len(trades)} remplis, "
          f"{len(sel)} traces (filtre={mode}) ===")
    if not sel:
        print("rien a tracer")
        return

    candles = ohlc_1min(cfg, day, day + _DAY)
    times = [tdt(m) for m, *_ in candles]
    closes = [c for *_, c in candles]
    fig = go.Figure(go.Candlestick(
        x=times,
        open=[o for _, o, *_ in candles], high=[h for _, _, h, _, _ in candles],
        low=[l for _, _, _, l, _ in candles], close=closes,
        name="prix", increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
        opacity=0.55))
    # MA30 = tendance locale (le "sens" que l'oeil lit sur le chart)
    win = 30
    ma = [sum(closes[i - win + 1:i + 1]) / win if i >= win - 1 else None
          for i in range(len(closes))]
    fig.add_trace(go.Scatter(x=times, y=ma, mode="lines", name="MA30 (tendance locale)",
                             line=dict(color="#ffb74d", width=1.2), hoverinfo="skip"))

    draw_levels = len(sel) <= 40
    for ct in sel:
        p = ct.plan
        win = ct.r_multiple > 0
        col = "#26a69a" if win else "#ef5350"
        t0, t1 = tdt(ct.opened_ts), tdt(ct.fills[-1].ts)
        dur = (ct.fills[-1].ts - ct.opened_ts) // 60000
        info = (f"{'LONG' if p.side == 1 else 'SHORT'}  r={ct.r_multiple:+.2f}  "
                f"mfe={ct.mfe_r:.2f}  mae={ct.mae_r:.2f}  "
                f"entry={p.entry:.1f} stop={p.stop:.1f} tgt={p.target:.1f}  "
                f"{dur}min  sortie={ct.fills[-1].kind}")
        # entree -> sortie : ligne + marqueurs
        fig.add_trace(go.Scatter(
            x=[t0, t1], y=[ct.fills[0].price, ct.fills[-1].price], mode="lines+markers",
            line=dict(color=col, width=1.2),
            marker=dict(size=[11, 9], symbol=["triangle-up" if p.side == 1 else "triangle-down", "x"],
                        color=col, line=dict(width=1, color="#222")),
            name=info, text=[f"ENTREE  {info}", f"SORTIE  {info}"],
            hoverinfo="text", showlegend=False))
        if draw_levels:
            for lvl, lc, dash in [(p.stop, "#ef5350", "dot"), (p.target, "#26a69a", "dot")]:
                fig.add_shape(type="line", x0=t0, x1=t1, y0=lvl, y1=lvl,
                              line=dict(color=lc, width=0.8, dash=dash), opacity=0.5)

    fig.update_layout(
        title=f"{cfg_path} | {date_s} | filtre={mode} | {len(sel)}/{len(trades)} remplis affiches "
              f"(--max {maxn}) — ▲long ▼short, x=sortie, vert=win rouge=loss",
        xaxis_rangeslider_visible=False, template="plotly_dark",
        hovermode="closest", height=800)
    fig.write_html(out, include_plotlyjs=True)
    print(f"-> {out}  (HTML autonome)")
    if "--no-open" not in sys.argv:
        webbrowser.open(Path(out).resolve().as_uri())   # ouvre au navigateur defaut


if __name__ == "__main__":
    main()

"""Viz du PORTEFEUILLE REEL (post-filtre), Plotly HTML autonome.

Contrairement a plot_trades_html.py (flux brut de candidats, simulate_isolated),
ici on rejoue le portefeuille reel via execute_plans : cap max_trades_per_day,
sessions, stop journalier, une seule position, compounding. Le journal qui en
sort = les trades VRAIMENT pris (~218 sur 6 mois, pas 7974 candidats).

Deux sorties :
  - courbe d'equite (tous les trades, drawdown, metriques)
  - une journee (bougies 1-min + les <=3 trades reels, sessions ombrees)

Usage:
  python scripts/plot_portfolio.py [config.yaml] [cache.jsonl] [YYYY-MM-DD]
         [--journal portfolio_journal.jsonl] [--refresh] [--no-open]

--refresh rejoue le backtest (sinon reutilise le journal existant = instantane).
"""
import datetime as dt
import sys
from collections import Counter
from itertools import accumulate
from pathlib import Path

import duckdb
import plotly.graph_objects as go

from orderflow_bot.cache import load_plans
from orderflow_bot.config import load_config
from orderflow_bot.execution.journal import TradeJournal
from orderflow_bot.__main__ import _ms

_DAY = 86_400_000


def _arg(flag: str, default):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def tdt(ms: int) -> dt.datetime:
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc)


def _files(cfg):
    return sorted(str(p) for p in (Path(cfg.market_data_dir) / cfg.symbol).glob("*.parquet"))


def _ohlc(cfg, a: int, b: int, bucket_ms: int):
    con = duckdb.connect()
    try:
        return con.execute(
            f"SELECT (ts // {bucket_ms}) * {bucket_ms} AS m, arg_min(price, ts) o, "
            "max(price) h, min(price) l, arg_max(price, ts) c "
            "FROM read_parquet(?) WHERE ts >= ? AND ts < ? GROUP BY m ORDER BY m",
            [_files(cfg), a, b]).fetchall()
    finally:
        con.close()


def ohlc_1min(cfg, a: int, b: int):
    return _ohlc(cfg, a, b, 60_000)


def daily_close(cfg, a: int, b: int) -> dict:
    """Dernier prix de chaque jour UTC -> {jour_index: close} (regime #9)."""
    con = duckdb.connect()
    try:
        r = con.execute(
            f"SELECT ts // {_DAY} AS d, arg_max(price, ts) c FROM read_parquet(?) "
            "WHERE ts >= ? AND ts < ? GROUP BY d", [_files(cfg), a - _DAY, b]).fetchall()
    finally:
        con.close()
    return {int(d): float(c) for d, c in r}


def build_journal(cfg, plans, jpath: str, refresh: bool) -> list[dict]:
    """Rejoue le portefeuille reel -> journal. Reutilise si deja present."""
    if Path(jpath).exists() and not refresh:
        return TradeJournal.load(jpath)
    from orderflow_bot.ingestion.reader import read_trades
    from orderflow_bot.pipeline import execute_plans
    cfg2 = cfg.model_copy(deep=True)
    cfg2.journal_path = jpath
    print(f"backtest portefeuille (stream complet, ~min)... -> {jpath}")
    rep = execute_plans(cfg2, plans, read_trades(cfg2.market_data_dir, cfg2.symbol))
    print(f"  metriques: trades={rep.get('trades')}  "
          f"expectancy_r={rep.get('expectancy_r')}  win_rate={rep.get('win_rate')}")
    return TradeJournal.load(jpath)


def open_html(out: str) -> None:
    if "--no-open" not in sys.argv:
        import webbrowser
        webbrowser.open(Path(out).resolve().as_uri())


def equity_html(cfg, rows: list[dict]) -> str:
    rows = sorted(rows, key=lambda r: r["closed_ts"])
    xs = [tdt(r["closed_ts"]) for r in rows]
    eq = list(accumulate((r["pnl"] for r in rows), initial=cfg.equity))[1:]
    peak = list(accumulate(eq, max))
    dd = [e - p for e, p in zip(eq, peak)]
    sumr = sum(r["r_multiple"] for r in rows)
    wr = sum(1 for r in rows if r["r_multiple"] > 0) / len(rows)
    maxdd = min(dd) if dd else 0.0
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=eq, mode="lines", name="equity $",
                             line=dict(color="#26a69a", width=1.6)))
    fig.add_trace(go.Scatter(x=xs, y=peak, mode="lines", name="pic",
                             line=dict(color="#888", width=0.8, dash="dot")))
    win = [(x, e) for x, e, r in zip(xs, eq, rows) if r["r_multiple"] > 0]
    los = [(x, e) for x, e, r in zip(xs, eq, rows) if r["r_multiple"] <= 0]
    for pts, col, nm in [(win, "#26a69a", "win"), (los, "#ef5350", "loss")]:
        if pts:
            fig.add_trace(go.Scatter(x=[p[0] for p in pts], y=[p[1] for p in pts],
                          mode="markers", name=nm,
                          marker=dict(size=5, color=col), hoverinfo="x+y"))
    fig.update_layout(
        title=f"PORTEFEUILLE reel | {len(rows)} trades | net {sumr:+.1f}R | "
              f"pnl {eq[-1] - cfg.equity:+.0f}$ | wr {wr:.0%} | maxDD {maxdd:+.0f}$",
        template="plotly_dark", height=750, hovermode="x unified")
    out = "portfolio_equity.html"
    fig.write_html(out, include_plotlyjs=True)
    print(f"-> {out}")
    return out


def _trend_tagger(cfg, rows):
    """Tag with/contre-tendance par trade (regime = signe(entry - clôture J-1))."""
    a = min(r["opened_ts"] for r in rows)
    b = max(r["closed_ts"] for r in rows) + _DAY
    close = daily_close(cfg, a, b)

    def tag(r) -> str:
        pdc = close.get(r["opened_ts"] // _DAY - 1)
        if pdc is None:
            return "?"
        reg = 1 if r["plan"]["entry"] >= pdc else -1
        return "with" if r["plan"]["side"] == reg else "contre"
    return tag


def overview_html(cfg, rows: list[dict]) -> str:
    """TOUS les trades sur une seule vue zoomable (bougies horaires + marqueurs)."""
    import statistics as st
    rows = sorted(rows, key=lambda r: r["opened_ts"])
    tag = _trend_tagger(cfg, rows)
    w = [r for r in rows if tag(r) == "with"]
    c = [r for r in rows if tag(r) == "contre"]
    unk = [r for r in rows if tag(r) == "?"]

    def mr(g):
        return st.mean(r["r_multiple"] for r in g) if g else float("nan")
    print(f"with-trend n={len(w)} R={mr(w):+.3f} | contre n={len(c)} R={mr(c):+.3f} | "
          f"sans-J-1 n={len(unk)}")

    a, b = rows[0]["opened_ts"], rows[-1]["closed_ts"] + _DAY
    candles = _ohlc(cfg, a, b, 3_600_000)
    fig = go.Figure(go.Candlestick(
        x=[tdt(m) for m, *_ in candles],
        open=[o for _, o, *_ in candles], high=[h for _, _, h, _, _ in candles],
        low=[l for _, _, _, l, _ in candles], close=[cc for *_, cc in candles],
        name="prix 1H", increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350", opacity=0.4))
    # SL / TP : un segment horizontal par trade, de l'entree a la sortie
    sx, sy, tx, ty = [], [], [], []
    for r in rows:
        t0, t1 = tdt(r["opened_ts"]), tdt(r["fills"][-1]["ts"])
        sx += [t0, t1, None]
        sy += [r["plan"]["stop"], r["plan"]["stop"], None]
        tx += [t0, t1, None]
        ty += [r["plan"]["target"], r["plan"]["target"], None]
    fig.add_trace(go.Scatter(x=sx, y=sy, mode="lines", name="SL", opacity=0.45,
                             line=dict(color="#ef5350", width=1, dash="dot"), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=tx, y=ty, mode="lines", name="TP", opacity=0.45,
                             line=dict(color="#26a69a", width=1, dash="dot"), hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=[tdt(r["opened_ts"]) for r in rows],
        y=[r["fills"][0]["price"] for r in rows], mode="markers", name="trades",
        marker=dict(size=9, line=dict(width=1, color="#222"),
                    color=["#26a69a" if r["r_multiple"] > 0 else "#ef5350" for r in rows],
                    symbol=["triangle-up" if r["plan"]["side"] == 1 else "triangle-down"
                            for r in rows]),
        text=[f"{tdt(r['opened_ts']):%Y-%m-%d %H:%M}  "
              f"{'LONG' if r['plan']['side'] == 1 else 'SHORT'}  r={r['r_multiple']:+.2f}  "
              f"pnl={r['pnl']:+.0f}$  [{tag(r)}-trend]  sortie={r['fills'][-1]['kind']}"
              for r in rows], hoverinfo="text"))
    fig.update_layout(
        title=f"PORTEFEUILLE | TOUS les {len(rows)} trades | "
              f"with-trend {mr(w):+.3f}R (n{len(w)}) vs contre {mr(c):+.3f}R (n{len(c)}) "
              f"— ▲long ▼short, vert=win rouge=loss",
        xaxis_rangeslider_visible=False, template="plotly_dark",
        hovermode="closest", height=800)
    out = "portfolio_all_trades.html"
    fig.write_html(out, include_plotlyjs=True)
    print(f"-> {out}")
    return out


def day_html(cfg, rows: list[dict], date: str | None) -> str | None:
    byday = Counter(r["opened_ts"] // _DAY for r in rows)
    if not byday:
        print("journal vide")
        return None
    day = (_ms(date) // _DAY) * _DAY if date else byday.most_common(1)[0][0] * _DAY
    date_s = date or tdt(day).strftime("%Y-%m-%d")
    sel = [r for r in rows if day <= r["opened_ts"] < day + _DAY]
    print(f"=== {date_s} | {len(sel)} trades reels (portefeuille) ===")
    if not sel:
        print("aucun trade reel ce jour")
        return None

    candles = ohlc_1min(cfg, day, day + _DAY)
    fig = go.Figure(go.Candlestick(
        x=[tdt(m) for m, *_ in candles],
        open=[o for _, o, *_ in candles], high=[h for _, _, h, _, _ in candles],
        low=[l for _, _, _, l, _ in candles], close=[c for *_, c in candles],
        name="prix", increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
        opacity=0.55))
    # sessions ombrees (fenetre ou les entrees sont autorisees)
    for s in cfg.sessions:
        sh, sm = map(int, s.start.split(":"))
        eh, em = map(int, s.end.split(":"))
        fig.add_vrect(x0=tdt(day + (sh * 60 + sm) * 60_000),
                      x1=tdt(day + (eh * 60 + em) * 60_000),
                      fillcolor="#5c6bc0", opacity=0.10, line_width=0)
    for r in sel:
        p, f0, f1 = r["plan"], r["fills"][0], r["fills"][-1]
        winr = r["r_multiple"] > 0
        col = "#26a69a" if winr else "#ef5350"
        t0, t1 = tdt(r["opened_ts"]), tdt(f1["ts"])
        dur = (f1["ts"] - r["opened_ts"]) // 60000
        info = (f"{'LONG' if p['side'] == 1 else 'SHORT'}  r={r['r_multiple']:+.2f}  "
                f"pnl={r['pnl']:+.0f}$  mfe={r['mfe_r']:.2f} mae={r['mae_r']:.2f}  "
                f"entry={p['entry']:.1f} stop={p['stop']:.1f} tgt={p['target']:.1f}  "
                f"{dur}min  sortie={f1['kind']}")
        fig.add_trace(go.Scatter(
            x=[t0, t1], y=[f0["price"], f1["price"]], mode="lines+markers",
            line=dict(color=col, width=1.4),
            marker=dict(size=[12, 10],
                        symbol=["triangle-up" if p["side"] == 1 else "triangle-down", "x"],
                        color=col, line=dict(width=1, color="#222")),
            name=info, text=[f"ENTREE  {info}", f"SORTIE  {info}"],
            hoverinfo="text", showlegend=False))
        for lvl, lc in [(p["stop"], "#ef5350"), (p["target"], "#26a69a")]:
            fig.add_shape(type="line", x0=t0, x1=t1, y0=lvl, y1=lvl,
                          line=dict(color=lc, width=0.8, dash="dot"), opacity=0.5)
    fig.update_layout(
        title=f"PORTEFEUILLE reel | {date_s} | {len(sel)} trades pris "
              f"(zone bleue = session ; ▲long ▼short, x=sortie, vert=win)",
        xaxis_rangeslider_visible=False, template="plotly_dark",
        hovermode="closest", height=800)
    out = f"portfolio_day_{date_s}.html"
    fig.write_html(out, include_plotlyjs=True)
    print(f"-> {out}")
    return out


def main() -> None:
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    skip = {_arg("--journal", "\0")}
    pos = [a for a in pos if a not in skip]
    cfg_path = pos[0] if len(pos) > 0 else "config.yaml"
    cache = pos[1] if len(pos) > 1 else "plans_cache.jsonl"
    date = pos[2] if len(pos) > 2 else None
    jpath = _arg("--journal", "portfolio_journal.jsonl")

    cfg = load_config(cfg_path)
    plans = load_plans(cache)
    rows = build_journal(cfg, plans, jpath, refresh="--refresh" in sys.argv)
    if not rows:
        print("aucun trade au portefeuille")
        return
    all_out = overview_html(cfg, rows)      # TOUS les trades (defaut)
    eq_out = equity_html(cfg, rows)
    open_html(all_out)
    open_html(eq_out)
    if date:                                # une journee detaillee seulement si demandee
        day_out = day_html(cfg, rows, date)
        if day_out:
            open_html(day_out)


if __name__ == "__main__":
    main()

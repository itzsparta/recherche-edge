"""Audit anti-overfitting (Lopez de Prado) sur les filtres empiles.

Repond a : "vu le nombre de variantes testees, la moins-pire config a-t-elle la
moindre chance d'etre reelle, ou est-ce du bruit selectionne ?"

- Deflated Sharpe Ratio (DSR) : deflate le Sharpe de la meilleure config par le
  nombre d'essais N + non-normalite (skew/kurtosis). DSR = P(SR_vrai > SR0).
  DSR > 0.95 = significatif malgre le multiple-testing. (Bailey & LdP 2014.)
- PBO via CSCV (avec embargo) : proba que la config best in-sample soit sous la
  mediane out-of-sample = proba d'overfitting de la SELECTION. (Bailey & LdP 2015.)

Les "configs" = les filtres que j'ai empiles (session, jour, tendance) appliques
au meme labeling fade net. T = jours, rendement journalier = R moyen net des
trades selectionnes ce jour (0 si aucun). Self-test synthetique a chaque run.

Usage: python scripts/overfit_audit.py [config.yaml] [cache.jsonl] START END
       python scripts/overfit_audit.py --selftest
"""
import datetime as dt
import math
import random
import sys
from itertools import combinations
from pathlib import Path
from statistics import NormalDist

from orderflow_bot.cache import load_plans
from orderflow_bot.config import load_config

_DAY = 86_400_000
_N01 = NormalDist()
WD = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]
SESS = ["asian", "london", "ny", "late"]


# ---------- stats ----------
def sharpe(xs: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    m = sum(xs) / n
    var = sum((x - m) ** 2 for x in xs) / n
    s = math.sqrt(var)
    return m / s if s > 0 else 0.0


def _moments(xs: list[float]) -> tuple[float, float]:
    n = len(xs)
    m = sum(xs) / n
    s = math.sqrt(sum((x - m) ** 2 for x in xs) / n)
    if s == 0:
        return 0.0, 3.0
    sk = sum(((x - m) / s) ** 3 for x in xs) / n
    ku = sum(((x - m) / s) ** 4 for x in xs) / n
    return sk, ku


def deflated_sharpe(rets: list[float], n_trials: int, var_trials: float):
    """Renvoie (DSR, SR_hat, SR0). SR par periode (pas annualise)."""
    T = len(rets)
    sr = sharpe(rets)
    g = 0.5772156649015329  # Euler-Mascheroni
    sr0 = math.sqrt(var_trials) * (
        (1 - g) * _N01.inv_cdf(1 - 1 / n_trials)
        + g * _N01.inv_cdf(1 - 1 / (n_trials * math.e)))
    sk, ku = _moments(rets)
    denom = math.sqrt(max(1e-12, 1 - sk * sr + (ku - 1) / 4 * sr ** 2))
    z = (sr - sr0) * math.sqrt(T - 1) / denom
    return _N01.cdf(z), sr, sr0


def pbo_cscv(M: list[list[float]], S: int = 12, embargo: int = 1):
    """M = T lignes x N configs. Renvoie (PBO, logit moyen)."""
    T, N = len(M), len(M[0])
    size = T // S
    subs = [list(range(i * size, (i + 1) * size)) for i in range(S)]
    subs[-1] = list(range((S - 1) * size, T))

    def perf(rows, j):
        return sharpe([M[r][j] for r in rows])

    n_le0, tot, lam_sum = 0, 0, 0.0
    for combo in combinations(range(S), S // 2):
        is_set = set(combo)
        oos_rows = set(r for si in range(S) if si not in is_set for r in subs[si])
        is_rows = [r for si in combo for r in subs[si]
                   if not any((r + d) in oos_rows for d in range(-embargo, embargo + 1))]
        oos_rows = sorted(oos_rows)
        is_sr = [perf(is_rows, j) for j in range(N)]
        nstar = max(range(N), key=lambda j: is_sr[j])
        oos_sr = [perf(oos_rows, j) for j in range(N)]
        rank = sorted(range(N), key=lambda j: oos_sr[j]).index(nstar)  # 0=pire
        w = (rank + 1) / (N + 1)
        lam = math.log(w / (1 - w))
        lam_sum += lam
        tot += 1
        if lam <= 0:
            n_le0 += 1
    return n_le0 / tot, lam_sum / tot


# ---------- self-test ----------
def selftest():
    random.seed(0)
    T, N = 120, 12
    noise = [[random.gauss(0, 1) for _ in range(N)] for _ in range(T)]
    pbo_n, _ = pbo_cscv(noise)
    dom = [[random.gauss(0, 1) + (0.8 if j == 0 else 0.0) for j in range(N)]
           for _ in range(T)]
    pbo_d, _ = pbo_cscv(dom)
    print(f"[self-test] PBO bruit iid = {pbo_n:.2f} (attendu ~0.5)  |  "
          f"PBO config dominante = {pbo_d:.2f} (attendu ~0.0)")
    dsr_noise, sr, sr0 = deflated_sharpe([random.gauss(0, 1) for _ in range(T)], N,
                                         var_trials=0.04)
    print(f"[self-test] DSR sur bruit = {dsr_noise:.2f} (attendu <0.95), SR={sr:+.3f} SR0={sr0:+.3f}")


# ---------- audit reel ----------
def hour(ts):
    return dt.datetime.fromtimestamp(ts / 1000, dt.timezone.utc).hour


def wday(ts):
    return dt.datetime.fromtimestamp(ts / 1000, dt.timezone.utc).weekday()


def sess(h):
    return SESS[0] if h < 8 else SESS[1] if h < 13 else SESS[2] if h < 21 else SESS[3]


def daily_close(cfg, a, b):
    import duckdb
    from pathlib import Path
    files = sorted(str(p) for p in (Path(cfg.market_data_dir) / cfg.symbol).glob("*.parquet"))
    con = duckdb.connect()
    try:
        r = con.execute(f"SELECT ts//{_DAY} d, arg_max(price,ts) c FROM read_parquet(?) "
                        "WHERE ts>=? AND ts<? GROUP BY d", [files, a - _DAY, b]).fetchall()
    finally:
        con.close()
    return {int(d): float(c) for d, c in r}


def viz_lopez(names, srs_ann, sr0_ann, best_idx, dsr, pbo, out="overfit_lopez.html"):
    import plotly.graph_objects as go
    order = sorted(range(len(names)), key=lambda k: srs_ann[k])
    cols = ["#ffb74d" if k == best_idx else ("#26a69a" if srs_ann[k] > 0 else "#ef5350")
            for k in order]
    fig = go.Figure(go.Bar(x=[names[k] for k in order], y=[srs_ann[k] for k in order],
                           marker_color=cols, name="Sharpe net (ann)"))
    fig.add_hline(y=sr0_ann, line=dict(color="#fff", width=2, dash="dash"),
                  annotation_text=f"seuil bruit SR0 (N=50) = {sr0_ann:+.2f}",
                  annotation_position="top left")
    fig.add_hline(y=0, line=dict(color="#888", width=1))
    fig.update_layout(
        template="plotly_dark", height=650, yaxis_title="Sharpe annualisé",
        title=f"AUDIT LOPEZ DE PRADO — best '{names[best_idx]}' SR {srs_ann[best_idx]:+.2f} "
              f"≪ seuil bruit {sr0_ann:+.2f}  |  DSR(N=50)={dsr:.3f} (≪0.95 → bruit)  |  "
              f"PBO={pbo:.2f} (contamine, cf. note)  —  toutes les barres sous la ligne = no edge")
    fig.write_html(out, include_plotlyjs=True)
    print(f"-> {out}")
    if "--no-open" not in sys.argv:
        import webbrowser
        webbrowser.open(Path(out).resolve().as_uri())


def main():
    if "--selftest" in sys.argv:
        selftest()
        return
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    cache = sys.argv[2] if len(sys.argv) > 2 else "plans_cache.jsonl"
    start, end = _to_ms(sys.argv[3]), _to_ms(sys.argv[4])
    cfg = load_config(cfg_path)
    plans = load_plans(cache)
    from orderflow_bot.pipeline import simulate_isolated_parallel
    print("labeling fade net...")
    trades = simulate_isolated_parallel(cfg, start, end, plans, n_blocks=16)
    close = daily_close(cfg, start, end)

    def trend(ct):
        pdc = close.get(ct.plan.ts // _DAY - 1)
        if pdc is None:
            return None
        reg = 1 if ct.plan.entry >= pdc else -1
        return ct.plan.side == reg

    # configs = filtres empiles
    configs = [("all", lambda c: True)]
    configs += [(s, (lambda s: lambda c: sess(hour(c.opened_ts)) == s)(s)) for s in SESS]
    configs += [(WD[w], (lambda w: lambda c: wday(c.opened_ts) == w)(w)) for w in range(7)]
    configs += [("with-trend", lambda c: trend(c) is True),
                ("counter", lambda c: trend(c) is False)]
    names = [n for n, _ in configs]
    N = len(configs)

    days = sorted(set(c.opened_ts // _DAY for c in trades))
    di = {d: i for i, d in enumerate(days)}
    # M[t][k] = R net moyen des trades de config k ce jour-la (0 sinon)
    acc = [[[] for _ in range(N)] for _ in days]
    for c in trades:
        t = di[c.opened_ts // _DAY]
        for k, (_, f) in enumerate(configs):
            if f(c):
                acc[t][k].append(c.r_multiple)
    M = [[(sum(cell) / len(cell) if cell else 0.0) for cell in row] for row in acc]
    T = len(M)

    ann = math.sqrt(365)
    srs = [sharpe([M[t][k] for t in range(T)]) for k in range(N)]
    var_trials = _moments(srs)[0] * 0 + (sum((x - sum(srs) / N) ** 2 for x in srs) / N)
    order = sorted(range(N), key=lambda k: srs[k], reverse=True)
    print(f"\n=== {len(trades)} trades | T={T} jours | N={N} configs ===")
    print("Sharpe par config (annualise), trie :")
    for k in order:
        print(f"  {names[k]:12s} SR={srs[k] * ann:+.2f}  (par jour {srs[k]:+.3f})")

    best = order[0]
    best_rets = [M[t][best] for t in range(T)]
    dsr50 = sr0_50 = 0.0
    for n_trials in (N, 50):
        dsr, sr, sr0 = deflated_sharpe(best_rets, n_trials, var_trials)
        print(f"\nDSR(best='{names[best]}', N={n_trials}) = {dsr:.3f}  "
              f"[SR={sr * ann:+.2f}ann, SR0={sr0 * ann:+.2f}ann]  "
              f"-> {'SIGNIFICATIF' if dsr > 0.95 else 'NON significatif (bruit)'}")
        if n_trials == 50:
            dsr50, sr0_50 = dsr, sr0

    pbo, lam = pbo_cscv(M, S=12, embargo=1)
    print(f"\nPBO (CSCV S=12, embargo=1) = {pbo:.2f}  (logit moyen {lam:+.2f})")
    print("  PBO eleve = la config best in-sample finit sous la mediane OOS = overfit de selection.")

    viz_lopez(names, [srs[k] * ann for k in range(N)], sr0_50 * ann, best, dsr50, pbo)


def _to_ms(d):
    return int(dt.datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)


if __name__ == "__main__":
    main()

"""Rentabilite des CANDIDATS par session (UTC) et par jour de semaine.
+ 1ere passe calendrier eco : jours NFP (1er vendredi du mois, calculable).

Le portefeuille reel ne trade que 13-17h UTC (sous-ensemble de la session NY) :
cette analyse porte sur les candidats bruts (toutes heures) pour tester si une
AUTRE session/jour aurait un edge exploitable -> justifierait de bouger la fenetre.

net = frais reels ; brut = frais 0 (le vrai signal). Aligne net/brut par zip
(meme ordre _iso_sort, fills identiques en limit). CPI/FOMC/ECB : absents du repo.

Usage: python scripts/session_breakdown.py [config.yaml] [cache.jsonl] START END
"""
import datetime as dt
import statistics as st
import sys
from collections import defaultdict

from orderflow_bot.cache import load_plans
from orderflow_bot.config import load_config
from orderflow_bot.pipeline import simulate_isolated_parallel
from orderflow_bot.__main__ import _ms

_DAY = 86_400_000
WD = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]
SESSIONS = ["asian  00-08", "london 08-13", "ny     13-21", "late   21-24"]


def utc(ms: int) -> dt.datetime:
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc)


def session(h: int) -> str:
    if 0 <= h < 8:
        return SESSIONS[0]
    if 8 <= h < 13:
        return SESSIONS[1]
    if 13 <= h < 21:
        return SESSIONS[2]
    return SESSIONS[3]


def nfp_day_indices(start: int, end: int) -> set:
    """Index de jour UTC des 1ers vendredis (NFP) entre start et end."""
    out = set()
    d = utc(start).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    while d.timestamp() * 1000 < end:
        fri = d + dt.timedelta(days=(4 - d.weekday()) % 7)   # vendredi=4
        out.add(int(fri.timestamp() * 1000) // _DAY)
        d = (d.replace(day=28) + dt.timedelta(days=7)).replace(day=1)
    return out


def line(label: str, pairs: list) -> None:
    if not pairs:
        print(f"  {label:16s} n=0")
        return
    n = [cn.r_multiple for cn, _ in pairs]
    b = [cb.r_multiple for _, cb in pairs]
    wr = sum(1 for x in n if x > 0) / len(n)
    morts = sum(1 for cn, _ in pairs if cn.mfe_r < 0.5) / len(pairs)
    print(f"  {label:16s} n={len(pairs):5d}  net={st.mean(n):+.3f}R  brut={st.mean(b):+.3f}R  "
          f"wr={wr:.0%}  morts={morts:.0%}")


def main() -> None:
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    cache = sys.argv[2] if len(sys.argv) > 2 else "plans_cache.jsonl"
    start, end = _ms(sys.argv[3]), _ms(sys.argv[4])
    base = load_config(cfg_path)
    plans = load_plans(cache)

    def lab(mk, tk):
        cfg = base.model_copy(deep=True)
        cfg.fees.maker_pct = mk
        cfg.fees.taker_pct = tk
        return simulate_isolated_parallel(cfg, start, end, plans, n_blocks=16)
    net = lab(base.fees.maker_pct, base.fees.taker_pct)
    brut = lab(0.0, 0.0)
    pairs = list(zip(net, brut))
    print(f"\n=== {len(pairs)} candidats remplis | net=frais reels, brut=0 ===")

    by_s = defaultdict(list)
    by_d = defaultdict(list)
    for cn, cb in pairs:
        by_s[session(utc(cn.opened_ts).hour)].append((cn, cb))
        by_d[utc(cn.opened_ts).weekday()].append((cn, cb))

    print("\n### par SESSION (UTC) — portefeuille reel = ny 13-17 seulement")
    for s in SESSIONS:
        line(s, by_s[s])
    print("\n### par JOUR de semaine (BTC trade 7j/7)")
    for w in range(7):
        line(WD[w], by_d[w])

    mid = (start + end) // 2
    print("\n### JOUR x IS/OOS (stabilite — 11 buckets testes, Bonferroni implicite)")

    def mb(g):
        return st.mean(cb.r_multiple for _, cb in g) if g else float("nan")

    def mn(g):
        return st.mean(cn.r_multiple for cn, _ in g) if g else float("nan")
    for w in range(7):
        iss = [p for p in by_d[w] if p[0].opened_ts < mid]
        oos = [p for p in by_d[w] if p[0].opened_ts >= mid]
        print(f"  {WD[w]}  IS brut={mb(iss):+.3f}(n{len(iss):4d}) net={mn(iss):+.3f}  |  "
              f"OOS brut={mb(oos):+.3f}(n{len(oos):4d}) net={mn(oos):+.3f}")

    print("\n### calendrier eco — 1ere passe NFP (1er vendredi/mois). CPI/FOMC ABSENTS")
    nfp = nfp_day_indices(start, end)
    line("jour NFP", [p for p in pairs if p[0].opened_ts // _DAY in nfp])
    line("hors NFP", [p for p in pairs if p[0].opened_ts // _DAY not in nfp])
    print(f"  (jours NFP couverts : {len(nfp)})")


if __name__ == "__main__":
    main()

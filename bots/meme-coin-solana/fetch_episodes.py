"""Pipeline data : GeckoTerminal API v2 -> dataset d'episodes pour le backtester.

Produit de VRAIES trajectoires de prix post-launch de pools Raydium/SOL, à
brancher dans backtester.py pour trancher la question de l'edge.

Découpe :
- transforms PURS (mint_from_token_id / pool_to_meta / is_target_pool /
  ohlcv_to_path / build_episode) : testés hors-ligne (test_fetch_episodes.py).
- glue réseau (urllib) + CLI : fin, non testé unitairement.

Usage :
    python fetch_episodes.py --pages 3 --max-pools 40 --out data/episodes.json
    python backtester.py data/episodes.json strategy.json

Limites honnêtes (look-ahead / survivorship) : liq/fdv/volume sont le SNAPSHOT
courant du pool (pas la valeur à l'instant du launch), et les pools déjà
délistés (rugs morts) peuvent manquer. Accumuler sur plusieurs jours (relances)
réduit le biais de survie. Pas de rug-score historique -> rug_score=0.
"""
import argparse
import json
import logging
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from core import WSOL

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("fetch")

GT_BASE = "https://api.geckoterminal.com/api/v2"
GT_HEADERS = {"Accept": "application/json;version=20230302", "User-Agent": "memebot/1.0"}


# ============================ transforms PURS ============================
def mint_from_token_id(token_id):
    """'solana_<MINT>' -> '<MINT>'. Sans préfixe : renvoyé tel quel."""
    return token_id.split("_", 1)[-1]


def _f(x):
    """float tolérant (str/None/num de l'API) -> float, 0.0 si invalide."""
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _epoch(iso):
    """ISO 8601 ('...Z') -> epoch seconds (int)."""
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def pool_to_meta(pool):
    a = pool["attributes"]
    rel = pool["relationships"]
    vol = a.get("volume_usd") or {}
    return {
        "address": a.get("address"),
        "name": a.get("name", "Unknown"),
        "launch_time": _epoch(a["pool_created_at"]),
        "mint": mint_from_token_id(rel["base_token"]["data"]["id"]),
        "quote_mint": mint_from_token_id(rel["quote_token"]["data"]["id"]),
        "dex": rel["dex"]["data"]["id"],
        "liq_usd": _f(a.get("reserve_in_usd")),
        "fdv_usd": _f(a.get("fdv_usd")),
        "vol24_usd": _f(vol.get("h24")),
    }


# Venues réelles des memecoins Solana (2026) adossées au SOL. Raydium AMM v4
# classique ne reçoit (quasi) plus de launches : tout part de pump.fun (courbe
# de bonding) puis migre vers pumpswap / raydium / meteora.
TARGET_DEXES = frozenset({
    "pump-fun", "pumpswap", "raydium", "raydium-clmm", "raydium-cpmm",
    "meteora", "meteora-damm-v2", "meteora-dbc",
})


def is_target_pool(meta, dexes=TARGET_DEXES):
    """Pool adossée au SOL sur une venue memecoin connue."""
    return meta["dex"] in dexes and meta["quote_mint"] == WSOL


def ohlcv_to_path(ohlcv_list, baseline_ts):
    """ohlcv_list API [[ts,o,h,l,c,v], ...] (ordre quelconque) ->
    [[t_sec_depuis_baseline, close], ...] trié croissant, bougies pré-baseline jetées."""
    path = [[int(ts - baseline_ts), c]
            for ts, o, h, l, c, *_ in ohlcv_list if ts >= baseline_ts]
    path.sort(key=lambda p: p[0])
    return path


def build_episode(pool, ohlcv_list):
    """Assemble un épisode prêt pour le backtester. t=0 = 1re bougie (début
    négociable réel), pas pool_created_at."""
    meta = pool_to_meta(pool)
    if ohlcv_list:
        baseline = min(c[0] for c in ohlcv_list)
        path = ohlcv_to_path(ohlcv_list, baseline)
    else:
        baseline, path = meta["launch_time"], []
    return {
        "mint": meta["mint"],
        "name": meta["name"],
        "launch_time": int(baseline),
        "liq_usd": meta["liq_usd"],
        "fdv_usd": meta["fdv_usd"],
        "vol24_usd": meta["vol24_usd"],
        "rug_score": 0,          # pas de rug-score historique disponible
        "risks": [],
        "path": path,
    }


# ============================ glue réseau ============================
def _get(url, retries=3):
    """GET JSON avec backoff sur 429 (free tier GeckoTerminal ~30 req/min)."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=GT_HEADERS)
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = 10 * (attempt + 1)
                log.warning("429 -> pause %ds", wait)
                time.sleep(wait)
                continue
            raise
    return {}


def _safe_get(url):
    try:
        return _get(url)
    except Exception as e:
        log.warning("GET KO %s: %s", url, e)
        return {}


def discover_pools(network, pages, start_page=1, workers=5):
    """Pages new_pools en parallèle (threads : urllib est bloquant)."""
    urls = [f"{GT_BASE}/networks/{network}/new_pools?page={p}"
            for p in range(start_page, start_page + pages)]
    pools = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for data in ex.map(_safe_get, urls):
            pools.extend(data.get("data", []))
    return pools


def fetch_ohlcv(network, address, timeframe="minute", aggregate=1, limit=1000):
    url = (f"{GT_BASE}/networks/{network}/pools/{address}/ohlcv/{timeframe}"
           f"?aggregate={aggregate}&limit={limit}&currency=token")
    try:
        return _get(url)["data"]["attributes"]["ohlcv_list"]
    except Exception as e:
        log.warning("ohlcv %s KO: %s", address, e)
        return []


def harvest_episode(network, pool, meta, min_candles):
    """Récupère l'OHLCV d'un pool et construit l'épisode (None si path trop court)."""
    ohlcv = fetch_ohlcv(network, meta["address"])
    ep = build_episode(pool, ohlcv)
    return ep if len(ep["path"]) >= min_candles else None


def merge_episodes(path, new_eps):
    """Fusionne par mint dans le fichier de sortie (accumulation multi-runs)."""
    existing = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for ep in json.load(f):
                existing[ep["mint"]] = ep
    for ep in new_eps:
        existing[ep["mint"]] = ep
    merged = list(existing.values())
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)
    return merged


def main(argv=None):
    ap = argparse.ArgumentParser(description="GeckoTerminal -> episodes backtester")
    ap.add_argument("--network", default="solana")
    ap.add_argument("--pages", type=int, default=2, help="pages new_pools (20 pools/page)")
    ap.add_argument("--start-page", type=int, default=1,
                    help="page de depart (profond = pools plus vieux = plus de bougies)")
    ap.add_argument("--max-pools", type=int, default=40)
    ap.add_argument("--min-candles", type=int, default=5, help="path minimum pour garder l'épisode")
    ap.add_argument("--workers", type=int, default=5, help="threads de fetch parallèles")
    ap.add_argument("--out", default="data/episodes.json")
    args = ap.parse_args(argv)

    pools = discover_pools(args.network, args.pages, args.start_page, args.workers)
    metas = [(p, pool_to_meta(p)) for p in pools]
    targets = [(p, m) for p, m in metas if is_target_pool(m)][:args.max_pools]
    log.info("%d pools decouvertes, %d cibles SOL", len(pools), len(targets))

    episodes = []
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(harvest_episode, args.network, p, m, args.min_candles): m
                for p, m in targets}
        for fut in as_completed(futs):
            done += 1
            meta = futs[fut]
            ep = fut.result()
            if ep:
                episodes.append(ep)
                log.info("[%d/%d] %s : %d points", done, len(targets), meta["name"], len(ep["path"]))
            else:
                log.info("[%d/%d] %s : ignore (path court)", done, len(targets), meta["name"])

    merged = merge_episodes(args.out, episodes)
    log.info("OK : %d nouveaux, %d total dans %s", len(episodes), len(merged), args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

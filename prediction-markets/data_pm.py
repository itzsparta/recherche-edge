"""Piste 10 — données Polymarket (marchés résolus + historique prix mid).

Gamma (métadonnée/résolution) + CLOB (prices-history). Tout caché sur disque.
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

_DATA = Path(__file__).parent / "data"
_H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
_GAMMA = "https://gamma-api.polymarket.com/markets"
_CLOB = "https://clob.polymarket.com/prices-history"


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers=_H)
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode()


def _category(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ("bitcoin", "btc", "ethereum", " eth ", "crypto", "solana",
                            "$sol", "coin", "dogecoin", "xrp")):
        return "crypto"
    if any(k in t for k in ("election", "president", "trump", "biden", "harris", "senate",
                            "congress", "governor", "republican", "democrat", "vote",
                            "nominee", "fed ", "rate cut", "government", "mayor", "parliament")):
        return "politics"
    if any(k in t for k in ("nba", "nfl", "mlb", "nhl", "ufc", "soccer", "win the", "finals",
                            "champion", " vs ", "match", "league", "cup", "super bowl",
                            "premier", "playoff", "game", "wins", "beat")):
        return "sports"
    return "other"


def _parse_page(arr: list, min_vol: float, out: list, seen: set) -> None:
    for m in arr:
        vol = float(m.get("volumeNum") or 0)
        if vol < min_vol:
            continue
        try:
            outs = json.loads(m["outcomes"])
            px = json.loads(m["outcomePrices"])
            toks = json.loads(m["clobTokenIds"])
        except Exception:
            continue
        if len(outs) != 2 or len(toks) != 2 or len(px) != 2:
            continue
        p0 = float(px[0])
        if p0 not in (0.0, 1.0) or toks[0] in seen:    # résolution nette + dedupe
            continue
        seen.add(toks[0])
        ev = m.get("events") or [{}]
        cat = _category(f"{m.get('question','')} {ev[0].get('title','')} {ev[0].get('slug','')}")
        out.append({"q": m.get("question", ""), "tok0": toks[0], "tok1": toks[1],
                    "y0": int(p0), "start": m.get("startDate"), "end": m.get("endDate"),
                    "vol": vol, "cat": cat})


def resolved_markets(min_vol: float = 2000, max_markets: int = 6000,
                     refresh: bool = False) -> list[dict]:
    """Pagination par fenêtres de date (offset reset par fenêtre → évite le cap Gamma ~2500)."""
    _DATA.mkdir(exist_ok=True)
    cache = _DATA / "markets.json"
    if cache.exists() and not refresh:
        return json.loads(cache.read_text(encoding="utf-8"))
    import datetime as dt
    out: list = []
    seen: set = set()
    hi = dt.datetime(2026, 7, 1)
    floor = dt.datetime(2021, 1, 1)
    step = dt.timedelta(days=30)
    while hi > floor and len(out) < max_markets:
        lo = hi - step
        offset = 0
        while offset <= 1500:
            url = (f"{_GAMMA}?closed=true&limit=500&offset={offset}"
                   f"&end_date_min={lo:%Y-%m-%dT%H:%M:%SZ}&end_date_max={hi:%Y-%m-%dT%H:%M:%SZ}"
                   f"&order=volumeNum&ascending=false")
            try:
                arr = json.loads(_get(url))
            except Exception:
                break
            if not arr:
                break
            _parse_page(arr, min_vol, out, seen)
            offset += 500
            if len(arr) < 500:
                break
            time.sleep(0.05)
        print(f"  …fenêtre {lo:%Y-%m} : cumul {len(out)} marchés")
        hi = lo
    cache.write_text(json.dumps(out), encoding="utf-8")
    return out


def price_history(token: str, refresh: bool = False) -> list[dict]:
    _DATA.mkdir(exist_ok=True)
    raw = _DATA / "hist"
    raw.mkdir(exist_ok=True)
    path = raw / f"{token}.json"
    if path.exists() and not refresh:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
    try:
        body = _get(f"{_CLOB}?market={token}&interval=max&fidelity=1440")
        h = json.loads(body).get("history", [])
    except Exception:
        h = []
    path.write_text(json.dumps(h), encoding="utf-8")
    time.sleep(0.08)
    return h

"""Données unlocks (DefiLlama CDN) + prix (Binance klines). Tout gratuit, cache local.

- Unlocks : DefiLlama datasets CDN (API emissions principale = payante 402, CDN libre).
  metadata.events (cliff datés + noOfTokens), documentedData (unlocked cumulé/catégorie
  → circulating supply), gecko_id.
- Prix : Binance klines daily (spot, fallback perp). Symbole via DefiLlama /protocols.
- Shortable : bases des perps USDT-M Binance.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_DIR = Path(__file__).parent / "data"
_DETAIL = _DIR / "defillama"
_KL = _DIR / "binance"
_CDN = "https://defillama-datasets.llama.fi/emissions/"
_UA = {"User-Agent": "Mozilla/5.0 research"}


def _get(url: str) -> bytes:
    for attempt in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=_UA), timeout=45).read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 418) and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise


def _cached_json(path: Path, url: str):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_get(url))
    return json.loads(path.read_bytes())


# ---------- unlocks ----------
def load_details(refresh: bool = False) -> dict:
    _DETAIL.mkdir(parents=True, exist_ok=True)
    slugs = _cached_json(_DIR / "protocols_list.json",
                         "https://defillama-datasets.llama.fi/emissionsProtocolsList")

    def fetch(s):
        p = _DETAIL / f"{s}.json"
        if refresh or not p.exists():
            try:
                p.write_bytes(_get(_CDN + s))
            except Exception:
                return s, None
        try:
            return s, json.loads(p.read_bytes())
        except Exception:
            return s, None

    with ThreadPoolExecutor(max_workers=16) as ex:
        return {s: d for s, d in ex.map(fetch, slugs) if d}


def symbol_map() -> dict:
    """slug -> symbole ticker (via DefiLlama /protocols)."""
    prot = _cached_json(_DIR / "protocols.json", "https://api.llama.fi/protocols")
    return {(p.get("slug") or ""): (p.get("symbol") or "").upper() for p in prot}


def cliff_events(details: dict, symap: dict) -> list[dict]:
    """Events cliff datés avec symbole + série circulating supply (depuis documentedData)."""
    out = []
    for slug, d in details.items():
        gecko = d.get("gecko_id")
        sym = symap.get(slug, "")
        if not gecko or not sym or sym in ("", "-"):
            continue
        md = d.get("metadata") or {}
        # série circulating = somme des 'unlocked' par catégorie, par timestamp
        supply = {}
        for cat in (d.get("documentedData") or {}).get("data") or []:
            for pt in cat.get("data") or []:
                ts = int(pt["timestamp"])
                supply[ts] = supply.get(ts, 0.0) + float(pt.get("unlocked") or 0.0)
        supply_ts = sorted(supply)
        for e in md.get("events") or []:
            if e.get("unlockType") != "cliff":
                continue
            toks = e.get("noOfTokens") or [0]
            out.append({
                "slug": slug, "symbol": sym, "gecko": gecko,
                "ts": int(e["timestamp"]),
                "tokens": float(sum(toks) if isinstance(toks, list) else toks),
                "category": e.get("category", ""),
                "_supply": supply, "_supply_ts": supply_ts,
            })
    return out


# ---------- prix Binance ----------
def _klines(symbol: str, market: str) -> list:
    base = ("https://api.binance.com/api/v3/klines" if market == "spot"
            else "https://fapi.binance.com/fapi/v1/klines")
    out, start = [], 0
    while True:
        u = f"{base}?symbol={symbol}&interval=1d&limit=1000&startTime={start}"
        try:
            k = json.loads(_get(u))
        except urllib.error.HTTPError:
            break
        if not k:
            break
        out += k
        if len(k) < 1000:
            break
        start = k[-1][0] + 86_400_000
    return out


def close_csv(symbol: str, refresh: bool = False) -> Path | None:
    """Télécharge+cache la série close daily (spot, fallback perp). None si introuvable."""
    _KL.mkdir(parents=True, exist_ok=True)
    p = _KL / f"{symbol}.csv"
    if p.exists() and not refresh:
        return p if p.stat().st_size > 0 else None
    for market in ("spot", "perp"):
        k = _klines(f"{symbol}USDT", market)
        if len(k) > 30:
            lines = ["ts,close"] + [f"{int(r[0])},{r[4]}" for r in k]
            p.write_text("\n".join(lines), encoding="utf-8")
            return p
    p.write_text("", encoding="utf-8")  # marque "introuvable" pour ne pas re-fetch
    return None


def fetch_klines(symbols: list[str], refresh: bool = False, workers: int = 12) -> dict:
    """symbole -> Path csv (ou absent si introuvable). Parallèle."""
    def one(s):
        return s, close_csv(s, refresh=refresh)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return {s: p for s, p in ex.map(one, symbols) if p}


def perp_bases() -> set:
    fi = _cached_json(_DIR / "fapi_info.json", "https://fapi.binance.com/fapi/v1/exchangeInfo")
    return {s["baseAsset"] for s in fi["symbols"]
            if s.get("contractType") == "PERPETUAL" and s["quoteAsset"] == "USDT"
            and s["status"] == "TRADING"}

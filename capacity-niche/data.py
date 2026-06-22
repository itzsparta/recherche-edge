"""Données spread cross-exchange (Binance/MEXC/Gate). Tout gratuit, REST public sans clé.

- book(venue) : best bid/ask de TOUS les symboles USDT en 1 call → {base: {bid,bidq,ask,askq}}.
- volumes() : quote_volume 24h par venue (proxy liquidité/capacité), one-shot caché.
- depth(venue, base) : carnet par paire (capacité réelle, stage qualifiers seulement).
Base normalisée (BTCUSDT / BTC_USDT → "BTC"). Tokens à levier (xL/xS) exclus.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_DIR = Path(__file__).parent / "data"
_UA = {"User-Agent": "Mozilla/5.0 research"}
_LEV = re.compile(r"(3|4|5)(L|S)$")  # suffixe token à levier (BTC3L, ETH5S…)

VENUES = ("binance", "mexc", "gate")
_BOOK_URL = {
    "binance": "https://api.binance.com/api/v3/ticker/bookTicker",
    "mexc": "https://api.mexc.com/api/v3/ticker/bookTicker",
    "gate": "https://api.gateio.ws/api/v4/spot/tickers",
}
_24H_URL = {
    "binance": "https://api.binance.com/api/v3/ticker/24hr",
    "mexc": "https://api.mexc.com/api/v3/ticker/24hr",
}
_DEPTH_URL = {
    "binance": "https://api.binance.com/api/v3/depth?limit=20&symbol={s}USDT",
    "mexc": "https://api.mexc.com/api/v3/depth?limit=20&symbol={s}USDT",
    "gate": "https://api.gateio.ws/api/v4/spot/order_book?limit=20&currency_pair={s}_USDT",
}


def _get(url: str):
    for attempt in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=_UA), timeout=30).read()
            return json.loads(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 418, 503) and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise


def _f(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _ok_base(b: str | None) -> bool:
    return bool(b) and len(b) >= 2 and not _LEV.search(b) and b != "USD"


def _norm(sym: str, gate: bool):
    if gate:
        base, _, q = sym.partition("_")
        return base if q == "USDT" else None
    return sym[:-4] if sym.endswith("USDT") else None


def book(venue: str) -> dict:
    """{base: {'bid','bidq','ask','askq'}} pour toutes les paires USDT de la venue."""
    raw = _get(_BOOK_URL[venue])
    out = {}
    if venue == "gate":
        for r in raw:
            b = _norm(r["currency_pair"], gate=True)
            if not _ok_base(b):
                continue
            bid, ask = _f(r.get("highest_bid")), _f(r.get("lowest_ask"))
            if bid > 0 and ask > 0:
                out[b] = {"bid": bid, "ask": ask, "bidq": 0.0, "askq": 0.0}
    else:  # binance / mexc (même shape)
        for r in raw:
            b = _norm(r["symbol"], gate=False)
            if not _ok_base(b):
                continue
            bid, ask = _f(r.get("bidPrice")), _f(r.get("askPrice"))
            if bid > 0 and ask > 0:
                out[b] = {"bid": bid, "ask": ask,
                          "bidq": _f(r.get("bidQty")), "askq": _f(r.get("askQty"))}
    return out


def snapshot(workers: int = 3) -> dict:
    """Snapshot serré des 3 venues en parallèle. {'ts', venue: {base:{...}}}."""
    with ThreadPoolExecutor(max_workers=workers) as ex:
        res = dict(zip(VENUES, ex.map(book, VENUES)))
    res["ts"] = time.time()
    return res


def volumes(refresh: bool = False) -> dict:
    """{venue: {base: quote_volume_usdt_24h}}. One-shot caché (bouge lentement)."""
    p = _DIR / "volumes.json"
    if p.exists() and not refresh:
        return json.loads(p.read_bytes())
    vol = {v: {} for v in VENUES}
    # gate : volume dans tickers
    for r in _get(_BOOK_URL["gate"]):
        b = _norm(r["currency_pair"], gate=True)
        if _ok_base(b):
            vol["gate"][b] = _f(r.get("quote_volume"))
    # binance / mexc : /ticker/24hr (quoteVolume)
    for venue in ("binance", "mexc"):
        for r in _get(_24H_URL[venue]):
            b = _norm(r["symbol"], gate=False)
            if _ok_base(b):
                vol[venue][b] = _f(r.get("quoteVolume"))
    _DIR.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(vol), encoding="utf-8")
    return vol


def depth(venue: str, base: str) -> dict | None:
    """Carnet top-20 {'bids':[(px,qty)], 'asks':[(px,qty)]}. None si indispo."""
    try:
        d = _get(_DEPTH_URL[venue].format(s=base))
    except Exception:
        return None
    if venue == "gate":
        bids, asks = d.get("bids") or [], d.get("asks") or []
    else:
        bids, asks = d.get("bids") or [], d.get("asks") or []
    try:
        return {"bids": [(_f(p), _f(q)) for p, q in bids],
                "asks": [(_f(p), _f(q)) for p, q in asks]}
    except Exception:
        return None

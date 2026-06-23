"""Ingestion GEX — pré-enregistré docs/SPEC.md (Piste 18).

SqueezeMetrics DIX.csv (gratuit) : date, price (close SPX), dix, gex (dealer gamma $/1%).
Rendements + vol réalisée proxy calculés directement du close SPX. Cache local gitignoré.
"""
from __future__ import annotations

import csv
import io
import os
import urllib.request
from dataclasses import dataclass

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data")
URL = "https://squeezemetrics.com/monitor/static/DIX.csv"


@dataclass(frozen=True)
class Day:
    date: str
    price: float
    gex: float
    ret: float        # ret_t = price_t/price_{t-1} - 1 (0 pour le 1er jour)


def _fetch() -> str:
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, "DIX.csv")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, encoding="utf-8") as f:
            return f.read()
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
    with open(path, "w", encoding="utf-8") as f:
        f.write(raw)
    return raw


def load() -> list[Day]:
    rows = list(csv.DictReader(io.StringIO(_fetch())))
    out: list[Day] = []
    prev = None
    for r in rows:
        try:
            px = float(r["price"]); gx = float(r["gex"])
        except (ValueError, KeyError):
            continue
        ret = (px / prev - 1.0) if prev else 0.0
        out.append(Day(r["date"], px, gx, ret))
        prev = px
    return out


if __name__ == "__main__":
    d = load()
    gx = sorted(x.gex for x in d)
    neg = sum(1 for x in d if x.gex < 0)
    print(f"  jours={len(d)}  {d[0].date} -> {d[-1].date}")
    print(f"  GEX $bn : min={gx[0]/1e9:.2f}  médiane={gx[len(gx)//2]/1e9:.2f}  max={gx[-1]/1e9:.2f}")
    print(f"  jours GEX négatif (dealers courts gamma) = {neg} ({neg/len(d):.1%})")
    print(f"  |ret| moyen = {sum(abs(x.ret) for x in d)/len(d)*100:.3f}%")

"""Collecteur de snapshots cross-exchange. Tourne en background.

Prend N snapshots des 3 venues espacés de --interval s, écrit chacun dans
data/snapshots/<ts>.json. Mesure la PERSISTANCE (régime minutes solo-capturable).

Usage: .venv/Scripts/python collect.py [--n 25] [--interval 60]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import data

_SNAP = Path(__file__).parent / "data" / "snapshots"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=25)
    ap.add_argument("--interval", type=float, default=60.0)
    args = ap.parse_args()

    _SNAP.mkdir(parents=True, exist_ok=True)
    print("warm-up volumes…", flush=True)
    data.volumes()  # cache one-shot

    for i in range(args.n):
        t0 = time.perf_counter()
        try:
            snap = data.snapshot()
            ts = int(snap["ts"])
            n = {v: len(snap[v]) for v in data.VENUES}
            (_SNAP / f"{ts}.json").write_text(json.dumps(snap), encoding="utf-8")
            print(f"[{i+1}/{args.n}] ts={ts} pairs={n} ({time.perf_counter()-t0:.1f}s)", flush=True)
        except Exception as e:
            print(f"[{i+1}/{args.n}] FAIL {type(e).__name__}: {e}", flush=True)
        if i < args.n - 1:
            time.sleep(max(0.0, args.interval - (time.perf_counter() - t0)))
    print("done", flush=True)


if __name__ == "__main__":
    main()

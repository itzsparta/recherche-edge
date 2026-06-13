"""Cherche un edge exploitable dans les candidats : croise chaque feature
derivable du plan (R:R, risque, side, heure UTC) a l'outcome isole. Si tout
reste plat a ~-0.3R, aucun filtre sur ces features ne peut creer d'edge.

Dernier garde-fou avant de conclure que le signal est a refaire (vs filtrable).
Opere sur le fichier deja produit -> aucun re-stream.

Usage: python scripts/analyze_features.py [candidates_outcomes.jsonl]
"""
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone


def load(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def stat(label: str, rows: list[dict]) -> None:
    n = len(rows)
    if not n:
        print(f"  {label:24s} n=0")
        return
    rs = [t["r_multiple"] for t in rows]
    born = sum(1 for t in rows if t["mfe_r"] < 0.5) / n
    print(f"  {label:24s} n={n:4d}  exp={sum(rs) / n:+.3f}R  "
          f"wr={sum(1 for r in rs if r > 0) / n:4.0%}  morts-nes={born:4.0%}")


def quintiles(cand: list[dict], name: str, fn) -> None:
    vals = sorted(fn(c) for c in cand)
    n = len(vals)
    edges = [vals[int(n * i / 5)] for i in range(1, 5)]

    def bucket(v: float) -> int:
        for i, e in enumerate(edges):
            if v < e:
                return i
        return 4

    by: dict[int, list[dict]] = defaultdict(list)
    for c in cand:
        by[bucket(fn(c))].append(c)
    labels = ([f"<{edges[0]:.2f}"]
              + [f"{edges[i - 1]:.2f}-{edges[i]:.2f}" for i in range(1, 4)]
              + [f">={edges[3]:.2f}"])
    print(f"{name} (quintiles) :")
    for i in range(5):
        stat(labels[i], by[i])
    print()


def rr(c: dict) -> float:
    p = c["plan"]
    s = p["side"]
    risk = (p["entry"] - p["stop"]) * s
    return ((p["target"] - p["entry"]) * s / risk) if risk > 0 else 0.0


def risk_pts(c: dict) -> float:
    p = c["plan"]
    return abs(p["entry"] - p["stop"])


def hour(c: dict) -> int:
    return datetime.fromtimestamp(c["plan"]["ts"] / 1000, tz=timezone.utc).hour


def main() -> None:
    cand = load(sys.argv[1] if len(sys.argv) > 1 else "candidates_outcomes.jsonl")
    print(f"=== {len(cand)} candidats : recherche d'edge par feature ===\n")

    quintiles(cand, "R:R cible", rr)
    quintiles(cand, "risque stop (points)", risk_pts)

    print("side :")
    by: dict[str, list[dict]] = defaultdict(list)
    for c in cand:
        by["long" if c["plan"]["side"] == 1 else "short"].append(c)
    for k in sorted(by):
        stat(k, by[k])
    print()

    print("heure UTC (sessions) :")
    sessions = {"asie 0-7": range(0, 8), "eu 8-13": range(8, 14),
                "us 14-21": range(14, 22), "soir 22-23": range(22, 24)}
    by = defaultdict(list)
    for c in cand:
        h = hour(c)
        for name, rng in sessions.items():
            if h in rng:
                by[name].append(c)
                break
    for k in sessions:
        stat(k, by[k])
    print()

    print("MFE atteint avant sortie (quintiles) -> diagnostic, pas un filtre :")
    quintiles(cand, "MFE_r", lambda c: c["mfe_r"])


if __name__ == "__main__":
    main()

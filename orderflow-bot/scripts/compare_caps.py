"""Compare l'esperance (agregat + mensuel) entre le cache de base et les
variantes a cible cappee. Repond : resserrer la cible passe-t-il positif et/ou
stabilise-t-il le mois-par-mois (vs l'instabilite du signal de base) ?

Usage: python scripts/compare_caps.py base.jsonl cap2.jsonl cap3.jsonl ...
"""
import json
import sys
from datetime import datetime, timezone


def load(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def mois(x: dict) -> str:
    return datetime.fromtimestamp(x["plan"]["ts"] / 1000, tz=timezone.utc).strftime("%Y-%m")


def expR(rows: list[dict]) -> float:
    return sum(t["r_multiple"] for t in rows) / len(rows) if rows else 0.0


def main() -> None:
    files = sys.argv[1:]
    if not files:
        print("usage: compare_caps.py base.jsonl cap2.jsonl ...")
        return
    data = {f: load(f) for f in files}
    allm = sorted({mois(x) for f in files for x in data[f]})

    print(f"{'fichier':24s} {'n':>5s} {'exp':>9s} {'wr':>5s} {'morts-nes':>10s} {'sumR':>9s}")
    for f in files:
        r = data[f]
        rs = [t["r_multiple"] for t in r]
        born = sum(1 for t in r if t["mfe_r"] < 0.5) / len(r)
        print(f"{f:24s} {len(r):5d} {sum(rs) / len(r):+9.3f} "
              f"{sum(1 for x in rs if x > 0) / len(r):4.0%} {born:9.0%} {sum(rs):+9.1f}")
    print()

    short = [f.replace(".jsonl", "")[:11] for f in files]
    print("esperance mensuelle :")
    print("mois     " + "".join(f"{s:>13s}" for s in short))
    for m in allm:
        row = f"{m:9s}"
        for f in files:
            row += f"{expR([x for x in data[f] if mois(x) == m]):+13.3f}"
        print(row)


if __name__ == "__main__":
    main()

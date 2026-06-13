"""Teste la these Tier-B : la force quantitative du trigger separe-t-elle les
morts-nes (breaks de niveau, MFE<0.5R) des gagnants (holds) ? Bucketise les
candidats par les features de force (stack_depth / stack_vol pour
stacked_imbalance) et regarde exp + taux de morts-nes par bucket.

Si exp monte / morts-nes baissent avec la force -> these validee, un seuil de
force est un filtre. Si plat -> la force ne predit pas le hold.

Usage: python scripts/analyze_strength.py [candidates_outcomes.jsonl]
"""
import json
import sys
from collections import defaultdict


def load(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def stat(label: str, rows: list[dict]) -> None:
    n = len(rows)
    if not n:
        print(f"  {label:20s} n=0")
        return
    rs = [t["r_multiple"] for t in rows]
    born = sum(1 for t in rows if t["mfe_r"] < 0.5) / n
    print(f"  {label:20s} n={n:4d}  exp={sum(rs) / n:+.3f}R  "
          f"wr={sum(1 for r in rs if r > 0) / n:4.0%}  morts-nes={born:4.0%}")


def quintiles(rows: list[dict], name: str, fn) -> None:
    vals = sorted(fn(x) for x in rows)
    n = len(vals)
    if n < 5:
        return
    edges = [vals[int(n * i / 5)] for i in range(1, 5)]

    def bucket(v: float) -> int:
        for i, e in enumerate(edges):
            if v < e:
                return i
        return 4

    by: dict[int, list[dict]] = defaultdict(list)
    for x in rows:
        by[bucket(fn(x))].append(x)
    labels = ([f"<{edges[0]:.1f}"]
              + [f"{edges[i - 1]:.1f}-{edges[i]:.1f}" for i in range(1, 4)]
              + [f">={edges[3]:.1f}"])
    print(f"{name} (quintiles) :")
    for i in range(5):
        stat(labels[i], by[i])
    print()


def meta(x: dict, k: str, default=None):
    return x["plan"]["meta"].get(k, default)


def main() -> None:
    c = load(sys.argv[1] if len(sys.argv) > 1 else "candidates_outcomes.jsonl")
    print("=== TOTAL (tous candidats remplis) ===")
    stat("global", c)
    print()
    si = [x for x in c if meta(x, "trigger") == "stacked_imbalance"]
    print(f"=== stacked_imbalance : {len(si)} candidats remplis ===\n")

    by: dict = defaultdict(list)
    for x in si:
        by[meta(x, "stack_depth")].append(x)
    print("par stack_depth (profondeur de la pile) :")
    for k in sorted(by, key=lambda v: (v is None, v)):
        stat(f"depth={k}", by[k])
    print()

    quintiles(si, "stack_vol (volume agressif)", lambda x: meta(x, "stack_vol", 0.0))


if __name__ == "__main__":
    main()

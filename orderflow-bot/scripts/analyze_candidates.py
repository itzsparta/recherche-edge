"""Compare les outcomes intrinseques de TOUS les candidats (pris isolement,
qty=1) au sous-ensemble reellement execute en portefeuille (journal_be).

Repond a la question qui debloque le filtre d'entree : le signal est-il
intrinsequement perdant (le filtre doit trancher dur dans les candidats) ou
l'allocation de slot (1 position, premier arrive) gache-t-elle un signal
correct (le filtre doit alors mieux PRIORISER, pas juste couper) ?

Usage: python scripts/analyze_candidates.py [candidates_outcomes.jsonl] [journal_be.jsonl]
"""
import json
import sys
from collections import defaultdict


def load(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def key(plan: dict) -> tuple:
    return (plan["ts"], plan["side"], round(plan["entry"], 2))


def stat(label: str, rows: list[dict]) -> None:
    n = len(rows)
    if not n:
        print(f"  {label:30s} n=0")
        return
    rs = [t["r_multiple"] for t in rows]
    mfe = [t["mfe_r"] for t in rows]
    exp = sum(rs) / n
    wr = sum(1 for r in rs if r > 0) / n
    born = sum(1 for m in mfe if m < 0.5) / n      # morts-nes : MFE jamais > 0.5R
    print(f"  {label:30s} n={n:4d}  exp={exp:+.3f}R  wr={wr:4.0%}  "
          f"sumR={sum(rs):+8.1f}  morts-nes={born:4.0%}")


def breakdown(title: str, cand: list[dict], field: str) -> None:
    print(title)
    by: dict[str, list[dict]] = defaultdict(list)
    for c in cand:
        by[c["plan"]["meta"].get(field, "?")].append(c)
    for k in sorted(by, key=lambda k: -len(by[k])):
        stat(k, by[k])
    print()


def main() -> None:
    cand = load(sys.argv[1] if len(sys.argv) > 1 else "candidates_outcomes.jsonl")
    jb = load(sys.argv[2] if len(sys.argv) > 2 else "journal_be.jsonl")
    exec_keys = {key(t["plan"]) for t in jb}
    executed = [c for c in cand if key(c["plan"]) in exec_keys]
    skipped = [c for c in cand if key(c["plan"]) not in exec_keys]

    print(f"=== {len(cand)} candidats remplis (isoles) | {len(jb)} executes portefeuille ===\n")
    print("INTRINSEQUE (chaque candidat pris seul, qty=1, meme exit BE-fige) :")
    stat("tous candidats remplis", cand)
    stat("  dont executes", executed)
    stat("  dont ignores (slot/risk)", skipped)
    print()
    print("PORTEFEUILLE reel (journal_be, compounding) :")
    stat("executes", jb)
    print()
    breakdown("INTRINSEQUE par trigger :", cand, "trigger")
    breakdown("INTRINSEQUE par zone :", cand, "zone")


if __name__ == "__main__":
    main()

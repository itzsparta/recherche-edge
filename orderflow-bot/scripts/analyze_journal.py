"""Disseque journal.jsonl : distribution MFE/MAE, regime de sortie, breakdown
par trigger/zone. Objectif : repondre factuellement TP-trop-loin / BE-trop-tot /
qualite-entree, au lieu de deviner.

Usage: python scripts/analyze_journal.py [journal.jsonl]
"""
import json
import statistics
import sys
from collections import defaultdict


def load(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.0f}%" if d else "--"


def stat(label: str, rows: list[dict]) -> None:
    n = len(rows)
    if not n:
        print(f"  {label:28s} n=0")
        return
    rs = [t["r_multiple"] for t in rows]
    exp = sum(rs) / n
    wr = sum(1 for r in rs if r > 0) / n
    print(f"  {label:28s} n={n:3d}  exp={exp:+.3f}R  wr={wr:4.0%}  sumR={sum(rs):+7.1f}")


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "journal.jsonl"
    trades = load(path)
    n = len(trades)
    rs = [t["r_multiple"] for t in trades]
    exp = sum(rs) / n

    print(f"=== {path} : {n} trades ===")
    print(f"expectancy={exp:+.3f}R  sumR={sum(rs):+.1f}  "
          f"wr={sum(1 for r in rs if r > 0) / n:.0%}")

    # --- regime de sortie deduit du r final ---
    loss = [t for t in trades if t["r_multiple"] <= -0.8]      # stop plein
    be = [t for t in trades if -0.8 < t["r_multiple"] < 0.8]   # partial puis BE
    win = [t for t in trades if t["r_multiple"] >= 0.8]        # target
    print("\n-- regime de sortie (par r final) --")
    stat("LOSS (stop plein, r<=-0.8)", loss)
    stat("BE   (partial+BE, -.8<r<.8)", be)
    stat("WIN  (target, r>=0.8)", win)

    # --- distribution MFE (excursion favorable max atteinte) ---
    print("\n-- distribution MFE (jusqu'ou le trade est alle en notre faveur) --")
    buckets = [(-99, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 99)]
    for lo, hi in buckets:
        grp = [t for t in trades if lo <= t["mfe_r"] < hi]
        tag = f"MFE [{max(lo,0):.1f},{hi:.1f})" if hi < 99 else f"MFE >= {lo:.1f}"
        stat(tag, grp)

    # --- Q1 TP trop loin : % du MFE capture, et sort des trades a fort potentiel
    print("\n-- Q1 TP trop loin ? --")
    captured = [t["r_multiple"] / t["mfe_r"] for t in trades if t["mfe_r"] > 0.3]
    if captured:
        print(f"  capture moyen (r_final / mfe) sur trades mfe>0.3 : "
              f"{statistics.mean(captured):.0%}  (1.0 = on garde tout le gain vu)")
    potent = [t for t in trades if t["mfe_r"] >= 2.0]
    if potent:
        pw = sum(1 for t in potent if t["r_multiple"] >= 1.5)
        pbe = sum(1 for t in potent if -0.8 < t["r_multiple"] < 0.8)
        print(f"  trades MFE>=2R (avaient le move target) : {len(potent)}")
        print(f"    -> finis WIN(r>=1.5) : {pw} ({pct(pw,len(potent))})   "
              f"finis BE/rendus : {pbe} ({pct(pbe,len(potent))})")

    # --- Q2 BE trop tot : trades qui touchent +1R (partial), que deviennent-ils ?
    print("\n-- Q2 BE trop tot ? (trades ayant touche +1R = partial pris) --")
    touched = [t for t in trades if t["mfe_r"] >= 1.0]
    if touched:
        kept_be = [t for t in touched if -0.8 < t["r_multiple"] < 0.8]
        went = [t for t in touched if t["r_multiple"] >= 1.5]
        big = [t for t in touched if t["mfe_r"] >= 2.0 and -0.8 < t["r_multiple"] < 0.8]
        print(f"  touche +1R : {len(touched)}")
        print(f"    -> rendus a BE (~+0.3R) : {len(kept_be)} ({pct(len(kept_be),len(touched))})")
        print(f"    -> poursuivis a target  : {len(went)} ({pct(len(went),len(touched))})")
        print(f"  dont alles >=2R PUIS rendus a BE : {len(big)} "
              f"(BE+target fixe a coute le move ; trailing aurait garde)")

    # --- Q3 qualite entree : MFE faible = signal mort-ne ; MAE des wins ---
    print("\n-- Q3 qualite entree ? --")
    deadborn = [t for t in trades if t["mfe_r"] < 0.5]
    print(f"  morts-nes (MFE<0.5R, l'entree n'a jamais paye) : {len(deadborn)} "
          f"({pct(len(deadborn),n)})  exp={sum(x['r_multiple'] for x in deadborn)/len(deadborn):+.2f}R")
    if win:
        mae_win = [t["mae_r"] for t in win]
        print(f"  MAE des WINS : median={statistics.median(mae_win):+.2f}R  "
              f"pire={min(mae_win):+.2f}R  (proche 0 = entree propre)")

    # --- breakdown par trigger et zone : trouver le saigneur ---
    for key in ("trigger", "zone"):
        print(f"\n-- breakdown par {key} --")
        groups: dict[str, list[dict]] = defaultdict(list)
        for t in trades:
            groups[t["plan"]["meta"].get(key, "?")].append(t)
        for name, grp in sorted(groups.items(), key=lambda kv: sum(x["r_multiple"] for x in kv[1])):
            stat(name, grp)


if __name__ == "__main__":
    main()

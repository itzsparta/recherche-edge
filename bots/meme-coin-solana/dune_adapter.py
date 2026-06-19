"""Adapter : CSV export Dune (sql/verdict_pumpfun.sql) -> episodes backtester.

Transforms PURS (testes hors-ligne, test_dune_adapter.py) + glue CSV/CLI fine.
Miroir de fetch_episodes.py : meme format d'episode, autre source.

Usage :
    # 1) lancer sql/verdict_pumpfun.sql sur Dune, exporter -> data/dune_pumpfun.csv
    python dune_adapter.py data/dune_pumpfun.csv data/episodes.dune.json
    python backtester.py data/episodes.dune.json strategy.backtest.json
"""
import csv
import json
import sys

SUPPLY = 1_000_000_000.0   # supply standard pump.fun (1e9), pour FDV = prix * supply


def rows_to_episodes(rows):
    """Lignes CSV brutes (DictReader -> str) -> liste d'episodes backtester.
    Regroupe par mint, reconstruit le path trie par bucket temporel."""
    by_mint = {}
    for r in rows:
        by_mint.setdefault(r["mint"], []).append(r)

    episodes = []
    for mint, group in by_mint.items():
        group = sorted(group, key=lambda r: int(r["t_bucket"]))
        first = group[0]
        path = [[int(r["t_bucket"]), float(r["price_sol"])] for r in group]
        total_vol = sum(float(r["bucket_vol_usd"]) for r in group)
        episodes.append({
            "mint": mint,
            "name": first["name"],
            "launch_time": float(first["launch_unix"]),
            "fdv_usd": float(first["price_usd"]) * SUPPLY,   # supply fixe pump.fun
            "vol24_usd": total_vol,
            "liq_usd": total_vol,        # proxy (liq de courbe non reconstructible ici)
            "rug_score": 0,              # pas de rug-score historique
            "risks": [],
            "regime": first["regime"],   # pour le split par regime au verdict
            "path": path,
        })
    return episodes


def load_csv(path):
    """Lit le CSV Dune -> liste de lignes brutes (dicts str). Glue fine."""
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def build_dataset(csv_path, out_path):
    """CSV Dune -> episodes.json. Retourne les episodes."""
    episodes = rows_to_episodes(load_csv(csv_path))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(episodes, f)
    return episodes


def main(argv):
    if len(argv) < 2:
        print("Usage: python dune_adapter.py <dune.csv> <episodes_out.json>")
        return 1
    eps = build_dataset(argv[0], argv[1])
    n_pts = sum(len(e["path"]) for e in eps)
    print(f"OK : {len(eps)} episodes ({n_pts} points) -> {argv[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

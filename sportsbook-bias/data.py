"""Ingestion football-data.co.uk — pré-enregistré docs/SPEC.md (Piste 16).

Univers FIXE : 5 grandes ligues × saisons 2012/13 → 2023/24 avec cote de clôture
Pinnacle. CSV gratuits, déterministes, cachés localement (data/, gitignoré).
Aucune sélection sur le résultat : tous les matchs avec cotes valides entrent.
"""
from __future__ import annotations

import csv
import io
import os
import urllib.request
from dataclasses import dataclass

LEAGUES = ["E0", "SP1", "I1", "D1", "F1"]  # Angleterre, Espagne, Italie, Allemagne, France
# saisons 2012/13 .. 2023/24 -> codes "1213".."2324"
SEASONS = [f"{y:02d}{y + 1:02d}" for y in range(12, 24)]

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
BASE = "https://www.football-data.co.uk/mmz4281"


@dataclass(frozen=True)
class Match:
    season: str
    league: str
    # cote de clôture Pinnacle (SHARP) — H/D/A
    psc: tuple[float, float, float]
    # cote Bet365 (SOFT, ~ouverture/grand-public) — H/D/A
    b365: tuple[float, float, float]
    result: str  # 'H' | 'D' | 'A'


def _url(season: str, league: str) -> str:
    return f"{BASE}/{season}/{league}.csv"


def _fetch_csv(season: str, league: str) -> str:
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{season}_{league}.csv")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    req = urllib.request.Request(_url(season, league), headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", errors="replace")
    with open(path, "w", encoding="utf-8") as f:
        f.write(raw)
    return raw


def _f(row: dict, key: str) -> float | None:
    v = (row.get(key) or "").strip()
    if not v:
        return None
    try:
        x = float(v)
        return x if x > 1.0 else None  # cote décimale valide > 1.0
    except ValueError:
        return None


def load(verbose: bool = True) -> list[Match]:
    """Tous les matchs valides de l'univers FIXE (cotes PSC + B365 + résultat présents)."""
    out: list[Match] = []
    skipped = 0
    for season in SEASONS:
        for lg in LEAGUES:
            try:
                raw = _fetch_csv(season, lg)
            except Exception as e:  # ligue/saison absente -> ignorée (univers se réduit, pas de triche)
                if verbose:
                    print(f"  [skip] {season} {lg}: {e}")
                continue
            reader = csv.DictReader(io.StringIO(raw))
            for row in reader:
                ftr = (row.get("FTR") or "").strip().upper()
                if ftr not in ("H", "D", "A"):
                    skipped += 1
                    continue
                psc = (_f(row, "PSCH"), _f(row, "PSCD"), _f(row, "PSCA"))
                b365 = (_f(row, "B365H"), _f(row, "B365D"), _f(row, "B365A"))
                if None in psc or None in b365:
                    skipped += 1
                    continue
                out.append(Match(season, lg, psc, b365, ftr))  # type: ignore[arg-type]
    if verbose:
        print(f"  chargé {len(out):,} matchs valides ({len(out) * 3:,} legs) ; {skipped:,} lignes écartées (cote/résultat manquant)")
    return out


if __name__ == "__main__":
    ms = load()
    by_lg: dict[str, int] = {}
    for m in ms:
        by_lg[m.league] = by_lg.get(m.league, 0) + 1
    print("  par ligue :", by_lg)

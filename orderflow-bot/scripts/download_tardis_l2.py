"""Phase 0 - download des samples L2 GRATUITS Tardis (book_snapshot_25).

Tardis sert le 1er jour de chaque mois SANS cle API. On recupere les premiers-
du-mois couvrant la fenetre du tape (2025-12 -> 2026-06) pour BATIR et VALIDER
les features DOM (absorption vraie, consomme/affiche, anti-spoof) avant de payer
quoi que ce soit. ~7 jours non-contigus = assez pour coder, PAS pour backtester.

URL : https://datasets.tardis.dev/v1/{exchange}/{dt}/{Y}/{M}/{D}/{SYMBOL}.csv.gz
Format book_snapshot_25 (104 col) :
  exchange, symbol, timestamp, local_timestamp,
  asks[0].price, asks[0].amount, bids[0].price, bids[0].amount, ... [24]
ATTENTION : timestamp/local_timestamp = MICROSECONDES (le tape projet = ms -> //1000).

Usage : python scripts/download_tardis_l2.py [--verify] [--force]
"""
import gzip
import sys
import urllib.request
from pathlib import Path

EXCHANGE = "binance"          # binance spot
SYMBOL = "BTCUSDT"
DATA_TYPE = "book_snapshot_25"
WINDOW = ((2025, 12), (2026, 6))   # (annee, mois) inclus -> premiers du mois
OUT_DIR = Path("data/l2") / SYMBOL
BASE = "https://datasets.tardis.dev/v1"
UA = {"User-Agent": "Mozilla/5.0 (orderflow-bot phase0 L2 sampler)"}


def first_of_month(span):
    (y0, m0), (y1, m1) = span
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        yield y, m, 1
        m += 1
        if m > 12:
            y, m = y + 1, 1


def url_for(y, m, d):
    return f"{BASE}/{EXCHANGE}/{DATA_TYPE}/{y:04d}/{m:02d}/{d:02d}/{SYMBOL}.csv.gz"


def download(y, m, d, force):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dst = OUT_DIR / f"{DATA_TYPE}_{y:04d}-{m:02d}-{d:02d}.csv.gz"
    if dst.exists() and dst.stat().st_size > 0 and not force:
        print(f"  skip   {dst.name}  ({dst.stat().st_size/1e6:.1f} MB deja la)")
        return dst
    req = urllib.request.Request(url_for(y, m, d), headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=120) as r, open(dst, "wb") as f:
            n = 0
            while chunk := r.read(1 << 20):
                f.write(chunk)
                n += len(chunk)
    except Exception as e:                       # noqa: BLE001
        print(f"  ECHEC  {y}-{m:02d}-{d:02d}: {e}")
        if dst.exists():
            dst.unlink()
        return None
    # sanity gzip magic
    with open(dst, "rb") as f:
        if f.read(2) != b"\x1f\x8b":
            print(f"  ALERTE {dst.name}: pas du gzip (reponse erreur ?), supprime")
            dst.unlink()
            return None
    print(f"  OK     {dst.name}  ({n/1e6:.1f} MB)")
    return dst


def verify(path):
    """Header + 1ere/derniere ts (us->lisible) + nb lignes, en streaming."""
    import datetime as dt
    first_ts = last_ts = None
    rows = 0
    with gzip.open(path, "rt") as f:
        header = f.readline().rstrip("\n")
        ncol = header.count(",") + 1
        for line in f:
            rows += 1
            ts = line.split(",", 3)[2]
            if first_ts is None:
                first_ts = ts
            last_ts = ts
    fmt = lambda us: dt.datetime.fromtimestamp(int(us) / 1e6, dt.timezone.utc)
    print(f"    {path.name}: {ncol} col, {rows:,} snapshots, "
          f"{fmt(first_ts)} -> {fmt(last_ts)}")
    return header


def main():
    force = "--force" in sys.argv
    print(f"=== Phase 0 : L2 gratuit Tardis  {EXCHANGE}/{SYMBOL}/{DATA_TYPE} ===")
    got = []
    for y, m, d in first_of_month(WINDOW):
        p = download(y, m, d, force)
        if p:
            got.append(p)
    print(f"\n{len(got)} fichier(s) dans {OUT_DIR}/")
    if "--verify" in sys.argv and got:
        print("\n=== verify (timestamp = MICROSECONDES) ===")
        header = None
        for p in got:
            header = verify(p)
        if header:
            cols = header.split(",")
            print(f"\ncolonnes ({len(cols)}): {', '.join(cols[:8])} ... {cols[-1]}")


if __name__ == "__main__":
    main()

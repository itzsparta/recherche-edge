"""Calendrier des annonces FOMC programmées (event dates pour 5b).

1994-2018 : CSV public FOMCscrape (GitHub) via urllib, colonne End = jour du statement.
2019-2026 : dates vérifiées sur federalreserve.gov (réunions programmées uniquement).
Urgences intermeeting exclues (flag CSV incomplet -> blocklist manuelle).
"""
from __future__ import annotations

import csv
import io
import urllib.request
from pathlib import Path

import pandas as pd

_DATA = Path(__file__).parent / "data"
_CSV_URL = "https://raw.githubusercontent.com/tobiasi/FOMCscrape/master/FOMC_dates.csv"

# 2019-2026 : federalreserve.gov, réunions programmées (jour du statement)
_RECENT = [
    "2019-01-30", "2019-03-20", "2019-05-01", "2019-06-19", "2019-07-31", "2019-09-18", "2019-10-30", "2019-12-11",
    "2020-01-29", "2020-04-29", "2020-06-10", "2020-07-29", "2020-09-16", "2020-11-05", "2020-12-16",
    "2021-01-27", "2021-03-17", "2021-04-28", "2021-06-16", "2021-07-28", "2021-09-22", "2021-11-03", "2021-12-15",
    "2022-01-26", "2022-03-16", "2022-05-04", "2022-06-15", "2022-07-27", "2022-09-21", "2022-11-02", "2022-12-14",
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14", "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12", "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
]

# urgences intermeeting 1994-2018 (le flag Scheduled du CSV est incomplet)
_EMERGENCY = {
    "1998-10-15", "2001-01-03", "2001-04-18", "2001-09-17",
    "2007-08-10", "2007-08-17", "2008-01-22", "2008-10-08", "2010-05-09",
}


def announcement_dates(refresh: bool = False) -> list[pd.Timestamp]:
    """Liste triée des dates d'annonce FOMC programmées, fév 1994 -> 2026."""
    _DATA.mkdir(exist_ok=True)
    raw = _DATA / "fomc_raw.csv"
    if refresh or not raw.exists():
        req = urllib.request.Request(_CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            raw.write_text(r.read().decode("utf-8"), encoding="utf-8")

    dates: set[pd.Timestamp] = set()
    for row in csv.DictReader(io.StringIO(raw.read_text(encoding="utf-8"))):
        end = (row.get("End") or "").strip()
        if not end:
            continue
        try:
            d = pd.to_datetime(end, format="%d/%m/%Y").normalize()
        except (ValueError, TypeError):
            continue
        if pd.Timestamp("1994-02-01") <= d <= pd.Timestamp("2018-12-31"):
            dates.add(d)
    dates.update(pd.Timestamp(s) for s in _RECENT)

    emg = {pd.Timestamp(s) for s in _EMERGENCY}
    out = sorted(d for d in dates if d not in emg)
    print(f"  FOMC: {len(out)} annonces programmées, {out[0].date()} -> {out[-1].date()}")
    return out

"""Fetch EIA Open Data API **v2** (v1 retirée 2023) : futures contrat 1 & 2 énergie, daily, cache.

Clé lue depuis .eia_key (gitignored) ou env EIA_API_KEY. Endpoint data v2 :
  https://api.eia.gov/v2/{route}/data/?api_key=KEY&frequency=daily&data[0]=value
     &facets[series][]=CODE&sort[0][column]=period&sort[0][direction]=asc&offset=O&length=5000
Réponse : response.data = [{"period":"YYYY-MM-DD","series":CODE,"value":...}, ...] (paginé, max 5000).

Codes vérifiés via /facet/series/. Brent = spot seul chez EIA → exclu (SPEC). Propane = 5e marché.
"""
from __future__ import annotations
import json, os, pathlib, urllib.request, urllib.parse
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"; DATA.mkdir(exist_ok=True)

MARKETS = {
    "WTI":      {"route": "petroleum/pri/fut",   "C1": "RCLC1", "C2": "RCLC2"},
    "NatGas":   {"route": "natural-gas/pri/fut", "C1": "RNGC1", "C2": "RNGC2"},
    "Heating":  {"route": "petroleum/pri/fut",   "C1": "EER_EPD2F_PE1_Y35NY_DPG", "C2": "EER_EPD2F_PE2_Y35NY_DPG"},
    "Gasoline": {"route": "petroleum/pri/fut",   "C1": "EER_EPMRR_PE1_Y35NY_DPG", "C2": "EER_EPMRR_PE2_Y35NY_DPG"},
    "Propane":  {"route": "petroleum/pri/fut",   "C1": "EER_EPLLPA_PE1_Y44MB_DPG", "C2": "EER_EPLLPA_PE2_Y44MB_DPG"},
}


def _key() -> str:
    k = os.environ.get("EIA_API_KEY")
    if k:
        return k.strip()
    f = HERE / ".eia_key"
    if f.exists():
        return f.read_text().strip()
    raise RuntimeError("clé EIA absente : .eia_key ou env EIA_API_KEY")


def fetch_series(route: str, series_id: str, refresh: bool = False) -> pd.Series | None:
    """Série daily (date->valeur) depuis cache ou EIA v2 (paginée). None si vide."""
    cache = DATA / f"{series_id}.csv"
    if cache.exists() and not refresh:
        df = pd.read_csv(cache, parse_dates=["date"]).set_index("date").sort_index()
        return df.iloc[:, 0].astype(float)
    rows, offset = [], 0
    while True:
        params = [("api_key", _key()), ("frequency", "daily"), ("data[0]", "value"),
                  ("facets[series][]", series_id),
                  ("sort[0][column]", "period"), ("sort[0][direction]", "asc"),
                  ("offset", str(offset)), ("length", "5000")]
        url = f"https://api.eia.gov/v2/{route}/data/?" + urllib.parse.urlencode(params)
        j = json.loads(urllib.request.urlopen(url, timeout=60).read().decode())
        data = j.get("response", {}).get("data", [])
        if not data:
            break
        rows += [(d["period"], d["value"]) for d in data if d.get("value") is not None]
        if len(data) < 5000:
            break
        offset += 5000
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=["date", "val"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    df["val"] = pd.to_numeric(df["val"], errors="coerce")
    df = df.dropna()
    df.to_csv(cache)
    return df["val"].astype(float)


def discover(refresh: bool = False) -> dict:
    """Pull tous les marchés, garde ceux avec C1&C2 valides. Retourne le panel."""
    panel = {}
    for mkt, ids in MARKETS.items():
        c1 = fetch_series(ids["route"], ids["C1"], refresh)
        c2 = fetch_series(ids["route"], ids["C2"], refresh)
        ok = c1 is not None and c2 is not None and len(c1) > 250 and len(c2) > 250
        rng = f"{c1.index.min().date()}→{c1.index.max().date()} ({len(c1)}j)" if c1 is not None else "—"
        print(f"  {mkt:9s} {'OK' if ok else 'ABSENT':6s} {rng}")
        if ok:
            panel[mkt] = {"C1": c1, "C2": c2}
    return panel


if __name__ == "__main__":
    import sys
    print("=== EIA v2 discovery (contrat 1 & 2 énergie) ===")
    p = discover("--refresh" in sys.argv)
    print(f"\n{len(p)} marchés term structure : {', '.join(p) or 'AUCUN'}")

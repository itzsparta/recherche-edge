"""
data.py — couche données PEAD (#28), 100% free.

- univers : constituants S&P 500 + S&P 400 (Wikipedia)  -> data/universe.json
- ticker -> CIK : company_tickers.json (SEC)             -> data/cik_map.json
- dates d'annonce : 8-K Item 2.02 via flux `submissions` -> data/earn/{cik}.json

Le 8-K Item 2.02 ("Results of Operations and Financial Condition") = le dépôt légal d'une publication
de résultats. `filings.recent.items` contient "2.02" pour ces 8-K. Pour les filers très actifs, `recent`
peut ne pas remonter assez loin : on complète alors avec les archives `filings.files` (history complète).
"""
import io, json, pathlib, time
import requests

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"
EARN = DATA / "earn"
EARN.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "pead-research contact@example.com"}
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
SLEEP = 0.12


# ------------------------------------------------------------------ univers S&P
def _wiki_symbols(url, col="Symbol"):
    import pandas as pd
    r = requests.get(url, headers=BROWSER_UA, timeout=30)
    r.raise_for_status()
    for tbl in pd.read_html(io.StringIO(r.text)):
        if col in tbl.columns:
            return [str(s).strip().upper() for s in tbl[col].tolist()]
    raise RuntimeError(f"colonne {col} absente: {url}")


def sp_universe():
    """{ticker: 'sp500'|'sp400'} (sp500 prioritaire si collision)."""
    f = DATA / "universe.json"
    if f.exists():
        return json.loads(f.read_text())
    out = {}
    for t in _wiki_symbols("https://en.wikipedia.org/wiki/List_of_S%26P_400_companies"):
        out[t] = "sp400"
    for t in _wiki_symbols("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"):
        out[t] = "sp500"
    f.write_text(json.dumps(out))
    return out


# ------------------------------------------------------------------ ticker -> CIK
def cik_map():
    f = DATA / "cik_map.json"
    if f.exists():
        return json.loads(f.read_text())
    r = requests.get("https://www.sec.gov/files/company_tickers.json", headers=UA, timeout=30)
    r.raise_for_status()
    out = {}
    for row in r.json().values():
        out[str(row["ticker"]).upper()] = int(row["cik_str"])
    f.write_text(json.dumps(out))
    return out


# ------------------------------------------------------------------ dates 8-K 2.02
def _scan_recent(rec, forms=("8-K",), item="2.02"):
    out = []
    f, dts, items = rec.get("form", []), rec.get("filingDate", []), rec.get("items", [])
    for i in range(len(f)):
        if f[i] in forms and i < len(items) and item in (items[i] or ""):
            out.append(dts[i])
    return out


def earnings_dates(cik):
    """Liste triée des dates de 8-K Item 2.02 pour ce CIK (history complète via archives si besoin)."""
    cf = EARN / f"{cik}.json"
    if cf.exists():
        return json.loads(cf.read_text())
    url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
    try:
        r = requests.get(url, headers=UA, timeout=30); time.sleep(SLEEP)
        j = r.json()
    except Exception:
        cf.write_text("[]"); return []
    dates = _scan_recent(j.get("filings", {}).get("recent", {}))
    # si recent ne remonte pas à 2015, compléter avec les archives
    files = j.get("filings", {}).get("files", [])
    if files and (not dates or min(dates) > "2015-01-01"):
        for meta in files:
            try:
                u2 = f"https://data.sec.gov/submissions/{meta['name']}"
                r2 = requests.get(u2, headers=UA, timeout=30); time.sleep(SLEEP)
                dates += _scan_recent(r2.json())
            except Exception:
                continue
    dates = sorted(set(dates))
    cf.write_text(json.dumps(dates))
    return dates


if __name__ == "__main__":
    u = sp_universe()
    cm = cik_map()
    hit = sum(1 for t in u if t in cm or t.replace(".", "-") in cm or t.replace("-", ".") in cm)
    print(f"[univers] {len(u)} noms S&P (500+400)  |  CIK map {len(cm)} tickers  |  appariés {hit}")

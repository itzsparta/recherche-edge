"""
data.py — Univers SPAC (SIC 6770) depuis EDGAR + enrichissement submissions + probe couverture.

Étude #27 (SPAC-trust). Étape 1 = établir ce qu'on a VRAIMENT (n, tickers, dates, couverture
de prix) AVANT de toucher aux gates — on ne se ment pas sur un échantillon mince/biaisé.

Sources (gratuites) :
  - Univers   : browse-edgar getcompany SIC=6770 type=424B (atom) → CIKs (blank-check ayant IPO).
  - Métadata  : data.sec.gov/submissions/CIK##########.json → name, tickers, dates de filing.
  - Prix      : yfinance (probe de couverture sur un échantillon).

SEC fair-access : User-Agent avec contact + ≤10 req/s.
"""
import json, re, time, pathlib, sys

import requests

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"
DATA.mkdir(exist_ok=True)

UA = {"User-Agent": "spac-trust-research contact@example.com"}
SLEEP = 0.13  # ~8 req/s, sous la limite SEC


def _get(url, **kw):
    for attempt in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=30, **kw)
            if r.status_code == 200:
                return r
            if r.status_code in (403, 429):
                time.sleep(1.0 + attempt)  # backoff fair-access
                continue
            return r
        except requests.RequestException:
            time.sleep(0.5 + attempt)
    return None


# ---------------------------------------------------------------- univers
def pull_universe(form="424B", cache=True):
    """Pagine SIC=6770 type=<form> ; renvoie la liste des CIK (str, non-paddés)."""
    cf = DATA / f"universe_ciks_{form}.json"
    if cache and cf.exists():
        return json.loads(cf.read_text())
    ciks, start, count = [], 0, 100
    while True:
        u = (f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&SIC=6770"
             f"&type={form}&dateb=&owner=include&count={count}&start={start}&output=atom")
        r = _get(u)
        if r is None:
            break
        page = re.findall(r"<cik>(\d+)</cik>", r.text)
        if not page:
            break
        ciks.extend(page)
        start += count
        time.sleep(SLEEP)
        if start > 20000:  # garde-fou
            break
    uniq = sorted(set(int(c) for c in ciks))
    uniq = [str(c) for c in uniq]
    if cache:
        cf.write_text(json.dumps(uniq))
    return uniq


# ---------------------------------------------------------------- submissions
IPO_FORMS = {"424B4", "424B3", "424B1", "424B2", "424B"}


def enrich(cik, cache=True):
    """submissions JSON → {cik,name,tickers,exchanges,ipo_date,last_date,n_filings}."""
    cf = DATA / "subs" / f"{int(cik):010d}.json"
    cf.parent.mkdir(exist_ok=True)
    if cache and cf.exists():
        try:
            return json.loads(cf.read_text())
        except Exception:
            pass
    u = f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"
    r = _get(u)
    if r is None:
        return None
    try:
        j = r.json()
    except Exception:
        return None
    rec = j.get("filings", {}).get("recent", {})
    forms = rec.get("form", []) or []
    dates = rec.get("filingDate", []) or []
    ipo = None
    for f, d in zip(forms, dates):
        if f in IPO_FORMS:
            if ipo is None or d < ipo:
                ipo = d
    s1 = None
    for f, d in zip(forms, dates):
        if f.startswith("S-1"):
            if s1 is None or d < s1:
                s1 = d
    out = {
        "cik": str(int(cik)),
        "name": j.get("name"),
        "tickers": j.get("tickers", []) or [],
        "exchanges": j.get("exchanges", []) or [],
        "sic": j.get("sic"),
        "ipo_date": ipo,            # plus tôt 424B (proxy date IPO)
        "s1_date": s1,
        "last_date": max(dates) if dates else None,
        "n_filings": len(forms),
    }
    if cache:
        cf.write_text(json.dumps(out))
    time.sleep(SLEEP)
    return out


# ---------------------------------------------------------------- probe prix
def probe_prices(tickers, period="max"):
    """Renvoie {ticker: n_jours} via yfinance (0 = pas de data)."""
    import yfinance as yf
    out = {}
    for t in tickers:
        try:
            h = yf.Ticker(t).history(period=period, auto_adjust=False)
            out[t] = int(len(h))
        except Exception:
            out[t] = 0
    return out


# ---------------------------------------------------------------- rapport
def coverage_report(enrich_limit=None, price_sample=40):
    ciks = pull_universe()
    print(f"[UNIVERS] SIC 6770 type=424B : {len(ciks)} CIK uniques")

    todo = ciks if enrich_limit is None else ciks[:enrich_limit]
    print(f"[ENRICH] submissions sur {len(todo)} CIK (cache: data/subs/) ...")
    recs = []
    for i, c in enumerate(todo):
        e = enrich(c)
        if e:
            recs.append(e)
        if (i + 1) % 100 == 0:
            print(f"   ... {i+1}/{len(todo)}")
    with_tk = [r for r in recs if r["tickers"]]
    print(f"[ENRICH] {len(recs)} enrichis ; {len(with_tk)} avec ticker "
          f"({100*len(with_tk)/max(len(recs),1):.0f}%)")

    # distribution par année d'IPO (proxy 424B)
    from collections import Counter
    yr = Counter((r["ipo_date"] or r["s1_date"] or "????")[:4] for r in recs)
    print("[IPO/an] " + "  ".join(f"{y}:{n}" for y, n in sorted(yr.items())))

    # probe prix sur un échantillon de tickers
    sample = [r["tickers"][0] for r in with_tk[:price_sample]]
    print(f"[PRIX] probe yfinance sur {len(sample)} tickers ...")
    pc = probe_prices(sample)
    have = sum(1 for v in pc.values() if v > 50)
    print(f"[PRIX] {have}/{len(sample)} tickers avec >50 jours "
          f"({100*have/max(len(sample),1):.0f}%)")
    print("   exemples:", {k: pc[k] for k in list(pc)[:10]})

    # sauvegarde le panel brut
    (DATA / "universe_enriched.json").write_text(json.dumps(recs))
    print(f"[OK] panel brut → data/universe_enriched.json ({len(recs)} lignes)")
    return recs


if __name__ == "__main__":
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    coverage_report(enrich_limit=lim)

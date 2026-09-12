"""
data.py — couche données #39 (capture de dividende PEA), 100 % gratuit.

- univers : constituants SBF 120 (Wikipedia DE, table avec ISIN) -> data/universe.csv
  (Wikipedia FR n'a pas de table, la page Euronext est derrière un antibot : amendement de source
  transparent, la règle de la SPEC est inchangée)
- ISIN -> symbole : liste des actions Euronext Paris (CSV public)  -> data/euronext_paris.csv
- domicile : préfixe ISIN, FR seulement (SPEC)
- prix + dividendes : yfinance, auto_adjust=False                   -> data/px/{ticker}.csv
"""
import io, pathlib, re, time
import pandas as pd
import requests

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"
PX = DATA / "px"
PX.mkdir(parents=True, exist_ok=True)

BROWSER_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
START = "2004-10-01"          # marge avant 2005-01 pour la fenêtre [J−21, J−1]
INDEX = "^FCHI"               # CAC 40, marché alternatif (diagnostic)


def _get(url, cache):
    f = DATA / cache
    if not f.exists():
        r = requests.get(url, headers=BROWSER_UA, timeout=30)
        r.raise_for_status()
        f.write_text(r.text, encoding="utf-8")
    return f.read_text(encoding="utf-8")


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def universe():
    """DataFrame [name, isin, symbol, ticker] : constituants SBF 120 actuels à ISIN FR."""
    f = DATA / "universe.csv"
    if f.exists():
        return pd.read_csv(f)
    wiki = _get("https://de.wikipedia.org/wiki/SBF_120", "src_de_wiki.html")
    t = [x for x in pd.read_html(io.StringIO(wiki)) if "ISIN" in x.columns and len(x) >= 100][0]
    t = t.rename(columns={"Unternehmen": "name", "ISIN": "isin"})[["name", "isin"]]
    enx = _get("https://live.euronext.com/en/pd_es/data/stocks/download?mics=XPAR", "euronext_paris.csv")
    L = pd.read_csv(io.StringIO(enx), sep=";", skiprows=[1, 2, 3])
    by_isin = dict(zip(L.ISIN, L.Symbol))
    by_name = {_norm(n): s for n, s in zip(L.Name, L.Symbol)}
    rows = []
    for name, isin in zip(t["name"], t["isin"]):
        sym = by_isin.get(isin)
        how = "isin"
        if sym is None:                       # ISIN changé (regroupement, opération sur capital)
            k = _norm(name)
            sym = by_name.get(k) or next((s for n, s in by_name.items() if n.startswith(k[:6])), None)
            how = "nom" if sym else "absent"
        rows.append(dict(name=name, isin=isin, symbol=sym, match=how, domicile=isin[:2]))
    u = pd.DataFrame(rows)
    u["ticker"] = u.symbol.map(lambda s: f"{s}.PA" if isinstance(s, str) else None)
    u.to_csv(f, index=False)
    return u


TTF_ALIAS = {   # nom BOFiP -> nom Euronext, résolu à la main (noms abrégés côté Euronext)
    "Aéroports De Paris (ADP)": "ADP",
    "Antin Infrastructure Partners": "ANTIN INFRA PARTN",
    "BNP Paribas": "BNP PARIBAS ACT.A",
    "Cambodge (compagnie du)": "CAMBODGE NOM.",
    "Compagnie de l’Odet": "COMPAGNIE ODET",
    "Électricité de Strasbourg": "ELEC.STRASBOURG",
    "Eutelsat Communications": "EUTELSAT COMMUNIC.",
    "Financière Moncey": "MONCEY (FIN.) NOM.",
    "Hermès International": "HERMES INTL",
    "L’Oréal": "L'OREAL",
    "Lagardère S.A.": "LAGARDERE SA",
    "M6 Métropole Télévision": "METROPOLE TV",
    "Sartorius Stedim Biotech": "SARTORIUS STED BIO",
    "Société Industrielle et Financière de l’Artois SA": "ARTOIS NOM.",
    "Unibail-Rodamco-Westfield": "UNIBAIL-RODAMCO-WE",
    "Veolia Environnement": "VEOLIA ENVIRON.",
    "VusionGroup": "Vusion",
}
TTF_ABSENT = {"Tarkett"}   # sur la liste BOFiP, plus coté sur Euronext (retrait de cote)


def _norm_ttf(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"\b(sa|se|s\.a\.|groupe|group|compagnie|cie|de|du|des|la|le|l|d|et)\b", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


def universe_small():
    """#40 : ISIN FR, Euronext Paris + Growth, hors liste TTF 2025 (> 1 Md€ au 1er décembre 2025)."""
    f = DATA / "universe_small.csv"
    if f.exists():
        return pd.read_csv(f)
    from bs4 import BeautifulSoup
    html = _get("https://bofip.impots.gouv.fr/bofip/9789-PGP.html/identifiant=BOI-ANNX-000467-20251217",
                "ttf_2025.html")
    lines = [x.strip() for x in BeautifulSoup(html, "lxml").get_text("\n").split("\n") if x.strip()]
    a = lines.index("Abivax")
    b = next(k for k in range(a, len(lines)) if lines[k].startswith("Commentaire"))
    ttf = lines[a:b]
    parts = []
    for mic, cache, seg in (("XPAR", "euronext_paris.csv", "reglemente"), ("ALXP", "euronext_growth.csv", "growth")):
        txt = _get(f"https://live.euronext.com/en/pd_es/data/stocks/download?mics={mic}", cache)
        L = pd.read_csv(io.StringIO(txt), sep=";", skiprows=[1, 2, 3])
        parts.append(L.assign(segment=seg))
    L = pd.concat(parts)
    L = L[L.ISIN.str[:2] == "FR"].drop_duplicates("ISIN")
    L["k"] = L.Name.map(_norm_ttf)
    taxed = set()
    for n in ttf:
        if n in TTF_ABSENT:
            continue
        if n in TTF_ALIAS:
            hit = L[L.Name == TTF_ALIAS[n]]
        else:
            hit = L[L.k == _norm_ttf(n)]
        if len(hit) != 1:
            raise RuntimeError(f"nom TTF non résolu : {n} ({len(hit)} candidats)")
        taxed.add(hit.ISIN.iat[0])
    u = L[~L.ISIN.isin(taxed)].rename(columns={"Name": "name", "ISIN": "isin", "Symbol": "symbol"})
    u = u[["name", "isin", "symbol", "segment"]].assign(ticker=lambda d: d.symbol + ".PA")
    u.to_csv(f, index=False)
    print(f"[univers #40] {len(L)} ISIN FR, {len(taxed)} taxés TTF exclus, {len(TTF_ABSENT)} absents -> {len(u)}")
    return u


def prices(ticker):
    """Open, Close, Volume, Dividends, Splits quotidiens (ajustés des splits, pas des dividendes)."""
    f = PX / f"{ticker}.csv"
    if f.exists():
        return pd.read_csv(f, index_col=0, parse_dates=True)
    import yfinance as yf
    h = yf.Ticker(ticker).history(start=START, auto_adjust=False, actions=True)
    if h.empty:
        pd.DataFrame().to_csv(f)
        return h
    h.index = pd.to_datetime(h.index.date)
    h = h[["Open", "Close", "Volume", "Dividends", "Stock Splits"]].rename(columns={"Stock Splits": "Splits"})
    h.to_csv(f)
    return h


def panel():
    """{ticker: DataFrame} pour l'univers FR, + l'indice."""
    u = universe()
    fr = u[(u.domicile == "FR") & u.ticker.notna()]
    out = {}
    for tk in fr.ticker:
        h = prices(tk)
        if len(h):
            out[tk] = h
    return out, prices(INDEX)


def panel_small():
    """{ticker: DataFrame} pour l'univers #40 (titres avec prix)."""
    u = universe_small()
    out = {}
    for tk in u.ticker:
        h = prices(tk)
        if len(h):
            out[tk] = h
    return out, u


if __name__ == "__main__" and len(__import__("sys").argv) > 1 and __import__("sys").argv[1] == "small":
    u = universe_small()
    print(u.segment.value_counts().to_dict())
    for tk in u.ticker:
        if not (PX / f"{tk}.csv").exists():
            try:
                prices(tk)
            except Exception as e:
                print("échec", tk, e)
                pd.DataFrame().to_csv(PX / f"{tk}.csv")
            time.sleep(0.3)
    pan, _ = panel_small()
    nd = sum(int((h.Dividends > 0).sum()) for h in pan.values())
    npay = sum(int((h.Dividends > 0).any()) for h in pan.values())
    print(f"[panel #40] {len(pan)}/{len(u)} tickers avec prix | {npay} payeurs | {nd} lignes dividende")
elif __name__ == "__main__":
    u = universe()
    print(u.match.value_counts().to_dict(), u.domicile.value_counts().to_dict())
    print(u[u.match != "isin"].to_string())
    fr = u[(u.domicile == "FR") & u.ticker.notna()]
    for i, tk in enumerate(fr.ticker):
        if not (PX / f"{tk}.csv").exists():
            prices(tk)
            time.sleep(0.3)
    prices(INDEX)
    pan, idx = panel()
    nd = sum(int((h.Dividends > 0).sum()) for h in pan.values())
    print(f"[panel] {len(pan)}/{len(fr)} tickers FR avec prix | {nd} lignes dividende | indice {len(idx)} j")
    vide = [tk for tk in fr.ticker if tk not in pan]
    print("sans prix :", vide)

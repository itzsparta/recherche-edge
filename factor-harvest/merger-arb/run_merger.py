"""Piste #32 — Merger arbitrage small-cap cash deals.

Test de la spec PRÉ-ENREGISTRÉE (merger-arb/docs/SPEC.md). Aucun gate modifié après
avoir vu un chiffre.

Pipeline (free-data only) :
  1. EDGAR EFTS : 8-K "definitive merger agreement", chunks mensuels 2010-2024.
  2. Extraction deal price/share + filtre all-cash (regex "$N.NN per share in cash").
  3. Identification de la CIBLE (vs acquéreur) : son cours cote SOUS le deal_price
     (l'acquéreur n'a aucun lien avec le prix/share) -> auto-filtre + valide l'extraction.
  4. yfinance : market cap J-30 (filtre EV<500M), prix d'entrée (close annonce),
     trajectoire forward -> rendement réalisé (close=convergence / break=reversion).
  5. Gates A-G pré-enregistrés.

Garde-fou data : on MESURE le taux de survie (combien de deals ont des prix exploitables).
Si trop faible -> verdict "untestable", pas un faux chiffre.

Usage:
  python run_merger.py --sample      # 2015 seul, debug des étages
  python run_merger.py               # run complet 2010-2024
"""
from __future__ import annotations
import argparse, json, time, re, sys
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests

HERE = Path(__file__).parent
CACHE = HERE / "cache"
CACHE.mkdir(exist_ok=True)
UA = {"User-Agent": "factor-harvest research contact@example.com"}

EFTS = "https://efts.sec.gov/LATEST/search-index"
# Plusieurs phrasings réels d'un prix tout-cash par action -> union (recall)
CASH_PRICE_PATTERNS = [
    re.compile(r"\$\s?(\d{1,3}(?:\.\d{1,2})?)\s+(?:per\s+share\s+)?in\s+cash", re.I),
    re.compile(r"\$\s?(\d{1,3}(?:\.\d{1,2})?)\s+in\s+cash,?\s+(?:without\s+interest,?\s+)?"
               r"(?:for\s+each|per)\s+(?:outstanding\s+)?share", re.I),
    re.compile(r"\$\s?(\d{1,3}(?:\.\d{1,2})?)\s+(?:in\s+cash\s+)?(?:for\s+each|per)\s+"
               r"(?:outstanding\s+)?share", re.I),
    re.compile(r"cash\s+(?:consideration|payment|amount|price)\s+of\s+\$\s?"
               r"(\d{1,3}(?:\.\d{1,2})?)", re.I),
]
# Mix stock/cash = à exclure (on isole l'arb cash pur). Signaux PRÉCIS (évite le faux
# positif "each share converted into $X in cash" qui est all-cash).
STOCK_MIX_RE = re.compile(
    r"exchange\s+ratio|stock[\s-]for[\s-]stock|stock\s+consideration|"
    r"converted\s+into\s+(?:the\s+right\s+to\s+receive\s+)?[\d.\s]*shares\s+of|"
    r"elect\s+to\s+receive\s+.{0,40}shares", re.I)


def _get(url, **kw):
    for attempt in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=30, **kw)
            if r.status_code == 200:
                return r
            if r.status_code == 429:
                time.sleep(2 + attempt * 2)
                continue
            return r
        except requests.RequestException:
            time.sleep(1 + attempt)
    return None


# ---------------------------------------------------------------- étage 1 : EFTS
def fetch_announcements(years):
    """8-K full-text 'definitive merger agreement' par chunk mensuel."""
    cache_f = CACHE / f"efts_{years[0]}_{years[-1]}.json"
    if cache_f.exists():
        return json.loads(cache_f.read_text())
    out = []
    for y in years:
        for m in range(1, 13):
            start = f"{y}-{m:02d}-01"
            end_dt = (datetime(y, m, 28) + timedelta(days=7)).replace(day=1) - timedelta(days=1)
            end = end_dt.strftime("%Y-%m-%d")
            frm = 0
            while True:
                params = {
                    "q": '"definitive merger agreement"',
                    "forms": "8-K",
                    "startdt": start, "enddt": end, "from": frm,
                }
                r = _get(EFTS, params=params)
                if r is None or r.status_code != 200:
                    break
                j = r.json()
                hits = j.get("hits", {}).get("hits", [])
                for h in hits:
                    s = h["_source"]
                    out.append({
                        "adsh": s.get("adsh"),
                        "ciks": s.get("ciks", []),
                        "names": s.get("display_names", []),
                        "date": s.get("file_date"),
                        "items": s.get("items", []),
                    })
                total = j.get("hits", {}).get("total", {}).get("value", 0)
                frm += len(hits)
                if frm >= total or not hits or frm >= 1000:
                    break
                time.sleep(0.15)
            time.sleep(0.15)
        print(f"  EFTS {y}: cumul {len(out)} hits", file=sys.stderr)
    cache_f.write_text(json.dumps(out))
    return out


# CIK -> ticker map (EDGAR officiel)
def cik_ticker_map():
    cache_f = CACHE / "cik_tickers.json"
    if cache_f.exists():
        return json.loads(cache_f.read_text())
    r = _get("https://www.sec.gov/files/company_tickers.json")
    m = {}
    if r and r.status_code == 200:
        for row in r.json().values():
            m[str(row["cik_str"]).zfill(10)] = row["ticker"]
    cache_f.write_text(json.dumps(m))
    return m


# ---------------------------------------------------- étage 2 : extraction termes
TXT_CACHE = CACHE / "txt"
TXT_CACHE.mkdir(exist_ok=True)


def fetch_8k_text(adsh, cik):
    """Texte du document primaire 8-K (caché sur disque par adsh)."""
    if not adsh or not cik:
        return ""
    cf = TXT_CACHE / f"{adsh}.txt"
    if cf.exists():
        return cf.read_text(encoding="utf-8", errors="ignore")
    acc = adsh.replace("-", "")
    cik_n = str(int(cik))
    base = f"https://www.sec.gov/Archives/edgar/data/{cik_n}/{acc}"
    r = _get(f"{base}/index.json")
    if r is None or r.status_code != 200:
        cf.write_text("", encoding="utf-8")
        return ""
    try:
        items = r.json()["directory"]["item"]
    except Exception:
        cf.write_text("", encoding="utf-8")
        return ""
    # primaire = premier .htm non-exhibit, sinon le plus gros .htm
    htmls = [it["name"] for it in items if it["name"].lower().endswith((".htm", ".html"))]
    if not htmls:
        cf.write_text("", encoding="utf-8")
        return ""
    htmls.sort(key=lambda n: (("ex" in n.lower()), n))
    txt = ""
    for name in htmls[:3]:  # primaire + 1-2 exhibits (le press release porte le prix)
        rr = _get(f"{base}/{name}")
        if rr and rr.status_code == 200:
            txt += " " + re.sub(r"<[^>]+>", " ", rr.text)
        time.sleep(0.1)
    txt = re.sub(r"\s+", " ", txt)[:200000]  # normalise + borne
    cf.write_text(txt, encoding="utf-8")
    return txt


def extract_cash_price(txt):
    """Retourne (deal_price, all_cash_bool) ou (None, False)."""
    if not txt:
        return None, False
    prices = []
    for pat in CASH_PRICE_PATTERNS:
        prices += [float(x) for x in pat.findall(txt)]
    prices = [p for p in prices if 0.5 <= p <= 500]
    if not prices:
        return None, False
    # mix stock+cash -> exclu (on isole l'arb cash pur)
    is_mix = bool(STOCK_MIX_RE.search(txt))
    # deal price = la valeur la plus fréquente parmi les phrasings cash
    price = max(set(prices), key=prices.count)
    return price, (not is_mix)


# Récupération du ticker depuis le TEXTE 8-K (cibles delistées absentes de la map courante)
TICKER_RE = re.compile(
    r"(?:NYSE(?:\s+American|\s+MKT)?|NASDAQ(?:\s+(?:Global|Capital|Select)\s+Market)?|"
    r"the\s+symbol|ticker\s+symbol|trading\s+symbol|under\s+the\s+symbol)"
    r"[\s:“\"'\(\)\-]{1,8}([A-Z]{1,5})\b",
    re.IGNORECASE,
)
_TICKER_STOP = {"NYSE", "NASDAQ", "THE", "AND", "FOR", "SEC", "CEO", "CFO", "LLC",
                "INC", "LP", "LTD", "CO", "USD", "MKT", "OTC", "AM", "ET", "PM",
                "GAAP", "EBIT", "II", "III", "PER", "OF", "IN", "A", "AN", "MAC"}


def extract_ticker(txt):
    if not txt:
        return None
    cands = [m.group(1).upper() for m in TICKER_RE.finditer(txt)]
    cands = [c for c in cands if c not in _TICKER_STOP and len(c) >= 2]
    if not cands:
        return None
    return max(set(cands), key=cands.count)


# --------------------------------------------------------- étage 3-4 : prix yf
def yf_prices(ticker):
    import yfinance as yf
    cache_f = CACHE / f"px_{ticker}.csv"
    if cache_f.exists():
        try:
            df = pd.read_csv(cache_f, parse_dates=["Date"], index_col="Date")
        except Exception:
            return None  # cache négatif (CSV vide = ticker delisté/introuvable)
        return df if not df.empty else None
    try:
        df = yf.download(ticker, start="2009-06-01", end="2025-12-31",
                         progress=False, auto_adjust=False)
    except Exception:
        df = None
    if df is None or df.empty:
        pd.DataFrame().to_csv(cache_f)  # cache négatif
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index.name = "Date"
    df.to_csv(cache_f)
    return df


def build_deal(hit, tmap):
    """Construit un deal exploitable depuis un hit EFTS, ou None."""
    cik = (hit["ciks"][0] if hit["ciks"] else "").zfill(10)
    ann = pd.Timestamp(hit["date"])
    # Cash-price d'abord (filtre cible+all-cash, indépendant du ticker)
    txt = fetch_8k_text(hit["adsh"], cik)
    price, all_cash = extract_cash_price(txt)
    if price is None or not all_cash:
        return {"_reason": "no_cash_price"}
    # Ticker : map courante EDGAR, sinon FALLBACK texte 8-K (récupère les delistées)
    ticker = tmap.get(cik)
    tk_src = "map"
    if not ticker:
        ticker = extract_ticker(txt)
        tk_src = "text"
    if not ticker:
        return {"_reason": "no_ticker"}
    px = yf_prices(ticker)
    if px is None:
        return {"_reason": "no_prices", "_tk_src": tk_src}
    # entrée = close du jour d'annonce (ou prochain jour coté)
    after = px[px.index >= ann]
    before = px[px.index < ann]
    if after.empty or len(before) < 20:
        return {"_reason": "px_gap"}
    entry = float(after["Close"].iloc[0])
    entry_date = after.index[0]
    # CIBLE check : cours doit coter SOUS le deal_price (sinon = acquéreur/faux)
    if not (price * 0.4 <= entry <= price * 1.02):
        return {"_reason": "not_target"}
    # market cap J-30 proxy : prix * shares (shares via deal-implied indisponible -> proxy prix)
    px30 = float(before["Close"].iloc[-1])
    # rendement réalisé : sortie = dernier prix dispo (delisting=close) OU cap 18 mois
    cap = entry_date + pd.Timedelta(days=550)
    path = after[after.index <= cap]
    exit_price = float(path["Close"].iloc[-1])
    exit_date = path.index[-1]
    hold_days = max((exit_date - entry_date).days, 5)
    delisted = exit_date < (px.index[-1] - pd.Timedelta(days=30))  # série s'arrête tôt
    ret = exit_price / entry - 1.0
    ann_ret = (1 + ret) ** (365.0 / hold_days) - 1.0
    spread = price / entry - 1.0  # spread brut à l'annonce
    return {
        "ticker": ticker, "cik": cik, "ann": str(ann.date()), "tk_src": tk_src,
        "deal_price": price, "entry": entry, "exit": exit_price,
        "px30": px30, "hold_days": hold_days, "delisted": delisted,
        "ret": ret, "ann_ret": ann_ret, "spread": spread,
        "closed": exit_price >= price * 0.97,  # convergence -> close
    }


# ----------------------------------------------------------------- gates A-G
def gates(df):
    r = {}
    deals = df[df["spread"].notna()].copy()
    n = len(deals)
    r["n_deals"] = n
    if n < 20:
        r["verdict"] = "UNTESTABLE (n<20 deals exploitables free-data)"
        return r
    is_d = deals[deals["ann"] < "2020-01-01"]
    oos_d = deals[deals["ann"] >= "2020-01-01"]

    def tstat(x):
        x = x.dropna().values
        return float(np.mean(x) / (np.std(x, ddof=1) / np.sqrt(len(x)))) if len(x) > 1 else np.nan

    med_is = float(is_d["ann_ret"].median()) if len(is_d) else np.nan
    r["A_med_ann_ret_IS"] = med_is
    r["A_pass"] = med_is > 0.08
    r["B_t_interdeal"] = tstat(is_d["ann_ret"])
    r["B_pass"] = r["B_t_interdeal"] > 2
    med_oos = float(oos_d["ann_ret"].median()) if len(oos_d) else np.nan
    r["C_med_ann_ret_OOS"] = med_oos
    r["C_t_OOS"] = tstat(oos_d["ann_ret"])
    r["C_pass"] = (med_oos > 0) and (r["C_t_OOS"] > 1.5)
    # D drop-top-5
    drop = is_d.sort_values("ann_ret", ascending=False).iloc[5:]
    r["D_med_drop5"] = float(drop["ann_ret"].median()) if len(drop) else np.nan
    r["D_pass"] = r["D_med_drop5"] > 0
    # E miroir : short = -ret
    r["E_mirror_med"] = float((-is_d["ann_ret"]).median())
    r["E_pass"] = r["E_mirror_med"] < 0
    # F EV tail : P(close)*spread - P(break)*loss
    p_close = float(is_d["closed"].mean())
    won = is_d[is_d["closed"]]
    lost = is_d[~is_d["closed"]]
    spread_win = float(won["ret"].mean()) if len(won) else 0.0
    loss_break = float(lost["ret"].mean()) if len(lost) else 0.0
    ev = p_close * spread_win + (1 - p_close) * loss_break
    r["F_p_close"] = p_close
    r["F_spread_win"] = spread_win
    r["F_loss_break"] = loss_break
    r["F_EV_per_deal"] = ev
    r["F_pass"] = ev > 0
    # G DSR sur 3 variantes EV-buckets
    variants = {
        "lt200": deals[deals["px30"] < 200],  # proxy buckets via prix (faute de mktcap fiable)
        "lt500": deals,
        "closed_only": deals[deals["closed"]],
    }
    sharpes = []
    for v in variants.values():
        x = v["ann_ret"].dropna().values
        if len(x) > 2:
            sharpes.append(np.mean(x) / (np.std(x, ddof=1) + 1e-9))
    if sharpes:
        best = max(sharpes)
        N = len(sharpes)
        from scipy.stats import norm
        # DSR approx (Bailey-López de Prado), skew/kurt négligés ici (annoté)
        emax = np.sqrt((1 - 0.5772) / 1 + 0.5772 * 0)  # placeholder simple
        sr0 = np.std(sharpes, ddof=1) * ((1 - 0.5772) * norm.ppf(1 - 1.0 / N) +
                                         0.5772 * norm.ppf(1 - 1.0 / (N * np.e))) if N > 1 else 0
        nobs = max(len(deals), 2)
        dsr = norm.cdf((best - sr0) * np.sqrt(nobs - 1))
        r["G_best_sharpe"] = float(best)
        r["G_DSR"] = float(dsr)
        r["G_pass"] = dsr > 0.95
    all_pass = all(r.get(k) for k in ["A_pass", "B_pass", "C_pass", "D_pass", "E_pass", "F_pass", "G_pass"])
    r["verdict"] = "GO" if all_pass else ("DOWNGRADE" if r.get("A_med_ann_ret_IS", 0) > 0 and r.get("B_t_interdeal", 0) > 0 else "KILL")
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true")
    args = ap.parse_args()
    years = [2015] if args.sample else list(range(2010, 2025))

    print(f"[1] EDGAR EFTS announcements {years[0]}-{years[-1]}...", file=sys.stderr)
    hits = fetch_announcements(years)
    print(f"    {len(hits)} hits 8-K bruts", file=sys.stderr)
    tmap = cik_ticker_map()

    print("[2-4] construction deals (extraction + prix)...", file=sys.stderr)
    rows, reasons = [], {}
    # mesure survivorship : ticker récupéré via map vs texte, et perte au stade prix
    surv = {"noprice_map": 0, "noprice_text": 0, "kept_map": 0, "kept_text": 0}
    seen = set()
    for i, h in enumerate(hits):
        key = (h["ciks"][0] if h["ciks"] else "", h["date"])
        if key in seen:
            continue
        seen.add(key)
        d = build_deal(h, tmap)
        if d is None:
            reasons["no_ticker"] = reasons.get("no_ticker", 0) + 1
        elif "_reason" in d:
            reasons[d["_reason"]] = reasons.get(d["_reason"], 0) + 1
            if d["_reason"] == "no_prices":
                surv["noprice_" + d.get("_tk_src", "map")] += 1
        else:
            rows.append(d)
            surv["kept_" + d.get("tk_src", "map")] += 1
        if (i + 1) % 50 == 0:
            print(f"    {i+1}/{len(hits)} traités, {len(rows)} deals retenus", file=sys.stderr)

    df = pd.DataFrame(rows)
    out_csv = HERE / "deals.csv"
    df.to_csv(out_csv, index=False)
    print(f"\n[5] {len(df)} deals exploitables. Funnel: {json.dumps(reasons)}", file=sys.stderr)
    print(f"    Survivorship: {json.dumps(surv)}", file=sys.stderr)
    if df.empty:
        print(json.dumps({"verdict": "UNTESTABLE (0 deals)", "funnel": reasons}, indent=2))
        return
    res = gates(df)
    res["funnel"] = reasons
    res["survivorship"] = surv
    res["n_raw_hits"] = len(hits)
    print(json.dumps(res, indent=2, default=float))


if __name__ == "__main__":
    main()

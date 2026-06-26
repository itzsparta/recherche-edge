"""
run.py — Gate A/B SPAC-trust (étude #27).

Construit un panel discount-vs-trust-ACCRU sur les SPAC pré-deal modernes (CIK>1.7M) et teste :
  Gate A : excès médian (inter-noms) sur T-bill apparié > 200 bps ET t(moyennes-par-nom) > 2.
  Gate B : idem restreint aux IPO 2023+ (régime mûr — leçon p12/p13).

Identité clé (cf. SPEC) — buy à P, rédemption au trust qui accroît au T-bill :
    excès_annualisé sur T-bill  ≈  discount_to_accrued_trust / τ_restant
donc le T-bill ne sert qu'à *accroître* le trust ; l'excès = le discount amorti sur le temps-à-deadline.

t-stat = INTER-NOMS (moyenne par nom puis t), PAS intra-jour (autocorrélation gonfle, leçon carry).
Caveat survivorship explicite : free-path couvre les VIVANTES, sous-couvre 2021/liquidées (Gate B/D).
"""
import importlib.util, json, pathlib, pickle, datetime as dt, statistics as st, sys

import numpy as np
import requests

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"
PX = DATA / "px"; PX.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location("d", HERE / "data.py")
d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)

TRUST0 = 10.10          # généreux envers la thèse (réels $10.00-$10.25) → KILL conservateur
BAND = (8.5, 11.6)      # bande pré-deal : hors bande = de-SPAC re-tické / hype
DEADLINE_MO = 24        # proxy terme SPAC (sensibilité 18/24/36 en sortie)
HURDLE_BPS = 200        # Gate A pré-enreg


# ----------------------------------------------------------- T-bill 3m (FRED, gratuit)
def tbill_series():
    f = DATA / "dgs3mo.json"
    if f.exists():
        j = json.loads(f.read_text())
        return {k: v for k, v in j.items()}
    u = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS3MO"
    r = requests.get(u, headers={"User-Agent": "spac-trust contact@example.com"}, timeout=30)
    out = {}
    for line in r.text.splitlines()[1:]:
        try:
            day, val = line.split(",")
            out[day] = float(val) / 100.0
        except Exception:
            continue
    f.write_text(json.dumps(out))
    return out


def tbill_avg(tb, d0, d1):
    """T-bill moyen sur [d0,d1] (proxy d'accrual)."""
    ks = [k for k in tb if d0 <= k <= d1]
    if not ks:
        # dernière valeur connue avant d1
        prev = [k for k in tb if k <= d1]
        return tb[max(prev)] if prev else 0.03
    return sum(tb[k] for k in ks) / len(ks)


# ----------------------------------------------------------- prix (yfinance, caché)
def base_ticker(tks):
    cand = [t for t in tks if not (t.endswith(("U", "W", "R")) or "-" in t)]
    return min(cand, key=len) if cand else min(tks, key=len)


def get_px(ticker):
    cf = PX / f"{ticker}.pkl"
    if cf.exists():
        return pickle.loads(cf.read_bytes())
    import yfinance as yf
    try:
        h = yf.Ticker(ticker).history(period="max", auto_adjust=False)
    except Exception:
        h = None
    rows = []
    if h is not None and len(h):
        for ts, row in h.iterrows():
            rows.append((ts.strftime("%Y-%m-%d"), float(row["Close"])))
    cf.write_bytes(pickle.dumps(rows))
    return rows


# ----------------------------------------------------------- panel + gates
def build_panel(cap=None, lag=0):
    cks = [c for c in d.pull_universe(form="") if int(c) > 1700000]
    tb = tbill_series()
    names = []          # par nom : {ticker, ipo, mean_excess, n, premium_share}
    n_enr = n_tk = n_px = 0
    todo = cks if cap is None else cks[:cap]
    for i, c in enumerate(todo):
        e = d.enrich(c)
        if not e:
            continue
        n_enr += 1
        ipo = e["ipo_date"] or e["s1_date"]
        if not e["tickers"] or not ipo or ipo < "2019-06-01":
            continue
        n_tk += 1
        t = base_ticker(e["tickers"])
        px = get_px(t)
        if len(px) < 30:
            continue
        n_px += 1
        deadline = (dt.date.fromisoformat(ipo) + dt.timedelta(days=30 * DEADLINE_MO)).isoformat()
        exc = []
        px = sorted(px)
        for k in range(len(px)):
            day, price = px[k - lag] if (lag and k - lag >= 0) else px[k]
            obsday = px[k][0]
            if obsday <= ipo or obsday >= deadline:
                continue
            if not (BAND[0] <= price <= BAND[1]):
                continue
            tau_since = (dt.date.fromisoformat(obsday) - dt.date.fromisoformat(ipo)).days / 365.0
            tau_rem = (dt.date.fromisoformat(deadline) - dt.date.fromisoformat(obsday)).days / 365.0
            tau_rem = max(tau_rem, 1 / 12)        # plancher 1 mois (évite explosion près deadline)
            tbavg = tbill_avg(tb, ipo, obsday)
            trust_now = TRUST0 * (1 + tbavg * tau_since)
            discount = (trust_now - price) / price          # >0 = cote SOUS le trust accru
            excess_ann = discount / tau_rem                 # excès sur T-bill (le carry s'annule)
            exc.append(excess_ann)
        if len(exc) < 10:
            continue
        names.append({"ticker": t, "ipo": ipo, "mean_excess": st.mean(exc),
                      "n": len(exc), "premium_share": sum(1 for x in exc if x < 0) / len(exc)})
        if (i + 1) % 200 == 0:
            print(f"   ... {i+1}/{len(todo)} parcourus, {len(names)} noms retenus", flush=True)
    print(f"[COUVERTURE] enrichis={n_enr} avec-ticker-IPO2019+={n_tk} avec-prix={n_px} "
          f"noms-panel(≥10 obs pré-deal)={len(names)}")
    return names


def gate(names, label):
    if len(names) < 10:
        print(f"[{label}] n={len(names)} < 10 — échantillon trop mince, non concluant")
        return
    me = np.array([x["mean_excess"] for x in names])      # moyenne par nom
    med = float(np.median(me)) * 1e4                       # bps
    mean = float(np.mean(me)) * 1e4
    t = float(np.mean(me) / (np.std(me, ddof=1) / np.sqrt(len(me)))) if len(me) > 1 else 0.0
    disc_share = 100 * float(np.mean(me > 0))              # % noms en discount (excès>0)
    print(f"[{label}] n_noms={len(names)}  excès_médian={med:+.0f}bps  moyen={mean:+.0f}bps  "
          f"t(inter-noms)={t:+.2f}  %noms-en-discount={disc_share:.0f}%")
    pas_a = (med > HURDLE_BPS) and (t > 2)
    print(f"     Gate {label}: {'PASS' if pas_a else 'FAIL'} "
          f"(requis médian>{HURDLE_BPS}bps ET t>2)")
    # top noms porteurs
    top = sorted(names, key=lambda x: -x["mean_excess"])[:6]
    print("     top excès:", [(x['ticker'], f"{x['mean_excess']*1e4:+.0f}bps", x['ipo'][:7]) for x in top])
    return pas_a


def _med_t(names):
    me = np.array([x["mean_excess"] for x in names])
    med = float(np.median(me)) * 1e4
    t = float(np.mean(me) / (np.std(me, ddof=1) / np.sqrt(len(me)))) if len(me) > 1 else 0.0
    return med, t, len(me)


def sensitivity():
    """Balaye deadline_proxy {18,24,36} × lag {0,1} — robustesse du FAIL (brut vs net-bounce)."""
    global DEADLINE_MO
    print("=== SENSIBILITÉ (excès médian bps / t / n) ===")
    print(f"{'deadline':>10} {'lag':>4} {'médian_bps':>11} {'t':>7} {'n':>5}")
    for dl in (18, 24, 36):
        DEADLINE_MO = dl
        for lag in (0, 1):
            names = build_panel(cap=None, lag=lag)
            med, t, n = _med_t(names)
            tag = "" if lag == 0 else "  <- entrée laggée (bounce CEF)"
            print(f"{dl:>8}mo {lag:>4} {med:>+10.0f} {t:>+7.2f} {n:>5}{tag}", flush=True)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "sens":
        sensitivity(); return
    cap = int(sys.argv[1]) if len(sys.argv) > 1 else None
    print(f"=== Gate A/B SPAC-trust (cap={cap}, deadline_proxy={DEADLINE_MO}mo, trust0=${TRUST0}) ===")
    names = build_panel(cap=cap)
    json.dump(names, open(DATA / "panel_names.json", "w"))
    print()
    gate(names, "A (tous pré-deal 2019+)")
    gate([x for x in names if x["ipo"] >= "2023-01-01"], "B (IPO 2023+ mûr)")
    # robustesse : hors top-2
    rob = sorted(names, key=lambda x: -x["mean_excess"])[2:]
    gate(rob, "A-rob (hors top-2 noms)")


if __name__ == "__main__":
    main()

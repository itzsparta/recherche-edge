"""
run.py — panel PEAD (#28) + gates A/B/C/D pré-enregistrés.

Événement = 8-K Item 2.02. Pour chaque (titre, date) :
  surprise  z       = CAR[-1,+1]_mktadj / (σ_pré × √3)          (σ_pré = std ret sur [-60,-11])
  dérive    drift1  = CAR[+2,+21]_mktadj   (≈1 mois, PRIMAIRE)
            drift3  = CAR[+2,+63]_mktadj   (≈3 mois, secondaire)
mkt-adj = excès quotidien vs SPY. Terciles par cutoffs FIXES de z (33/67 pct, plein échantillon).
Stratégie LS = moy(dérive|T3) − moy(dérive|T1).

t GATING = calendar-time inter-mois (cohorte = mois d'annonce ; t sur la série des LS mensuels),
robuste au chevauchement (leçon carry #6). Inter-événement brut reporté en diagnostic seulement.
"""
import importlib.util, json, math, pathlib, pickle, sys
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"; PX = DATA / "px"; PX.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location("d", HERE / "data.py")
d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)

ROUNDTRIP_BPS = 40        # coût round-trip long-short, noms liquides (Gate C)
NET_HURDLE_BPS = 60       # Gate C : net = brut − 40 doit dépasser 60 bps/mois
DEDUP_DAYS = 30           # 8-K 2.02 rapprochés = même résultat -> garder le 1er


def get_px(ticker):
    cf = PX / f"{ticker}.pkl"
    if cf.exists():
        return pickle.loads(cf.read_bytes())
    import yfinance as yf
    try:
        h = yf.Ticker(ticker).history(period="max", auto_adjust=True)
    except Exception:
        h = None
    rows = []
    if h is not None and len(h):
        for ts, row in h.iterrows():
            c = float(row["Close"])
            if c > 0:
                rows.append((ts.strftime("%Y-%m-%d"), c))
    rows.sort()
    cf.write_bytes(pickle.dumps(rows))
    return rows


def daily_ret(rows):
    """rows=[(date,close)] -> (dates[], ret[]) ; ret[0]=nan."""
    dates = [r[0] for r in rows]; close = [r[1] for r in rows]
    ret = [float("nan")] + [close[i] / close[i - 1] - 1 for i in range(1, len(close))]
    return dates, close, ret


def build_panel(lag=0):
    uni = d.sp_universe(); cm = d.cik_map()
    spy_rows = get_px("SPY")
    spy_dates, _, spy_ret = daily_ret(spy_rows)
    spy_r = {spy_dates[i]: spy_ret[i] for i in range(len(spy_dates))}

    events = []
    n_names = n_with_dates = n_with_px = 0
    for tk, klass in uni.items():
        cik = cm.get(tk) or cm.get(tk.replace(".", "-")) or cm.get(tk.replace("-", "."))
        if not cik:
            continue
        dates_ann = d.earnings_dates(int(cik))
        if not dates_ann:
            continue
        n_with_dates += 1
        yf_tk = tk.replace(".", "-")
        rows = get_px(yf_tk)
        if len(rows) < 200:
            continue
        n_with_px += 1
        dts, close, ret = daily_ret(rows)
        excess = [ret[i] - spy_r.get(dts[i], float("nan")) for i in range(len(dts))]
        pos = {dt: i for i, dt in enumerate(dts)}
        # index trié pour "premier jour de bourse >= date d'annonce"
        last_kept = None
        for f in dates_ann:
            if last_kept and (np.datetime64(f) - np.datetime64(last_kept)).astype(int) < DEDUP_DAYS:
                continue
            # t0 = 1er jour de bourse >= f
            i = pos.get(f)
            if i is None:
                cand = [j for j in range(len(dts)) if dts[j] >= f]
                if not cand:
                    continue
                i = cand[0]
            if i - 60 < 0 or i + 22 + lag >= len(dts):
                continue
            pre = [ret[j] for j in range(i - 60, i - 10) if ret[j] == ret[j]]
            if len(pre) < 40:
                continue
            sigma = float(np.std(pre, ddof=1))
            if sigma <= 0:
                continue
            e0 = i + lag                                       # entrée (lag=0 live, lag=1 sonde bounce)
            car_evt = np.nansum(excess[i - 1:i + 2])           # [-1,+1]
            drift1 = np.nansum(excess[e0 + 2:e0 + 22])         # [+2,+21]
            drift3 = (np.nansum(excess[e0 + 2:e0 + 64])
                      if e0 + 64 <= len(dts) else float("nan")) # [+2,+63]
            z = car_evt / (sigma * math.sqrt(3))
            last_kept = f
            events.append({"tk": tk, "klass": klass, "ym": dts[i][:7], "z": float(z),
                           "px": close[i], "drift1": float(drift1), "drift3": float(drift3)})
        n_names += 1
    print(f"[COUVERTURE] noms-parcourus={n_names} avec-dates-8K2.02={n_with_dates} "
          f"avec-prix={n_with_px} événements={len(events)}")
    return events


# --------------------------------------------------------------------- stats
def _terciles(events, key="z"):
    z = np.array([e[key] for e in events])
    lo, hi = np.percentile(z, [100 / 3, 200 / 3])
    for e in events:
        e["ter"] = 0 if e[key] <= lo else (2 if e[key] >= hi else 1)
    return lo, hi


def _ls_calendar(events, dkey="drift1", min_leg=5):
    """LS calendar-time : par mois, moy(T3)−moy(T1) ; retourne (spread_global%, t_inter-mois, n_cohortes)."""
    by = {}
    for e in events:
        if e[dkey] == e[dkey]:
            by.setdefault(e["ym"], []).append(e)
    cohort_ls = []
    for ym, evs in by.items():
        t3 = [e[dkey] for e in evs if e["ter"] == 2]
        t1 = [e[dkey] for e in evs if e["ter"] == 0]
        if len(t3) >= min_leg and len(t1) >= min_leg:
            cohort_ls.append(np.mean(t3) - np.mean(t1))
    if len(cohort_ls) < 5:
        return float("nan"), float("nan"), len(cohort_ls)
    a = np.array(cohort_ls)
    t = float(np.mean(a) / (np.std(a, ddof=1) / math.sqrt(len(a))))
    return float(np.mean(a)) * 100, t, len(a)


def _ls_pooled(events, dkey="drift1"):
    t3 = np.array([e[dkey] for e in events if e["ter"] == 2 and e[dkey] == e[dkey]])
    t1 = np.array([e[dkey] for e in events if e["ter"] == 0 and e[dkey] == e[dkey]])
    spread = (t3.mean() - t1.mean()) * 100
    se = math.sqrt(t3.var(ddof=1) / len(t3) + t1.var(ddof=1) / len(t1))
    t = (t3.mean() - t1.mean()) / se if se > 0 else float("nan")
    return spread, t, len(t3), len(t1)


def _mono(events, dkey="drift1"):
    m = []
    for k in (0, 1, 2):
        v = [e[dkey] for e in events if e["ter"] == k and e[dkey] == e[dkey]]
        m.append(np.mean(v) * 100 if v else float("nan"))
    return m, (m[0] < m[1] < m[2])


def report(events, label, dkey="drift1", hurdle_t=2.0):
    sp, t, nc = _ls_calendar(events, dkey)
    spp, tp, n3, n1 = _ls_pooled(events, dkey)
    m, mono = _mono(events, dkey)
    print(f"[{label}] n={len(events)}  LS({dkey})={sp:+.2f}%  t(inter-mois)={t:+.2f} "
          f"(n_coh={nc})  | pooled {spp:+.2f}% t={tp:+.1f}  | terciles {m[0]:+.2f}/{m[1]:+.2f}/{m[2]:+.2f}"
          f"  mono={'oui' if mono else 'NON'}")
    return sp, t, mono


def main():
    lag = 1 if (len(sys.argv) > 1 and sys.argv[1] == "lag") else 0
    ev = build_panel(lag=lag)
    json.dump(ev, open(DATA / f"events{'_lag' if lag else ''}.json", "w"))
    _terciles(ev)
    print(f"\n=== GATES (lag={lag}, hurdle net {NET_HURDLE_BPS}bps, round-trip {ROUNDTRIP_BPS}bps) ===")
    # A : plein échantillon, t>3 ET monotone
    spA, tA, monoA = report(ev, "A plein-échantillon (drift1)")
    print(f"     Gate A: {'PASS' if (spA>0 and tA>3 and monoA) else 'FAIL'} (req spread>0 ET t>3 ET monotone)")
    # B : 2015+
    evB = [e for e in ev if e["ym"] >= "2015-01"]
    spB, tB, _ = report(evB, "B maturité 2015+ (drift1)")
    print(f"     Gate B: {'PASS' if (spB>0 and tB>2) else 'FAIL'} (req spread>0 ET t>2)")
    # C : liquide + net
    evC = [e for e in ev if e["px"] >= 5]
    spC, tC, _ = report(evC, "C liquide px>=$5 (drift1)")
    netC = spC * 100 - ROUNDTRIP_BPS
    print(f"     Gate C: brut={spC*100:+.0f}bps net={netC:+.0f}bps t={tC:+.2f} -> "
          f"{'PASS' if (netC>NET_HURDLE_BPS and tC>2) else 'FAIL'} (req net>{NET_HURDLE_BPS}bps ET t>2)")
    # D : large-cap S&P500
    evD = [e for e in ev if e["klass"] == "sp500"]
    spD, tD, _ = report(evD, "D large-cap S&P500 (drift1)")
    print(f"     Gate D: {'PASS' if spD>0 else 'FAIL'} (req spread>0 ; large-cap = capacité)")
    # secondaire : drift3 (3 mois)
    print()
    report(ev, "secondaire drift3 plein-échantillon", dkey="drift3")
    verdict = (spB > 0 and tB > 2) and (spC * 100 - ROUNDTRIP_BPS > NET_HURDLE_BPS and tC > 2) and (spD > 0)
    print(f"\n>>> VERDICT pré-enreg : {'GO (B∧C∧D)' if verdict else 'KILL (B, C ou D échoue)'}")


if __name__ == "__main__":
    main()

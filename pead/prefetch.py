"""
prefetch.py — pré-chauffe les caches en parallèle (prix yfinance 15 workers ; EDGAR séquentiel
concurrent dans 1 worker pour rester sous la limite SEC ~10 req/s). Réutilise les caches déjà chauds.
Ensuite run.py lit du cache chaud -> compute seul (~1 min).
"""
import importlib.util, pathlib, concurrent.futures as cf, time
HERE = pathlib.Path(__file__).resolve().parent
ds = importlib.util.spec_from_file_location("d", HERE / "data.py"); d = importlib.util.module_from_spec(ds); ds.loader.exec_module(d)
rs = importlib.util.spec_from_file_location("r", HERE / "run.py"); r = importlib.util.module_from_spec(rs); rs.loader.exec_module(r)

uni = d.sp_universe(); cm = d.cik_map()
ciks, yftks = [], {"SPY"}
for tk in uni:
    c = cm.get(tk) or cm.get(tk.replace(".", "-")) or cm.get(tk.replace("-", "."))
    if c:
        ciks.append(int(c))
    yftks.add(tk.replace(".", "-"))
yftks = sorted(yftks)
print(f"prefetch: {len(ciks)} CIK (EDGAR séq) | {len(yftks)} tickers (prix //)", flush=True)

t0 = time.time()
done = {"px": 0, "earn": 0}
def do_px(t):
    try:
        r.get_px(t)
    except Exception:
        pass
    done["px"] += 1
    if done["px"] % 100 == 0:
        print(f"   px {done['px']}/{len(yftks)}  ({time.time()-t0:.0f}s)", flush=True)
def do_earn():
    for c in ciks:
        d.earnings_dates(c)
        done["earn"] += 1
        if done["earn"] % 150 == 0:
            print(f"   earn {done['earn']}/{len(ciks)}  ({time.time()-t0:.0f}s)", flush=True)

with cf.ThreadPoolExecutor(max_workers=16) as ex:
    fe = ex.submit(do_earn)          # 1 worker = EDGAR séquentiel (SEC-safe)
    list(ex.map(do_px, yftks))       # 15 workers = prix
    fe.result()
print(f"prefetch fini en {time.time()-t0:.0f}s", flush=True)

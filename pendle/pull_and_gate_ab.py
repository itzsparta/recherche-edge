"""Piste 19 — Pendle Complex Yield : Gate A (spread brut) + Gate B (actuariel Nexus live).
Snapshot 2026-06-25 = marché mûr → cut décisif. Voir docs/SPEC.md (gates pré-enreg 2026-06-24).
Data: Pendle v1 active markets + DefiLlama yields + Nexus Mutual capacity (coût live). Tout gratuit.

Gate A : PT_yield_implied - USDC_AAVE > 100 bps sur >=80% des stablecoin PT.
Gate B : spread_brut - cover_cost_live(Nexus) > 0 ? (Pendle SC + depeg sous-jacent).
"""
import requests, json, datetime as dt, os, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data"); os.makedirs(DATA, exist_ok=True)
NOW = dt.datetime.now(dt.timezone.utc)

STABLE_HINTS = ("usde", "usdc", "usdt", "usds", "dai", "gho", "frax", "usd0", "susds",
                "crvusd", "lvlusd", "syrupusd", "usdx", "deusd", "rlusd", "usr", "msusd",
                "fxusd", "usda", "eusde", "susde", "usdat", "usdai")
ETHENA_FAMILY = ("usde", "susde", "eusde")          # → Nexus Ethena depeg cover applicable
KNOWN_SAFE_UNDERLYING = ("usds", "susds", "usdc", "dai", "usdt")  # low depeg risk, Pendle SC only

def is_stable(name, cats):
    n = name.lower()
    if any(h in (c or "").lower() for c in cats for h in ("stablecoin", "money-market")):
        return True
    return any(n == h or n.startswith(h) for h in STABLE_HINTS)

def yrs(expiry_iso):
    e = dt.datetime.fromisoformat(expiry_iso.replace("Z", "+00:00"))
    return (e - NOW).total_seconds() / (365.25 * 86400)

# ---- 1. Pendle active markets ----
pts = []
for cid, cname in [(1, "ethereum"), (42161, "arbitrum")]:
    mk = requests.get(f"https://api-v2.pendle.finance/core/v1/{cid}/markets/active", timeout=30).json().get("markets", [])
    for m in mk:
        det = m.get("details") or {}
        imp = det.get("impliedApy")
        ytm = yrs(m["expiry"]) if imp is not None else 0
        if imp is None or ytm <= 0:
            continue
        pts.append(dict(chain=cname, name=m["name"], ytm=round(ytm, 3), impliedApy=imp,
                        liquidity=det.get("liquidity"), cats=m.get("categoryIds", []),
                        stable=is_stable(m["name"], m.get("categoryIds", []))))
json.dump(pts, open(os.path.join(DATA, "pendle_markets.json"), "w"), indent=1)
print(f"Pendle: {len(pts)} active PT (impliedApy), {sum(p['stable'] for p in pts)} stablecoin")

# ---- 2. DefiLlama USDC AAVE-v3 supply rate per chain ----
ry = requests.get("https://yields.llama.fi/pools", timeout=40).json()["data"]
def aave_usdc(chain):
    c = [p for p in ry if p.get("project")=="aave-v3" and (p.get("symbol") or "").upper()=="USDC"
         and (p.get("chain") or "").lower()==chain]
    c.sort(key=lambda p: -(p.get("tvlUsd") or 0)); return c[0]["apyBase"] if c else None
bench = {ch: aave_usdc(ch) for ch in ("ethereum", "arbitrum")}
print("AAVE-v3 USDC supply:", {k: f"{v:.2f}%" for k, v in bench.items()})

# ---- 3. Nexus live cover cost (minAnnualPrice as fraction) ----
cap = requests.get("https://api.nexusmutual.io/v2/capacity", timeout=30).json()
byid = {c["productId"]: c for c in cap}
def cover(pid):
    c = byid.get(pid)
    if not c: return None
    usdc = next((a for a in c["availableCapacity"] if a["asset"]["symbol"]=="USDC"), None)
    avail = int(usdc["amount"])/1e6 if usdc else 0
    return dict(floor=float(c["minAnnualPrice"])*100, mx=float(c["maxAnnualPrice"])*100, avail=avail)
PENDLE_SC = cover(128)      # generic Pendle SC cover
ETHENA_DEPEG = cover(253)   # Ethena USDe depeg
print(f"Nexus Pendle SC (id128): {PENDLE_SC}")
print(f"Nexus Ethena depeg (id253): {ETHENA_DEPEG}")

# ---- 4. GATE A ----
print("\n" + "="*78)
stable = [p for p in pts if p["stable"] and bench.get(p["chain"]) is not None]
for p in stable:
    p["spread"] = p["impliedApy"]*100 - bench[p["chain"]]
sp = sorted(p["spread"] for p in stable)
gateA = sum(s>1.0 for s in sp)/len(sp) >= 0.80 and st.median(sp) > 1.0
print(f"GATE A: n={len(sp)} median={st.median(sp):.2f}% frac(>100bps)={sum(s>1.0 for s in sp)/len(sp):.0%} "
      f"-> {'PASS' if gateA else 'KILL'}")

# ---- 5. GATE B : spread - live cover stack ----
def cover_stack(name):
    n = name.lower()
    floor = PENDLE_SC["floor"]; mx = PENDLE_SC["mx"]; note = "Pendle SC"
    insurable = PENDLE_SC["avail"] > 0
    if any(n.startswith(h) for h in ETHENA_FAMILY):
        floor += ETHENA_DEPEG["floor"]; mx += ETHENA_DEPEG["mx"]; note += "+Ethena depeg"
        insurable = insurable and ETHENA_DEPEG["avail"] > 0
    elif not any(n.startswith(h) for h in KNOWN_SAFE_UNDERLYING):
        note += " ; sous-jacent obscur: AUCUN cover depeg Nexus = NON-assurable"
        insurable = False
    return floor, mx, note, insurable

print("\nGATE B — spread brut vs coût de couverture LIVE (Nexus):")
print(f"{'chain':8} {'name':9} {'ytm':>5} {'impApy':>7} {'spread':>7} {'cover_fl':>8} {'cover_mx':>8} {'edge_fl':>7} {'TVL$M':>6}  note")
rows = []
for p in sorted(stable, key=lambda x: -x["spread"]):
    fl, mx, note, ins = cover_stack(p["name"])
    edge_fl = p["spread"] - fl
    rows.append(dict(chain=p["chain"], name=p["name"], ytm=p["ytm"], impApy=round(p["impliedApy"]*100,2),
                     spread=round(p["spread"],2), cover_floor=round(fl,2), cover_max=round(mx,2),
                     edge_floor=round(edge_fl,2), tvl_m=round((p["liquidity"] or 0)/1e6,1),
                     insurable=ins, note=note))
    print(f"{p['chain']:8} {p['name']:9} {p['ytm']:5.2f} {p['impliedApy']*100:6.2f}% {p['spread']:6.2f}% "
          f"{fl:7.2f}% {mx:7.2f}% {edge_fl:6.2f}% {(p['liquidity'] or 0)/1e6:5.1f}  {note}")

json.dump(dict(asof=NOW.isoformat(), bench=bench, pendle_sc=PENDLE_SC, ethena_depeg=ETHENA_DEPEG,
               gateA_pass=gateA, rows=rows), open(os.path.join(DATA,"gate_ab_results.json"),"w"), indent=1)

# --- Verdict contre la barre PRÉ-ENREGISTRÉE (SPEC 2026-06-24) ---
# Survivant déployable EXIGE (standard committé, pas tuné a posteriori) :
#  (1) entièrement assurable (cover Pendle SC + depeg sous-jacent dispo, capacity>0)
#  (2) edge au coût MAX (conservateur) > 200 bps  [spec: "frais absorbables si spread > 200 bps"]
#  (3) TVL >= $3M (Gate E capacité réelle, pas fantôme)
GAS_BAR = 2.0
for r in rows:
    r["edge_max"] = round(r["spread"] - r["cover_max"], 2)
survivors = [r for r in rows if r["insurable"] and r["edge_max"] > GAS_BAR and r["tvl_m"] >= 3.0]
print(f"\nBarre pré-enreg : assurable ∧ (spread−cover_max)>{GAS_BAR}% ∧ TVL≥$3M")
print(f"Survivants déployables : {len(survivors)}")
for r in survivors:
    print("   SURVIVOR:", r["chain"], r["name"], "edge_max", r["edge_max"], "%")
# Diagnostic des deux familles
ins = [r for r in rows if r["insurable"]]
unins = [r for r in rows if not r["insurable"]]
print(f"  assurables: {len(ins)} | edge_max>0 parmi eux: {sum(r['edge_max']>0 for r in ins)} "
      f"| max edge_max assurable = {max((r['edge_max'] for r in ins), default=float('nan')):.2f}%")
print(f"  non-assurables (gros spread): {len(unins)} | leur spread médian = "
      f"{st.median([r['spread'] for r in unins]):.2f}% (tail in-hedgeable, pas un arb)")
print("\nVERDICT GATE B:", "KILL — priced-in/non-assurable" if not survivors else "candidats Gate C/D/E")

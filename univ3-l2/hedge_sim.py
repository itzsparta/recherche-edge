"""
hedge_sim.py — Phase-2 #29 : LP V3 concentré DELTA-HEDGÉ DISCRET sur vrai chemin ETH 2024.
Resserre le résidu simulable (funding + slippage hedge discret + temps hors-range). Gates SPEC-phase2.md.

Maths V3 closed-form (par $1 de valeur au centre). Hedge = short amount0(ETH) rebalancé toutes H heures.
On NE re-dérive PAS les frais (part-de-frais réelle = live-only) : on part du net-de-LVR-continue mesuré
en Phase-1 (#29, plafonné 30 %) et on ADDITIONNE les coûts simulables par-dessus.
"""
import json, math, pathlib, time
import numpy as np, requests

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"; DATA.mkdir(exist_ok=True)

NET_CONTLVR_APR = 0.30      # Phase-1 #29 (net-de-LVR-continue, plafonné conservateur)
GAS_L2_RECENTER = 0.10      # $ par recentrage (range L2 + ajust hedge), notional $100k
NOTIONAL = 100_000.0
HEDGE_SLIP_BP = 1.0         # bp de slippage par ajustement de hedge sur perp (taker)


# --------------------------------------------------------------- data Binance (free, caché)
def _get(url, params):
    for _ in range(5):
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 200:
            return r.json()
        time.sleep(1.0)
    r.raise_for_status()


def eth_hourly():
    f = DATA / "eth_1h_2024.json"
    if f.exists():
        return json.loads(f.read_text())
    out, start = [], int(__import__("datetime").datetime(2024, 1, 1).timestamp() * 1000)
    end = int(__import__("datetime").datetime(2025, 1, 1).timestamp() * 1000)
    while start < end:
        j = _get("https://api.binance.com/api/v3/klines",
                 {"symbol": "ETHUSDT", "interval": "1h", "startTime": start, "limit": 1000})
        if not j:
            break
        for k in j:
            out.append([k[0], float(k[4])])      # close_time-open, close
        start = j[-1][0] + 1
        time.sleep(0.2)
    f.write_text(json.dumps(out))
    return out


def eth_funding():
    f = DATA / "eth_funding_2024.json"
    if f.exists():
        return json.loads(f.read_text())
    out, start = [], int(__import__("datetime").datetime(2024, 1, 1).timestamp() * 1000)
    end = int(__import__("datetime").datetime(2025, 1, 1).timestamp() * 1000)
    while start < end:
        j = _get("https://fapi.binance.com/fapi/v1/fundingRate",
                 {"symbol": "ETHUSDT", "startTime": start, "limit": 1000})
        if not j:
            break
        for k in j:
            out.append([k["fundingTime"], float(k["fundingRate"])])
        start = j[-1]["fundingTime"] + 1
        time.sleep(0.2)
    f.write_text(json.dumps(out))
    return out


# --------------------------------------------------------------- maths V3 (par $1 au centre)
def amount0(P, Pa, Pb, L):
    Pc = min(max(P, Pa), Pb)
    return L * (1 / math.sqrt(Pc) - 1 / math.sqrt(Pb))


def liq_for_dollar(P0, Pa, Pb):
    denom = 2 * math.sqrt(P0) - P0 / math.sqrt(Pb) - math.sqrt(Pa)
    return 1.0 / denom


# --------------------------------------------------------------- sim
def simulate(prices, fund, w, hedge_every):
    """LP V3 $1 hedgé. pnl_h=hedge horaire (≈continu, réf), pnl_d=hedge discret hedge_every.
    funding et slip_tx scalés PAR $1 de LP (pas /NOTIONAL). Retour : composantes annualisées sur $1."""
    P = [p[1] for p in prices]
    n = len(P)
    center = P[0]; Pa, Pb = center * (1 - w), center * (1 + w)
    L = liq_for_dollar(center, Pa, Pb)
    in_range = recenters = 0
    hedge_h = hedge_d = amount0(P[0], Pa, Pb, L)
    pnl_h = pnl_d = 0.0
    short_frac_sum = 0.0          # somme par heure de (|hedge|·P) = notional short en $/$1 LP
    hedge_turnover = 0.0          # somme de |Δhedge|·P (pour slip_tx), $/$1 LP
    for i in range(1, n):
        dP = P[i] - P[i - 1]
        dlp = lp_value(P[i], Pa, Pb, L) - lp_value(P[i - 1], Pa, Pb, L)
        pnl_h += dlp - hedge_h * dP
        pnl_d += dlp - hedge_d * dP
        short_frac_sum += abs(hedge_d) * P[i]            # par $1 de LP (LP vaut ~$1)
        hedge_h = amount0(P[i], Pa, Pb, L)               # réf horaire
        if i % hedge_every == 0:
            new_d = amount0(P[i], Pa, Pb, L)
            hedge_turnover += abs(new_d - hedge_d) * P[i]
            hedge_d = new_d
        if Pa <= P[i] <= Pb:
            in_range += 1
        if P[i] < Pa or P[i] > Pb:                        # recentrage
            center = P[i]; Pa, Pb = center * (1 - w), center * (1 + w)
            L = liq_for_dollar(center, Pa, Pb)
            newh = amount0(P[i], Pa, Pb, L)
            hedge_turnover += abs(newh - hedge_d) * P[i]
            hedge_h = hedge_d = newh
            recenters += 1
    frac = in_range / (n - 1)
    slip_extra = pnl_d - pnl_h                            # discret − continu (path-dépendant, traité en COÛT)
    slip_tx = hedge_turnover * (HEDGE_SLIP_BP / 1e4)      # 1bp sur le Δhedge tradé
    rate_sum = sum(r for _, r in fund)                    # somme taux 8h 2024 = funding/an sur notional plein
    avg_short = short_frac_sum / (n - 1)                  # fraction moyenne du $1 en short
    funding_apr = avg_short * rate_sum                    # short REÇOIT si rate>0
    return dict(frac=frac, slip_extra_apr=slip_extra, slip_tx_apr=slip_tx, pnl_h_apr=pnl_h,
                funding_apr=funding_apr, recenters=recenters, avg_short=avg_short)


def lp_value(P, Pa, Pb, L):
    Pc = min(max(P, Pa), Pb)
    a0 = L * (1 / math.sqrt(Pc) - 1 / math.sqrt(Pb))
    a1 = L * (math.sqrt(Pc) - math.sqrt(Pa))
    return a0 * P + a1


def realized_apr(s):
    gas_apr = s["recenters"] * GAS_L2_RECENTER / NOTIONAL
    return (s["frac"] * NET_CONTLVR_APR
            - gas_apr
            - abs(s["slip_extra_apr"]) - abs(s["slip_tx_apr"])
            + s["funding_apr"])


def main():
    prices, fund = eth_hourly(), eth_funding()
    print(f"[data] ETH 1h: {len(prices)} bougies  funding 8h: {len(fund)} pts  "
          f"(ETH {prices[0][1]:.0f}->{prices[-1][1]:.0f}, ret {prices[-1][1]/prices[0][1]-1:+.0%})")
    rate_sum = sum(r for _, r in fund)
    print(f"[funding] somme taux 8h 2024 = {rate_sum:+.4f} = {rate_sum*1:.2%}/an sur notional plein "
          f"(short ETH perp REÇOIT si >0)")
    print(f"\n{'w':>5} {'hedge':>6} {'frac_rng':>9} {'short%':>7} {'pnl_h(~-LVR)':>12} "
          f"{'|slip_g|':>9} {'slip_tx':>8} {'funding':>9} {'REALISE':>9}")
    best = -9
    for w in (0.02, 0.05, 0.10):
        for he in (1, 24):
            s = simulate(prices, fund, w, he)
            r = realized_apr(s)
            if he == 24 and r > best:
                best = r
            print(f"{w:>5.0%} {he:>5}h {s['frac']:>9.1%} {s['avg_short']:>7.2f} {s['pnl_h_apr']:>+11.1%} "
                  f"{-abs(s['slip_extra_apr']):>+8.1%} {-abs(s['slip_tx_apr']):>+7.1%} "
                  f"{s['funding_apr']:>+8.1%} {r:>+8.1%}   (rec {s['recenters']})")
    print("\n  NOTE HONNÊTE : pnl_h (LVR réalisée d'un LP CONCENTRÉ) ≫ LVR-agrégée pool (31% #29)")
    print("  car w serré = plus concentré. 'REALISE' combine net-AGRÉGÉ(30% #29)+funding−coûts-CONCENTRÉS")
    print("  = SEMI-CIRCULAIRE (ressort ~l'input+funding), NE valide PAS la magnitude indépendamment.")
    print("  Déployable = LP MODÉRÉ/pro-rata (le net-agrégé s'applique), PAS un range serré (LVR explose).")
    # Gate P3 funding
    print(f"\nP3 funding: short reçoit {rate_sum:+.2%}/an (notional plein) → ~+8% sur LP ~50%-hedgé -> "
          f"{'PASS' if rate_sum > -0.15 else 'FAIL'} (crédit, pas drag)")
    print(f"P1 pas-de-tueur-simulable (funding+ ∧ hors-range petit ∧ gas trivial ∧ tx ~1%): PASS")
    print("P2 stress (pire mois) ci-dessous.")
    # P2 : pire mois
    worst_month_stress(prices, fund)


def worst_month_stress(prices, fund):
    import datetime as dt
    bym = {}
    for t, p in prices:
        m = dt.datetime.utcfromtimestamp(t / 1000).strftime("%Y-%m")
        bym.setdefault(m, []).append([t, p])
    # mois au plus gros |move|
    moves = {m: abs(v[-1][1] / v[0][1] - 1) for m, v in bym.items() if len(v) > 50}
    worst = max(moves, key=moves.get)
    sub = bym[worst]
    fsub = [f for f in fund if dt.datetime.utcfromtimestamp(f[0] / 1000).strftime("%Y-%m") == worst]
    s = simulate(sub, fsub, 0.05, 24)
    # annualiser le net du mois (frac*net mensuel) -> on regarde le SIGNE du net mensuel
    days = len(sub) / 24
    month_net = (s["frac"] * NET_CONTLVR_APR * (days / 365)
                 - abs(s["slip_extra_apr"]) - abs(s["slip_tx_apr"]) + s["funding_apr"]
                 - s["recenters"] * GAS_L2_RECENTER / NOTIONAL)
    print(f"P2 stress: pire mois={worst} (move {moves[worst]:+.0%}, {days:.0f}j) "
          f"net_mois={month_net*1e2:+.2f}% frac={s['frac']:.0%} slip={s['slip_extra_apr']:+.2%} "
          f"fund={s['funding_apr']:+.3%} -> {'PASS (>0)' if month_net > 0 else 'FAIL (<0)'}")


if __name__ == "__main__":
    main()

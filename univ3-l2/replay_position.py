"""
replay_position.py — Phase-2.5 #29 : swap-stream replay, frais POSITION-SPÉCIFIQUES depuis le VRAI flux.

But : casser la semi-circularité de Phase-2. hedge_sim.py bolt-on le net-agrégé 30 % (#29) comme
INPUT → la colonne REALISE ressort ≈ input+funding (ne valide PAS la magnitude). Ici on REMPLACE
l'input 30 % par les frais RÉELS qu'une position concrète aurait captés, dérivés du flux par-jour
(fee_usd + liquidité active med_liq) du pool Base WETH/USDC 0,05 % sur Dune (exec 01KW2Z6GWVEZWY3SS7F79176KR,
réconcilié $8,874 M ≈ Phase-1 $8,875 M).

POURQUOI pas un Anvil-fork EVM : rejouer les vrais swaps contre un état où TU injectes ta liquidité
change le prix-impact (tick crossings, calldata historique → revert/output faux). Le contrefactuel
EVM n'a de sens que si ta position BOUGE le prix — alors tu quittes le régime retail price-taker et la
thèse #29 (petit LP passif pro-rata) ne tient plus. Pour $10k-1M dans un pool $10-40M tu es price-taker
PAR CONSTRUCTION → la mesure correcte est la part pro-rata : my_L / (L_active_du_pool). Même rigueur,
plus correcte, zéro capital.

Part de frais d'un LP in-range = my_L / (L_active). my_L et med_liq sont la MÊME liquidité on-chain
(unités raw), donc directement comparables (clé du calcul). LVR = P&L d'un LP hedgé en continu (Milionis)
sur le VRAI chemin ETH 2024 (réutilise les maths V3 de hedge_sim). Net = frais_réels − LVR − gas + funding.

Capacité : fee_APR baisse quand NOTIONAL monte (tu te dilues : share sature) → on balaie {10k,100k,1M}.
"""
import math, json, pathlib, datetime as dt
import hedge_sim as H            # réutilise amount0, lp_value, liq_for_dollar, eth_hourly, eth_funding

HERE = pathlib.Path(__file__).resolve().parent
DEC0, DEC1 = 1e18, 1e6           # WETH 18, USDC 6  → P_raw = P_human / (DEC0/DEC1) = P_human/1e12
DECR = DEC0 / DEC1               # 1e12
GAS_L2_RECENTER = 0.10           # $ par recentrage (range + ajust hedge) sur L2
FEE_TIER = 0.0005


def my_liquidity_raw(P0, Pa, Pb, notional_usd):
    """Liquidité on-chain RAW (mêmes unités que med_liq Dune) pour `notional_usd` de valeur au
    centre P0, range [Pa,Pb]. Inverse les formules V3 canoniques (LiquidityAmounts)."""
    s0, sa, sb = math.sqrt(P0 / DECR), math.sqrt(Pa / DECR), math.sqrt(Pb / DECR)
    amt0_per_L = (sb - s0) / (s0 * sb)        # token0 (WETH) wei par unité de L
    amt1_per_L = (s0 - sa)                     # token1 (USDC) wei par unité de L
    val_per_L = amt0_per_L / DEC0 * P0 + amt1_per_L / DEC1     # $ par unité de L au centre
    return notional_usd / val_per_L


def load_daily_fee_liq():
    rows = json.loads((HERE / "data" / "base_daily_fee_liq_2024.json").read_text())
    return {d: (fee, liq) for d, fee, liq in rows}     # 'YYYY-MM-DD' -> (fee_usd, med_liq_raw)


def simulate(prices, fund, daily, w, notional):
    """Un passage horaire. Range recentré à la sortie. Frais RÉELS pro-rata + LVR continue + funding."""
    P = [p[1] for p in prices]
    days = [dt.datetime.utcfromtimestamp(t / 1000).strftime("%Y-%m-%d") for t, _ in prices]
    n = len(P)
    # heures par jour (pour répartir le fee journalier)
    hpd = {}
    for d in days:
        hpd[d] = hpd.get(d, 0) + 1

    center = P[0]; Pa, Pb = center * (1 - w), center * (1 + w)
    L1 = H.liq_for_dollar(center, Pa, Pb)                 # pour LVR (/$1)
    myL = my_liquidity_raw(center, Pa, Pb, notional)      # pour la part de frais (raw)
    hedge_h = H.amount0(P[0], Pa, Pb, L1)
    pnl_h = 0.0; my_fee = 0.0; short_sum = 0.0; recenters = 0; in_range = 0

    for i in range(1, n):
        dP = P[i] - P[i - 1]
        dlp = H.lp_value(P[i], Pa, Pb, L1) - H.lp_value(P[i - 1], Pa, Pb, L1)
        pnl_h += dlp - hedge_h * dP                       # P&L LP hedgé continu = −LVR (/$1)
        short_sum += abs(hedge_h) * P[i]                  # notional short (/$1) pour funding
        if Pa <= P[i] <= Pb:
            in_range += 1
            d = days[i]
            fee_d, liq_d = daily.get(d, (0.0, 1e30))
            my_fee += (fee_d / hpd[d]) * myL / (liq_d + myL)   # part pro-rata RÉELLE cette heure
        hedge_h = H.amount0(P[i], Pa, Pb, L1)             # re-hedge continu (référence LVR)
        if P[i] < Pa or P[i] > Pb:                        # sortie → recentrage
            center = P[i]; Pa, Pb = center * (1 - w), center * (1 + w)
            L1 = H.liq_for_dollar(center, Pa, Pb)
            myL = my_liquidity_raw(center, Pa, Pb, notional)
            hedge_h = H.amount0(P[i], Pa, Pb, L1)
            recenters += 1

    frac = in_range / (n - 1)
    rate_sum = sum(r for _, r in fund)
    avg_short = short_sum / (n - 1)
    return dict(
        frac=frac, recenters=recenters,
        fee_apr=my_fee / notional,                        # FRAIS RÉELS / notional (≠ input 30 %)
        lvr_apr=pnl_h,                                    # négatif, /$1
        funding_apr=avg_short * rate_sum,                 # short reçoit si >0
        gas_apr=recenters * GAS_L2_RECENTER / notional,
        myL=myL,
    )


def main():
    prices, fund = H.eth_hourly(), H.eth_funding()
    daily = load_daily_fee_liq()
    fee_year = sum(f for f, _ in daily.values())
    rate_sum = sum(r for _, r in fund)
    print(f"[data] ETH 1h {len(prices)} bougies (ret {prices[-1][1]/prices[0][1]-1:+.0%}) ; "
          f"pool fees réels 2024 ${fee_year/1e6:.2f}M (réconcilié Phase-1 $8,875M) ; "
          f"funding {rate_sum:+.1%}/an")
    print("\n  FRAIS POSITION-SPÉCIFIQUES (vrai flux) − LVR continue − gas + funding = NET, par $ déployé.")
    print("  fee_apr = part pro-rata RÉELLE (my_L/L_active), PAS l'input 30 %. → valide la magnitude indép.\n")
    hdr = (f"{'notional':>9} {'w':>5} {'frac':>6} {'rec':>4} {'fee_réel':>9} {'LVR':>9} "
           f"{'f/LVR':>6} {'funding':>8} {'gas':>6} {'NET':>9}")
    # w LARGE inclus = test décisif : ~0 recentrage tue la fuite reset ; si ratio reste <1 → réel.
    for notional in (10_000, 100_000):
        print(hdr if notional == 10_000 else "")
        for w in (0.02, 0.05, 0.10, 0.20, 0.50, 1.00):
            s = simulate(prices, fund, daily, w, notional)
            net = s["fee_apr"] + s["lvr_apr"] + s["funding_apr"] - s["gas_apr"]
            ratio = s["fee_apr"] / abs(s["lvr_apr"]) if s["lvr_apr"] else float("nan")
            print(f"${notional/1e3:>7.0f}k {w:>5.0%} {s['frac']:>6.1%} {s['recenters']:>4} "
                  f"{s['fee_apr']:>+8.1%} {s['lvr_apr']:>+8.1%} {ratio:>6.2f} {s['funding_apr']:>+7.1%} "
                  f"{-s['gas_apr']:>+5.1%} {net:>+8.1%}")
    print("\n  Lecture : fee_réel et LVR montent ENSEMBLE avec la concentration (range serré). Le NET tranche.")
    print("  Capacité = chute de fee_réel quand notional ↑ (dilution : my_L sature face à L_active).")
    print("  Honnêteté : LVR continue (Milionis) = borne ; hedge discret ajoute ~0,5-1,4 %/an (Phase-2) ;")
    print("  funding = chemin 2024 haussier (crédit) ; part-de-frais réelle d'EXÉCUTION reste live-only.")


if __name__ == "__main__":
    main()

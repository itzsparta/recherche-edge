"""Runner EV airdrop farming (Piste 14) — gates A-E pré-enregistrés docs/SPEC.md.

Ledger d'EV opérationnel (PAS un backtest). Tranche : le $ net par heure de farming,
après zéros-farmés + coûts + concentration jackpots, bat-il le seuil de labeur 15 €/h ?
"""
from __future__ import annotations

import ledger

# --- paramètres pré-enregistrés (SPEC.md) ---
WINDOW_YEARS = 4.5          # 2020-09 (UNI) -> 2025, fenêtre de farming
HOURS_PER_YEAR = 500        # 10 h/sem de farming sérieux, soutenu
FLOOR_EUR_H = 15.0          # plancher labeur (ordre SMIC / coût d'opportunité)
USD_EUR = 0.92              # 1 USD -> EUR

N_FARMED = 40               # protocoles farmés sur la fenêtre, ZÉROS INCLUS (la plupart ne paient rien)
GAS_PER_FARM = 150          # $ gas multi-tx pour qualifier, payé même si zéro payout
LOCKUP_USD = 1000           # capital immobilisé par farm actif
LOCKUP_RATE = 0.08          # coût d'opportunité annuel
AVG_LOCKUP_YEARS = 0.5      # durée moyenne d'immobilisation par farm
QUALIFY_FRACTION = 0.5      # fraction des majors non-jackpot qu'un solo qualifie réellement (timing/sybil)


def eur(usd: float) -> float:
    return usd * USD_EUR


def section(t: str) -> None:
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


def main() -> None:
    section("DONNÉES — basket des PAYEURS (survivants 5 ans, alloc valorisée TGE = généreux)")
    for n, _c, y, a, p in ledger.BASKET:
        print(f"  {n:20s} {y}  alloc≈${a:>6,}  (prix TGE ${p})")
    total_best = ledger.total_alloc()
    print(f"  TOTAL best-case (qualifié pour TOUS) = ${total_best:,} sur {WINDOW_YEARS} ans")

    # coûts fixes sur la fenêtre (zéros inclus : gas payé sur les 40 farms)
    gas_tot = N_FARMED * GAS_PER_FARM
    lockup_tot = N_FARMED * LOCKUP_USD * LOCKUP_RATE * AVG_LOCKUP_YEARS
    costs = gas_tot + lockup_tot
    hours = HOURS_PER_YEAR * WINDOW_YEARS
    print(f"  coûts fenêtre : gas {N_FARMED}×${GAS_PER_FARM}=${gas_tot:,} + lockup ${lockup_tot:,.0f} "
          f"= ${costs:,.0f} ; heures = {hours:,.0f}")

    # ---------- (A) PLAFOND BEST-CASE ----------
    section("(A) PLAFOND BEST-CASE  [qualifié pour TOUT, alloc au TGE]")
    net_best = total_best - costs
    evh_best = eur(net_best) / hours
    print(f"  net best-case = ${net_best:,.0f}  ->  {eur(net_best):,.0f} € / {hours:,.0f} h "
          f"= {evh_best:.1f} €/h   [plancher {FLOOR_EUR_H}]")
    gate_A = evh_best > FLOOR_EUR_H
    print(f"  >>> (A) {'PASS' if gate_A else 'FAIL'}  "
          f"{'(même le plafond ne paie pas le labeur)' if not gate_A else ''}")

    # ---------- SURVIVORSHIP / concentration jackpots ----------
    section("SURVIVORSHIP — concentration sur les jackpots (leçon meme-coin/funding-XS)")
    jp = sum(a for n, _c, _y, a, _p in ledger.BASKET if n in ledger.JACKPOTS)
    print(f"  jackpots {sorted(ledger.JACKPOTS)} = ${jp:,} / ${total_best:,} "
          f"= {jp / total_best:.0%} du $ total")
    mirage = jp / total_best > 0.40
    print(f"  >>> {'MIRAGE' if mirage else 'OK'} : "
          f"{'le gros du $ dépend de 2 jackpots non-répétables' if mirage else 'pas concentré'}")

    # ---------- (B) EV BASE-RATE HONNÊTE ----------
    section("(B) EV BASE-RATE  [sans jackpots non-répétables, qualif partielle, zéros farmés]")
    base_pool = ledger.total_alloc(exclude=ledger.JACKPOTS)
    realized = base_pool * QUALIFY_FRACTION
    net_base = realized - costs
    evh_base = eur(net_base) / hours
    print(f"  pool non-jackpot ${base_pool:,} × qualif {QUALIFY_FRACTION:.0%} = ${realized:,.0f} réalisé")
    print(f"  net base = ${realized:,.0f} − ${costs:,.0f} coûts = ${net_base:,.0f}  "
          f"-> {evh_base:.1f} €/h")
    gate_B = net_base > 0
    print(f"  >>> (B) {'PASS' if gate_B else 'FAIL'}  (EV {'positive' if gate_B else '≤0'})")

    # ---------- (C) DÉCROISSANCE (réel, CoinGecko) ----------
    section("(C) DÉCROISSANCE post-TGE  [hold-to-now, data réelle]")
    px = ledger.fetch_current_prices()
    if px:
        decays = []
        for n, c, _y, _a, p in ledger.BASKET:
            cur = px.get(c, float("nan"))
            if cur == cur and p > 0:
                dec = cur / p - 1.0
                decays.append(dec)
                print(f"    {n:20s} TGE ${p:<6} -> now ${cur:<10.4g}  {dec:+.0%}")
        if decays:
            med = sorted(decays)[len(decays) // 2]
            print(f"  décroissance médiane hold-to-now = {med:+.0%} "
                  f"(qui n'a pas vendu au TGE s'est fait laminer ; la valo TGE EST le best-case)")

    # ---------- (E) SEUIL DE LABEUR ----------
    section("(E) SEUIL DE LABEUR  [EV/heure > 15 €/h ET > 500 €/trimestre]")
    eur_per_q = eur(net_base) / (WINDOW_YEARS * 4)
    gate_E = (evh_base > FLOOR_EUR_H) and (eur_per_q > 500)
    print(f"  base-case : {evh_base:.1f} €/h  ;  {eur_per_q:,.0f} €/trimestre")
    print(f"  >>> (E) {'PASS' if gate_E else 'FAIL'}")

    # ---------- VERDICT ----------
    section("VERDICT PRÉ-ENREGISTRÉ  (docs/SPEC.md)")
    if not gate_A or not gate_B:
        print("  ¬(A) ∨ ¬(B) => KILL : plafond sous le labeur, ou EV base-rate ≤ 0")
        print("                (mirage survivorship : la traîne + les zéros mangent les jackpots).")
    elif gate_A and gate_B and not gate_E:
        print("  (A) ∧ (B) ∧ ¬(E) => DOWNGRADE : EV réelle mais sous le seuil labeur")
        print("                = un petit boulot opérationnel, pas un edge d'investissement.")
    else:
        print("  (A) ∧ (B) ∧ (E) => GO : seul edge opérationnel du programme.")
        print("                Projet séparé (build farming). Chasse mirage déjà passée.")
    if mirage:
        print("  NB : MIRAGE jackpot actif — tout GO dépendrait de répéter dYdX/Hyperliquid (chance).")


if __name__ == "__main__":
    main()

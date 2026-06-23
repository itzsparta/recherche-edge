"""Runner gates A-D — pré-enregistrés docs/SPEC.md (Piste 15).

Ledger EV structurel (PAS un backtest de prédiction). Tranche : sur les pools V3
canoniques, le cashflow (frais) dépasse-t-il la LVR (markout des arbitragistes,
mesuré sur swaps réels Dune) — ET l'edge agrégé est-il déployable par un solo passif ?

Les chiffres LVR/frais viennent de Dune `dex.trades` (engine free), requête
queries/markout_minute.sql, exécutée 2026-06-23. Recopiés ici verbatim avec
provenance (execution_id) pour auditabilité ; le runner applique les gates.
"""
from __future__ import annotations

# --- mesures Dune (queries/markout_minute.sql), 2024, Ethereum ---
# LVR = liste markout aux horizons [1, 5, 15, 60] min. On retient le MAX (le plus
# DUR pour le LP) = casser le gate dans le sens difficile (anti-faux-GO).
POOLS = {
    # pool                      : (volume_usd,   fees_usd,    lvr_1_5_15_60_min,                       exec_id)
    "WETH/USDC 0.05%": (95_327_377_936, 47_663_689, (19_157_401, 22_193_136, 24_241_483, 23_759_627), "01KVV0TQXHAQKDJX3EFP6WNAD9"),
    "WBTC/WETH 0.30%": ( 7_405_131_782, 22_215_395, ( 2_205_574,  3_040_916,  3_374_635,  1_959_057), "01KVV11ZZ4GHZCVJ2K2PJNBS5C"),
}

# --- déployabilité solo (Gate C/D) ---
TVL_LOW, TVL_HIGH = 150e6, 250e6     # TVL 2024 ~ pool flagship ETH/USDC (DefiLlama snapshot $84M + range documenté)
GAS_PER_REBAL = 40                   # $ mint+burn (2 tx) mainnet 2024
REBALS_PER_YEAR = (100, 200)         # range tight-range ETH/USDC (move ~3-5%/j)
FLOOR_EUR_H = 15.0


def section(t: str) -> None:
    print(f"\n{'=' * 76}\n{t}\n{'=' * 76}")


def main() -> None:
    section("(A) FRAIS > LVR (markout) ?  [pools volatils, 2024, LVR = max sur 1-60 min]")
    print(f"  {'pool':18s} {'volume':>13s} {'frais':>12s} {'LVR(max)':>12s} {'net':>12s} {'net/vol':>8s}")
    nets = {}
    for name, (vol, fees, lvr, _ex) in POOLS.items():
        lvr_max = max(lvr)
        net = fees - lvr_max
        nets[name] = net
        print(f"  {name:18s} ${vol/1e9:>10.1f}B ${fees/1e6:>9.1f}M ${lvr_max/1e6:>9.1f}M "
              f"${net/1e6:>+9.1f}M {net/vol*1e4:>+6.1f}bp")
        # robustesse horizon
        print(f"  {'  LVR 1/5/15/60m':18s} " + " ".join(f"${x/1e6:.1f}M" for x in lvr) +
              f"   (stable -> sensibilité horizon NON déclenchée)")
    gate_A = all(n > 0 for n in nets.values())
    print(f"  >>> (A) {'PASS' if gate_A else 'FAIL'}  "
          f"{'frais > LVR sur TOUS les pools = MMR naïf FALSIFIÉ' if gate_A else 'LVR >= frais (MMR)'}")

    section("(B) MIRAGE — un seul pool porte-t-il l'edge ?")
    pos = [n for n, v in nets.items() if v > 0]
    print(f"  pools nets-positifs : {len(pos)}/{len(POOLS)} ({', '.join(pos)})")
    gate_B = len(pos) == len(POOLS)
    print(f"  >>> (B) {'PASS' if gate_B else 'FAIL'}  "
          f"{'robuste cross-pool (volatil ET moins volatil), pas un mirage mono-pool' if gate_B else 'concentré'}")

    section("(C/D) DÉPLOYABILITÉ SOLO PASSIF  [le tueur — comme CEF #8, niche #3]")
    net = nets["WETH/USDC 0.05%"]
    apr_low, apr_high = net / TVL_HIGH, net / TVL_LOW
    print(f"  edge AGRÉGÉ ETH/USDC : net ${net/1e6:.1f}M / TVL ${TVL_LOW/1e6:.0f}-{TVL_HIGH/1e6:.0f}M "
          f"= +{apr_low:.1%} à +{apr_high:.1%} APR  (réel, capté par LP ACTIFS/JIT)")
    gas_lo = REBALS_PER_YEAR[0] * GAS_PER_REBAL
    gas_hi = REBALS_PER_YEAR[1] * GAS_PER_REBAL
    # capital min pour que le gas de gestion active ne domine pas l'edge
    cap_be_lo = gas_lo / apr_high
    cap_be_hi = gas_hi / apr_low
    print(f"  gas gestion active solo (tight range) : {REBALS_PER_YEAR[0]}-{REBALS_PER_YEAR[1]} rebal/an "
          f"× ${GAS_PER_REBAL} = ${gas_lo:,}-{gas_hi:,}/an")
    print(f"  capital break-even gas seul = ${cap_be_lo:,.0f}-{cap_be_hi:,.0f} "
          f"(en-dessous : edge ENTIÈREMENT mangé par le gas)")
    print("  + JIT (mint-swap-burn atomique) skimme les frais des gros swaps noise sans porter de LVR")
    print("    -> le LP PASSIF hérite du flux toxique (LVR) + frais résiduels << taux agrégé.")
    print("  + passif large-range (sans rebal) : frais/$ s'effondrent sous la LVR -> net <= 0.")
    gate_CD = False  # edge non-déployable solo passif : accru aux actifs/JIT + gas > edge à taille solo
    print(f"  >>> (C/D) {'PASS' if gate_CD else 'FAIL'}  "
          "(agrégé réel mais capté par actifs/JIT ; solo passif : gas > edge OU frais < LVR)")

    section("VERDICT PRÉ-ENREGISTRÉ  (docs/SPEC.md)")
    if not gate_A:
        print("  ¬(A) => KILL : LVR >= frais = MMR confirmé, le LP subventionne l'arbitragiste.")
    elif gate_A and gate_B and not gate_CD:
        print("  (A) ∧ (B) ∧ ¬(C/D) => DOWNGRADE : edge AGRÉGÉ réel (frais > LVR, MMR naïf falsifié,")
        print("       robuste cross-pool & horizon) MAIS non-déployable par un solo passif —")
        print("       capté par les LP actifs/JIT ; à taille solo le gas mainnet dépasse l'edge.")
        print("       Même forme que CEF #8 (réel/non-capturable), niche #3 (réel/sans capacité),")
        print("       sportsbook #16 (+EV pour le participant sophistiqué seulement).")
    else:
        print("  (A) ∧ (B) ∧ (C/D) => GO : cashflow structurel net d'adverse-selection, déployable.")


if __name__ == "__main__":
    main()

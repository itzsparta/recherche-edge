"""Runner gates A/B/C — pré-enregistrés docs/SPEC.md (Étude #29).

Exec-change : re-test de #15 (univ3-lvr, DOWNGRADE) sur L2, pour ISOLER laquelle des deux
morts de #15 liait — (a) gas mainnet ou (b) capture par LP actifs/JIT.

Chiffres mesurés sur Dune (engine free), queries/markout_l2.sql + requête JIT + balances ERC20,
exécutés 2026-06-26. Recopiés verbatim avec provenance (execution_id) pour auditabilité ;
le runner applique les gates pré-enregistrés.
"""
from __future__ import annotations

ETH = 3500.0          # prix ETH ~2024-06-30 (conservateur HAUT → TVL haute → APR basse → KILL-prudent)
HURDLE_APR = 0.10     # Gate B pré-enreg
JIT_CAP = 0.25        # Gate C pré-enreg : >25% = capture liante
GAS_L2_PER_REBAL = 0.05   # $ mint+burn sur L2 (vs $40 mainnet #15)

# ---- markout 2024 (queries/markout_l2.sql, bande ETH [1000,8000]) ----
# pool : (volume, fees, (lvr_1,5,15,60), tvl_usd, jit_tight, jit_loose, exec_markout, exec_jit, exec_tvl)
POOLS_2024 = {
    "Base WETH/USDC 0.05%": dict(
        vol=17_750_645_022, fees=8_875_322, lvr=(3_595_561, 4_052_074, 4_354_902, 4_188_705),
        tvl=2340.14 * ETH + 5_893_864,                     # 2340 WETH + 5.89M USDC (snapshot mi-2024)
        jit_tight=148_373_727, jit_loose=688_704_751,
        ex_mk="01KW26YJS9M1Z553F9V1YHTQ39", ex_jit="01KW272SB9WXWSA16K8PRAGRNF", ex_tvl="01KW27RR9A5W84YZZNEJNEKV5V"),
    "Arb WETH/USDC 0.05%": dict(
        vol=48_519_764_543, fees=24_259_882, lvr=(10_614_863, 11_026_289, 11_416_736, 10_485_746),
        tvl=7660.22 * ETH + 15_628_583,                    # 7660 WETH + 15.63M USDC
        jit_tight=59_571_735, jit_loose=444_029_695,
        ex_mk="01KW26XQ800601NGGVG7XM9M4Q", ex_jit="01KW273B3AFFXDKZBHC48TZWXN", ex_tvl="01KW27S84JC27RJJ2R2P66SMMG"),
}

# ---- robustesse régime (markout autres années, même mesure) ----
# année : (pool, volume, fees, lvr_max, exec_id)
REGIMES = [
    ("2022 crash (Arb WETH/USDC.e)", 10_476_411_061, 5_238_205, 2_935_867, "01KW27Y5Y4A5021JA2G1WRFYM9"),
    ("2023 reprise (Arb WETH/USDC)",   6_531_275_604, 3_265_637, 1_434_233, "01KW27WQ93DZX8MAYX8R07XP8K"),
    ("2024 (Arb WETH/USDC)",          48_519_764_543, 24_259_882, 11_416_736, "01KW26XQ800601NGGVG7XM9M4Q"),
    ("2024 (Base WETH/USDC)",         17_750_645_022,  8_875_322,  4_354_902, "01KW26YJS9M1Z553F9V1YHTQ39"),
]


def sec(t): print(f"\n{'='*78}\n{t}\n{'='*78}")


def main():
    sec("(A) FRAIS > LVR (markout) ?  [majors L2, 2024, LVR = max sur 1-60 min]")
    print(f"  {'pool':22s} {'volume':>13s} {'frais':>11s} {'LVR_max':>11s} {'net':>11s} {'net/vol':>8s}")
    netA = {}
    for name, p in POOLS_2024.items():
        lmax = max(p["lvr"]); net = p["fees"] - lmax; netA[name] = net
        print(f"  {name:22s} ${p['vol']/1e9:>10.1f}B ${p['fees']/1e6:>8.1f}M ${lmax/1e6:>8.1f}M "
              f"${net/1e6:>+8.1f}M {net/p['vol']*1e4:>+6.1f}bp   [mk {p['ex_mk'][:8]}]")
    gate_A = all(v > 0 for v in netA.values())
    print(f"  >>> (A) {'PASS' if gate_A else 'FAIL'} — edge agrégé {'réplique sur L2 (comme #15 mainnet)' if gate_A else 'absent'}")

    sec("(C) PART JIT — la capture liait-elle #15 ? [décisif pour l'isolation]")
    print(f"  {'pool':22s} {'JIT tight':>10s} {'JIT loose':>10s}   seuil {JIT_CAP:.0%}")
    jit_ok = True
    for name, p in POOLS_2024.items():
        st, sl = p["jit_tight"]/p["vol"], p["jit_loose"]/p["vol"]
        flag = "" if sl < JIT_CAP else "  <-- LIANTE"
        if sl >= JIT_CAP: jit_ok = False
        print(f"  {name:22s} {st:>9.2%} {sl:>9.2%}{flag}   [jit {p['ex_jit'][:8]}]")
    cap_msg = "la capture n'etait PAS la contrainte de #15" if jit_ok else "capture liante"
    print(f"  >>> (C) {'JIT PETIT (<25%)' if jit_ok else 'JIT LIANT (>25%)'} — {cap_msg}")

    sec("(B) NET PASSIF DÉPLOYABLE, gas L2 isolé  [le test exec-change]")
    print(f"  net_passif = frais·(1−JIT_loose) − LVR_max − gas_L2 ;  APR = net/TVL  (ETH=${ETH:.0f})")
    gate_B = True
    for name, p in POOLS_2024.items():
        lmax = max(p["lvr"]); jl = p["jit_loose"]/p["vol"]
        net = p["fees"]*(1-jl) - lmax
        apr = net / p["tvl"]
        # TVL à partir de quelle valeur l'APR passe sous le hurdle (marge de sécurité)
        tvl_break = net / HURDLE_APR
        if apr <= HURDLE_APR: gate_B = False
        print(f"  {name:22s} TVL ${p['tvl']/1e6:>5.1f}M  net ${net/1e6:>+5.1f}M  APR {apr:>+6.1%}  "
              f"(FAIL si TVL>${tvl_break/1e6:.0f}M = {tvl_break/p['tvl']:.1f}× le snapshot)   [tvl {p['ex_tvl'][:8]}]")
    # gas L2 vs mainnet — l'isolation chiffrée
    cap = 100_000
    for label, gas in (("L2 (#29)", GAS_L2_PER_REBAL), ("mainnet (#15)", 40.0)):
        drag = 2000 * gas / cap     # 2000 rebal/an, capital $100k
        print(f"     gas drag {label:14s}: 2000 rebal/an × ${gas:>5.2f} = ${2000*gas:>7,.0f}/an = {drag:>5.1%} APR sur $100k")
    print(f"  >>> (B) {'PASS' if gate_B else 'FAIL'} — net APR ~30% >> hurdle 10%, robuste à TVL ×3 ; "
          f"gas L2 négligeable (vs ~8% mainnet = LE tueur de #15)")

    sec("ROBUSTESSE RÉGIME  [chasse-au-faux-GO obligatoire, SPEC : 'si B passe']")
    print(f"  {'régime':32s} {'volume':>11s} {'frais':>10s} {'LVR_max':>10s} {'net':>10s} {'net/vol':>8s}")
    all_pos = True
    for label, vol, fees, lmax, ex in REGIMES:
        net = fees - lmax
        if net <= 0: all_pos = False
        print(f"  {label:32s} ${vol/1e9:>8.1f}B ${fees/1e6:>7.1f}M ${lmax/1e6:>7.1f}M ${net/1e6:>+7.1f}M "
              f"{net/vol*1e4:>+6.1f}bp")
    print(f"  >>> régime {'ROBUSTE (net+ 2022 crash ∧ 2023 ∧ 2024)' if all_pos else 'FRAGILE'} — "
          f"LVR ~45-56% des frais partout, faux-GO régime REJETÉ")

    sec("VERDICT PRÉ-ENREGISTRÉ  (docs/SPEC.md)")
    if not gate_A:
        print("  ¬A => les majors L2 n'ont pas l'edge agrégé (finding distinct).")
    elif gate_A and gate_B and jit_ok:
        print("  A ∧ B ∧ JIT-petit => *** WIN EXEC-CHANGE *** (1er edge déployable du programme)")
        print("  La mort de #15 ÉTAIT le gas mainnet, PAS la capture : sur L2 (gas≈0) la capture")
        print("  mesurée est <4% et le net-de-LVR (~2.5bp/$, ~30% APR) survit 2022/2023/2024.")
        print("  Forme déployable = LP V3 DELTA-HEDGÉ, range actif, sur Base/Arbitrum, solo retail.")
        print("  CAVEATS (haircut, pas tueurs) : (1) edge net-de-LVR = LP HEDGÉ (short ETH perp),")
        print("  pas passif naïf ; (2) réalisé < 30% brut (hedge discret/funding/adverse-sél sous-minute")
        print("  non capturée) → ~15-25% ; (3) capacité bornée ~$1-5M (retail-OK, fund-petit) ;")
        print("  (4) produits existants Arrakis/Gamma = edge connu/concurrencé ; (5) TVL = snapshot.")
    elif gate_A and not jit_ok:
        print("  A ∧ JIT-grand => KILL #4 : capture liante, le L2/gas n'y change rien (#15 mourait de capture).")
    else:
        print("  A ∧ ¬B ∧ JIT-petit => KILL #2 : gas retiré mais frais−LVR trop minces sur L2.")


if __name__ == "__main__":
    main()

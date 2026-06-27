# FINDINGS Phase-2.5 — #29 : replay POSITION-SPÉCIFIQUE = **REVERSAL, GO → KILL**

**Verdict : le GO de #29 NE survit PAS à une mesure de LVR position-spécifique full-path.
Les frais d'un LP delta-hedgé sont < sa LVR à TOUTE concentration ; le seul net positif est du
funding-carry, qui domine #29 → #29 est strictement dominé par la piste #6 (carry funding), déjà KILL.**

Supersede [`FINDINGS-phase2.md`](FINDINGS-phase2.md) (« GO-pending-live TIENT ») : Phase-2 retirait
les coûts simulables MAIS gardait l'edge fee>LVR de Phase-1 comme INPUT (le net-agrégé 30 %, plafonné).
Phase-2.5 mesure cet edge **indépendamment** depuis le vrai flux et il **disparaît**.

Code : [`../replay_position.py`](../replay_position.py). Data : frais+liquidité active par-jour du pool
Base WETH/USDC 0,05 % via Dune (exec `01KW2Z6GWVEZWY3SS7F79176KR`, **réconcilié $8,874 M ≈ Phase-1
$8,875 M** — preuve que l'attribution de frais est juste), prix/funding ETH 2024 Binance (cache Phase-2).

## La mesure (ce que Phase-1 n'a pas fait)

Phase-1 : LVR = **markout 1-60 min** (flux signé × rendement forward), agrégé pool → LVR = 45-56 % des
frais → net = frais−LVR ≈ +moitié-des-frais ≈ **+30 % APR**. Phase-2.5 : pour une **position concrète**
(centre, demi-largeur `w`), frais réels = part pro-rata `my_L/(L_active)` du vrai flux par-jour ; **LVR =
P&L d'un LP hedgé en continu** (Milionis) sur le vrai chemin ETH 2024. C'est le coût EXACT de la forme
déployable de #29 (« LP delta-hedgé »), pas un proxy.

`my_L` et `L_active` (Dune `liquidity`) sont la **même** liquidité on-chain (unités raw) → part de frais
directement comparable. POURQUOI pas un Anvil-fork EVM : injecter ta liquidité change le prix-impact des
swaps historiques (revert/output faux) ; le contrefactuel EVM n'a de sens que si tu BOUGES le prix = hors
régime retail price-taker, où la thèse #29 ne tient plus. À $10k-1M dans un pool $10-40M tu es price-taker
→ la part pro-rata est la mesure correcte.

## Le résultat décisif (frais RÉELS vs LVR full-path, par $ déployé, 2024)

| notional | w | frac_in_range | frais_réels | LVR | **frais/LVR** | funding | NET |
|---|---|---|---|---|---|---|---|
| $10k | 2 % | 94,0 % | +412 % | −458 % | **0,90** | +8,3 % | −38,0 % |
| $10k | 5 % | 98,7 % | +188 % | −201 % | **0,93** | +8,0 % | −5,3 % |
| $10k | 10 % | 99,7 % | +98 % | −105 % | **0,93** | +8,3 % | +0,7 % |
| $10k | 20 % | 99,9 % | +50 % | −54 % | **0,93** | +7,7 % | +4,0 % |
| $10k | 50 % | 100 % | +20 % | −21 % | **0,94** | +7,0 % | **+5,8 %** |
| $10k | 100 % | 100 % | +9 % | −9 % | **0,94** | +2,7 % | +2,2 % |

(à $100k : NET de −105 % à +5,1 %, optimum w=50 % ; dilution de capacité visible — `my_L` sature face à
`L_active`.)

## Pourquoi c'est un KILL, pas un bruit

1. **Le cœur frais−LVR est NÉGATIF partout.** Meilleur cas w=50 % : frais 19,9 % − LVR 21,2 % = **−1,3 %**.
   Jamais positif à aucune concentration. L'edge LP « frais > LVR » de Phase-1 est **faux** sous LVR full-path.

2. **Ratio frais/LVR ≈ 0,90-0,94 CONSTANT** de 543 recentrages (w=2 %) à **0 recentrage** (w=100 %) →
   la fuite reset-recentrage est **exonérée** (même ratio à 0 recentrage). Bruit micro horaire :
   inflation LVR **≤ 2,2 %** relatif (`Var(bruit)/Var(rendement réel)`, std horaire 0,68 %) — il faudrait
   **+115 %** pour sauver le GO. Le ratio <1 est **structurel et réel**.

3. **Markout 1-60 min sous-estime la LVR ~2× en année trend.** ETH +41 % 2024 : après chaque trade l'arb
   continue de driver le prix **au-delà de 60 min** → le markout tronque la perte, la mesure continue la
   capture. Le « LVR = 45-56 % des frais » de Phase-1, suspicieusement propre (net = +moitié partout),
   était un artefact d'horizon. Pour un LP **delta-hedgé**, le coût correct EST le P&L hedgé continu —
   c'est la thèse de #29 elle-même.

4. **Cohérent avec la littérature** : les LP passifs ETH/USDC 0,05 % font ≈ break-even / négatif après LVR
   (Milionis-Moallemi-Roughgarden ; dashboards LVR). Le net~0 ex-funding du replay matche ; le +30 % de
   Phase-1 était l'outlier.

## L'effondrement dans #6 (le coup de grâce logique)

LP delta-hedgé = (LP long-delta + short perp) = **funding-carry market-neutral + (frais − LVR)**. Comme
frais − LVR ≤ 0 à toute concentration, **#29-hedgé est STRICTEMENT DOMINÉ par #6** (carry funding pur :
long spot / short perp, market-neutral, sans le drag LVR ni la limite de capacité du LP). Le seul net
positif de #29 (+5,8 %, w=50 %) **est** le funding 2024, et un short perp nu le capte mieux. Or **#6 =
KILL** (Phase-2 forward : OOS-24m +3,8 % < hurdle 8 %, break-even exchange 3,6 % < 5 %). Donc **#29 = KILL
a fortiori** : le wrapper LP ajoute de la LVR et une borne de capacité pour **zéro** bénéfice de frais net.

## Ce que ça ne tue pas / honnêteté

- La **réplication géographique de #15** (gas mainnet liait, pas la capture JIT) reste un finding valide et
  intéressant — mais il rendait l'edge *déployable* en supposant fee>LVR, qui tombe ici.
- Un LP **non hedgé** directionnel peut gagner en bull (mais c'est du beta ETH, pas un edge).
- Un **ALM sophistiqué** (range dynamique, JIT, rebalancement optimal) peut faire mieux que ce replay
  mécanique — mais c'était **déjà** le caveat de Phase-1 (« edge capté par le sophistiqué ») ; Phase-2.5
  quantifie que même le LP-hedgé-passif, la forme retail revendiquée, **nette ~0 ex-funding**.

## Verdict

**#29 : GO → KILL (Phase-2.5).** 3e faux-GO démasqué en chasse post-GO (après VRP, CEF), et le seul GO du
programme tombe. Le LP delta-hedgé ne bat pas sa propre LVR ; ce qui restait = funding-carry = #6 déjà mort.
**Programme : 29 études, 0 edge déployable.** Deliverable trading = mono-sleeve trend seul (sleeve faible,
pas un edge standalone). Leçon méta : **un markout court-horizon n'est pas une mesure de LVR pour un LP
hedgé en année trend ; la seule mesure honnête est le P&L hedgé full-path, position-spécifique.**

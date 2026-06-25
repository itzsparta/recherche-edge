# FINDINGS — Étude #25 : flux forcé de fin de séance (rebalancement LETF)

**Verdict : KILL.** Le flux de rebalancement des ETF à levier est **réel et mécanique**, mais il
ne laisse **aucune empreinte exploitable** là où il est le plus gros : l'interaction identifiante
`I = r·(G/volume$)` est **insignifiante** (t=−0.30 plein échantillon, **−0.64 en sous-échantillon
mûr 2023+**), la **dose-réponse est INVERSÉE** (le reversal est le plus fort là où il y a le *moins*
de LETF), et le trade de fade overnight est **net négatif** (t=−3.20). C'est le **sous-type #2
(arbitré/absorbé jusqu'au coût)** : sur les gros sous-jacents LETF (QQQ, SOXX, SPY = les plus
liquides), le flux est entièrement absorbé. Spec + gates pré-enregistrés 2026-06-25 :
[`SPEC.md`](SPEC.md). Code : [`../pull_and_gate.py`](../pull_and_gate.py). Données :
`../data/gate_results.json`.

## Ce qui a été testé

Première piste sous l'angle **« arme structurelle neuve »** = contrepartie nommée, insensible au
prix, dont le flux mécanique pourrait dépasser le capital d'arbitrage. Mécanique : un LETF de levier
`L` doit, au close, trader `Δ = AUM·r·L(L−1)` pour reset son exposition ; `L(L−1) > 0` pour **tous**
les leviers → long et inverse achètent du même côté → flux agrégé `Imbalance ≈ r·G`, avec
`G = Σ AUM_i·L_i(L_i−1)`. Panel de **11 sous-jacents** (45 562 name-jours, 2010-2026 ; 9 581 mûrs
2023+), spread de `G` très large (proxy AUM = snapshot `totalAssets` yfinance) :

```
QQQ $296B  SOXX $178B  SPY $103B  TLT $18B  XLF $14B  IWM $12B
DIA $7B    XBI $4B     GDX $3B    EEM $2B   XLE $0.8B
```

**Identification** = l'interaction `I = r·(G/volume$)`, PAS `r` seul (= momentum générique) : à
rendement égal, l'effet doit être plus fort là où le complexe LETF est gros vs la liquidité.

## Résultats — Gate A (identification) : FAIL

| test | coef(I = driver·G/vol$) | t(I) | coef(driver) | t(driver) |
|---|--:|--:|--:|--:|
| FULL (driver r_cc) | −0.00001 | **−0.30** | −0.00019 | −1.04 |
| **MÛR 2023+** (r_cc) | −0.00008 | **−0.64** | +0.00018 | +0.53 |
| FULL (driver r_oc) | −0.00002 | −0.58 | +0.00006 | +0.43 |

SE clusterisées par date. L'interaction identifiante est **nulle partout**, et le reversal
générique (`driver` seul) est lui-même insignifiant sur ces ETF liquides.

**Dose-réponse INVERSÉE (le tueur décisif).** Pente `r_on ~ r_cc` par quintile de `G/volume$`
(attendu : *plus négatif* quand `G/vol$` monte) :

```
FULL :   q0(bas G/vol$) −0.024  →  q1 −0.010  q2 −0.011  q3 −0.009  →  q4(haut) −0.003
MÛR  :   q0 +0.018  q1 +0.024  q2 −0.020  q3 +0.032  q4 +0.003   (bruit, aucune structure)
```

Le reversal est **maximal là où il y a le MOINS de LETF** (q0) et **s'évanouit là où il y a le PLUS**
(q4). C'est l'**opposé** de la prédiction LETF. Lecture cohérente : q0 = petits/illiquides → reversal
microstructure générique ; q4 = QQQ/SOXX/SPY = les plus liquides et efficients → flux LETF **absorbé**,
zéro résidu. Même falsification que le **spread fantôme p3** : un effet sans dose-réponse (ici à
contre-sens) = pas le mécanisme invoqué.

## Résultats — Gate B (déployabilité) : FAIL

Trade = fade overnight pondéré par `I` (short le close des jours de flux acheteur, etc.),
gross-normalisé/jour, sortie à l'open suivant. Coût round-trip **borné bas 4 bp** (best-case).

| sous-ensemble | brut/j | t | net/j | t(net) | both-halves |
|---|--:|--:|--:|--:|:--|
| FULL | −0.00010 | −0.64 | **−0.00050** | **−3.20** | non |
| MÛR 2023+ | −0.00015 | −0.36 | −0.00055 | −1.33 | non |
| UP-days | −0.00068 | −4.86 | −0.00108 | −7.71 | non |
| DOWN-days | +0.00065 | +4.30 | +0.00025 | +1.65 | OK |

Le fade est **net négatif** (t=−3.20 plein). **Asymétrie révélatrice** : après les jours de hausse
l'overnight **continue** (fader perd, t=−7.71), seuls les jours de baisse rebondissent — et ce
rebond est **sous-coût** (net t=1.65) **et générique** (aucune dose-réponse en `G/vol$`). La
**symétrie** prédite par la mécanique LETF (les deux côtés rebondissent au close) est **fausse** :
ce qu'on capte est le « overnight bounce après selloff » connu (prime de risque overnight), pas le
flux LETF.

## Le mécanisme du kill

1. **Le flux est réel mais sans résidu là où il est gros.** Δ=AUM·r·L(L−1) existe ; mais sur QQQ/
   SOXX/SPY (G de $100-300B) la liquidité et les desks d'arbitrage absorbent l'imbalance au close →
   l'interaction `I` est nulle (#2, **absorbé jusqu'au coût**). La dose-réponse inversée le prouve :
   l'effet est dans les petits noms (microstructure), pas dans les gros (LETF).
2. **Pas de momentum/reversal LETF-spécifique.** `r` seul est insignifiant ; le seul reste tradable
   (rebond post-baisse) est une prime overnight déjà connue, non liée au levier, et **sous-coût**.
3. **Conforme au prior pré-enregistré** : thèse textbook depuis Cheng-Madhavan 2009 → arbitrée. Le
   gate a tranché sans faux-GO, barre `t>3 / net>0` non tunée [[feedback-gate-override]].

## Robustesse / honnêteté

- **Best-case donné à la thèse** : coûts bornés bas (4 bp), proxy AUM généreux, identification
  testée des deux drivers (r_cc, r_oc) → un KILL est conservateur.
- **Caveat AUM statique** : `G` utilise un snapshot d'AUM (pas l'historique des créations/rachats) →
  `G/vol$` varie surtout par le volume et `r`. Mais le **classement** des sous-jacents (ce qui porte
  la dose-réponse) est stable, et la dose-réponse est *inversée*, pas *plate-par-bruit* → un AUM
  time-varying ne sauverait pas un signe à contre-sens.
- **Bonus push intraday non requis** : le daily ayant KILLé en Gate A (interaction nulle) ET Gate B
  (fade net<0), le test horaire du push late-day serait confirmatoire au mieux — non bloquant.

## Place dans le programme

**Étude #25, 1re sous l'angle « arme structurelle neuve », KILL.** Sous-type = **#2 (arbitré /
absorbé jusqu'au coût)**, confirmé de façon nette par la **dose-réponse inversée** (le flux n'a
d'empreinte que là où il est petit). La famille « flux forcé » rejoint le motif unifié du programme :
un flux mécanique public et daté est absorbé au close par la liquidité des gros sous-jacents. La
contrepartie insensible au prix (l'émetteur LETF) existe, mais son flux **ne dépasse pas** le capital
d'arbitrage là où il compte.

**Bilan programme : 25 études, 0 edge déployable.** L'arme structurelle neuve cherchée n'était pas
neuve assez : le flux LETF est trop public et trop concentré sur des sous-jacents trop liquides.

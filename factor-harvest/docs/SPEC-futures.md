# Piste 1bis — Trend-following univers FUTURES riche : pré-test (PRÉ-ENREGISTRÉ)

> Écrit **avant** de voir le moindre résultat. Suite au KILL ETF (Sharpe 0.42, t=1.87) :
> l'univers ETF maigre (9, corrélés actions) sous-vend un premium qui **dépend de la
> largeur**. Ce test corrige le seul vrai défaut identifié. Critères **identiques** à
> [`SPEC.md`](SPEC.md) — seul l'univers change. Aucun critère modifiable après résultats.

## Hypothèse

Le **même** trend-following pré-spécifié (12m, vol-target, gross=1x, net), sur un
univers **futures continus diversifié (32 marchés / 8 secteurs)** au lieu de 9 ETF :

1. récolte un premium positif et **significatif (t>2)** en standalone — ce que l'ETF
   ratait de peu — grâce à la diversification cross-sectorielle, ET
2. reste worth-harvesting (bat 60/40 OU crisis-alpha).

## Univers (FIXE — 32 futures continus, gratuit yfinance `=F`)

| Secteur | Tickers |
|---|---|
| Indices actions | ES NQ YM RTY |
| Taux / oblig | ZB ZN ZF |
| Énergie | CL NG HO RB BZ |
| Métaux | GC SI HG PL PA |
| Grains | ZC ZW ZS |
| Softs | KC SB CC CT |
| Bétail | LE HE |
| FX | 6E 6J 6B 6A 6C 6S |

Échantillon ~2000 → 2026 (~25 ans, plus long que l'ETF). Dates de départ
hétérogènes (RTY 2017…) → moteur en **mode union** : un actif entre dès qu'il a 12m
d'historique, poids gross=1x normalisé sur les actifs actifs.

## Signal / sizing / frais / métriques / décision

**Identiques à SPEC.md** : momentum 12m signe ; vol-target 60j ; gross=1x ; 10 bps
round-trip ; robustesse {6,9,12,15} en diagnostic + DSR ; (A) edge existe [Sharpe>0,
t>2, majorité régimes, drop-one, lookbacks positifs, DSR>0.95] ; (B) vaut le coup
[bat 60/40 OU crisis-alpha 2008&2022]. Décision : (A)∧(B)⇒GO, (A)∧¬(B)⇒DOWNGRADE,
¬(A)⇒KILL.

Benchmark 60/40 reste sur **ETF SPY/IEF** (rendement total propre) — le comparant est
l'investisseur passif réel.

## Caveat pré-enregistré — roll-adjustment

Les continus front-month yfinance `=F` ne sont **pas** back-adjustés : à chaque roll,
un gap (contango/backwardation) contamine le rendement. C'est du **bruit** (Norgate/CSI
back-adjustés = payant, hors scope). Le bruit de roll **baisse** le Sharpe → **un PASS
t>2 malgré ça est conservateur/crédible** ; un FAIL marginal pourrait être en partie du
bruit de roll (à ne pas sur-interpréter comme « trend mort » sans data propre).

## Parallélisation (demande explicite)

- **Fetch** : 32 tickers en `ThreadPoolExecutor` (I/O réseau, GIL relâché).
- **Compute** : drop-one (32 runs) + lookbacks (4) en `ProcessPoolExecutor`
  (CPU, pandas vectorisé), `initializer` partageant le DataFrame prix une fois par worker.

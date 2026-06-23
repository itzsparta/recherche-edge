# SPEC — Piste 18 : Dealer gamma (GEX) — flux forcé (pré-enregistré)

> Écrit **avant** tout chiffre. Pari sur un **flux FORCÉ** : les dealers d'options **doivent** hedger
> leur gamma (delta-hedging mécanique, price-insensitive) — la catégorie théoriquement **la moins
> arbitrée**. Question : le signe/niveau du **GEX** (dealer gamma exposure) prédit-il le comportement
> du marché du lendemain **de façon tradable nette de coûts**, ou seulement la **vol** (mécanisme réel
> mais sans alpha de rendement, priced-in depuis que GEX est mainstream ~2021) ?

## Hypothèse d'edge

Le **GEX** prédit le régime du lendemain : **GEX très positif** → dealers longs gamma → ils vendent les
hausses / achètent les baisses → **vol supprimée + mean-reversion** ; **GEX négatif** → dealers courts
gamma → ils achètent les hausses / vendent les baisses → **vol amplifiée + momentum**. Un switch
mean-reversion/momentum conditionné au GEX, ou un overlay de vol-timing, dégage un edge net.

## Pourquoi ça pourrait persister — flux forcé, price-insensitive

Le hedging de gamma n'est **pas** un pari : c'est une obligation mécanique du dealer (rester delta-neutre).
Le hedger est **insensible au prix** → c'est le seul type de flux qui, en théorie, **ne s'arbitre pas**
de lui-même (≠ edge à info/prix public). Famille « flux forcés » (piste 2 unlocks) mais récurrent et
quotidien, pas événementiel.

## Le null honnête (= verdict attendu a priori)

Prior bas (17 morts). Morts pré-enregistrées :
1. **GEX prédit la vol (réel) mais pas le rendement (priced-in)** — le mécanisme gamma-vol est solide
   et documenté → **(A) PASSE probablement**. Mais l'alpha de **rendement** (mean-rev/momentum switch)
   est **mangé** une fois public : GEX est devenu un mème retail (~2021, SpotGamma/Menthor/SqueezeMetrics)
   → **(B)/(C) KILL** comme **pré-FOMC #5b** (mécanisme réel, alpha mort à la publication, McLean-Pontiff).
2. **Juste du short-vol déguisé** — GEX négatif = vol haute ; un « edge » conditionné au GEX peut n'être
   que du **bêta de vol** (long vol quand vol monte). → DOWNGRADE si non-orthogonal (D).
3. **Daily-only** — données quotidiennes (close SPX), pas intraday ; le pinning intraday (le plus cité)
   n'est pas testable → on teste le switch **daily**, plus faible. Honnête sur la limite.

## Univers / data (FIXE — déterministe)

**SqueezeMetrics DIX.csv** (gratuit, `squeezemetrics.com/monitor/static/DIX.csv`) : date, **price**
(close SPX), dix, **gex** (dealer gamma $/1 %). ~3808 jours **2011-05 → 2026-06**. Rendements + vol
réalisée calculés **directement** du close SPX. Aucune autre source. Cache local (gitignoré).

## Mesure (FIXE)

- **Rendement** `ret_t = close_t/close_{t-1} − 1`. **Vol réalisée proxy** = `|ret_t|` (daily).
- **Signal GEX** = `gex_{t-1}` (laggé, connu en clôture veille). Régimes par quantiles (ex. tercile
  haut / bas) ou signe.
- **Stratégies tradables** (signal en t-1, rendement en t, coûts 1 bp/jour de turnover SPX) :
  - **(S1) switch mean-rev/momentum** : `pos_t = −sign(ret_{t-1})` si GEX haut (fade), `+sign(ret_{t-1})`
    si GEX bas (follow).
  - **(S2) vol-timing overlay** : pleine expo SPX si GEX > médiane (régime supprimé), réduite/0 si
    GEX bas (régime amplifié). Comparé au buy-hold SPX.
- **Sleeve / orthogonalité** : corrélation du rendement de la stratégie au niveau de vol (|ret|) et au
  SPX, pour isoler le bêta de vol.

## Gates de décision (pré-enregistrés)

- **(A) Mécanisme — GEX prédit la vol** : `corr(gex_{t-1}, |ret_t|) < 0` significatif (haut GEX → vol
  basse). Si même ça échoue → **KILL** (pas de signal du tout).
- **(B) Edge de rendement tradable** : meilleure de {S1, S2}, **t > 2** net de coûts **∧ DSR > 0.95**
  (audit.py, anti-multiple-testing sur les variantes de régime).
- **(C) Priced-in / Gate-G** : l'edge tient **post-2021** (GEX mainstream), pas seulement pré-2021.
  Si alpha pré-2021 only → **KILL priced-in** (McLean-Pontiff, comme pré-FOMC post-2015).
- **(D) Orthogonal au bêta de vol** : l'edge n'est pas expliqué par un simple long/short vol (contrôle
  niveau de vol). Sinon **DOWNGRADE** (bêta de vol déguisé).

## Décision pré-enregistrée

- **(A)∧(B)∧(C)∧(D) ⇒ GO** : flux forcé tradable non-arbitré — rare. Chasse mirage obligatoire.
- **(A)∧(B)∧(C)∧¬(D) ⇒ DOWNGRADE** : réel mais = bêta de vol.
- **(A)∧¬(B) ⇒ KILL-tradable** : GEX prédit la vol (réel) mais **aucun alpha de rendement** déployable
  (comme overnight #5a / pré-FOMC #5b : mécanisme réel, rien à trader net).
- **(A)∧(B)∧¬(C) ⇒ KILL priced-in** : alpha mort post-mainstream 2021.
- **¬(A) ⇒ KILL** : pas même de signal vol.

## Falsifiabilité (comment ça meurt)

1. corr(GEX, vol) ≥ 0 ou ns → KILL (A). 2. S1/S2 t<2 ou DSR<0.95 → KILL-tradable (B). 3. Alpha
pré-2021 only, mort post-2021 → KILL priced-in (C). 4. Edge expliqué par bêta de vol → DOWNGRADE (D).

## Données & implémentation

- **GEX + SPX** : SqueezeMetrics DIX.csv (urllib, cache). **DSR** : `factor-harvest/audit.py` copié.
- **Sortie** : `data_gex.py` (DIX + returns/vol), `gex.py` (S1/S2 + régimes), `run_gex.py`
  (gates A-D + verdict), `docs/FINDINGS.md`. Interpréteur stdlib (pas de pandas requis).

## Verdict attendu a priori

Le mécanisme gamma-vol est **réel** (flux forcé, bien documenté) → **(A) devrait PASSER** : GEX est un
**prédicteur de vol** authentique. La discriminante est **(B)/(C)** : l'alpha de **rendement** survit-il
au coût et au fait que GEX soit public depuis 2021 ? Le programme prédit **KILL-tradable** (un vrai
prédicteur de vol ≠ un edge de rendement déployable — comme overnight/pré-FOMC : le mécanisme est réel,
l'alpha net est mort) ou **KILL priced-in** (mème retail post-2021). Un GO exigerait un switch tradable,
robuste, post-2021, orthogonal au bêta de vol — improbable mais le test tranche.

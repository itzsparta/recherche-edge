# FINDINGS — Étude #28 : PEAD (post-earnings-announcement drift)

**Verdict : KILL (Gates B et C ; D passe la barre triviale mais insignifiant).** L'anomalie publiée la
plus robuste du factor-zoo est **absente de l'univers liquide déployable, net de friction**. Sur un panel
propre de **58 917 événements** (898 noms S&P 500+400, 8-K Item 2.02, 2004-2026), le **spread** PEAD —
les fortes surprises dérivent-elles plus que les faibles ? — vaut **+0,00 % avec t(inter-mois) = +0,01**.
Il n'y a pas de long-short à monétiser : ce qu'on voit (dérive uniforme ~+0,3 %/mois sur les trois
terciles) est un **résidu midcap-vs-SPY**, pas un effet de surprise, et le long-short l'annule à zéro.

Pré-enregistré : [`SPEC.md`](SPEC.md). Code : [`../data.py`](../data.py) (univers S&P + CIK + dates 8-K),
[`../run.py`](../run.py) (panel + gates calendar-time), [`../prefetch.py`](../prefetch.py) (caches //).
Données : `../data/events.json`, `../data/run_log.txt`.

## Ce qui était testé

PEAD (Bernard-Thomas 1989) : après une publication, le prix dérive dans le sens de la surprise pendant
des semaines. **Surprise** (proxy free, sans estimés analystes) = rendement d'annonce **standardisé**
`z = CAR[-1,+1]_mkt-adj / (σ_pré·√3)`. **Dérive** = `CAR[+2,+21]_mkt-adj` (≈1 mois, primaire). LS =
moy(dérive | T3 haut-z) − moy(dérive | T1 bas-z), terciles à cutoffs fixes 33/67 pct. `mkt-adj` = excès
quotidien vs SPY (un rendement = marché n'est pas un alpha).

**t de gating = calendar-time inter-mois** : cohorte = mois d'annonce, t sur la série des LS mensuels —
robuste au chevauchement des fenêtres de détention. L'inter-événement *pooled* (autocorrélé) est reporté
en diagnostic seulement (leçon carry #6).

## Les chiffres (gates pré-enregistrés)

| Gate | n | LS calendar-time | t(inter-mois) | pooled (diag.) | terciles T1/T2/T3 | Statut |
|---|---|---|---|---|---|---|
| **A** plein (drift1) | 58 917 | **+0,00 %** | **+0,01** | +0,11 % (t=1,4) | +0,27/+0,35/+0,38 mono | **FAIL** (req t>3) |
| **B** maturité 2015+ | 38 475 | **−0,07 %** | **−0,37** | +0,03 % (t=0,3) | +0,27/+0,40/+0,30 | **FAIL** |
| **C** liquide net | 57 486 | brut +0,07 % → **net −33 bps** | +0,51 | — | — | **FAIL** (req net>60) |
| **D** large-cap S&P500 | 35 324 | +0,10 % | +0,65 | +0,23 % (t=2,4) | +0,23/+0,34/+0,46 mono | PASS (barre >0 seule) |

Secondaire **drift3** (3 mois) : LS **−0,18 %**, t=−0,59, terciles +0,74/+1,02/+0,89 **non-monotone** →
même verdict à l'horizon classique 60-jours : dérive de niveau, **pas de spread de surprise**.

## Pourquoi c'est un KILL propre (et pas un faux-KILL)

1. **Le spread est nul, pas le niveau.** Les trois terciles dérivent ~+0,3 %/mois *en mkt-adj* — mais
   c'est le **résidu midcap-vs-SPY** (le S&P 400 bat le S&P 500 large-cap, donc l'ajustement vs SPY laisse
   un positif uniforme sans rapport avec la surprise). Le **long-short l'annule à 0,00 %**. La construction
   LS fait exactement son travail : elle isole l'effet-surprise, et il n'y a rien.

2. **La discipline calendar-time a tué un faux-positif.** Le t *pooled* disait 1,4 (A) et **2,4** (D) — de
   quoi se raconter « mild edge en large-cap ». Le t **inter-mois** honnête dit **0,01** et **0,65** : du
   bruit. Sans la correction d'autocorrélation (leçon carry #6), j'aurais sur-vendu le Gate D. Gate D ne
   « passe » que parce qu'il ne demandait que spread>0 ; il est **statistiquement insignifiant**.

3. **Décroissance + friction, les deux tueurs canoniques.** Le spread est **négatif** en régime mûr 2015+
   (B), et **net −33 bps** après un round-trip de 40 bps pourtant généreux (C). C'est la mort sous-type #2
   dans sa forme manuel-d'école : anomalie réelle, publiée, **arbitrée et décrue** depuis qu'elle est
   connue.

## Place dans le programme

**KILL, sous-type #2 (réel historiquement mais arbitré / décru), forme canonique.** C'était l'attaque
**prédiction-de-prix** la plus haut-prior qui restait jamais testée — l'anomalie publiée *par excellence*.
Résultat : dans l'univers **où l'on peut trader** (liquide), net de coût, **le spread PEAD a disparu**.
Le motif unifié du programme tient : tout edge à information publique (ici, une date de publication
connue de tous) est mangé — par l'arbitrage (décru 2015+) puis par la friction (net négatif).

## Caveats (déclarés d'avance, honnêtes)

- **Microcaps exclues PAR DESIGN.** Le PEAD est historiquement le plus fort dans les micro/illiquides.
  L'univers S&P 500+400 est liquide exprès → ceci teste la **déployabilité**, pas l'existence
  universelle. Lecture exacte : « le PEAD n'est pas là où l'on peut le trader, net de friction »,
  *pas* « le PEAD n'existe nulle part ». C'est la question déployable, et elle est tranchée NON.
- **Variante prix vs SUE fondamental.** On a testé la version *price-based* (earnings-momentum), la plus
  arbitragée. La SPEC prévoyait un Phase-2 SUE (EPS XBRL, seasonal random walk) **seulement si A passait** ;
  A échoue → Phase-2 sans objet pour le verdict déployable. Un SUE fondamental *pourrait* montrer un résidu
  en microcap, mais hors univers tradable, donc hors-sujet pour le but du programme.
- **Survivorship** : constituants actuels du S&P → dérive sur les survivants. Direction du biais pour le
  PEAD ambiguë ; non corrigé en Phase-1.

**Bilan : 28 études, 0 edge déployable.** Le PEAD — l'anomalie publiée la plus solide — confirme le motif :
réel dans les microcaps de la littérature, **nul dans l'univers liquide net de coût**. Deliverable trading
inchangé = **mono-sleeve trend**. La discipline calendar-time a, une fois de plus, démasqué un faux-positif
(Gate D pooled t=2,4 → inter-mois 0,65).

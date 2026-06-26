# FINDINGS — Étude #27 : arbitrage SPAC-trust

**Verdict : KILL (Gate A, hurdle pré-enregistré).** Le discount-vers-trust est **RÉEL, robuste et
*clause-safe*** — la propriété qui manquait à #26 (un plancher que la contrepartie ne peut pas voider)
**TIENT** : t inter-noms **+11 à +15**, **87-90 %** des noms cotent sous le trust accru, survit en
régime mûr 2023+ et hors top-2 noms, **et n'est PAS un bounce** (entrée laggée +1 ≈ entrée live).
**Mais l'excès sur T-bill est compressé SOUS la barre déployable** : **+145 bps** (deadline central
24 mo) / **+85 bps** (réaliste 36 mo avec extensions) < **hurdle pré-enregistré 200 bps**. Le plancher
est réel et inviolable ; le marché a **arbitré l'excès jusqu'à ~la prime d'illiquidité**, en-dessous
de ce qui justifie d'immobiliser du capital dans un instrument illiquide à lock-up. Discipline
[[feedback-gate-override]] : je **ne baisse pas** le hurdle à 145 pour fabriquer un PASS.

Pré-enregistré : [`SPEC.md`](SPEC.md). Code : [`../data.py`](../data.py) (univers EDGAR + couverture),
[`../run.py`](../run.py) (panel trust-accru + gates). Données : `../data/panel_names.json`,
`../data/run_log.txt`.

## Ce qui était testé (et pourquoi c'était le bon test post-#26)

La tenaille #26 a posé le critère de toute reprise = un **plancher +EV *clause-safe*** (que la
contrepartie ne peut annuler). La SPAC pré-deal en est le candidat : downside contractuellement planché
au **droit de rédemption** (trust en T-bills), pas à une règle de firme révocable. **Identité testée** :
acheter à `P`, rédimer au trust qui accroît au T-bill →

```
excès_annualisé sur T-bill  ≈  discount_to_accrued_trust / τ_restant
```

Le T-bill n'accroît que le trust ; l'**excès** = le discount amorti sur le temps-à-rédemption. Test
décisif = excès **SUR T-bill** (un rendement = cash n'est pas un alpha), **t inter-noms** (pas
intra-jour, qui gonfle par autocorrélation — leçon carry #6), **mûr 2023+** (leçon p12/p13).

## Couverture & mur survivorship (honnête, quantifié)

Univers EDGAR SIC 6770 = **3299 CIK** ; modernes (CIK>1.7M, 2020+) = 1320. Après enrichissement
`submissions` → **327** avec ticker+IPO 2019+ → **253** avec prix yfinance → **249** au panel (≥10 obs
pré-deal). **Mur structurel** : `submissions.tickers[]` est l'état **actuel** → une SPAC fusionnée
(ticker = NewCo) ou liquidée (delistée) **perd son ticker**, et yfinance droppe les delistées (des
dizaines de `possibly delisted`). Le free-path **sous-couvre la cohorte 2021 + les liquidées** (Gate D
inatteignable). **Direction du biais** : il sur-représente les noms **encore pré-deal coincés à
discount** → s'il fausse, il **gonfle** le discount mesuré → un KILL est conservateur (le vrai excès
déployable est ≤ mesuré). La question **forward-déployable** (les SPAC tradables aujourd'hui offrent-
elles un excès ?) est, elle, bien couverte.

## Les chiffres (gates pré-enregistrés)

| Gate | n_noms | excès médian | t (inter-noms) | %discount | Statut |
|---|---|---|---|---|---|
| **A** tous pré-deal 2019+ | 249 | **+145 bps** | +11.0 | 87 % | **FAIL** (<200) |
| **B** IPO 2023+ mûr | 231 | **+147 bps** | +14.6 | 90 % | **FAIL** (<200) |
| **A-rob** hors top-2 | 247 | +145 bps | +11.1 | 87 % | **FAIL** |

**Sensibilité deadline × lag (le résultat charnière) :**

| deadline | lag 0 | lag +1 (sonde bounce CEF) |
|---|---|---|
| 18 mo | +232 bps | +234 bps |
| **24 mo (central)** | **+145** | **+147** |
| 36 mo (réaliste, extensions) | +85 | +85 |

- **lag +1 ≈ lag 0** partout → **PAS un bid-ask bounce** (contraste CEF #8 qui s'inversait au lag). Le
  discount est réel et capturable, pas un artefact de microstructure.
- **L'excès s'effondre avec l'horizon** (mécanique `discount/τ`). Les extensions SPAC post-2022 sont la
  norme → horizon réel **24-36 mo** → excès **+85 à +145 bps**, **sous 200 partout** sauf un 18 mo
  sans-extension irréaliste (+232). FAIL robuste à l'hypothèse de deadline.

## Pourquoi 200 bps, et pourquoi le KILL tient (discipline dans les deux sens)

Le hurdle 200 bps a été figé **avant data** pour encoder « bat le cash assez pour survivre aux
frictions » : bid-ask SPAC (illiquide), **lock-up** du capital jusqu'à rédemption, capacité minuscule.
+145 bps est **BRUT** (le lag teste le bounce, pas le spread d'entrée) → net plus bas encore. La
discipline coupe dans les deux sens : **pas de faux-GO** (je ne descends pas la barre à 145), **pas de
faux-KILL** (le discount est RÉEL, je ne prétends pas qu'il est nul — il vaut ~T-bill + 1,45 % brut,
downside planché). Lecture honnête = **money-market-plus illiquide**, pas un alpha déployable.

## Place dans le programme

**KILL, sous-type #2 (réel mais arbitré jusqu'à ~la prime de friction), nuance NEUVE.** Distinct des
24 kills antérieurs sur un point fort : **la propriété recherchée post-#26 — un plancher *clause-safe*,
réel, sans contrepartie voidable — a été CONFIRMÉE** (t=11-15, lag-stable, mûr). #26 mourait sur la
**contrepartie** (clause de void) ; #27 ne meurt PAS là — le plancher SPAC est inviolable. Il meurt sur
la **magnitude** : le marché a déjà compressé l'excès à la prime d'illiquidité, **sous la barre
déployable**. Autrement dit, « changer d'arme » a produit un **vrai plancher inviolable**, mais
l'efficience l'a arbitré jusqu'au coût — le motif unifié du programme (*structurel réel ≠ gratuit*)
tient une fois de plus, ici dans sa forme la plus propre (ni voiding, ni bounce, ni tail : juste une
prime compressée au niveau de l'illiquidité).

**Caveat data** : trust en approximation ($10,10 + intérêts), deadline en proxy (24 mo), panel
survivorship-biaisé vers les vivantes (gonfle le discount → KILL conservateur). Un éventuel
re-test Phase-2 lirait le trust exact par 10-Q + dates de deal/liquidation réelles (8-K) pour clore
Gate D — mais Gate A échouant déjà la barre forward, Gate D est sans objet pour le verdict.

**Bilan : 27 études, 0 edge déployable.** Deliverable trading = **mono-sleeve trend**. Le critère
post-#26 (plancher clause-safe) a produit un vrai plancher inviolable — arbitré sous la barre.

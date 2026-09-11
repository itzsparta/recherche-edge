# FINDINGS #35 — Prime fallen angels : **KILL** (prime nette de bêta réelle 2012-2021, éteinte depuis, ne survit pas à la déflation)

**Verdict (2026-09-11) : KILL (¬A, via A3).** Pré-enregistré : [`SPEC.md`](SPEC.md) (commit `0579126`
avant tout code). Code : [`../run_fa.py`](../run_fa.py). Data : ETF total-return prix yfinance,
ANGL 2012-05→2026-08 (172 mois), FALN/WING.L 2016+ (122 mois).

**Note d'étiquette (honnêteté 2 sens).** Le mapping pré-enregistré étiquette tout ¬A avec écart brut > 0
« KILL bêta déguisé ». La **classe KILL est maintenue**, mais la **cause** est autre : l'alpha
**survit** au contrôle du bêta (A1 et A2 PASS) ; il meurt sur la **déflation** (A3) et parce qu'il s'est
**éteint depuis 2022**. Le trou du mapping (ne pas distinguer ¬A1 de ¬A3) est noté pour les specs futures.

## Résultat

| Mesure | Valeur |
|---|---|
| Écart brut ANGL − HYG (diagnostic) | **+2,15 %/an** (t=2,31) — le chiffre marketing est vrai |
| **α 2F** (HYG + IEF, NW lag 3) | **+1,77 %/an, t=2,27** — β_HY 1,12, β_T 0,01 |
| α 3F (+ crédit IG) | +1,90 %/an, t=2,67 — β_IG 0,62 (la qualité BB est bien un facteur, mais n'absorbe pas α) |
| DSR(h_2F, n=5) | **0,887** (SR/mois 0,149 vs SR0 0,057) |

## Gates

| Gate | Résultat | |
|---|---|---|
| **A1** α_2F ≥ 1 %/an ∧ t ≥ 2 | +1,77 %, t=2,27 | PASS |
| **A2** α_3F > 0 ∧ t ≥ 1,5 | +1,90 %, t=2,67 | PASS |
| **A3** DSR > 0,95 | **0,887** | **FAIL** |
| B1 moitiés | H1 +2,84 % (t=2,41) / **H2 +0,93 % (t=0,96)** | PASS (signe) ⚠️ |
| B2 drop 2020-02→12 | +1,73 % (t=2,23) | PASS |
| B3 drop meilleure année (2016) | +1,28 % (t=1,72) | PASS |
| B4 FALN | +0,83 % (t=1,06) | PASS (signe) ⚠️ |
| C1 WING.L (UCITS) | +1,03 % (t=0,96) | PASS (signe) ⚠️ |
| C2 sleeve sur 60/40+trend | incr FA **+0,008** vs HYG −0,023 | PASS (négligeable) |

## Pourquoi c'est un KILL et pas un « presque GO »

### 1. La prime s'est éteinte : tout le t vient de 2012-2021
Série couverte `h_2F` par année (α + ε, %) :

`2012 +1,9 · 2013 +0,8 · 2014 +0,5 · 2015 +4,3 · 2016 +9,1 · 2017 +2,7 · 2018 −3,5 · 2019 +2,1 · 2020 +8,4 · 2021 +2,6 · 2022 −2,1 · 2023 +0,2 · 2024 −2,0 · 2025 −0,1 · 2026 +0,3`

Cumul 2022→2026 ≈ **−3,7 pts**. Le full-sample est porté par deux épisodes de **vagues de dégradations**
(énergie 2015-16, COVID 2020) ; hors vague, ≈ 0 ; depuis 2022, négatif. H2 t=0,96, FALN et WING (qui
ne voient que 2016+) t≈1 : **tout ce qui mesure la période récente est non significatif**. B passe
parce que les gates B ne testent que le **signe** — la magnitude récente est du bruit autour de zéro.
Cohérent avec le motif du programme (effet index S&P 7,4 % → <1 %) : un flux forcé documenté
attire le capital qui l'arbitre. Mécanisme (arrivée de capital dédié) = hypothèse, non testée ici.

### 2. Même un GO n'aurait rien apporté au portefeuille
corr ANGL/SPY **+0,75** (stress +0,76) : c'est du crédit HY, donc de l'actions déguisé. Incrément Sharpe
sur 60/40+trend = **+0,008**. Le meilleur cas pré-enregistré (GO) aurait été « remplacer HYG par FA »
pour qui détient déjà du HY — et le deliverable #22/#34 n'en détient pas.

### 3. Queue plus grosse que HYG
maxDD ANGL −18,1 % vs HYG −15,2 % ; skew −0,93 ; 2018 −3,8 pts et 2022 −3,3 pts vs HYG. Le surplus de
rendement est payé en drawdown (duration résiduelle + concentration sectorielle).

## Place dans le programme

Premier flux forcé **par mandat juridique** testé (vs flux public daté : index #2, LETF #25). Il fait
mieux que ses cousins — l'alpha net de bêta existait vraiment sur un cycle — mais finit au même
endroit : **réel dans le passé, arbitré aujourd'hui, et de toute façon corrélé actions**. Sous-type de
mort #2/#3 hybride : prime **mangée par la diffusion** (comme pré-FOMC 5b), pas par la friction.

**Bilan : 35 études, 0 edge déployable standalone.** Deliverable inchangé = #22 (60/40 + trend) levé à
1,5× (#34). Le multiplicateur restant identifié par #34 : **vol-target** (diagnostic non promu : net
+11,5 %, Sharpe 1,16, maxDD −17 % vs −29 % en levier constant).

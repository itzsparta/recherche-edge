# SPEC — Piste 8 : CEF discount mean-reversion (pré-enregistré)

> Écrit AVANT tout chiffre. Protocole partagé `RESEARCH-ROADMAP.md` : hypothèse + règle + critère
> de succès ET de kill fixés avant de voir le moindre résultat.

## Hypothèse d'edge

Le `discount(t) = (price − NAV) / NAV` d'un closed-end fund est **I(0)** (mean-reverting vers un
niveau d'équilibre propre au fonds), pas une marche aléatoire. Donc : acheter les fonds au discount
le plus large / shorter (ou hedger) les moins décotés → capter la **convergence** du discount + le
carry de distribution, market-neutral sur le sous-jacent.

## Source de l'inefficience structurelle — pourquoi NON arbitrée

Un CEF n'a **pas** de mécanisme de création/rachat par Authorized Participant (≠ ETF). Le discount
ne **peut pas** être fermé par arbitrage mécanique — c'est exactement ce qui a tué la piste B (ETF) et
qui, retourné, devient l'edge ici. Énigme documentée et persistante 30+ ans (Lee–Shleifer–Thaler 1991).
Contrepartie = sentiment retail. Les activistes attaquent les gros CEF (tender offers) → reste les
petits, terrain solo (capacité + patience). **Étang structurellement différent** des 8 pistes mortes
(contrepartie ≠ fonds optimisateur).

## Données

CEFConnect API publique (gratuite) :
- Univers : `GET /api/v3/funds` → liste {Ticker, Name} de tous les CEF.
- Historique : `GET /api/v3/pricinghistory/{TICKER}/All` → ~hebdomadaire 2012→2026, champs `Data`
  (prix), `NAVData` (NAV), `DiscountData` (premium/discount %, **signe : positif = premium, négatif =
  discount**), `DataDate`.
- Métadonnée : `GET /api/v3/DailyPricing` → catégorie Morningstar + sponsor (pour Gate E anti-value-trap).

Fréquence hebdo = adéquate (rebal cible mensuel ; moins de bruit que daily). 2012-2026 couvre les
régimes 2015 / 2018-selloff / 2020-COVID / 2022-bear.

## Gates de décision (pré-enregistrés, ordre = cheap-first)

### Gate A — Stationnarité du discount (Phase-1, ce run)

Précondition nécessaire : si le discount est I(1), « acheter le plus décoté » n'a aucune convergence
espérée (le discount peut s'élargir indéfiniment) → pas d'edge, KILL avant tout backtest.

- **Univers retenu** : tout CEF avec ≥ 156 obs hebdo valides de discount (≈ 3 ans, ≥ 1 régime de stress).
- **(A1) par fonds** : ADF (`regression='c'`, autolag AIC) sur la série discount de chaque fonds.
- **(A2) pooled** : démoyenner chaque série par sa propre moyenne, empiler, ADF sur le pooled
  (test de racine commune type Levin-Lin-Chu).
- **PASS Gate A** : `(≥ 50 % des fonds rejettent la racine unitaire à 5 %)` **ET** `(pooled démoyenné ADF p < 0.05)`.
- **KILL** : sinon. Discount = marche aléatoire ⇒ pas de niveau d'équilibre ⇒ thèse morte.
- **Diagnostic non-gating** : half-life médiane (AR(1)). Tradabilité exige reversion < ~1 an ; une
  half-life pluri-annuelle = stationnaire mais mangé par le drag (renvoyé à Gate C, pas un KILL ici).

### Opérationalisation Phase-2 (pré-enregistrée AVANT le run B-G)

- **Fréquence** : série hebdo resamplée en fin de mois → premium mensuel par fonds. Rebal mensuel.
- **Signal (mean-reversion, sans look-ahead)** : `z_{i,m} = (prem_{i,m} − μ) / σ` où μ,σ = moyenne/écart-type
  **trailing 24 mois** (min 12) du fonds i jusqu'à m inclus. z négatif = anormalement décoté vs sa propre norme.
- **Portefeuille** : long quintile z le plus bas (cheap vs sa norme) / short quintile z le plus haut. Equal-weight par jambe. Univers du mois = fonds avec ≥12 mois trailing.
- **Rendement market-neutral, sans distribution** : pour un fonds, la convergence sur [m, m+1] =
  `Δlog(1 + prem/100)`. Dérivation : `log price = log NAV + log(1+prem)` → en retirant `Δlog NAV` (le beta
  du sous-jacent) il reste `Δlog(1+prem)` = pur effet discount. Brut_m+1 = moyenne(longs) − moyenne(shorts).
  ⚠ Suppose le NAV hedgé/diversifié ; la forme **réellement déployable sans hedge** = L/S **intra-catégorie**
  (Gate E, NAV se compensent).
- **Coûts pré-enregistrés (Gate C)** : 30 bps/côté (60 bps round-trip) × turnover mensuel + borrow short 4%/an
  sur le notionnel short. Spreads CEF réels élevés (illiquides). On reporte AUSSI le **break-even cost** (honnête).
- **Gate G variantes (DSR)** : lookback z ∈ {12, 24, 36 mois} × {quintile, tercile} = 6 essais ; DSR(best) > 0.95.

### Gates B-G (Phase-2, seulement si A PASS)

- **(B) brut > 0, t > 2** : portefeuille L/S = long quintile discount le plus large / short le moins
  large (premium), rebal mensuel, OOS. Signal = discount relatif au z-score propre du fonds.
- **(C) net > 0** : après expense ratio CEF (drag ~1-2 %/an) + commissions + coût du short/hedge.
- **(D) brut > miroir** : bat le long-only du sous-jacent (sinon = beta sectoriel, pas convergence).
- **(E) anti-value-trap** : le quintile décoté ≠ simplement les pires actifs ; contrôle par catégorie
  Morningstar / sponsor. Le discount capté doit survivre au neutralisation sectorielle.
- **(F) split régime** : positif dans ≥ 2/3 régimes (2018 / 2020 / 2022).
- **(G) DSR** : DSR(best, N variantes de seuil/lookback) > 0.95.

## Falsifiabilité (comment ça meurt)

1. Discount I(1) → KILL Gate A (ce run).
2. Stationnaire mais half-life pluri-annuelle → mangé par le drag (Gate C).
3. Quintile décoté = value-trap (sous-jacents pourris, discount justifié) → Gate E.
4. Convergence réelle mais < expense ratio + coût hedge → Gate C net négatif.

## Verdict attendu a priori

Prior bas (8 kills). MAIS la littérature dit les discounts CEF SONT persistants/stationnaires (c'est
le « puzzle ») → Gate A devrait **passer**, et le vrai combat se jouera en C (le drag mange-t-il la
convergence ?) et E (value-trap ?). C'est le profil de kill le plus probable, pas Gate A.

## Verdict RÉEL (2026-06-23) — KILL, par un tueur NON prédit

A est passé, et même C/D/E/F/G en brut (faux GO, premier du programme). Le tueur n'était **ni** le
drag (C) **ni** le value-trap (E) prédits ci-dessus, mais le **bid-ask bounce** (microstructure),
attrapé hors-gate par le test de robustesse (lag d'entrée 1 mois → alpha s'inverse). Leçon : les
gates pré-enregistrés ne suffisaient pas ; il a fallu une chasse au mirage post-GO. Détail :
[`FINDINGS-cef.md`](FINDINGS-cef.md).

# FINDINGS — Piste 10 : favorite-longshot bias (Polymarket)

**Statut : KILL (2026-06-23) — Gate A, hypothèse INVERSÉE.** Le biais favorite-longshot n'existe pas
sur Polymarket : c'est le **pattern inverse** (favoris surcotés, longshots sous-cotés). Fader les
longshots — l'hypothèse pré-enregistrée — **perdrait de l'argent**.

## Hypothèse testée

Contrepartie récréative ⇒ longshots surcotés ⇒ fade systématique = EV>0. Polymarket choisi car CLOB
**sans vig** (≠ bookmaker) → si le biais existait il serait capturable. Étang structurellement ≠ des
9 pistes mortes (contrepartie non-optimisatrice).

## Données

Polymarket Gamma (résolution) + CLOB (prices-history). **3082 marchés** binaires résolus, vol ≥ 5 000 $,
2023-12 → 2026-06 (pagination par fenêtres de date pour contourner le cap d'offset Gamma ~2500).
Prix ex-ante = prix du token au **midpoint temporel** du marché (jamais adjacent à la résolution).
2 legs/marché poolés → **5586 legs (2793 marchés exploitables)**. N ≫ 500.

## Résultat — Gate A : KILL

Calibration (prix implicite vs fréquence réalisée) :

| bucket implied | n | implied | realized | gap (réel − implicite) |
|---|---|---|---|---|
| 0.05–0.10 | 269 | 0.073 | 0.123 | **+0.049** |
| 0.10–0.20 | 383 | 0.145 | 0.225 | **+0.080** |
| 0.20–0.35 | 495 | 0.279 | 0.315 | +0.036 |
| 0.65–0.80 | 488 | 0.723 | 0.691 | −0.033 |
| 0.80–0.90 | 388 | 0.857 | 0.776 | **−0.081** |
| 0.90–0.95 | 266 | 0.928 | 0.880 | **−0.048** |

**Longshots (implied < 0.10) : gap +0.0109, t = +2.26.** Signe POSITIF = les longshots se réalisent
**plus** que leur prix = **sous-cotés**. C'est l'**inverse exact** du favorite-longshot bias classique
(paris hippiques/sportifs où le longshot est surcoté). Sur Polymarket ce sont les **favoris** (0.8-0.95)
qui sont **surcotés** (gaps −0.05 à −0.08).

**Gate E (split catégorie)** : aucune catégorie ne montre de longshot-overpricing significatif
(crypto −0.005 t=−0.32 ; politics +0.006 t=0.89 ; sports +0.014 t=1.71 ; other +0.020 t=1.72 — tous
non-significatifs ou de signe contraire). Le « biais » récréatif attendu est absent partout.

**Interprétation** : Polymarket est dominé par une foule crypto-native + des arbitragistes, pas par des
parieurs récréatifs lottery-like. Le marché est calibré (voire reverse-biaisé). L'« étang différent »
s'est révélé efficient.

## Pourquoi le pattern inverse n'est PAS un sauvetage

Le résultat suggère un trade opposé (fader les favoris / acheter le côté cheap sous-coté). On NE le
poursuit PAS :

1. **Post-hoc** — retourner l'hypothèse après avoir vu les données = exactement le data-snooping que le
   pré-enregistrement interdit. Exigerait une nouvelle étude pré-enregistrée indépendante.
2. **Même tueur de friction (analogue du bounce CEF)** — le gap favori est 5-8 %, mais l'exploiter
   revient à acheter le côté « No » à ~0.10-0.20, où le spread absolu (~1¢) est un coût relatif énorme.
   On achèterait à l'ask : le gap brut serait mangé, comme le bid-ask bounce a mangé la convergence CEF.
   Prior : KILL au Gate B (friction) même avec une hypothèse propre.

## Conclusion

L'hypothèse pré-enregistrée est **réfutée avec le mauvais signe** : pas de prime récréative à récolter
sur Polymarket. Le seul autre « étang structurellement différent » du reframe rejoint les 9 autres
kills. Motif unifié intact : là où le prix est public, un solo n'a pas d'edge récoltable — ici parce
que la contrepartie supposée naïve est en fait sophistiquée/arbitrée.

**Valeur** : kill pré-enregistré propre sur N=2793 marchés, data gratuite, en un run. Le pipeline a
évité de trader une hypothèse qui aurait perdu (fader des longshots sous-cotés). Reproductible :
`run_phase1.py`.

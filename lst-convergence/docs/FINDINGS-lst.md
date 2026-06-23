# FINDINGS — Piste 9 : LST convergence (stETH/ETH) — KILL (edge one-off pré-redemption, n=1 régime)

**Date :** 2026-06-23
**Verdict :** **KILL** — Gates B/C PASS mais **A, D, E KILL**. Le PASS de B/C est un **artefact
in-sample** : tout l'edge vit dans le régime pré-Shapella non-répétable.
**Motif :** la tension structurelle anticipée dans le SPEC s'est réalisée à la lettre — le mécanisme
qui *garantit* la convergence (redemption 1:1, Shapella avr-2023) est aussi celui qui *détruit le
discount* une fois actif. L'edge est un **événement unique** (2021-2022), pas une prime récurrente.

## Setup

- 989 jours alignés, **2021-01-01 → 2023-09-27**, prix stETH + ETH résolus au **même timestamp cible**
  (DeFiLlama coins historical, skew médian 100-134s, garde anti-artefact `|skew|<2h` — voir `data_lst.py`).
- `discount = stETH/ETH − 1`. min −7.54 %, max +4.52 %, mean −0.90 %, std 1.40 %.
- Stratégie pré-enregistrée : entrée `discount < −1.5 %`, sortie `≥ −0.25 %`, PnL hedgé = Δ log(ratio),
  coût swap Curve 20 bps aller-retour. Seuils écrits avant tout chiffre (`docs/SPEC.md`).

## Résultats par gate

| Gate | Critère | Résultat | Verdict |
|------|---------|----------|---------|
| **A** reconvergence | stationnaire ET half-life portable | ADF p=**0.058** (I(1) borderline), HL=2.0 j | **KILL** |
| **B** brut>0, t>2 | — | brut **+82.0 %**, t=**+3.14**, 331/989 j déployés | PASS |
| **C** net>0 | après frais | net **+76.8 %** (26 trades × 20 bps) | PASS |
| **D** tail break-even | P(dépeg) implicite élevée = sur-réaction | au creux 7.5 %, perte=50 % → P_be **13 %** | **KILL** |
| **E** échantillon | ≥2 épisodes stress indépendants | 26 épisodes, **TOUS pré-Shapella, 0 post** | **KILL** |

## Le point clé : B/C PASS est un mirage in-sample

Le brut **+82 %** et le net **+76.8 %** (t=3.14) ont l'air d'un GO. Ils n'en sont pas : **les 26
épisodes de stress sont tous antérieurs à Shapella** (avr-2023). Le backtest récolte les reconvergences
de 2021 (lancement stETH, faible liquidité, gros discounts −7 %) et le dépeg de juin-2022 (creux −6.6 %,
épisode de 142 jours). Ce sont des excursions du **même régime structurel** : pas de marché de retrait
fonctionnel → le discount peut diverger librement → il reconverge quand le sentiment revient.

**Post-Shapella (169 j, avr→sep 2023, présents dans les données) : discount pinné, min −0.40 %,
mean −0.07 %.** Il n'atteint **jamais** le seuil d'entrée −1.5 %. Zéro trade. Une fois la redemption
1:1 active, l'arbitrage (mint/burn stETH↔ETH) écrase le discount sous le seuil exploitable → **l'edge
n'existe plus**. C'est exactement le scénario `KILL Gate E` pré-enregistré comme le plus probable.

## Pourquoi ça meurt (structurel, pas artefact de données)

1. **n=1 régime (Gate E)** : tous les épisodes sont pré-redemption. Le « taux de succès sur 26
   épisodes » est faux-indépendant — c'est un seul régime de marché (LST jeune sans retrait) échantillonné
   26 fois. Aucune puissance statistique pour un edge **déployable aujourd'hui**.
2. **Edge tué par son propre succès** : le mécanisme de garantie (redemption) supprime la condition
   d'existence du discount. La piste prédit sa propre obsolescence — confirmée par les 169 j post-Shapella.
3. **Non-stationnaire borderline (Gate A)** : ADF p=0.058 = pas de niveau d'équilibre robuste hors du
   régime de stress ; la « convergence » est conditionnelle au régime, pas une force de rappel stable.
4. **Priced-in plausible (Gate D)** : au creux −7.5 %, une perte permanente de 50 % (slashing/dépeg)
   n'implique qu'une proba de catastrophe de **13 %** pour breakeven — parfaitement dans le plausible.
   Le discount **paie un vrai risque de queue** (cf. juin-2022 : peur réelle d'insolvabilité). Comme le
   carry (piste 6) et le bounce CEF (piste 8) : la prime ≈ le risque, pas un free lunch.

## Limite de données (n'affecte pas le verdict)

Les données DeFiLlama gratuites s'arrêtent à 2023-09-27 pour ce contrat. Mais la fenêtre post-Shapella
disponible (5.5 mois) **suffit** : le discount y est déjà pinné sous le seuil. Étendre à 2026 ne ferait
que confirmer (le discount stETH est resté ~0 depuis, redemption mature). Le KILL est robuste.

## Conclusion

Piste 9 = **KILL**, conforme au prior bas et à la prédiction a priori du SPEC. Novelty faible : étang
« structurellement différent » (convergence protocolaire) mais tué par le **même type de tueur** que le
carry — la prime existe et paie *brut*, mais elle rémunère un **risque de queue réel** (Gate D) **et**
elle est **non-répétable** car le mécanisme de garantie la détruit en s'activant (Gate E). Le brut
+82 % t=3.14 est le piège pédagogique : un t-stat élevé sur un **régime unique non-reproductible** n'est
pas un edge — exactement la leçon des faux GO VRP (t aveugle au tail) et CEF (t=7.13 aveugle au bounce).
Coût marginal du test ≈ 0 (infra légère, data gratuite). **Restantes : aucune** — piste 11 (funding XS)
aussi KILL ; le programme V2 est clos.

# FINDINGS — Piste 11-v2 : funding XS lissé 7j — KILL (le mur de frais se dissout, il cachait une loterie en compression)

**Date :** 2026-07-02
**Verdict :** **KILL** — A, B, E, F PASS mais **C et D KILL** (mêmes seuils que v1, non abaissés).
**Motif :** le levier turnover fonctionne (coût 72 %→3.25 %/an) et le brut survit au lissage —
mais ce que le mur de frais cachait est une **prime de queue one-sided, concentrée, en
compression forward**, pas une prime régulière récoltable.

Test contre [`SPEC-v2.md`](SPEC-v2.md) pré-enregistrée (commit `1e0fc9d` avant tout code).
Un seul point de paramètres (lissage 21 périodes, holding 21 périodes), pas de sweep, pas de DSR requis.

## Résultats par gate (mêmes seuils que v1)

| Gate | Critère | Résultat | Verdict |
|------|---------|----------|---------|
| **A** dispersion lissée paie | brut>0, t>2 | **brut +38.8 %/an, t=+2.97**, sharpe 1.12 | **PASS** |
| **B** net @5 bps | net>0, t>2 | turnover 0.059/8h (v1 : 1.32) → coût **3.25 %/an** (v1 : ~72 %) ; **net +35.5 %, t=+2.72** | **PASS** |
| **C** market-neutral | corr≈0 ET deux jambes>0 | corr −0.085 OK, long +31.8 %/an, **short −10.9 %/an** | **KILL** |
| **D** drop-top | sans top-2 : net>0, t>2 | BNB+TRX = 34 % du brut ; sans eux net +22.3 % mais **t=+1.58 < 2** | **KILL** |
| **E** régimes | ≥2/3 positifs | bull +77.3 % (t=2.20), bear +19.4 % (ns), range +19.8 % (ns) — **3/3** | **PASS** |
| **F** hurdle déploiement | net > 8 %/an (hérité #6) | +35.5 % > 8 % | PASS |

## Ce que le re-creusage établit (la réponse à la question posée)

**Oui, le mur de frais v1 était soluble.** L'argument v1 « rebal moins fréquent abandonne le
spread de funding » était trop pessimiste : le funding est assez autocorrélé pour qu'un tri sur
funding **lissé 7j** retienne l'essentiel du brut (+38.8 % vs +51.9 % à 8h) en divisant le
turnover par **22**. Décomposition (corrigée, cf. erratum) : spread PRIX **+35.1 %/an** domine le
spread funding **+13.8 %/an** — c'est bien un effet cross-sectionnel de prix lent, pas seulement
la mécanique du funding.

**Mais dissoudre le mur révèle ce qu'il y avait derrière** (diagnostics NON-gating, tous dans le
sens du kill) :

- **Structure loterie** : kurtosis 17.2 ; les **10 meilleures périodes 8h (sur 7 742) = 35 % du
  net total** ; **médiane annualisée +1.27 %** vs moyenne +35.5 %. La période typique ne gagne
  rien — tout le P&L vit dans une poignée de squeezes. Même anatomie que les jackpots airdrop
  (#14 : 53 % sur 2 noms) et le mirage meme-coin.
- **One-sided structurel** (C) : la jambe short perd −10.9 %/an dans v2 comme dans v1 (−4.4 %
  éch. corrigée ~×k). Shorter les coins à funding élevé = shorter les squeezes. La prime vit
  côté long uniquement (porter les coins massacrés à funding négatif).
- **Concentration** (D) : sans BNB+TRX le point estimate reste +22 %/an mais t=1.58 — mieux que
  v1 (net sans top-2 : −47 %) mais toujours pas significatif.
- **Compression forward** : 24 derniers mois +24.6 % (t=1.57, ns) ; **12 derniers mois −4.3 %**
  (t=−0.27). Écho exact de #6 (carry 2021 +29.6 % → 2026 −0.5 %) : la prime se fait arbitrer
  pendant qu'on la mesure. Le t global 2.97 est porté par le bull 2020-21 (+77 %/an).
- **Survivorship non résolu** (déclaré en SPEC) : univers = 18 survivants ; un edge trouvé ici
  serait à discounter encore. Il n'a même pas fallu invoquer ce caveat.

## Erratum v1 (affichage seulement)

`run_xs.py` v1 divisait la décomposition et les jambes par k une fois de trop (`wl * mean()`).
Les chiffres v1 « spread funding +3.45 % / prix +7.19 % / short −4.4 % » sont ~k≈5× trop petits
en niveau ; **signes, hiérarchie prix>funding, gross/net/turnover et les cinq verdicts de gates
v1 sont inchangés** (aucun gate ne portait sur ces affichages).

## Pourquoi on s'arrête ici (et pas un v3)

La suite « évidente » — jambe longue seule, beta-hedgée BTC — hériterait telles quelles des trois
pathologies mesurées : la jambe longue porte le même kurt de squeeze, la même concentration, et
la même compression forward (12 mois négatifs). Un v3 serait du design post-hoc guidé par les
résultats (forking paths) pour attraper une médiane de +1.3 %/an. L'information marginale
attendue ≈ 0. Pré-enregistrable plus tard SEULEMENT si le funding se ré-élargit durablement
(même condition de réveil que #6).

## Place dans le programme

Le re-creusage était la bonne question : #11 était le seul kill « brut réel mangé par la
friction » dont la friction était **mécanique** (turnover) et non structurelle (adverse
selection). v2 montre qu'on pouvait la contourner — et que le motif unifié tient un cran plus
profond : *contourner la friction ne rend pas l'edge récoltable ; à info publique, ce qui reste
après le coût est une queue concentrée que le marché est déjà en train de compresser.* La
friction n'était pas le tueur — elle était le **premier rideau**.

**Bilan piste 11 : KILL v1 (frais), KILL v2 (structure).** Reste au repos avec la même clause de
réveil que #6 : ré-élargissement durable du funding (nouveau cycle de levier long).

# FINDINGS — Piste 11 : funding cross-sectionnel — KILL (brut réel, mangé par le turnover 8h)

> **Erratum (2026-07-02, découvert en v2)** : la décomposition affichée (spread funding
> +3.45 %/prix +7.19 %) et les jambes (short −4.4 %) sont ~k≈5× trop petites en niveau (double
> division par k dans `run_xs.py`). Signes, hiérarchie et les 5 verdicts de gates inchangés.
> Re-creusage : [`FINDINGS-xs-v2.md`](FINDINGS-xs-v2.md) — KILL aussi (structure).

**Date :** 2026-06-23
**Verdict :** **KILL** — Gate A PASS (la dispersion paie brut), mais **B, C, D, E tous KILL**.
**Motif :** edge brut réel **arbitré-jusqu'au-coût** par le turnover 8h. Cas d'école du motif unifié.

## Setup

- Univers 18 perps USDT-margined (BTC ETH BNB XRP ADA DOGE LTC BCH EOS TRX ETC LINK XLM XTZ NEO ATOM VET ZEC),
  funding 8h Binance fapi + klines perp 8h, **7048 périodes 8h**, 2020-01-17 → 2026-06-23.
- Long tercile funding le plus négatif / short tercile le plus positif, dollar-neutral, rebal 8h.
- Frais pré-enregistrés : 5 bps par unité de book tournée. Réutilise l'infra `carry/`.

## Résultats par gate

| Gate | Critère | Résultat | Verdict |
|------|---------|----------|---------|
| **A** dispersion paie | brut>0, t>2 | **brut +51.9%/an, t=+3.43**, sharpe 1.35 | **PASS** |
| **B** net>0 | après turnover×spread | **net −20.6%/an, t=−1.36** | **KILL** |
| **C** market-neutral | corr≈0 ET deux jambes>0 | corr −0.09 OK, mais **short leg −4.4%/an** (une seule jambe porte) | **KILL** |
| **D** drop-top | retirer top-2 → survit | top-2 (ETC, BNB) = **51% du P&L** ; sans eux net **−47%** | **KILL** |
| **E** split régime | ≥2/3 régimes positifs | bull +5.7% (t=0.15 ns), **bear −3.8%, range −39.6%** | **KILL** |

## Le point clé : l'edge brut EXISTE, le coût le mange entièrement

Décomposition du brut (+51.9%/an, t=3.43) :
- **spread de funding = +3.45 %/an** — positif par construction (on collecte le funding des deux côtés).
- **spread de prix = +7.19 %/an** — les perps à funding bas surperforment ceux à funding haut (effet
  cross-sectionnel réel, pas que mécanique).

Donc ce n'est **pas** un no-edge brut comme l'orderflow ou le meme-coin. La dispersion paie vraiment,
significativement. **Mais le turnover de rebalancement 8h = 1.32 du book à chaque période** (≈4 flips de
book par jour) → coût 6.6 bps/8h = **~72 %/an de frais**, qui transforme +52 % brut en **−20.6 % net**.

C'est le motif unifié du programme dans sa forme la plus nette : *un edge brut réel, exactement
neutralisé par la friction structurelle requise pour le capter*. Le funding 8h impose le turnover ;
le turnover impose le coût ; le coût ≈ le brut.

## Sensibilité au coût (le KILL est robuste)

- Break-even : net>0 exigerait un coût aller-retour < **3.58 bps/unité tournée** (vs 5 bps pré-enregistré).
- Même en supposant 2 bps (spread majors optimiste), Gates **C/D/E tuent quand même** : le P&L est
  porté à 51 % par 2 alts (ETC, BNB), une seule jambe est positive, et seul le régime bull (t=0.15,
  non-significatif) survit. Aucun réglage de coût ne sauve une stratégie concentrée + one-sided + mono-régime.
- Réduire le turnover (rebal moins fréquent que 8h) abandonnerait l'essentiel du spread de funding qui
  est le seul terme garanti → pas une issue.

## Pourquoi ça meurt (structurel, pas artefact)

1. **Turnover 8h non-compressible** : le funding se paie toutes les 8h ; capter le spread impose de
   re-trier et re-trader le book à chaque échéance. La friction est consubstantielle au signal.
2. **Concentration** : 51 % du P&L sur ETC+BNB → capacité fantôme (cf. piste 3). Le « spread » vit sur
   une poignée d'alts au funding extrême, souvent les moins profonds.
3. **One-sided** : la jambe short perd en standalone (−4.4 %/an) — shorter les coins à funding élevé,
   c'est shorter les coins qui rippent (adverse selection prix), exactement le risque pré-enregistré.
4. **Mono-régime** : seul le bull 2020-21 est ≥0 (et non-significatif). Bear + range négatifs.

## Conclusion

Piste 11 = **KILL**. Novelty faible confirmée : extension directe du carry (piste 6), tuée par le même
type de friction. La nuance utile vs les no-edge précédents : ici le **brut est réel et significatif**
(t=3.43) — l'inefficience de dispersion de funding existe — mais elle est **intégralement arbitrée par
le coût de turnover 8h**, plus concentrée, one-sided et mono-régime. Coût marginal du test ≈ 0 (infra
`carry/` réutilisée). Renforce le motif : *à information/prix public, même un brut significatif ne
survit pas à la friction structurelle qui le capture*.

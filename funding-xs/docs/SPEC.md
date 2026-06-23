# SPEC — Piste 11 : funding cross-sectionnel (≠ niveau) — pré-enregistré

> Écrit AVANT tout chiffre. Bolt-on sur l'infra `carry/` (data_funding, data_prices, audit).
> La piste 6 a tué le **niveau** du funding (long basket de funding négatif = directionnel, mangé).
> Ici on hedge le niveau : on parie sur la **dispersion** cross-sectionnelle, dollar-neutral.

## Hypothèse d'edge

À chaque timestamp de funding (8h), trier l'univers de perps par funding rate. **Long le tercile au
funding le plus négatif** (on est PAYÉ pour être long), **short le tercile au funding le plus positif**
(on est PAYÉ pour être short), dollar-neutral, rebalancé 8h. On collecte le **spread de funding** sur
les deux jambes.

Décomposition du rendement par période (1$ long-leg, 1$ short-leg, dollar-neutral) :

```
ret_porto = [mean_L(r) − mean_S(r)]   +   [mean_S(f) − mean_L(f)]
            └── spread de PRIX ──┘        └── spread de FUNDING ──┘
            incertain (risque)            POSITIF par construction (S=top funding, L=bottom)
```

- `r_i` = rendement prix du perp i sur la période ; `f_i` = funding rate.
- Long PnL d'une unité = `r − f` (un long PAIE le funding s'il est positif, le REÇOIT s'il est négatif).
- Le terme funding est mécaniquement > 0 mais **minuscule par 8h**. Le terme prix peut être adverse
  (les coins à funding élevé = souvent ceux qui rippent → les shorter perd en prix).

## Source de l'inefficience structurelle

Extension de la piste 6 ; **novelty faible** — risque d'être arbitré-jusqu'au-coût à l'identique.
Justification du test : coût marginal quasi-nul (toute l'infra existe). Si ça survit, c'est de la
dispersion de prime de financement entre alts, payée à celui qui porte le leg-risk multi-actifs.

## Données (gratuites, déjà câblées)

- `carry/data_funding.funding(symbol)` → funding 8h Binance fapi, depuis 2019-09, cache `carry/data/`.
- `carry/data_prices.perp_8h(symbol)` → klines perp 8h (close-to-close pour le rendement prix réel).
- Univers pré-enregistré (perps à historique long, listés ~2019-2021) :
  `BTC ETH BNB XRP ADA DOGE LTC BCH EOS TRX ETC LINK XLM XTZ NEO ATOM VET ZEC` (USDT-margined).
  À chaque timestamp, n'utiliser que les symboles **présents** ; exiger **≥ 9 symboles** présents pour
  former des terciles (sinon période skippée).

## Biais de survivorship — déclaré d'avance

Univers = perps **encore listés** (le funding endpoint ne sert pas les delistés). Un set de survivants
ne peut qu'**INFLER** un edge de dispersion (les delistés étaient souvent les pires high-funding qui se
sont effondrés — exactement la jambe short rêvée). Donc : **absence d'edge sur les survivants = KILL
robuste** ; présence d'edge = caveat survivorship à creuser avant d'y croire (analogue CEF piste 8).

## Mécanique anti-look-ahead

- Signal au temps `t` = funding **réalisé/publié** connu à `t`.
- Position tenue sur `(t, t+8h]`.
- PnL = rendement prix `close_{t+8h}/close_t − 1` par leg + funding **réalisé stampé à `t+8h`**
  (funding fortement autocorrélé → ranker sur `f_t` pour collecter `f_{t+8h}` n'est pas du look-ahead).

## Gates de décision (pré-enregistrés, cheap-first)

| Gate | PASS | KILL |
|------|------|------|
| **(A) dispersion paie** | brut > 0, **t > 2** sur le porto L/S funding-ranked | brut ≤ 0 ou t ≤ 2 → KILL |
| **(B) net > 0** | après frais réels (turnover 8h × spread perp ~5 bps/leg aller-retour) | net ≤ 0 → KILL (tueur probable) |
| **(C) market-neutral** | corr ≈ 0 avec BTC **ET** brut_long > 0 **ET** brut_short > 0 | un seul côté porte = pas market-neutral |
| **(D) drop-top** | retirer les 2 alts contribuant le plus au P&L → **survit** | meurt = capacité fantôme (cf. piste 3) |
| **(E) split régime** | positif ≥ 2/3 régimes (bull 2020-21, bear 2022, range 2023-24) | 1 seul = drift |

Paramètre principal unique : taille de tercile `k = n//3` (pré-enregistré). Pas de balayage = pas de
DSR nécessaire (un seul modèle testé).

## Modèle de coût pré-enregistré (Gate B)

- Spread perp majors ~1-2 bps, alts ~3-5 bps. Pré-enregistré conservateur : **5 bps par leg par
  rebalancement** sur le **turnover** (fraction du portefeuille effectivement tournée à chaque 8h).
- Turnover mesuré comme la rotation réelle des deux paniers entre t et t+8h.
- Funding déjà net (c'est un cash-flow réel, pas un coût ajouté).

## Falsifiabilité

1. brut ≤ 0 ou t ≤ 2 → KILL Gate A (la dispersion ne paie pas, ou noyée dans le bruit prix).
2. Net ≤ 0 (turnover 8h élevé mange le spread) → KILL Gate B — **tueur le plus probable**.
3. P&L porté par 1-2 alts illiquides → KILL Gate D (capacité fantôme).
4. Un seul côté / un seul régime porte → KILL Gate C/E.

## Verdict attendu a priori

Prior très bas (10 kills, novelty faible). Le funding spread brut est positif par construction mais
minuscule ; les deux tueurs structurels = (B) turnover 8h, (D) concentration sur des alts injouables.
Issue la plus probable = KILL B ou D. Test fait car coût marginal ≈ 0.

## Verdict RÉEL

_(à remplir après run)_

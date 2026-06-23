# Piste 17 — FX carry G10 (sleeve) : FINDINGS

**Verdict (2026-06-23) : KILL.** La prime de carry FX (long haut-taux / short bas-taux, 6 G10 vs USD,
2003-2026) est **de la bonne direction** (+1.35 %/an net) mais **statistiquement insignifiante** :
Sharpe 0.21, **t = 0.99** (< 2), **DSR = 0.754** (< 0.95). La **décennie taux-zéro 2009-2021** a
annulé le différentiel qui fait vivre le carry. Bonne nouvelle isolée — le carry est **parfaitement
orthogonal** au trend (corr **+0.01**) et le combo 50/50 a un Sharpe (0.34) supérieur à chaque jambe
(carry 0.21, trend 0.27) — mais on **ne bâtit pas un sleeve sur une jambe dont la prime propre est
indiscernable de zéro**. (A) FAIL, (B) FAIL.

> Reproduire : `python run_carry.py`. Data = futures FX factor-harvest (spot) + taux 3 m FRED IR3TIB01
> (signal + accrual), gratuit/déterministe. 275 mois.

## Ce qui a été testé

Pré-enregistré dans [`SPEC.md`](SPEC.md). Retour à un **edge de prime de risque** (≠ payoff opérationnel
#14, cashflow #15). Question discriminante = **(D)** : le carry ajoute-t-il un **sleeve orthogonal** au
seul deliverable (trend +0.12, piste 1) ? Carry Lustig-Verdelhan : ranking mensuel par différentiel de
taux 3 m, long 3 plus hauts / short 3 plus bas, dollar-neutral, signal & accrual **laggés** (pas de
look-ahead), coûts 2 bps/jambe.

## Gates

| Gate | Résultat | |
|---|---|---|
| **(A) prime réelle** | net Sharpe 0.21, **t = 0.99** | **FAIL** — insignifiant |
| **(B) pas un mirage** | **DSR 0.754** (SR 0.060 vs SR0 bruit 0.017) | **FAIL** — sous 0.95 |
| (C) tail | 2008 **−16.4 %**, max DD −23.5 %, skew −0.62 ; Sharpe hors-2008 0.35 | carry-crash présent mais pas catastrophique |
| **(D) sleeve** | **corr +0.01**, combo 0.34 > trend 0.27 > carry 0.21 | orthogonal & additif… *si* la jambe était significative |

## Le paradoxe (D) — bon diversifiant, mauvaise prime

Le résultat le plus intéressant : carry et trend sont **les deux primes macro canoniques**, et la mesure
le confirme — **corr +0.01** (orthogonalité quasi-parfaite), combo Sharpe 0.34 > chaque jambe. C'est
*exactement* le profil d'un 2e sleeve. **Mais** la condition préalable manque : la prime de carry
elle-même n'est **pas significative** sur 2003-2026 (t=0.99, DSR 0.754). Le gain du combo vient
surtout du trend ; ajouter une jambe bruitée orthogonale améliore mécaniquement le ratio sans qu'il
y ait d'edge à récolter. **Empiler une prime non-significative ≠ un sleeve déployable.**

## Pourquoi insignifiant — la décennie taux-zéro

Le carry vit du **différentiel de taux**. Sur 2009-2021, toutes les G10 ont convergé vers ~0 (ZLB
post-GFC, puis COVID) → différentiel ≈ 0 → **pas de signal**. La prime était réelle pré-2008 (AUD/NZD
vs JPY/CHF) et re-émerge post-2022 (resserrements désynchronisés), mais le **plein échantillon** —
le test honnête d'une stratégie déployable sur 20 ans — est noyé par la décennie morte. Découper
pré-2008 / post-2022 pour sauver l'edge = exactement le **data-snooping de sous-échantillon favorable**
que le programme refuse (cf. artefacts early-market crypto p12/p13). Le t=0.99 plein-échantillon est
le verdict.

## Leçon

- **La 2e prime macro canonique (carry) ne survit pas au régime ZLB 2009-2021 sur les G10.** Contraste
  **trend #1** : réel-mais-faible mais qui **passe** la significativité (t=1.87, **DSR 0.988**) → sleeve
  +0.12. Carry est **plus faible** (DSR 0.754) → échoue le seuil → KILL. Le deliverable reste **à un
  seul sleeve**.
- **L'orthogonalité (D) ne sauve pas** : un diversifiant parfait sans prime propre significative
  n'ajoute pas d'edge, juste du bruit décorrélé. La condition (A)/(B) est **préalable** à (D).
- Univers limité (6 devises, pas de NZD/SEK/NOK faute de futures gratuits) = cross-section mince ; mais
  le verdict tient sur le design pré-enregistré, et un univers plus riche ne ressusciterait pas la
  décennie ZLB.

## Caveat

Spot via futures front-month (bruit de roll mineur en mensuel) ; taux 3 m interbancaires FRED (signal
& accrual). Le verdict repose sur la **significativité plein-échantillon** (t=0.99, DSR 0.754),
robuste : la prime est positive en moyenne mais sa volatilité (carry crashes + décennie morte) la rend
indiscernable du bruit. La piste **rejoint VRP/overnight/trend** comme « prime réelle mais
non-déployable solo » — ici par insignifiance, pas par tail (le tail était supportable).

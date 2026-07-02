# SPEC — Piste 11-v2 : funding XS **lissé, holding 7j** — pré-enregistré

> Écrit AVANT tout chiffre (2026-07-02). Re-creusage demandé explicitement (« recreuse la piste
> crypto kill par les frais mais prometteuse »). Le re-litige nu est interdit — ceci n'est PAS un
> re-run de v1 : c'est **le levier structurel que v1 n'a pas testé**, avec les MÊMES gates aux
> MÊMES seuils.

## Ce que v1 a établi (et qu'on ne re-litige pas)

- **Brut réel** : +51.9 %/an, t=+3.43 — la dispersion de funding paie brut. Décomposition :
  spread funding +3.45 %/an, spread **prix** +7.19 %/an (termes moyens annualisés).
- **KILL B** : turnover 1.32×book/8h → ~72 %/an de frais @5 bps → net −20.6 %.
- **KILL C/D/E** : jambe short −4.4 %/an ; ETC+BNB = 51 % du P&L ; seul le bull survit (ns).
- v1 a fermé : (a) le coût à 2 bps (C/D/E tuent quand même) ; (b) « rebal moins fréquent »
  au motif que ça abandonne le spread funding.

## L'hypothèse v2 (le levier non-testé)

L'argument (b) de v1 est incomplet : le terme dominant du brut est le spread **PRIX**
(+7.19 %/an > +3.45 %/an funding). Le funding est fortement autocorrélé → un tri sur funding
**lissé** devrait retenir une part du spread prix (et une part du funding, les extrêmes persistant
plusieurs jours) en divisant le turnover par ~10-20. Falsifiable : si le spread prix vit dans la
réaction immédiate (≤8h) post-extrême, le holding 7j le dilue → brut lissé ≈ 0 → KILL A net.

## Paramètres (UN SEUL point, pré-committé, pas de sweep → pas de DSR)

- **Signal à t** : moyenne des **21 derniers funding publiés** (≈7 j) par symbole ; exige ≥15/21
  observations non-NaN.
- **Rebalancement** : tous les **21 stamps 8h** (≈7 j). Poids constants entre deux re-tris.
- Tout le reste **identique v1** : univers 18 USDT-perps, MIN_PRESENT 9, terciles k=n//3,
  dollar-neutral 1$/1$, PnL granularité 8h, funding réalisé collecté à chaque stamp,
  anti-look-ahead identique (signal = funding publiés ≤ t ; position sur (t, t+H]).
- **Coût pré-enregistré identique** : 5 bps par unité de book tournée, payé au re-tri.
  Diagnostic secondaire NON-gating : net @2 bps (maker moderne).

## Gates (identiques v1, seuils inchangés + un gate de déploiement hérité #6)

| Gate | PASS | KILL |
|------|------|------|
| **(A)** dispersion lissée paie | brut > 0 **et** t > 2 | sinon KILL — le spread prix ne survit pas au holding |
| **(B)** net > 0 | net @5 bps > 0 **et** t > 2 | sinon KILL |
| **(C)** market-neutral | \|corr BTC\| < 0.2 **et** long > 0 **et** short > 0 | un côté porte → KILL |
| **(D)** drop-top | sans top-2 contributeurs : net > 0 **et** t > 2 | capacité fantôme → KILL |
| **(E)** régimes | net > 0 sur ≥ 2/3 (bull 20-21, bear 22, range 23-25) | sinon KILL |
| **(F, déploiement)** | net @5 bps > **8 %/an** (hurdle #6 : dérangement + tail exchange, break-even faillite ≥5 %) | net ∈ (0, 8 %] → **DOWNGRADE** (réel non-déployable), pas GO |

Verdict GO exige A-F. A-E PASS avec F FAIL = DOWNGRADE documenté (même famille que #6 KILL-FORWARD).

## Biais & caveats déclarés d'avance (hérités v1)

- **Survivorship** : univers = survivants → un edge trouvé serait à creuser, une absence d'edge
  est un KILL robuste (asymétrie conservée).
- Le t-stat sur PnL 8h reste valide sous poids constants (rendements 8h non chevauchants).
- Univers 2019-21 = majors vieillissants ; la dispersion moderne vit sur des alts récents NON
  testables ici (endpoint ne sert pas les délistés) → un KILL v2 clôt la **structure** (lissage),
  pas l'univers. Extension d'univers = étude séparée, non promise.

## Prior honnête (écrit avant run)

KILL probable (~80 %) : (i) le lissage ampute le terme funding (on ne colle plus aux extrêmes
instantanés) ; (ii) si le spread prix est une réaction courte, il se dilue ; (iii) C/D/E ont tué
v1 **indépendamment du coût** — le lissage ne corrige ni la concentration ni la jambe short par
construction, il faut que la structure lente soit différente. Chance résiduelle : le
funding-momentum est documenté comme facteur lent dans la littérature → si réel ici, A+B peuvent
passer ; F (8 %/an) reste la barre la plus improbable.

## Sortie

`run_xs_v2.py` (variation minimale de `run_xs.py`), `FINDINGS-xs-v2.md`. Commit spec avant code,
commit findings après run.

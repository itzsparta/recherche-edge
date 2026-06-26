# SPEC — Arbitrage SPAC-trust : plancher contractuel sans contrepartie voidable

**Pré-enregistré le 2026-06-26, AVANT tout chiffre.** Étude **#27** du programme. Choisie après le
**KILL pré-live de #26** (buffer-harvest prop firm) : la tenaille #26 a posé le critère de toute
reprise = trouver un **plancher +EV qui soit *clause-safe*** — un plancher que la contrepartie **ne
peut pas annuler à discrétion**. Le prop buffer échouait là-dessus (clause de void FTMO). La SPAC
pré-deal est le **cousin honnête** : même convexité de plancher statique, mais le plancher est un
**droit de rédemption contractuel et *enforceable*** (compte en fidéicommis / trust en bons du
Trésor), pas une règle de firme révocable. C'est la **seule arme structurelle du programme à
échapper à la tenaille #26**.

## Question

Une SPAC **pré-deal** cotant **sous sa valeur de trust** offre-t-elle un rendement **structurellement
planché** (rédemption au trust + intérêts courus) qui **bat le taux sans risque d'une marge RÉELLE**,
**net de frictions**, **en régime MÛR (2023+)** — ou le « discount » n'est-il qu'un proxy de bons du
Trésor (rendement ≈ sans-risque, pas d'edge) et/ou un **artefact d'immaturité 2020-21** ?

## Mécanique (pourquoi un plancher contractuel existe)

Une SPAC lève `$N` à **$10,00/action** placés dans un **trust** investi en bons du Trésor court. Avant
la fusion, chaque actionnaire détient un **droit de rédemption** : récupérer la **valeur de trust par
action** (≈ $10,00 + intérêts courus) au vote de fusion **ou** à l'échéance (deadline). Donc :

```
downside  =  valeur_rédemption_t  ≈  10.10 × (1 + r_Tbill · τ)      (τ = temps écoulé depuis l'IPO)
upside    =  optionalité du deal (action peut monter) + warrant souvent CONSERVÉ même si on rédime
```

Si `prix_marché < valeur_rédemption`, on verrouille un **rendement-à-rédemption positif** + on garde
l'optionalité. **À la différence du buffer prop #26, aucune contrepartie ne peut « voider » la
rédemption** : c'est un droit contractuel exécutoire (le cash est dans le trust). C'est le test du
critère post-#26.

## Hypothèse & null central

- **Hypothèse (plancher +EV clause-safe)** : il existe, sur les SPAC pré-deal, un sous-ensemble cotant
  sous le trust dont le **rendement-à-rédemption excède le T-bill de maturité appariée d'une marge
  réelle** (> hurdle), **net de frictions**, **et qui survit en 2023+**. Un panier long-le-discount
  bat le cash après coûts.
- **Null central (attendu)** : le discount n'est que la **valeur actualisée du portage** — les SPAC
  sont *pricées comme des proxys de T-bill*, donc rendement-à-rédemption ≈ sans-risque, **excès ≈ 0**.
  ET/OU l'excès n'existait qu'en **2020-21** (glut d'émissions + ZIRP → sponsors pressés, mispricing)
  et a **disparu post-2022** (taux hauts + effondrement des émissions → discount arbitré à ≈ 0). On
  **s'attend à un KILL**.

**Identification** : le test décisif n'est PAS le discount brut ni le rendement brut (≈ T-bill = PAS
un edge), mais l'**excès du rendement-à-rédemption SUR le T-bill apparié**. C'est l'analogue du
« interaction, pas `r_t` seul » de #25 : un rendement = cash n'est pas un alpha.

## Modèle / données (free-data, multi-régime)

- **Univers** : SPAC pré-deal 2019-2026 (blank-check, SIC 6770). Liste tickers + date IPO + **deadline
  contractuelle** + statut (deal / liquidée / vivante). Source = EDGAR full-text (SIC 6770) + tracker
  libre ; **goulot data assumé** = assembler la liste (voir caveat). **Survivorship traité** : inclure
  les SPAC **liquidées** (rendent ≈ le trust = le plancher qui fonctionne), PAS seulement celles qui
  ont fait un deal — exclure les mortes biaiserait, et leur inclusion **teste le plancher** (Gate D).
- **Valeur de rédemption** (approx. 1er passage, **généreuse envers la thèse**) : `trust0 × (1 +
  r_Tbill3m · τ)`, `trust0 = $10,10` (trusts réels $10,00-$10,25 ; prendre la borne basse-haute
  $10,10 donne sa chance à la thèse → un KILL est conservateur).
- **Prix** : clôture quotidienne du ticker SPAC (yfinance/stooq).
- **Sans-risque** : T-bill 3m (FRED, déjà caché par `fx-carry`), maturité appariée à `τ_restant`
  jusqu'à la deadline.
- **Rendement-à-rédemption annualisé** : `(valeur_rédemption / prix − 1) × 365 / jours_restants`.
- **Excès** `= rendement-à-rédemption − T-bill(τ_restant)` = **l'identifiant**.
- **Frictions** : bid-ask SPAC (illiquide → entrée à l'**ask**, rédemption au trust = le **bounce**
  qui a tué CEF #8) ; coût d'**immobilisation du capital** jusqu'à rédemption (déjà dans l'excès vs
  T-bill) ; bornées **généreuses** (best-case donné à la thèse).

## Gates (pré-enregistrés — coupent dans les DEUX sens)

- **Gate A (existence / excès sur le sans-risque)** : sur les SPAC-mois où `prix < valeur_rédemption`,
  l'**excès médian annualisé > 200 bps** **ET** un panier long-le-discount (equal-weight, rebal
  mensuel) rend un **excès-sur-T-bill > 0 avec t > 2**. KILL si excès ≈ 0 (rendement ≈ T-bill = proxy
  cash, pas d'edge).
- **Gate B (maturité / régime — OBLIGATOIRE, leçon p12/p13)** : l'excès doit **survivre en 2023+**
  (post-glut, taux hauts). KILL si l'excès n'existe **qu'en 2020-2021** (artefact d'immaturité /
  régime — exactement le piège crypto-2021).
- **Gate C (frictions + bounce — cicatrice CEF #8)** : net du **bid-ask** (entrée à l'ask) et testé
  avec **lag d'entrée +1 période** (la sonde même qui a **inversé** CEF t=7.13). PASS si l'excès
  net-de-friction reste **> 0, t > 2, both-halves**, **ET survit au lag**. KILL si l'excès s'inverse /
  s'évapore à l'exécution réaliste (= bounce non-capturable).
- **Gate D (plancher exécutoire / tail)** : le plancher n'est pas gratuit si le trust **fuit** (taxes,
  contributions d'extension diluant le per-share) ou si la rédemption a des **gates/délais**. PASS
  exige que la **valeur_rédemption modélisée nette de fuite plausible reste ≥ prix** sur les legs PASS,
  et que les SPAC liquidées de l'échantillon aient **effectivement rendu ≈ trust** (vérif empirique du
  plancher). KILL si le « discount » n'existe qu'en **ignorant** la fuite de trust.
- **KILL** si A échoue (≈ T-bill) **OU** B échoue (2021-only) **OU** C échoue (bounce / lock-up)
  **OU** D échoue (plancher non exécutoire au prix modélisé).
- **Robustesse** : la conclusion doit tenir **hors des 2 SPAC les plus discountées** (sinon poignée de
  noms = bruit, leçon plancher min_n p2b) ; **plancher de liquidité** (écarter les tickers à
  dollar-volume négligeable = discount fantôme infaisable, cicatrice profondeur #3) ; nommer les noms
  porteurs.

## Sorties bonus

- **Distribution du discount 2019-2026** : visualiser le glut 2021 (free optionality) vs la
  **compression 2023+** (l'histoire de régime, attendue).
- **Dose-réponse** : excès vs **temps-à-deadline** (logique de plancher → plus court = plus serré ;
  profil plat/inversé **falsifie** l'identification, leçon spread fantôme p3).
- **Décompo** : composante rendement-de-rédemption vs composante warrant/optionalité.

## Falsifiabilité / honnêteté

- Bornes **généreuses envers la thèse** (trust $10,10 + intérêts, coûts bas) → un **KILL est
  conservateur**, un GO crédible.
- Le test décisif = **excès SUR T-bill**, pas le rendement brut : un rendement = cash **ne suffit
  pas** (= proxy de bons du Trésor, pas un alpha).
- Sous-échantillon **mûr 2023+ obligatoire** (un excès 2020-21 qui meurt après = artefact de régime).
- **Survivorship** géré dans les DEUX sens : inclure les liquidées (plancher qui marche) **et** vérifier
  qu'aucune ne rend < trust (plancher qui casse, Gate D).
- **Prior honnête = KILL probable** via Gate A (pricé au T-bill post-2022) ou Gate B (artefact 2021).
  **Mais** la SPAC-trust est le **seul plancher structurel sans contrepartie voidable** (échappe à la
  tenaille #26) → le test cheap est justifié. Je **ne tune pas** les barres (200 bps / t>2 / 2023+ /
  lag) vers un verdict [[feedback-gate-override]].
- **Caveat data** : valeur de trust en **approximation** ($10,10 + intérêts courus) au lieu du trust
  exact par filing — borné généreux ; si un GO émerge, la Phase-2 lira le trust exact par 10-Q.

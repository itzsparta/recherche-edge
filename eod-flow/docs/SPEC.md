# SPEC — Flux forcé de fin de séance : rebalancement des ETF à levier (LETF)

**Pré-enregistré le 2026-06-25, AVANT tout chiffre.** Étude **#25** du programme. Première piste sous
l'angle **« arme structurelle neuve »** = une contrepartie nommée, **insensible au prix**, dont le
flux mécanique dépasse (peut-être) le capital d'arbitrage qui le chasse. Distincte des 24 kills :
ce n'est ni un edge à info/prix public (#1), ni — c'est l'enjeu du test — forcément arbitré jusqu'au
coût (#2). C'est le seul candidat de la famille « flux forcé » non encore attaqué (les token-unlocks
#2 en étaient mais priced-in par dérive *pré*-date ; ici le flux est **intraday et mécanique**).

## Question

Le rebalancement quotidien obligatoire des ETF à levier crée-t-il un **flux de fin de séance
prévisible** (signe = celui du rendement du jour), assez grand vs la liquidité pour produire un
rendement late-day exploitable et/ou un **reversal overnight** — **net de coûts, en sous-échantillon
mûr (2023+)** ?

## Mécanique (pourquoi un flux forcé existe)

Un LETF de levier `L` (ex. +3, +2, −1, −2, −3) doit, au close, ramener son exposition à `L × NAV`
pour le lendemain. Dérivation au 1ᵉʳ ordre : pour un rendement d'indice `r` sur la journée, le trade
de rebalancement (en notionnel d'exposition) d'un fonds d'actif `A` est

```
Δ_i = A_i · r · L_i·(L_i − 1)
```

Le facteur `L(L−1)` est **positif pour TOUS les leviers** (long ET inverse) : `+3 → 6`, `+2 → 2`,
`−1 → 2`, `−2 → 6`, `−3 → 12`. Donc **long et inverse achètent du même côté** (les jours de hausse,
tous achètent le sous-jacent ; les jours de baisse, tous vendent). Les flux **s'additionnent**.
Flux agrégé d'un sous-jacent au close :

```
Imbalance_t  ≈  r_t · G ,   avec   G = Σ_i A_i · L_i·(L_i − 1)   (> 0, $ par unité de rendement)
```

`G` = sensibilité brute de rebalancement du complexe LETF sur ce sous-jacent. Le flux frappe les
~30 dernières min, dans le **sens** de `r_t`, à hauteur de `G / volume$`. Effet prédit : **push
late-day** (momentum de fin de séance dans le sens du jour) puis **reversal** (impact temporaire qui
se dissipe → overnight / lendemain réverse).

## Hypothèse & null central

- **Hypothèse (flux forcé exploitable)** : le rendement late-day charge **positivement** sur
  `r_reste-du-jour × (G/volume$)`, et l'overnight **réverse** ; l'effet est **plus fort là où
  `G/volume$` est grand** (semis SOXL/SOXS, etc.) ; un trade simple (entrer dans le sens du flux à la
  dernière barre, sortir au close ; ou fader l'overnight) est **net positif après coûts**.
- **Null central (attendu)** : le flux est **réel mais arbitré jusqu'au coût** (#2) — connu depuis
  Cheng-Madhavan 2009, des desks le front-runnent → l'interaction `G/volume$` est insignifiante
  une fois contrôlé le momentum générique, OU l'effet existe mais est **sous-coût** (spread + impact
  d'entrée/sortie le mangent), OU **n'existe qu'en sous-échantillon ancien**. On **s'attend à un KILL**.

L'**identification** ne repose PAS sur `r_t` seul (= momentum générique, déjà connu) mais sur
l'**interaction avec `G/volume$`** : à rendement intraday égal, l'effet doit être plus fort là où le
complexe LETF est gros vs la liquidité. C'est ce qui sépare « flux LETF » de « momentum/reversal
quelconque ».

## Modèle / données (free-data, multi-régime)

**Panel** (~10-15 sous-jacents ayant des paires LETF, choisis AVANT les chiffres pour couvrir des
`G/volume$` très différents) : SPY (SPXL/SPXS/UPRO/SPXU/SSO/SDS), QQQ (TQQQ/SQQQ/QLD/QID),
SOXX/semis (SOXL/SOXS), IWM (TNA/TZA), XLF (FAS/FAZ), XLE (ERX/ERY), GDX or (NUGT/DUST), Treasuries
20Y (TMF/TMV), DIA (UDOW/SDOW), XLK, XBI/LABU-LABD, EEM (EDC/EDZ).

**Variables (par sous-jacent, par jour t)** :
- `r_oc` = (Close_t − Open_t)/Open_t : rendement intraday = driver du rebalancement.
- `G` = Σ sur les LETF du sous-jacent de `AUM_i · L_i(L_i−1)`. AUM proxy = `shares_outstanding ×
  prix` (yfinance ; shares courantes × prix historique → AUM variable par le prix, pas par les
  créations/rachats — **caveat v1 noté**). Levier `L_i` connu (dans le nom du fonds).
- `vol$` = dollar-volume du sous-jacent (free, daily).
- `I = r_oc · G / vol$` : proxy d'imbalance normalisé (l'identifiant).
- `r_on` = (Open_{t+1} − Close_t)/Close_t : fenêtre de reversal overnight.
- Bonus intraday (yfinance horaire, ~2 ans) : `r_lasthour` (15:00→16:00) vs `r_rest` (Open→15:00)
  pour mesurer le **push** directement.

**Coûts** : spread + impact réalistes pour un retail/prop sur ETF liquides (à fixer dans le code,
bornés bas = best-case donné à la thèse). Trade overnight = subit le gap → coût de slippage de
sortie au close / entrée à l'open modélisé.

## Gates (pré-enregistrés — coupent dans les DEUX sens)

- **Gate A (existence / identification)** : régression panel `r_on,t+1 ~ I_t` (+ contrôles : `r_oc`
  seul pour absorber le reversal générique, effets-fixes sous-jacent). PASS si le coef sur
  l'**interaction `I`** a le **signe prédit** (reversal : négatif) **et** `|t| > 3` **et** survit en
  **sous-échantillon mûr 2023+** (leçon p12/p13). Bonus confirmatoire : push late-day `r_lasthour ~
  r_rest·G/vol$` de signe positif `t>3` sur l'horaire 2 ans.
- **Gate B (déployabilité)** : un trade explicite (fade overnight pondéré par `I`, OU suivre le flux
  sur la dernière barre) est **brut > 0, t > 2, net coûts > 0**, **both-halves** positif, **mûr
  2023+**, **les deux côtés** (jours up ET down) contribuent.
- **KILL** si Gate A échoue (interaction insignifiante = momentum générique, pas de signal LETF
  spécifique) **OU** Gate A passe mais Gate B net ≤ 0 (réel mais arbitré au coût = **#2**) **OU** rien
  ne survit en 2023+ (artefact ancien).
- **Robustesse** : la conclusion doit tenir hors des 2 sous-jacents les plus extrêmes en `G/vol$`
  (sinon = poignée de noms = bruit, leçon plancher min_side p2b) ; nommer le(s) nom(s) porteur(s).

## Sorties bonus

- Profil `coef de reversal` vs quantile de `G/vol$` : **dose-réponse** attendue (monotone croissante).
  Plate = falsifie l'identification LETF (leçon spread fantôme p3 : significatif sans dose-réponse =
  faux).
- Décomposition early vs mûr, up-days vs down-days.

## Falsifiabilité / honnêteté

- Coûts **bornés bas** + AUM en proxy prix-seul = **généreux envers la thèse** → un KILL est
  conservateur, un GO crédible.
- Le test décisif est l'**interaction**, pas `r_t` : un effet `r_t` seul significatif **ne suffit
  pas** (= momentum connu), il faut la **dose-réponse en `G/vol$`**.
- Prior honnête = **#2 probable** (thèse textbook depuis 2009). Le gate tranche ; je ne tune pas la
  barre `t>3 / net>0` vers un verdict [[feedback-gate-override]].
- Sous-échantillon **mûr 2023+** obligatoire (un effet 2010-2015 qui meurt après = priced-in).

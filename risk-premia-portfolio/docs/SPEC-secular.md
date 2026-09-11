# SPEC — Étude #37 : stress séculaire du deliverable levé + puissance du trend — pré-enregistré

> Écrit le 2026-09-11, **AVANT tout pull de données**. Sources vérifiées joignables par code HTTP
> seulement (Ken French 200, FRED LTGOVTBD/GS10 200, AQR xlsx 200) — aucun contenu lu. Origine :
> critiques 1 et 2 de la revue du 2026-09-11 (`factor-harvest/EDGE-IDEAS-LOG.md`, piste P1).
> **Pas une chasse à l'edge** : test de robustesse hors régime de l'objet qui porte l'argent réel
> (deliverable #22 levé 1,5× par #34, déployé 80 WTEF / 20 DBMFE, `DEPLOIEMENT.md`).

## Pourquoi

1. **#34 est mono-régime.** Toute la preuve du levier tient sur 2006-04 → 2026-02 : corrélation
   actions/obligations négative (sauf 2022), taux bas, surperformance US. Son gate C « both-halves »
   compare deux moitiés du même régime. Le levier ne paie que si le portefeuille bat son financement
   (cash + 0,40 %) : faux par construction dans un régime où les obligations font moins que le cash
   (1966-1981). Jamais mesuré.
2. **Le trend est « non prouvé », pas « absent ».** #1 : Sharpe 0,42, t = 1,87 sur 20 ans. t = SR·√T :
   il faut ~46 ans pour détecter SR 0,42 à 80 % de puissance. Le premium trend sur lequel repose
   le sleeve (et les 20 % DBMFE) n'a jamais été testé sur un échantillon qui a la puissance.

## Questions

- **Q1.** Le levier 1,5× ajoute-t-il du rendement **composé** hors de 2006-2026 ? Que coûte-t-il en
  stagflation ?
- **Q2.** La règle de ruine de #34 (maxDD > −35 % ⇒ L\* = 1,5) tient-elle hors fenêtre ?
- **Q3.** Le premium trend, net de coûts réalistes, est-il significatif sur ~41 ans, et le sleeve
  améliore-t-il le 60/40 sur une période entièrement antérieure à #34 ?

## Données (pré-committées)

| Rôle | Source | Période | Construction |
|---|---|---|---|
| Actions US | Ken French `F-F_Research_Data_Factors` (mensuel) | 1926-07 → | `Mkt = (Mkt-RF) + RF` (marché US value-weighted, rendement total) |
| Cash | Ken French `RF` (T-bill 1 mois) | 1926-07 → | Financement = `RF + 0,40 %/an` (spread #34 inchangé) |
| Obligations 10 ans | FRED `LTGOVTBD` (1925-04 → 1953-03) raccordé à FRED `GS10` (1953-04 →) | 1926-07 → | Obligation au pair reconstruite (ci-dessous) |
| Trend | AQR « Time Series Momentum: Factors, Monthly », facteur **agrégé** `TSMOM` (58 marchés, excès de rendement, brut de frais) | 1985-01 → | Sleeve DBMF-like (ci-dessous) |
| Inflation (diag) | FRED `CPIAUCNS` | 1926-07 → | Rendements réels, diagnostic seulement |
| Référence W0 | `sleeves.load_sleeves()` (#22), `data/irx.csv` (TB3MS, #34) | 2006-04 → 2026-02 | Inchangé |

**Obligation 10 ans.** Au mois t−1 on achète une obligation 10 ans au pair (coupon semestriel = y_{t−1}),
revalorisée en t au taux y_t avec une maturité résiduelle de 10 − 1/12 ans :
`R_t = P(y_t ; coupon y_{t−1}, 119 mois) − 1 + y_{t−1}/12`. Construction standard (celle de Shiller).
Pas de coût de transaction.

**Sleeve trend (1985-01 →).** `trend_t = RF_t + k·TSMOM_t − 1,0 %/12`
- Le collatéral rapporte le cash (comme DBMFE, contrairement au sleeve ETF #22 qui ne le rémunère pas).
- `k` = vol du sleeve #22 sur 2006-04 → 2026-02 / vol de `TSMOM` sur tout l'échantillon AQR : mise à
  l'échelle **à volatilité égale** au sleeve du deliverable. Ex-post, déclaré ; n'affecte ni Sharpe ni t.
- **Haircut 1,0 %/an** à cette vol (TER DBMFE 0,75 % + ~0,25 % d'exécution), figé.

**Avant 1985-01 : `trend = RF`** (sleeve à plat, aucune prime). Biais **contre** le deliverable :
Hurst-Ooi-Pedersen (2017) documentent un trend positif en 1929-32 et dans les années 1970.

**Portefeuille** (identique #34) : `r_p = 0,80 × 6040 + 0,20 × trend`, 6040 = 0,6 actions + 0,4 oblig
10 ans rebalancé mensuellement ; levier constant `r_L = L·r_p − (L−1)·(RF + 0,40 %)/12`.

## Fenêtres (pré-committées, nommées avant tout chiffre)

| Id | Période | Rôle |
|---|---|---|
| **W0** | 2006-04 → 2026-02 | Fenêtre #34 : fidélité des proxys |
| **W1** | 1926-07 → 2006-03 | Hors fenêtre séculaire, entièrement antérieur à #34 (trend = RF avant 1985, AQR après) |
| **W2** | 1966-01 → 1981-12 | Stagflation : obligations < cash, corrélation actions/obligs positive |
| **W3** | 1985-01 → 2006-03 | Deliverable **complet** (trend AQR), entièrement antérieur à #34 |
| **W4** | 1985-01 → dernier mois AQR | Puissance du trend (~41 ans) |

## Métriques

- **Rendement composé (CAGR)** pour les gates de levier. #34 gatait sur la moyenne arithmétique ×12,
  qui ignore la traînée de volatilité (l'incrément arithmétique du levier est positif dès que l'excès
  l'est). Le CAGR est ce que l'investisseur vit → **plus strict** que #34, déclaré ici. Arithmétique
  rapportée à côté.
- **Sharpe = excès sur RF** (`mean(r − RF)/std(r − RF)·√12`). `audit.sharpe` (#34) divise le
  rendement **total** par sa vol : acceptable avec un cash à ~1 %, faux avec un cash à 15 % (1981).
  Les deux sont rapportés sur W0 pour mesurer l'écart.
- **t calendar-time** = t de la moyenne mensuelle des excès.
- maxDD sur équité composée mensuelle.

## Gates (figés avant run)

| Gate | Fenêtre | PASS si |
|---|---|---|
| **G0 fidélité** (prérequis) | W0 | corr(proxy 6040, `base6040` #22) ≥ 0,95 **et** \|écart CAGR\| ≤ 1,5 pt/an |
| **A levier paie hors fenêtre** | W1 | CAGR(L=1,5) − CAGR(L=1) ≥ **+1,0 pt/an** (hurdle #34 A) |
| **B stagflation** | W2 | CAGR(L=1,5) − CAGR(L=1) > 0 |
| **C ruine avec trend** | W3 | maxDD(L=1,5) > −35 % (règle #34) |
| **R ruine séculaire** | W1 | maxDD(L=1,5) > −35 % |
| **D puissance du trend** | W4 | sleeve net (`trend − RF`) : t > 2,0 **et** Sharpe > 0 sur W3 **et** sur 2006-04 → fin |
| **E sleeve hors fenêtre** | W3 | Sharpe(0,8×6040 + 0,2×trend) − Sharpe(6040) > 0 |

## Verdict (mapping pré-enregistré)

| Cas | Verdict et conséquence |
|---|---|
| ¬G0 | **UNTESTABLE** : proxys non fidèles, aucun autre gate n'est lu. |
| A ∧ C ∧ D ∧ E | **CONFIRMÉ** : déploiement inchangé. B et R deviennent des caveats chiffrés dans `DEPLOIEMENT.md`. |
| ¬A | **RÉVISER LE LEVIER** : l'incrément 2006-26 n'existe pas hors fenêtre → cible L = 1 (allocation redéfinie dans une étude suivante, pas ici). |
| ¬C | **RÉVISER L\* À LA BAISSE** : L\*_W3 = plus grand L de {1 ; 1,25 ; 1,5 ; 2} avec maxDD > −35 % sur W3. |
| ¬D ou ¬E | **TREND DÉGRADÉ** : sleeve réduit à un rôle d'assurance, attente de rendement trend ramenée à 0 ; les 20 % DBMFE sont à rediscuter (pas changés ici). |

Plusieurs FAIL → toutes les conséquences s'appliquent.

**B et R ne tuent rien seuls :**
- **¬B** : le coût du levier en stagflation (pts/an sur 16 ans) entre dans `DEPLOIEMENT.md`. Un cœur
  incluant un actif réel serait une étude suivante, pas une conséquence automatique.
- **¬R** : on regarde **L = 1 sur W1**. Si L = 1 franchit aussi −35 %, la règle de ruine est une
  propriété de la fenêtre 2006-26, pas du levier → le DD de planification de `DEPLOIEMENT.md`
  (aujourd'hui « −30 % ») est remplacé par le chiffre séculaire à L = 1,5. Si L = 1 respecte −35 %
  mais pas 1,5 → le levier crée la ruine → traité comme ¬C (L\* à la baisse, calculé sur W1).
- **¬D** : si t < 2, on rapporte la borne haute de l'IC à 95 % du Sharpe. Si elle contient 0,40 →
  « non prouvé à cette taille », pas « absent » (critique 2 : ne pas refaire l'erreur dénoncée).

## Diagnostics non-gating

- Grille L ∈ {1 ; 1,25 ; 1,5 ; 2} sur W0-W4 : CAGR, arithmétique, vol, Sharpe excès, maxDD, pire mois.
- Financement broker RF + 1,5 %.
- Épisodes : 1929-09 → 1932-06, 1940-1951 (répression financière, en réel), 1973-74, 1987-10,
  2000-02, 2008, 2022.
- Fenêtres glissantes de 15 ans (W1 ∪ W0) : part des fenêtres où CAGR(1,5) < CAGR(1).
- Sous-facteurs AQR (matières premières, actions, taux, devises) : Sharpe par classe.
- corr(sleeve AQR, `trend` #22) sur W0 ; corr(sleeve AQR, DBMF) sur 2019-06 → si DBMF est dans
  `data/deploy_px.csv`.
- RF Ken French vs TB3MS sur W0 (écart moyen du financement).
- W3 avec trend = RF (sans AQR) : part du trend dans l'incrément.

## Caveats déclarés d'avance

1. **Proxys.** Marché Ken French (tout le marché US, sans frais) ≠ SPY. Obligation 10 ans
   reconstruite, sans coûts ; avant 1953, `LTGOVTBD` porte sur des maturités > 10 ans, et les taux
   sont administrés en 1942-51 (vol obligataire écrasée).
2. **Trend à plat avant 1985** : R et B sont biaisés contre le deliverable (conservateur).
3. **AQR brut de frais** : haircut 1 %/an déclaré ; mise à l'échelle ex-post.
4. **Financement anachronique.** Futures S&P : 1982 ; box-spreads : plus tard. Avant, un particulier
   empruntait au taux call-money, bien au-dessus du cash. On teste la stratégie **avec la
   technologie de financement d'aujourd'hui**, pas son investissabilité historique.
5. **Biais du survivant US** (Jorion-Goetzmann 1999) : le siècle américain est le meilleur marché du
   XXe siècle → le test est optimiste sur les actions, pas pessimiste.
6. Gap intra-mois non simulé ; nominal USD ; hors fiscalité.

## Prior honnête (écrit avant run)

- **G0** : PASS (~95 %). Marché Ken French ≈ SPY, 10 ans reconstruit ≈ IEF.
- **A** : **à pile ou face (~50 %).** Excès du 60/40 sur le cash 1926-2006 ≈ 4 %/an → excès de
  `r_p` ≈ 3,2 % → incrément arithmétique ≈ 0,5 × (3,2 − 0,4) ≈ 1,4 pt ; moins la traînée de vol
  (≈ 0,625 × σ², σ ≈ 9-10 %) ≈ 0,5-0,6 pt → **CAGR ≈ +0,8-0,9 pt**, juste sous le hurdle. Le gate
  le plus informatif.
- **B** : FAIL (~85 %). Obligations < cash en 1966-81, actions à peine au-dessus.
- **R** : FAIL (~85 %), et L = 1 aussi (~80 %) : 0,8 × 60/40 en 1929-32 ≈ −40 %. Issue attendue :
  « règle de ruine = propriété de la fenêtre », DD de planification réécrit.
- **C** : PASS (~80 %). 2000-02 : 60/40 ≈ −20 %, trend positif en 2002 ; 1987 : un mois.
- **D** : PASS (~75 %). TSMOM fort 1985-2008, décennie perdue 2009-19 ; le haircut coûte ~0,14 de
  Sharpe.
- **E** : PASS (~75 %).

**Issue la plus probable : CONFIRMÉ, A limite**, avec deux caveats chiffrés dans `DEPLOIEMENT.md` :
coût du levier en stagflation, et DD de planification bien plus profond que −30 % dans un 1929.
Un ¬A serait la surprise qui change le déploiement.

## Sortie

`run_secular.py`, `docs/FINDINGS-secular.md`. Caches dans `data/` (gitignoré) : `ff_factors.csv`,
`fred_ltgovtbd.csv`, `fred_gs10.csv`, `fred_cpi.csv`, `aqr_tsmom.xlsx`.
Commit de la spec avant tout pull et tout code ; findings après run.

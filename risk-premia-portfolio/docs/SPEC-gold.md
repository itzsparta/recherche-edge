# SPEC — Étude #41 : l'or dans le cœur du deliverable, contre la stagflation — pré-enregistré

> Écrit le 2026-09-12, **AVANT tout pull du prix de l'or**. Sources vérifiées joignables par code HTTP
> seulement (Banque mondiale 200, datahub 200 ; clés Bundesbank 404) : aucun contenu lu. Les séries de
> #37 (Ken French, FRED, AQR, CPI) sont déjà en cache et réutilisées telles quelles.
> Origine : caveat B de #37 (`FINDINGS-secular.md`). En 1966-81, le levier coûte −0,87 pt/an et le
> portefeuille reste 16 ans sous le cash (réel −1,65 %/an). Pas une chasse à l'edge : un test
> d'assurance sur l'objet qui porte l'argent réel.

## Question

Remplacer une part fixe du portefeuille déployé par de l'or physique (ETC) comble-t-il le trou
stagflation, **à un coût tolérable hors stagflation**, et **mieux que du cash** à la même place ?

## Deux pièges déclarés avant les données

1. **L'or des années 1970 n'est pas une couverture répétable, c'est une réévaluation unique.** De
   35 $ (parité de Bretton Woods, fin en 1971) à 850 $ (1980), le gain inclut la libération d'un prix
   administré. Un gate « l'or aide en 1971-81 » passerait par construction (n = 1). L'assurance doit
   donc aussi se montrer **après 1982**.
2. **Remplacer 10 % d'un portefeuille levé par n'importe quel actif stable réduit la baisse
   mécaniquement.** L'or doit battre la même part mise en **cash** (dé-risquage simple), pas seulement
   le portefeuille inchangé.

## Données (pré-committées)

| Rôle | Source | Construction |
|---|---|---|
| Or | Banque mondiale, *Commodity Price Data* (Pink Sheet), mensuel, `Gold` $/oz | **Moyenne mensuelle** (caveat 1) ; rendement de prix seul, moins 0,25 %/an (frais d'ETC) |
| Or (contrôle) | datahub `core/gold-prices` mensuel | Diagnostic de cohérence seulement |
| Fidélité | yfinance `GLD` (2004-11 →), fin de mois | G0 |
| Actions, cash | Ken French (`mkt`, `rf`), comme #37 | Inchangé |
| Obligation 10 ans | FRED `DGS10` quotidien, **dernier taux du mois** → obligation au pair reconstruite | Post-hoc de #37 : corr IEF 0,99 contre 0,72 en moyenne mensuelle. Couvre 1962+ |
| Trend | AQR TSMOM, comme #37 (k, haircut 1 %/an) ; trend = RF avant 1985 | Inchangé |
| Inflation | FRED `CPIAUCNS` | Rendements réels et définition de S |

## Portefeuilles

- **P0**, deliverable déployé (proxy #37) : `r_L = 1,5·r_p − 0,5·(RF + 0,40 %)/12`, avec
  `r_p = 0,8 × 6040 + 0,2 × trend`.
- **Pg** = `(1 − g)·P0 + g·or`, **g = 10 %**, rebalancé mensuellement. En déploiement :
  **72 % WTEF / 18 % DBMFE / 10 % ETC or** (prorata).
- **Pc** = `(1 − g)·P0 + g·RF` : la même part en cash (contrefactuel du piège 2).

Un seul g est gaté, pour éviter le choix du meilleur poids ; les autres poids sont en diagnostic.

## Fenêtres

| Id | Période | Rôle |
|---|---|---|
| **WG** | 1968-04 → dernier mois commun | Or à prix de marché (le double marché commence en mars 1968) |
| **W2g** | 1968-04 → 1981-12 | Stagflation, W2 de #37 restreint à l'or libre |
| **WP** | 1982-01 → dernier mois commun | Après la réévaluation : là où l'assurance doit se montrer |
| **S** | mois de WP où l'inflation CPI sur 12 mois glissants > 5 % | Chocs d'inflation modernes, définis par une règle, pas par des dates |

## Gates (figés avant run)

| Gate | Test | PASS si |
|---|---|---|
| **G0 fidélité** (prérequis) | or Banque mondiale vs GLD, 2004-12 → fin | corr des rendements **12 mois glissants** ≥ 0,95 **et** \|écart de CAGR\| ≤ 1,0 pt/an |
| **A protection** | W2g, réel | CAGR réel(Pg) − CAGR réel(P0) ≥ **+1,0 pt/an** |
| **B coût** | WP | CAGR(Pg) − CAGR(P0) ≥ **−0,75 pt/an** |
| **C mieux que le cash dans les chocs modernes** | S | Σ (r_Pg − r_Pc) > 0 |
| **D mieux que le cash en efficacité** | WP | Sharpe excès(Pg) > Sharpe excès(Pc) |

G0 est gaté en rendements 12 mois, pas mensuels : une moyenne mensuelle décale les rendements d'environ
un demi-mois. Ce décalage ne biaise pas un CAGR sur 14 à 44 ans, mais il ferait échouer une corrélation
mensuelle. La corrélation mensuelle est rapportée en diagnostic.

## Verdict (mapping pré-enregistré)

| Cas | Verdict et conséquence |
|---|---|
| ¬G0 | **UNTESTABLE** : série or non fidèle, aucun autre gate lu. |
| ¬A | **KILL** : même dans les années 1970, 10 % d'or ne protège pas. |
| A ∧ ¬B | **TROP CHER** : l'assurance coûte plus de 0,75 pt/an hors stagflation. Non ajouté ; le caveat stagflation reste dans `DEPLOIEMENT.md`. |
| A ∧ B ∧ (¬C ∨ ¬D) | **ASSURANCE 1970s SEULEMENT** : la protection mesurée est la réévaluation post-Bretton Woods (n = 1). Hors de celle-ci, l'or ne fait pas mieux que du cash. Non ajouté, le caveat reste. |
| A ∧ B ∧ C ∧ D | **AJOUTER** : `DEPLOIEMENT.md` passe à 72 / 18 / 10 (ETC or physique, CTO). |

## Diagnostics non-gating

- g ∈ {5 ; 15 ; 20 %} : les mêmes quatre mesures.
- Sous-périodes de WP : 1982-2001 (marché baissier de l'or) ; 2002-2026 ; **WP arrêtée à 2023-12**
  (sans le rallye 2024-26 porté par les achats des banques centrales).
- Épisodes P0 / Pg / Pc, nominal et réel : 1973-74, 1979-80, 1980-82 (krach de l'or), 1987, 2000-02,
  2008, 2013, 2020, 2022.
- maxDD réel sur WG ; glissant 15 ans : part des fenêtres où CAGR(Pg) > CAGR(P0).
- Liste des mois de S, et contribution par épisode d'inflation.
- corr(or, P0) par régime ; corr mensuelle or Banque mondiale vs GLD ; cohérence datahub.
- Or seul : CAGR nominal et réel, Sharpe excès sur WG et WP.

## Caveats déclarés d'avance

1. **Moyennes mensuelles** : la volatilité de l'or est sous-estimée, le maxDD est adouci, et les dates
   sont décalées d'environ un demi-mois. Sans effet matériel sur les CAGR longs ; C (des blocs de mois
   contigus) est peu touché.
2. **USD nominal**, comme #37. Pour un investisseur en EUR, l'or et le deliverable non couvert partagent
   le risque dollar ; non modélisé.
3. **Investissabilité historique** : les Américains n'ont pu détenir de l'or qu'à partir de 1975. On
   teste avec l'instrument d'aujourd'hui (ETC), comme le financement dans #37.
4. **Rallye 2024-2026** (achats des banques centrales) : peut porter B et D, d'où le diagnostic arrêté à
   2023-12.
5. Hors fiscalité (un ETC en CTO relève du PFU, comme le reste du deliverable).

## Prior honnête (écrit avant run)

- **G0** : PASS (~85 %).
- **A** : PASS (~95 %), par le piège 1.
- **B** : ~65 %. L'or croît d'environ 5 %/an sur 1982-2026, contre environ 10 % pour P0 : −0,5 pt,
  moins un bonus de rebalancement.
- **C** : **~40 %.** En 1990, l'or baisse pendant que le cash rapporte 8 % ; en 2021-23, il est à peu
  près stable face à un cash à 2-5 %.
- **D** : ~60 %. L'or est décorrélé avec un excès positif, donc probablement un meilleur 10 % que le cash.
- **Issue la plus probable : ASSURANCE 1970s SEULEMENT** (~45 %). AJOUTER ~25 %. Le gate qui décide
  est C.

## Sortie

`run_gold.py` (réutilise les loaders de `run_secular.py`), `docs/FINDINGS-gold.md`. Caches `data/`
(gitignoré) : `wb_cmo_monthly.xlsx`, `gold_datahub.csv`. Commit de la spec avant tout pull ; findings
après le run.

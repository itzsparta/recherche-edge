# FINDINGS — Piste #32 : merger arbitrage small-cap cash deals

Verdict rendu le 2026-06-28. Test contre la spec **pré-enregistrée** ([`SPEC.md`](SPEC.md)) —
aucun gate modifié après avoir vu les résultats. Code : [`../run_merger.py`](../run_merger.py).

## Verdict

**UNTESTABLE sur données gratuites — pas par absence d'edge, mais parce que le panel ne peut pas
être construit sans biais de survie directionnel qui retire exactement la jambe profitable.**

Les gates A-G ne sont jamais atteints : la construction du panel échoue en amont. Ce n'est PAS un
« n trop petit » réparable par l'échelle — c'est un **mur de données structurel et directionnel**.

## Ce qui a été bâti (la plomberie FONCTIONNE)

Pipeline complet, validé étage par étage sur l'année-échantillon 2015 (391 annonces 8-K brutes) :

1. **EDGAR EFTS** — full-text search 8-K « definitive merger agreement », chunks mensuels, caché. ✓
2. **Extraction prix cash** — union de 4 phrasings réels (`$N per share in cash`, `cash
   consideration of $N`, `$N in cash for each share`…) + exclusion mix stock/cash précise. ✓
3. **Résolution ticker** — map EDGAR courante, **fallback texte 8-K** (`NYSE:/NASDAQ: XYZ`) pour
   récupérer les cibles absentes de la map. ✓ (ramène `no_ticker` de 248 à 46)
4. **Prix yfinance** + identification cible (cours sous le deal_price) + rendement réalisé. ✓

## Le mur — biais de survie DIRECTIONNEL (le tueur)

Funnel 2015 après élargissement (391 hits → 5 « deals exploitables ») :

| Étage | Compte | Lecture |
|------|--:|------|
| no_cash_price | 263 (67 %) | plafond de recall : la plupart des 8-K « merger » n'exposent pas un prix/action cash parseable en texte libre |
| no_ticker | 46 | cible sans ticker ni dans la map ni dans le texte |
| **no_prices** | **10** | **ticker récupéré via texte → yfinance ZÉRO prix = delisté** |
| not_target | 18 | cours hors bande sous deal_price (acquéreur / misparse) |
| px_gap | 3 | historique insuffisant |
| **kept** | **5** | |

**La diagnose décisive (survivorship) :**

```
kept_map:    5   kept_text:    0   → 100 % des deals gardés = encore cotés aujourd'hui
noprice_map: 0   noprice_text: 10  → 100 % des delistés (récupérés via texte) = yfinance vide
```

- **yfinance sert 0/10 des cibles delistées.** Un deal qui **CLÔTURE** → la cible est rachetée →
  **delistée** → yfinance ne renvoie **rien** (ni exit, **ni même l'entry**). La jambe gagnante de
  l'arb disparaît à 100 %, et son entry n'est récupérable par **aucune** source gratuite (EDGAR n'a
  pas de prix de marché ; Stooq a le même trou).
- **Les 5 gardés sont tous des break-survivors** : `closed = 0/5`, encore cotés indépendamment des
  années après l'annonce = le deal a cassé. Le panel constructible est **structurellement
  break-only**. Scaler ×15 (2010-2024) donne **plus de break-survivors, pas un panel représentatif**.
- Un échantillon break-only mesure un rendement d'arb **systématiquement pessimiste et non
  représentatif** → tout chiffre serait un mirage de survie. La discipline du programme l'interdit.

## Mur secondaire — extraction contaminée (pas de termes structurés en EDGAR free)

Les 5 « gardés » sont en plus pollués, faute de champ structuré de termes de deal :

| ticker | deal_price | entry | nature réelle |
|---|--:|--:|---|
| DHR ×2 | 127.20 | ~58 | **Danaher = ACQUÉREUR** de Pall ($127.20/action) ; son cours tombe dans la bande target par coïncidence |
| ELV | 184.0 | 171 | **Anthem = ACQUÉREUR** (Anthem-Cigna) |
| PED | 400.0 | 180→46 | **misparse** ($400 n'est pas le prix cash réel) |
| COR | 190.0 | 91 | spread 2:1 implausible = **misparse** |

Le test « cible = cours sous deal_price » ne sépare pas proprement cible et acquéreur quand le
deal_price lui-même est faux. Séparer les deux exigerait un prix de deal fiable — indisponible en
texte libre. Un EDGAR « structuré » (termes de deal, type cash/stock, statut close/break) n'existe
pas gratuitement ; c'est précisément ce que vendent Bloomberg MA / CapIQ / SDC.

## Pourquoi le run complet 2010-2024 n'a PAS été lancé

Un dropout **directionnel à 100 %** de la jambe close ne se corrige pas par l'échelle. Le run complet
(~5 800 hits, ~2,5 h de fetch) produirait un panel break-only contaminé déjà prouvé sur l'année 2015.
Le pré-enreg fixait `n < 20 ⇒ UNTESTABLE` ; on rend le verdict avec sa **cause structurelle**, pas un
pseudo-chiffre.

## Ce qu'il aurait fallu (et le prior tient)

Tester proprement le merger-arb small-cap exige une base M&A structurée (termes + **prix des cibles
delistées** + statut close/break) = données payantes. Le prior honnête de la spec (DOWNGRADE/KILL
sub-hurdle, à la SPAC #27 / ILS #31) reste **non-réfuté et non-confirmé** : on n'a pas pu l'atteindre.

## Place dans le programme

**Étude #32, UNTESTABLE free-data.** Sous-type proche du **mur de données** de commodity-carry #30
(univers large non-gratuit), mais **pire car directionnel** : ici la donnée gratuite ne se contente
pas de manquer, elle retire **exactement les issues profitables** (deals clos), biaisant tout estimé
vers le pessimisme. Distinct des KILL (où la prime est mesurée puis jugée sub-hurdle). Le mécanisme
candidat (prime d'incertitude binaire) restait structurellement distinct des 31 pistes — mais
**inatteignable sans base payante**. Deliverable trading inchangé : **mono-sleeve trend**.

**Bilan : 32 études, 0 edge déployable** (31 verdicts rendus + 1 untestable).

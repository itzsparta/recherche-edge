# SPEC — Étude #39 : capture de dividende sous statut PEA — pré-enregistré

> Écrit le 2026-09-11, **AVANT tout pull de données** (aucun prix, aucun dividende, aucune liste de
> constituants lus). Origine : piste P3 de la revue du 2026-09-11 (`factor-harvest/EDGE-IDEAS-LOG.md`).
> Gates numériques figés ici ; je ne les bouge pas pour fabriquer un PASS ([[feedback-gate-override]]).
> Les gates du log sont repris et **durcis** (B exige t > 2 et un segment de rendement fixé d'avance ;
> A exige la dose-réponse) : le log n'était qu'une esquisse.

## Thèse (arme neuve : le statut fiscal)

Le re-vois du 2026-07-02 ne voit le statut de résident FR que comme une **contrainte** (sous-type 5).
Le PEA est une arme : un dividende d'une société française y est encaissé **brut, non imposé**.

Le jour ex (J), le cours baisse de ρ·D. Elton-Gruber (1970) : ρ reflète la fiscalité du
price-setter marginal, ρ = (1 − τ_div)/(1 − τ_pv). Si le prix est fixé par des investisseurs pour qui
le dividende vaut moins que la plus-value (non-résidents soumis à la retenue à la source), alors
ρ < 1 et un détenteur exonéré capte (1 − ρ)·D en achetant cum et en revendant ex.

**Mécanisme (identité, pré-enregistrée).** Achat au fixing de clôture de J−1 (cum), vente au fixing
d'ouverture de J (ex). Rendement capté, ajusté du marché :

```
R_cap = (O_J + D) / C_{J−1} − 1
AR    = R_cap − Rm_J                       Rm_J = rendement overnight C_{J−1} → O_J du marché
AR    = (1 − ρ) · y          avec  y = D / C_{J−1},   ρ = (C_{J−1}·(1 + Rm_J) − O_J) / D
```

Les deux fixings (enchères) évitent le spread ; le coût réel est la fiscalité de transaction.

## Le tueur identifié avant les données : la TTF

La taxe sur les transactions financières (art. 235 ter ZD CGI) frappe **toute acquisition** d'actions
de sociétés françaises capitalisant > 1 Md€, **PEA compris**. Seule exonération pertinente : l'intraday
(position nette nulle en fin de journée). La capture exige de détenir le titre au soir de J−1 → **taxée**.
Taux : 0,20 % (2012-08), 0,30 % (2017-01), **0,40 % (2025-04 →)**.

Coût d'un aller-retour aux conditions d'aujourd'hui, figé :

| Poste | Coût |
|---|---|
| TTF à l'achat | 0,40 % |
| Courtage PEA en ligne + écart au fixing | 2 × 0,10 % |
| **Total `c`** | **0,60 %** |

Les conditions d'aujourd'hui s'appliquent à toute la période, comme le financement dans #37. On
teste la stratégie telle qu'on la déploierait maintenant, pas son histoire.

Seuil de rentabilité : (1 − ρ)·y > 0,60 %. À y = 3 %, il faut ρ < 0,80. À y = 5 %, il faut ρ < 0,88.

## Données (pré-committées)

| Rôle | Source | Construction |
|---|---|---|
| Univers | Constituants **actuels** du SBF 120 (Wikipedia FR, table des composants) | Tickers `.PA` |
| Domicile | Préfixe ISIN (Wikipedia ou liste Euronext) | **ISIN `FR` seulement**. Hors France, la retenue étrangère est non récupérable en PEA : autre objet, exclu |
| Prix + dividendes | yfinance `history(auto_adjust=False, actions=True)` | `Open`, `Close`, `Volume` (ajustés des splits, pas des dividendes), `Dividends` indexés à la date ex |
| Période | 2005-01-01 → dernier jour dispo | 2005 : fin de l'avoir fiscal, changement de régime du price-setter |

**Marché `Rm_J`** : moyenne équipondérée du rendement overnight C_{J−1} → O_J des titres de l'univers
**sans** date ex en J. Même source, mêmes enchères, même nuit : retire la prime overnight générique
(#5a) et le mouvement de marché. Au moins 20 titres valides exigés, sinon la nuit est exclue.

**Règles de validité des données (a priori, symétriques, pas des gates)** :
- nuit invalide si `O_J` manquant ou ≤ 0, si `Volume_J = 0`, ou si `O_J == C_{J−1}` exactement (ouverture
  périmée). La règle vaut pour l'événement et pour les titres du benchmark ;
- y > 10 % exclu : distribution exceptionnelle ou erreur. Le nombre d'exclusions est rapporté ;
- |AR| > 15 % exclu (désalignement de split ou de date). Rapporté, plus un diagnostic sans ce filtre.

## Statistique

- **t calendar-time** : événements groupés par **mois** de J, moyenne par cohorte, t sur la série des
  cohortes (leçon #6 et #28 : les ex-dates se concentrent en mai-juin, et les événements d'une même nuit
  partagent `Rm_J`). Le t inter-événements est rapporté, pas gating.
- **ρ̂** = 1 − Σ(AR·C_{J−1}) / ΣD (ratio de sommes, stable pour D petit).
- **Segments de rendement** (seuils fixes, pas des quantiles) : y < 1,5 % ; 1,5 % ≤ y < 3 % ; y ≥ 3 %.
  Le seul segment tradable est y ≥ 3 %. `c` est fixe par trade alors que la capture ∝ y, et y est connu
  des semaines avant J (dividende voté en AG) : filtrer sur y n'est pas du look-ahead.

## Gates (figés avant run)

| Gate | Test | PASS si |
|---|---|---|
| **G0 fidélité** (prérequis) | alignement dates/montants | ρ̂ sur la nuit J ∈ [0,5 ; 1,5] **et** \|ρ̂\| < 0,3 sur les nuits placebo J−1 et J+1 (même formule, même D) |
| **A existence** | tous événements, AR brut | moyenne > 0 **et** t_cal > 2 **et** moyennes croissantes sur les 3 segments de y (signature du mécanisme fiscal) |
| **B déployable** | y ≥ 3 %, AR − 0,60 % | moyenne > 0 **et** t_cal > 2 |
| **C maturité** | segment B net, 2015+ vs < 2015 | moyenne 2015+ > 0 **et** Welch t(avant − après) < 2 (critique 2 : un test de différence, pas « ns après ») |
| **D concentration** | segment B net, hors les 5 noms à plus forte ΣAR | moyenne > 0 **et** t_cal > 2 |

## Verdict (mapping pré-enregistré)

| Cas | Verdict et conséquence |
|---|---|
| ¬G0 | **UNTESTABLE** : dates ou montants yfinance non fiables, aucun autre gate lu. |
| G0 ∧ ¬A | **KILL ρ ≈ 1** : le price-setter est neutre fiscalement (dealers, cum-cum) ; le statut PEA ne confère rien le jour ex. |
| A ∧ ¬B | **KILL friction** (sous-type 2) : ρ < 1 réel mais ≤ coût. Si le segment y ≥ 3 % passe avec le coût **hors TTF** (0,20 %, t > 2), la TTF est le seul obstacle. La porte restante serait alors les capitalisations < 1 Md€, exonérées : nouvelle SPEC, pas une conséquence automatique. |
| A ∧ B ∧ (¬C ∨ ¬D) | **DOWNGRADE** : réel, mais décru ou porté par quelques noms. |
| A ∧ B ∧ C ∧ D | **GO phase 2** : premier GO du programme. Phase 2 = vérification d'exécution aux fixings sur un petit montant réel avant toute taille. |

## Diagnostics non-gating

- ρ̂ par segment de y, par période (2005-11 / 2012-16 / 2017-25-03 / 2025-04+), et pente de AR sur y.
- **Nuit 2025-04+** : la loi de finances 2025 étend la retenue à la source aux montages cum-cum, qui
  poussaient ρ vers 1. Moyenne et n rapportés. Échantillon trop court pour conclure, lu comme indice.
- Variante clôture-clôture (C_{J−1} → C_J + D).
- Coût optimiste 0,44 % (TTF + 2 × 0,02 %, courtage forfaitaire 1 € sur 5 k€) ; coût hors TTF 0,20 %.
- Marché alternatif : overnight de l'indice CAC 40 (`^FCHI`) au lieu du benchmark en coupe.
- Rendement annualisé sur capital du segment B net : capital réparti à parts égales entre les
  événements d'une même nuit, part des nuits investies. Le cash du PEA n'est pas rémunéré.
- Hartzmark-Solomon (2013), en temps d'événement : AR clôture-clôture sur [J−21, J−1] (run-up avant
  l'ex-date) et [J, J+5]. Diagnostic seulement : une promotion exigerait sa propre SPEC.
- Nombre d'événements par étape de filtre ; top-5 noms ; sans le filtre |AR| > 15 %.

## Caveats déclarés d'avance

1. **Survivorship** : constituants actuels. Le biais sur le ρ du jour ex est a priori faible (la
   microstructure du jour ex n'est pas liée à la survie), mais non corrigé.
2. **Qualité yfinance Euronext** : `Open` = fixing d'ouverture ou premier trade ? Dividendes parfois
   dupliqués ou mal datés. G0 contrôle l'alignement ; les placebos J±1 détectent un décalage d'un jour.
3. **TTF appliquée à tous** : quelques noms du SBF 120 capitalisent < 1 Md€ et en sont exonérés. Biais
   conservateur, borné par le diagnostic hors TTF.
4. **Exécution aux fixings** : suppose un remplissage au prix d'enchère, réaliste pour une taille de
   particulier sur le SBF 120. L'écart est compris dans les 0,10 % par jambe.
5. **Taux TTF 0,40 % et courtage** : valeurs 2025-2026 à revérifier (BOFiP, grille du courtier) avant
   tout déploiement. Ne change pas un KILL : un taux plus bas élargirait seulement la marge d'un PASS.
6. Hors prélèvements sociaux à la sortie du PEA (17,2 %, communs à tout usage du PEA). Dividende
   optionnel en actions supposé pris en cash.

## Prior honnête (écrit avant run)

- **G0** : PASS (~85 %). Les dividendes yfinance sur `.PA` sont la source la plus fragile.
- **A** : ~45 %. Des non-résidents sous retenue à la source détiennent ~40 % du CAC 40 → ρ < 1 plausible.
  Mais l'arbitrage cum-cum des banques, légal jusqu'en 2019-2025, est précisément ce qui ramène ρ à 1.
- **B** : **~5 %.** Il faut ρ < 0,80-0,85 sur le segment à haut rendement, **et** t > 2 net. La TTF seule
  (0,40 %) mange la capture d'un ρ à 0,87 sur un y de 3 %.
- **C, D** : conditionnels à B, sans objet sinon.

**Issue la plus probable : KILL friction** (A PASS, B FAIL), ou KILL ρ ≈ 1. Même mort, la mesure a une
valeur : un ρ chiffré, et la réponse à la question « la TTF est-elle le seul obstacle ? ». Si oui, la
seule porte restante est celle des petites capitalisations.

## Sortie

`dividend-pea/data.py` (univers, prix, dividendes ; cache `data/`, gitignoré), `run.py`,
`docs/FINDINGS.md`. Commit de la spec avant tout pull et tout code ; findings après le run.

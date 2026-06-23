# SPEC — Piste 16 : Biais des books sportifs récréatifs (pré-enregistré)

> Écrit **avant** tout chiffre. Comme la piste 14, **ce n'est PAS un backtest de prédiction
> de prix** : c'est un **ledger d'espérance net-de-vig**. La question n'est pas « un signal bat-il
> le marché ? » mais « un **biais de tarification documenté** d'un book récréatif laisse-t-il une
> **EV nette positive après le vig HONNÊTE**, et est-elle **encaissable** par un solo sans se faire
> limiter ? ». Même rigueur, autre étang.

## Hypothèse d'edge

Les books sportifs grand-public portent des **biais de tarification persistants** (favorite-longshot,
sur-cote du côté « public ») parce que leur contrepartie est de l'**argent récréatif** et que leur
modèle économique est le **vig**, pas l'efficience parfaite. Un solo peut récolter une fraction de ce
biais **nette de vig**.

## Pourquoi ça pourrait persister — l'arme structurelle inédite

C'est le **premier marché du programme où la contrepartie est PROUVÉE bête**. Les 15 morts précédentes
partagent une hypothèse cachée : contrepartie sophistiquée (arbs, market-makers, crypto-natifs,
institutions). Ici l'inverse — le récréatif domine le flux, et le book **ne corrige pas** le biais
jusqu'au bout parce que **son business EST** ce flux + le vig. Le biais favorite-longshot est documenté
depuis >50 ans et **persiste** : il n'est pas compétitionné comme un edge à info/prix public.
C'est le seul test qui attaque l'**hypothèse partagée** par tous les kills, au lieu de la re-tester.

## Le null honnête (= verdict attendu a priori)

Prior bas (15 kills). Le motif unifié du programme — *tout edge réel est mangé par le coût/la friction,
ou inaccessible par structure* — prédit la mort sous **trois formes spécifiques**, pré-enregistrées :

1. **Biais < vig (analogue spread-fantôme / CEF)** — le biais favorite-longshot est **réel** dans la
   courbe winrate-vs-cote, mais au **prix sharp de clôture (Pinnacle)**, net du hold, le ROI du côté
   exploitable reste **≤ 0**. Le biais **vit à l'intérieur du vig**. C'est le tueur le plus probable :
   un biais peut être statistiquement réel sans franchir le **prix offert**. (Leçon : capacity-niche
   #3, le spread existait t=+7 mais sans profondeur derrière.)
2. **Priced-in à la clôture (analogue unlocks #2 / pré-FOMC #5b)** — tout biais visible sur la cote
   d'**ouverture / book soft** a disparu à la cote de **clôture Pinnacle** (le benchmark efficient).
   Si l'edge a besoin du prix early/soft → ce n'est pas une vraie inefficience.
3. **Inencaissable par accès structurel (le THÉORÈME récurrent du programme)** — les books soft qui
   **sur-mispricent** au-delà du biais sont **exactement** ceux qui **limitent/bannissent** les comptes
   gagnants ; les books qui ne bannissent pas (Pinnacle, Betfair) tarifent efficacement (pas de biais).
   L'intersection *réel ∧ encaissable* est **vide**. C'est « ce qui te laisse entrer est ce qui tue
   l'edge » (CEF bounce, niche illiquide), en version sportive.

## Univers / basket (FIXE — déterministe, anti-cherry-pick)

Basket = **tous les matchs des 5 grandes ligues européennes de football** (E0 Angleterre, SP1 Espagne,
I1 Italie, D1 Allemagne, F1 France), **toutes les saisons 2012/13 → 2023/24 où la cote de clôture
Pinnacle existe**. ≈ 22 000 matchs, ≈ 66 000 legs (3 issues H/D/A par match). Liste figée par cette
règle — elle **inclut tous les matchs**, aucune sélection sur le résultat. Source : football-data.co.uk
(CSV gratuits, académiques) — colonnes `PSCH/PSCD/PSCA` (Pinnacle **closing** = sharp), `B365H/D/A`
(Bet365 = soft), `FTR` (résultat).

## Mesure (FIXE)

- **Proba implicite dévigée** : pour chaque match, normaliser les 3 probas implicites Pinnacle-closing
  (`1/cote`) pour sommer à 1 → estimateur « fair » sharp `p_sharp`. Le vig = somme brute − 1.
- **Courbe de biais** : bucketiser les legs par `p_sharp` (déciles / buckets de cote). Par bucket :
  winrate réalisé vs `p_sharp`. Favorite-longshot = les longshots gagnent **moins** que leur proba
  dévigée (les parieurs surpaient le ticket loterie) ⇒ direction exploitable = **parier les favoris**.
- **ROI net de vig** : ROI d'une mise à plat par bucket, calculé à la **cote réellement offerte**
  (vig inclus) — `ROI = winrate × cote − 1`. Calculé séparément (a) à **Pinnacle closing** (sharp,
  dur à battre) et (b) à **Bet365** (soft).
- **Closing-line value (CLV)** : comparer la cote soft offerte vs Pinnacle closing → parier les
  mispricings soft bat-il la clôture ?

## Gates de décision (pré-enregistrés)

- **(A) Le biais franchit le vig au prix SHARP** : sur la direction de biais documentée (parier favoris
  si longshots surcotés), **ROI net à Pinnacle closing > 0 avec t > 2**. Si ROI ≤ 0 (biais dans le vig)
  → **KILL**. *Exister dans la courbe winrate ≠ franchir le prix offert.*
- **(B) Survit à la cote de CLÔTURE (pas seulement open/soft)** : une stratégie +EV à la cote soft mais
  ≤ 0 à Pinnacle closing → **priced-in, KILL**. La clôture est le benchmark efficient.
- **(B′) Robustesse sous-période [Gate G généralisé]** : le biais doit tenir dans les **DEUX moitiés**
  temporelles (2012-2017 **et** 2018-2024). Les books se sont algorithmisés post-2018 ; si l'edge
  n'existe qu'en early-era → **priced-out, KILL** (analogue exact p12/p13 : artefact early-market,
  test sous-échantillon mûr obligatoire).
- **(C) Encaissable à un venue NON-limitant** : edge réalisable = edge à Pinnacle/Betfair (non-limitant
  mais efficient) **OU** edge soft × P(non-limité avant de scaler). Pré-enregistré : les edges soft sont
  **inencaissables à l'échelle** (gagnants limités en quelques semaines → turnover réalisé plafonné).
  Si le seul +EV est aux books soft → **DOWNGRADE/KILL (inencaissable)**.
- **(D) Matérialité / seuil de labeur** (ledger EV, comme airdrop #14) : même si un petit edge survit,
  EV par unité de turnover et **EV/heure** de line-shopping + gestion de comptes. Hurdle pré-enregistré :
  edge net > **2 % du turnover** (pour franchir le vig effectif + limites réalistes) **ET**
  EV/heure > **15 €/h**. Sinon **DOWNGRADE** (réel mais pas worth-it).

## Décision pré-enregistrée

- **(A) ∧ (B) ∧ (B′) ∧ (C) ∧ (D) ⇒ GO** : premier edge à contrepartie bête du programme — projet
  opérationnel séparé. **Chasse au mirage obligatoire** (vérifier que ce n'est pas 1 ligue / 1 saison /
  1 bookmaker qui porte tout = leçon meme-coin, funding-XS, CEF).
- **(A) ∧ (B) ∧ ¬(C ∨ D) ⇒ DOWNGRADE** : biais réel mais inencaissable au venue non-limitant, ou
  sous le seuil → pas worth-it pour l'objectif.
- **¬(A) ∨ ¬(B) ∨ ¬(B′) ⇒ KILL** : biais dans le vig, priced-in à la clôture, ou early-era only.

## Falsifiabilité (comment ça meurt)

1. ROI direction-favoris ≤ 0 à Pinnacle closing → KILL (A). 2. +EV soft mais ≤ 0 à la clôture → KILL (B).
3. Edge en 2012-2017 mais mort en 2018-2024 → KILL (B′). 4. +EV seulement aux books qui bannissent →
DOWNGRADE inencaissable (C). 5. Edge < 2 %/turnover ou EV/h < 15 € → DOWNGRADE (D).
6. Tout l'edge porté par 1 ligue / 1 saison → mirage (chasse obligatoire).

## Données & implémentation

- **Source** : football-data.co.uk, CSV par (saison, ligue), colonnes Pinnacle-closing + Bet365 + FTR.
  Gratuit, déterministe, cache local (gitignoré, régénérable).
- **Sortie** : `data.py` (fetch + parse), `bias.py` (courbe + ROI net), `run_sportsbook.py`
  (gates A-D + verdict), `docs/FINDINGS.md`.

## Verdict attendu a priori

Le biais favorite-longshot est **réel** (50 ans de littérature) — et c'est le seul étang à contrepartie
bête. Mais le programme prédit la mort en **(A)** (le biais vit dans le vig : réel dans la courbe
winrate, ≤ 0 au prix sharp offert) ou en **(C)** (la portion qui dépasse le vig n'existe qu'aux books
soft qui te bannissent). La seule façon que ça survive : un ROI **net positif, t > 2, dans les deux
moitiés temporelles, à la cote de clôture Pinnacle** — un book sharp qui laisse de l'argent sur la
table de façon systématique et capturable. Le motif unifié du programme rend ça improbable, mais
l'étang est **authentiquement neuf**, donc le test est informatif quel que soit le verdict.

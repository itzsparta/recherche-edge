# Piste 2 — Flux forcés : token unlocks (cliff) — pré-test (PRÉ-ENREGISTRÉ)

> Écrit **avant** tout code et tout résultat. Critères figés ici ; les modifier après
> avoir vu un chiffre = overfit, interdit. Discipline héritée d'orderflow/factor-harvest.

## Thèse

Un **cliff unlock** (libération discrète de tokens vestés à date connue) crée un
**vendeur forcé** (équipe/VC/investisseurs qui encaissent) → pression baissière
**anormale** (au-delà du marché) autour de l'unlock. On veut savoir si cette pression
est réelle, robuste, et **capturable net** (= shortable).

## Données (gratuit, vérifié 2026-06-21)

- **Calendrier unlocks** : DefiLlama datasets CDN (API emissions principale = payante 402,
  mais le CDN est libre). Liste : `…/emissionsProtocolsList` (338 protocoles). Détail :
  `…/emissions/{slug}` → `metadata.events` = events discrets avec `timestamp`,
  `noOfTokens`, `category`, **`unlockType`** ("cliff" vs linéaire) ; `gecko_id` ;
  `unlockUsdChart` ; `supplyMetrics`.
- **Prix + supply** : CoinGecko via `gecko_id` (gratuit). Marché = BTC (facteur).

## Définition de l'événement (FIXE)

- Garder uniquement `unlockType == "cliff"` (choc discret ; le vesting linéaire est
  continu → pas un event mesurable).
- **Taille** = valeur USD de l'unlock / market cap à T−1 (proxy pression). Quartiles de
  taille pré-spécifiés pour le test dose-réponse.
- Exclure events où le prix/supply CoinGecko manque sur la fenêtre.

## Mesure — CAR MARKET-ADJUSTED (leçon étage-1, NON négociable)

Mesurer le rendement **anormal**, jamais le brut (sinon on remesure le drift crypto qui
a tué fade-vers-value).

- Fenêtre événement : **[−10, +10]** jours autour de T0 (date du cliff).
- Rendement anormal journalier `AR_t = r_token,t − r_BTC,t` (excès marché, β=1 en base ;
  β estimé sur [−60,−11] en robustesse).
- `CAR = Σ AR_t` sur la fenêtre. Sous-fenêtres pré-spécifiées : pré [−10,−1],
  événement [−1,+1], post [+1,+10] (sépare priced-in / choc / dérive).

## Critères PRÉ-ENREGISTRÉS

### (A) L'effet existe — TOUT requis
- CAR moyen (fenêtre post ou événement) **< 0**, **t < −2**.
- **Dose-réponse** : quartile de plus grosse taille plus négatif que le plus petit.
- **Majorité des années négatives** (pas un millésime unique).
- **Pas porté par une poignée de tokens** : robuste en winsorisant / drop-top-5 events.
- **DSR** sur les variantes testées (fenêtres × β) > 0.95 (déflation multi-essais).

### (B) Capturable net — au moins le cœur requis
- L'effet **survit sur le sous-ensemble SHORTABLE** (tokens avec perp Binance/Bybit) —
  le vrai tueur pratique : un small-cap sans perp/borrow = edge intradeable.
- **Net de coûts short** (funding perp + frais ~taker) reste < 0.
- Assez d'events/an sur l'univers shortable pour que ça compte.

## Décision pré-enregistrée

- **(A) ∧ (B) ⇒ GO** (protocole complet).
- **(A) ∧ ¬(B) ⇒ KILL-pour-l'objectif** : effet réel mais intradeable (pas de short) =
  pas un edge récoltable solo. Documenter.
- **¬(A) ⇒ KILL** : pas d'effet anormal robuste (priced-in / décayé / bruit).

## Tueurs anticipés (à ne pas sur-interpréter)

- **Priced-in** : dates connues → effet pourrait être dans [−10,−1] (anticipé) ou absent
  à T0. La décompo pré/event/post le révèle.
- **Décroissance/crowding** : « short l'unlock » est un meme connu → tester par année.
- **Buy-the-news** : reversal haussier post-unlock possible (sell-rumor-buy-news).
- **Survivorship** : les 338 protocoles DefiLlama = survivants à schedule documenté →
  biais vers tokens « réussis ». À flagger, ne pas généraliser aux morts-nés.

## Implémentation

- Projet `code python/forced-flows/`, réutilise `audit.py` (DSR/PBO) de factor-harvest.
- Data via `urllib` stdlib (DefiLlama CDN + CoinGecko), cache `data/`. Fetch parallèle
  (threads). Pandas/numpy pour CAR cross-sectionnel.
- Sortie : verdict console + `docs/FINDINGS-unlocks.md` au format orderflow/meme.

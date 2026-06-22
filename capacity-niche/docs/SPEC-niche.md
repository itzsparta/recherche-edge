# Piste 3 — Niche contrainte en capacité : spreads cross-exchange small-caps (PRÉ-ENREGISTRÉ)

> Écrit **avant** tout code/résultat. Critères figés ici ; les modifier après avoir vu un
> chiffre = overfit, interdit. Discipline héritée d'orderflow/factor-harvest/forced-flows.

## Thèse (différente des pistes 1-2)

Pistes 1-2 mortes car **déclencheur public** (signal/date connus → arbitrés). Ici l'edge ne
repose **pas** sur une info cachée mais sur la **capacité** : un mispricing cross-exchange sur
un small-cap est **trop petit pour qu'un fonds le récolte** (friction opérationnelle : custody
multi-venue, retraits, taille plafonnée à quelques $k). C'est la **seule arme structurelle d'un
solo** — un desk gérant $100M ne peut pas déployer sur un edge plafonné à $20k.

Question du scan : un spread cross-exchange **exécutable net** existe-t-il sur les small-caps
co-listés, **persiste-t-il sur des minutes** (régime capturable par un solo), et **quelle
capacité $** ? On répond **avant** toute custody/infra multi-venue.

## Régime ciblé (NON négociable)

On ne chasse **que** les mispricings **persistants sur minutes**. Le sub-seconde appartient au
HFT colocalisé — un solo retail ne peut pas le capturer. Donc : snapshots espacés (~60 s),
mesure de **persistance** sur ~20-30 min. Un edge solo-capturable = positif net sur plusieurs
snapshots consécutifs ; un artefact (quote périmée, flicker) = positif ponctuel non reproductible.

## Données (gratuit, vérifié 2026-06-21)

- 3 venues, REST public sans clé : **Binance** (`/api/v3/ticker/bookTicker`, 3603 paires, 0.4 s),
  **MEXC** (même API clonée, 2345 paires, 0.1 s), **Gate** (`/api/v4/spot/tickers`, 2196 paires,
  `highest_bid`/`lowest_ask` + `quote_volume`). 1 call = best bid/ask de **tous** les symboles.
- Volume 24 h (proxy liquidité/capacité) : Gate dans tickers ; MEXC/Binance via `/ticker/24hr`
  (one-shot au début, volume bouge lentement).
- Profondeur (capacité réelle) : `/depth` par paire, seulement pour les paires qui passent (A).

## Définitions (FIXES)

- **Univers** : toutes paires quote USDT **co-listées** sur Binance ∩ (MEXC ∪ Gate). Aucune
  exclusion (les mega-caps servent de contrôle : spread attendu ≈ 0 = sanity check).
- **Spread exécutable round-trip** (par snapshot, par paire) : acheter au `min(ask)` sur les
  venues, vendre au `max(bid)` sur les venues. `net = (max_bid − min_ask)/mid − 2·fee`.
  Ne compte que si **venue(max_bid) ≠ venue(min_ask)** (vrai cross-venue, pas un spread intra-book).
- **fee** = **0.10 %/jambe** taker (pré-enregistré, conservateur ; certaines venues moins avec
  token discount, mais petit compte = tarif liste).
- **Modèle de coût = inventaire pré-positionné** (capital sur les 2 venues, **pas de retrait par
  trade** ; on capture en achetant/vendant contre des soldes pré-financés). C'est le **meilleur
  cas** (zéro drag de transfert). Si même le meilleur cas meurt → KILL a fortiori. Si ça passe →
  le coût transfert/inventaire/capital devient le **gate suivant** (hors scan cheap).
- **Bucket liquidité** = `quote_volume` 24 h de la **petite** venue (Gate/MEXC) participant au
  cross (la jambe qui plafonne la capacité). Quartiles.
- **Capacité $** : pour les paires (A)-positives, marcher le carnet (`/depth`) côté petite venue
  → $ exécutable avant que le net retombe à 0 (slippage + fees). Qty top-of-book = proxy plancher.

## Critères PRÉ-ENREGISTRÉS

### (A) Le spread existe ET est solo-capturable — TOUT requis
- **Persistance** : ≥ **20** paires avec net > 0 sur **≥ 60 %** des snapshots (positif reproductible,
  pas un flicker de quote périmée).
- **Dose-réponse structurelle** : net médian **plus grand dans le quartile de plus basse liquidité**
  que dans le plus haut (signature « trop petit pour un fonds », pas du bruit uniforme).
- **Pas porté par 1-2 paires** : robuste en retirant le top-3 paires par net moyen.

### (B) La capacité vaut le coup — cœur requis
- $ exécutable agrégé au net > 0 (après slippage carnet + fees) sur les paires qualifiées
  ≥ **2 000 $ par cycle** (seuil pré-enregistré : déployable, pas un jouet à 50 $).
- Assez de paires qualifiées simultanément pour diversifier (≥ 10).

## Décision pré-enregistrée

- **(A) ∧ (B) ⇒ GO** — seule piste vivante ; passer au gate transfert/inventaire puis protocole complet.
- **(A) ∧ ¬(B) ⇒ KILL-trop-petit** — spread réel mais capacité jouet = **le piège piste-3 prédit**.
  C'est un résultat, pas un échec : confirme que l'edge survit *parce que* trop petit pour compter.
- **¬(A) ⇒ KILL-pas-de-spread** — même les small-caps sont arbitrés au top-of-book / seulement
  du flicker périmé non capturable par un solo.

## Tueurs anticipés (à ne pas sur-interpréter)

- **Quote périmée** : top-of-book d'une venue illiquide peut être un dernier prix non hittable →
  filtre persistance + check profondeur atténuent, mais le scan ne peut pas le tuer à 100 % sans
  exécution live. Flaggé.
- **Top-of-book minuscule** : spread réel mais sur 20 $ → c'est exactement le gate (B).
- **Token non retirable** : dépôt/retrait suspendu sur la petite venue → l'inventaire pré-positionné
  suppose qu'on a pu le poser une fois ; flaggé.
- **Async des snapshots** : 3 venues fetchées en ~2-3 s ; on ne compare qu'à l'intérieur d'un snapshot
  serré. Le sub-snapshot n'est de toute façon **pas** la cible (régime minutes).
- **Frais réels** : 0.10 %/jambe pré-enregistré ; un compte plus gros paierait moins (fragile vers le
  GO, pas vers le KILL).

## Amendement (2026-06-21, post-sanity 1-shot, AVANT le run de persistance)

Le sanity 1-shot a révélé un artefact de **collision de ticker** : un même symbole (ex. « ELON »,
« VON ») désigne des **tokens différents** selon la venue → faux spread de +199 %. La persistance ne
les tue pas (2 tokens distincts gardent leurs prix). Ajout de 2 filtres de **validité données**
(principe marché a priori, **pas** des seuils de décision — les gates A/B ci-dessus restent
**inchangés**) :

- **`gross > 5 % ⇒ rejet`** : aucun vrai arbitrage cross-venue ne laisse 5 %+ debout sur des minutes
  (serait pris instantanément) → collision de ticker / quote gelée / marché halté.
- **`volume petite-venue < 1 000 $/24 h ⇒ rejet`** : marché mort, quote non hittable.

Justification anti-overfit : ces filtres **retirent du faux edge** (sens conservateur), ils ne peuvent
pas en fabriquer. Sans eux, le junk +199 % passerait (A) → faux GO.

## Implémentation

- Projet `code python/capacity-niche/`, réutilise le pattern `audit.py`. Data via `urllib` stdlib,
  cache `data/snapshots/`. Collecteur background (~25 snapshots × 60 s). Pandas/numpy pour l'analyse.
- Sortie : verdict console + `docs/FINDINGS-niche.md` au format orderflow/meme/unlocks.

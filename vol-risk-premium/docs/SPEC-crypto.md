# SPEC — Piste 12 : Crypto VRP en **defined-risk** (pré-enregistré)

> Écrit **avant** tout chiffre. Protocole partagé `RESEARCH-ROADMAP.md` : hypothèse + règle +
> critère de succès ET de kill fixés avant de voir le moindre résultat. (Leçon orderflow/VRP.)
> Enfant direct de la **Piste 4 (VRP actions, DOWNGRADE)** — relire [`FINDINGS.md`](FINDINGS.md)
> avant d'attaquer celle-ci.

## Ce que la Piste 4 a déjà tranché (ne pas le re-tester)

Le VRP **existe** (vol implicite > réalisée) est un fait établi, actions comme crypto. La Piste 4
l'a confirmé (t=4.03) puis **DOWNGRADE** non pas parce que le premium était trop mince, mais parce
que le **véhicule de récolte a un tail catastrophique** (SVXY −95 %, −83 % en un jour) et que le
Sharpe est aveugle au skew. Le FINDINGS Piste 4 a explicitement laissé **une seule porte ouverte**
(lignes 79-81) :

> « La seule forme solo-viable = short-vol à **risque défini** (spreads d'options) qui plafonne le
> −95 %. Mais le hedge **mange aussi la prime** → EV résiduelle vraisemblablement mince. »

**Cette piste teste exactement cette porte, là où elle a la meilleure chance de s'ouvrir : la crypto.**

## Hypothèse d'edge (distincte de la Piste 4)

Le VRP crypto (BTC/ETH) est en **points de vol absolus** beaucoup plus gros que l'actions
(gap DVOL−réalisée historiquement ~10-25 pts vs ~4 pts sur le SPX). Hypothèse : ce premium est
**assez gros pour qu'une structure short-vol à risque défini** (strangle/straddle vendu, couvert
par des ailes OTM longues → perte max bornée) **garde une EV nette positive et worth-it
APRÈS le coût des ailes** — ce que l'actions ne permettait pas (4 pts − ailes ≈ 0).

Les **deux** conditions de la Piste 4 restent requises, re-spécifiées pour la crypto :
- **(A)** le premium existe ET est **matériellement plus gros** que l'actions (sinon : aucune raison
  de porter un tail crypto pire pour la même prime → rien de neuf).
- **(B)** une fois **plafonné en defined-risk** et net du coût réel des ailes, ça bat un BTC buy-hold
  en risk-adjusted, tail-inclus.

## Le null honnête (= verdict attendu a priori)

**La peur du krach qui gonfle le premium gonfle AUSSI l'aile.** Le VRP crypto est gros précisément
parce que le marché paie cher la protection contre les −50 % (skew downside violemment bid). Or
c'est exactement la put-wing OTM qu'on doit **acheter** pour borner le risque. Donc le premium fat
et le coût de l'aile fat ont **la même source** → ils risquent de se **neutraliser** → net mince →
**DOWNGRADE, même mort que la Piste 4** (motif friction #2 du programme), juste déplacée du tail
nu vers le coût du hedge.

Le null secondaire : naked short-vol crypto est un **−100 % évident** (BTC a fait −50 % en une
séance : mars-2020, mai-2021, FTX nov-2022) — donc on **n'évalue jamais** la forme nue ; elle est
hors-spec d'office. Seul le defined-risk est sur la table.

## Univers (FIXE — aucun cherry-pick)

- **Implicite** : indice **DVOL** Deribit (vol implicite 30 j, annualisée, %) pour **BTC** et **ETH**.
  Analogue crypto du VIX. Source publique gratuite (API Deribit).
- **Sous-jacent / réalisée** : spot **BTC-USD**, **ETH-USD** (pour la variance réalisée 30 j).
- **Benchmark passif** : **BTC buy-hold** (le « worth-it » bar, équivalent du SPY de la Piste 4).

Échantillon = **tout l'historique DVOL commun** (BTC ~2021-03 →, ETH plus tard). Couvre par
construction : **bull 2021, krach −50 % mai-2021, bear 2022 (LUNA / 3AC / FTX), reprise 2023,
bull 2024, 2025**. **Aucune exclusion de krach** (mensonge canonique du short-vol).

> **Caveat puissance pré-enregistré.** ~5 ans → **~60 points mensuels non-chevauchants** (vs 436
> sur l'actions). n petit ⇒ barre t-stat plus dure à franchir et **DSR plus punitif**. On
> l'accepte : un premium qui n'est pas franc sur 60 mois multi-régime n'est pas worth-it.

## Phase 0 — mesure du premium (FIXE)

- **Implicite** : `IV_vol_t = DVOL_t / 100` (décimal annualisé), `IV_var_t = IV_vol_t²`.
- **Réalisée forward** : sur les **h = 30 jours calendaires** suivant `t` (horizon du DVOL ;
  crypto trade 365 j/an), `RV_var_t = 365/h · Σ_{i=1..h} r_{t+i}²`, `r = Δln(spot)`.
  `RV_vol_t = √RV_var_t`. h = 30 **pré-spécifié**, pas de tuning.
- **Premium** : `VRP_var_t = IV_var_t − RV_var_t` (>0 = prime au vendeur),
  `VRP_vol_t = DVOL_t − 100·RV_vol_t` (points de vol).
- **Échantillonnage** : **mensuel non-chevauchant** (fin de mois, fenêtre forward 30 j). Évite
  l'autocorrélation qui gonfle le t. BTC et ETH analysés séparément + poolés démoyennés.

## Phase 1 — récolte synthétique provisoire (FIXE, free-data)

Comme la Piste 4 : P&L mensuel d'un short-vol vega-flat en points de vol, **mais avec un coût
pré-enregistré nettement plus lourd** pour internaliser (a) les spreads d'options crypto larges et
(b) une **provision d'aile** (le defined-risk de la Phase 2) :

- `pnl_t = VRP_vol_t − coût`.
- **Coût pré-enregistré = 3.0 points de vol / mois** (round-trip bid-ask Deribit + provision
  d'aile OTM, conservateur ; cf. spreads crypto 5-15 % du premium sur les OTM).
- On reporte **AUSSI le break-even cost** (le coût qui annule l'EV) — honnêteté, comme la Piste 8.
- **Sizing honnête** : vega-notional constant **1×**, zéro levier empilé (leçon Piste 1 : le sizing
  levé a renversé un faux GO).

> La Phase 1 est **provisoire** : elle borne le premium net mais **ne prouve pas** le defined-risk
> (qui exige la surface d'options réelle). C'est l'équivalent du `run.py` actions ; la preuve tail
> réelle = Phase 2, l'équivalent de `stress.py`/SVXY.

## Gates de décision (pré-enregistrés)

### Gate A — le premium existe ET est FAT (Phase 0/1, ce run) — TOUT requis

- `mean(VRP_var) > 0` ET `t-stat > 2` sur le mensuel non-chevauchant (BTC ; ETH en confirmation).
- **Barre de magnitude (le neuf vs actions)** : `mean(VRP_vol) > 8.0 points de vol` (l'actions
  faisait +4.07). En-dessous → le premium crypto n'est **pas matériellement plus gros** → aucune
  raison de porter un tail pire → **KILL « crypto n'apporte rien »**, sans aller en Phase 2.
- **Majorité des régimes positifs** (bull-2021 / krach-mai-2021 / bear-2022 / reprise-2023 /
  bull-2024 / 2025). Les régimes négatifs attendus = les krachs (signature assurance, pas edge).
- **DSR(best, n_trials sur h ∈ {21, 30, 45})** > 0.95 — diagnostic, jamais pour sélectionner.

### Gate B — worth-it en defined-risk, tail-inclus — TOUT requis

- **Net Phase 1 > 0 ET t-stat(pnl net) > 2** au coût pré-enregistré de 3 pts/mois (si le premium
  fat ne survit même pas à la provision d'aile forfaitaire → DOWNGRADE direct, pas besoin de Phase 2).
- **Sharpe net annualisé > Sharpe BTC buy-hold** sur la même fenêtre.
- **Miroir** : long-vol (signe inversé) doit **perdre** (sinon le premium n'est pas la source du P&L).
- **Phase 2 (data-gated, seulement si A ∧ pré-B Phase-1 passent)** : construire le **vrai
  iron-condor / strangle-couvert** sur surface d'options Deribit historique (Laevitas/Tardis si
  accessible, sinon skew modélisé), perte max **bornée par construction**, net des **spreads
  réels des ailes**. PASS = net > 0 worth-it après le coût réel du hedge (≠ la provision forfaitaire).

## Décision pré-enregistrée

- **(A) ∧ (B) ⇒ GO** vers protocole complet (surface réelle, walk-forward, paper). Ce serait le
  **premier GO ferme du programme** — donc chasse au mirage post-GO **obligatoire** (leçon CEF :
  un t élevé peut être aveugle au bounce/friction).
- **(A) ∧ ¬(B) ⇒ DOWNGRADE** : premium réel et fat, mais l'aile (Phase 2) ou la provision (Phase 1)
  le mange → **même mort que la Piste 4, déplacée tail→hedge**. **Verdict le plus probable.**
- **¬(A) ⇒ KILL** : soit premium absent (implausible), soit **pas plus gros que l'actions** (barre
  8 pts ratée) → crypto n'apporte aucune raison neuve.

## Falsifiabilité (comment ça meurt)

1. `mean(VRP_vol) ≤ 8 pts` → KILL Gate A (crypto = actions, rien de neuf).
2. Premium fat mais net Phase-1 ≤ 0 à 3 pts/mois → DOWNGRADE (provision d'aile mange tout).
3. Premium fat, net Phase-1 > 0, mais Phase-2 sur ailes réelles ≤ 0 → DOWNGRADE (skew downside
   rend la put-wing trop chère = le null central).
4. Net > 0 partout mais porté par un seul régime (ex. bull-2021) → KILL non-répétabilité (leçon LST).

## Données & implémentation

- **Source implicite** : Deribit `GET /api/v2/public/get_volatility_index_data`
  (`currency=BTC|ETH`, `resolution=1D`), gratuit, public. Cache CSV local `data/`.
- **Source spot** : `BTC-USD`, `ETH-USD` via le pattern `data.py` existant (yfinance), ou klines
  Binance déjà ingérées ailleurs.
- **Audit** : `audit.py` (DSR Bailey-López de Prado) porté **tel quel** depuis ce dossier.
- **Sortie** : `run.py` (Phase 0/1 + gates) + `stress.py` (Phase 2 / tail réel), verdict console +
  `docs/FINDINGS-crypto.md` au format orderflow/meme/factor. Index global à mettre à jour.

## Verdict attendu a priori

Prior bas (12 kills). Gate A devrait **passer** (le VRP crypto est documenté large). Le vrai combat
= Gate B, et le tueur le plus probable est le **null central** : le skew downside qui fait la
grosseur du premium fait aussi la cherté de l'aile → net mince → DOWNGRADE. La question pré-enregistrée,
seule raison de dépenser ce run cheap : **le premium crypto est-il assez gros, en absolu, pour
qu'il reste quelque chose APRÈS avoir payé l'aile ?** L'actions disait non (4 pts). La crypto a
~3-5× plus de premium brut — c'est le seul endroit du programme où le defined-risk a une vraie
chance. Cheap à falsifier en Phase 1 (data DVOL gratuite).

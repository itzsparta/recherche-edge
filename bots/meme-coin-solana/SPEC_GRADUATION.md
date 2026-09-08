# Pré-enregistrement — Piste 1 : edge de graduation pump.fun

**Statut : figé AVANT extraction. Toute modification postérieure à la vue d'un
chiffre doit être datée, justifiée et comptée dans le budget de tests (DSR).**

Date de gel : 2026-09-07. Auteur : Rémi. Contexte : succède au KILL t0
(`FINDINGS.md`, 2026-06-19) dont le mécanisme était le péage ~40 % round-trip.

## Hypothèse

Il existe une anomalie de continuation exploitable dans les minutes qui suivent
la mise en ligne du pool post-graduation d'un token pump.fun.

**Raison d'y croire — une seule, et ce n'est pas le signal :** le péage
s'effondre d'un ordre de grandeur (pool à liquidité réelle vs bonding curve).
Le breakeven passe d'environ 36,5 % à environ 14 % de win-rate. Prior sur le
signal lui-même : mauvais (événement public, bots Rust devant nous).

## Ancrage temporel (corrigé après vérification du schéma Dune)

- `pump_evt_completeevent` = courbe complétée. **Ce n'est PAS le moment tradable.**
- `pump_amm_evt_createpoolevent` / `pump_evt_completepumpammmigrationevent` = pool
  PumpSwap live. **C'est l'ancre d'entrée.**
- Entre les deux : fenêtre non tradable, de durée à mesurer (probe Q2).
- Le trigger `initialize2` + `RAYDIUM_LP_V4` de `event_parser.py:254` est obsolète
  pour cette piste et doit être remplacé par l'ancre pool PumpSwap.

## Modèle de coût — MESURÉ, pas supposé

Le point non négociable : la thèse entière repose sur l'effondrement du péage.
Poser un slippage de 1,5 % en constante, c'est supposer la conclusion.

1. **Slippage** : calculé par trade en produit constant à partir des réserves
   réelles (`pool_base_token_reserves` / `pool_quote_token_reserves`, présentes
   sur chaque `buyevent`/`sellevent`). Jamais une constante de config.
2. **Frais** : barème réel on-chain à **trois jambes** — `lp_fee_basis_points`
   + `protocol_fee_basis_points` + `coin_creator_fee_basis_points`. Le 0,25 %
   Raydium de `core.py:12` ne s'applique pas ici.
3. **Priority fee / tip Jito** : le bloc de migration est le plus disputé de la
   vie du token. Interdit d'utiliser un tarif de marché calme. À défaut de
   mesure, stress-test explicite.
4. `execution_type: "LIMIT"` reste **banni** (branche `core.simulate_buy` qui
   annule slippage + priority + tip).
5. **Sensibilité obligatoire** : à quel niveau de coût total l'edge meurt ?
   Si la réponse est « 2 % », la thèse est morte en pratique même si le t-stat passe.

## Entrée — latence balayée, pas choisie

On ne suppose pas être premier. Entrée mesurée à plusieurs décalages depuis le
pool live : **+0 slot, +1 slot, +5 s, +30 s, +120 s**. Résultat rapporté comme
une courbe.

> Si l'edge n'existe qu'à +0 slot, il n'est pas à nous : il appartient aux bots
> Rust. Ce cas compte comme un KILL, pas comme un PASS.

## Variable de conditionnement (fusion de la piste 3)

**Une seule variable, un seul degré de liberté** : nombre d'acheteurs uniques
sur la courbe **strictement avant** `completeevent` (`pump_evt_tradeevent`,
filtre `block_slot < slot_complete` — pas `block_time`, pour éviter la fuite
intra-bloc).

Découpage **binaire à la médiane de l'échantillon**. Pas de seuil « 40 », pas de
ratio buy/sell 3:1, pas de dev-holdings 10 % : quatre seuils libres = machine à
overfitter, déjà réfutée par le sweep FDV en quartiles.

Si un balayage de seuils est fait malgré tout, DSR obligatoire sur N tests.

## Miroirs — trois, pas un

1. **Naive** : même trade, SL/TP désactivés, sortie au time-stop seul → isole la
   mécanique de sortie.
2. **Buy-and-hold** du même token sur la fenêtre → isole la dérive du token.
3. **Placebo temporel** (ajouté) : même token, entrée décalée à pool+30 min.
   → isole **l'événement**. Si le placebo fait aussi bien, la graduation
   n'apporte aucune information : on a seulement sélectionné de bons tokens.
   C'est le miroir qui falsifie réellement l'hypothèse.

## Régimes (MAJ : 2026-09-07)

Suite à l'analyse de volumétrie, les moyennes mensuelles masquaient la structure des données (pics d'activité locaux). Les fenêtres de régime exigent une stabilité interne (homogénéité du nombre de graduations/jour) et un contraste maximal entre elles (facteur 20x).

Les trois régimes validés pour l'ère PumpSwap sont :
1. **BAS** : 25 juillet → 4 août 2025 (~25 graduations/jour, n=~277).
2. **MOYEN** : 4 jours espacés dans avril 2025 (~300 graduations/jour, n=~1400).
3. **HAUT** : 4 jours dans le pic du 11-20 mars 2026 (~510 graduations/jour, n=~2100).

Ces 19 jours cumulés fournissent le plancher statistique requis (n >= 200 par régime) tout en limitant le temps de scan (optimisation coût/crédits) et en évitant qu'un artefact d'une seule journée ne fausse un régime entier.

## Gate de décision — figée

PASS exige **tout** :

- `brut > 0`
- `t > 2` (ddof=1)
- moyenne positive **dans chacun des 3 régimes**
- `net > 0` après coût mesuré (pas supposé)
- `bat le miroir naive` **et** `bat le placebo temporel`
- `n >= 200 par régime`
- edge survivant à **au moins +1 slot** de latence

### Note sur le plancher n

`n >= 30` (formulation initiale) est **trop bas ici** et a été relevé. Justification :
n n'est pas la contrainte sur cette piste — les graduations se comptent en
dizaines/centaines par jour (à confirmer, probe Q4). Un plancher bas
n'achèterait rien et laisserait passer un run mince. Serrage dans le sens
difficile, conforme à `feedback_gate_override`.

Tout échec sur un seul critère = **KILL**, documenté dans `FINDINGS.md`.

## Ordre d'exécution

1. `sql/probe_graduation_calibration.sql` — 4 inconnues (endianness, délai
   courbe→pool, barème de frais réel, volumétrie). Coût : une requête.
2. `sql/verdict_graduation.sql` — extraction, écrite **après** la probe.
3. Adaptateur → `backtester.py` → `verdict.py`.
4. Aucune ligne de bot live avant un PASS.

## Piste 2 (smart money) — non démarrée

Bloquée derrière un seul pré-test de persistance : formation 30j → holdout 30j
disjoint, le décile supérieur a-t-il une espérance > 0 en holdout ? Aucune ligne
de bot copytrade avant cette réponse.

Bug connu à corriger avant tout usage de `sql/smart_money.sql` : le PnL y est un
différentiel de flux sur fenêtre (`usd_cashed_out - usd_invested`), qui
sélectionne les **vendeurs nets** de la fenêtre, pas les traders habiles.

---

# Calibration mesurée — 2026-09-07

Sonde exécutée sur Dune (queries 8636809 / 8636818), fenêtre 2026-06-01 → 06-08.
`sql/probe_graduation_calibration.sql` fige la version qui a tourné.

## Pièges de schéma (3 échecs avant succès — tous instructifs)

1. Colonnes bloc/tx **préfixées `evt_`** (`evt_block_date`, `evt_block_time`,
   `evt_block_slot`). Le catalogue MCP les annonce sans préfixe : **faux**.
   Déjà documenté dans `FINDINGS.md`, re-confirmé.
2. Les montants sont **déjà en `uint256`**, pas en `varbinary`.
   `bytearray_to_uint256()` échoue dessus. **La question Q1 (endianness) était
   sans objet** — il n'y a rien à décoder.
3. La CTE frais doit filtrer `quote_mint = SOL`. Sans ce filtre, les pools à
   quote non-SOL (décimales différentes) polluent : clip médian lu à **1716 SOL**
   au lieu de **0,14 SOL**. Retenir : toute métrique de montant doit être
   restreinte au quote SOL avant lecture.

## Résultats

| Mesure | Valeur | Conséquence |
|---|---|---|
| Graduations / 7 j | **1 426** (~204/jour) | `n >= 200`/régime trivialement atteint. n n'est pas la contrainte. |
| Appariement `completeevent` → `createpoolevent` | **1426 / 1426, 0 orpheline** | Jointure sur `base_mint` propre, 1:1. |
| Délai courbe → pool | **p50 = 1 s, p90 = 3 s, max = 8 s** (~2,3 slots) | **Correction de spec** : la fenêtre morte est négligeable, pas de plusieurs minutes. |
| Profondeur du pool à la création | **médiane 84,99 SOL**, p10 31,6 SOL | Constante de protocole. ~12,7 k$ — cohérent avec l'hypothèse initiale. |
| Réserve SOL médiane (tous swaps) | 140,9 SOL, p10 55,6 SOL | Les pools s'épaississent après création. |
| Barème de frais réel | **lp 25 bps + protocol 5 bps + creator 0 bps = 30 bps / jambe** | Le 0,25 % Raydium ne s'applique pas. `amm_fee_pct = 0.0030`. |
| Clip médian réel (cohorte SOL) | **0,14 SOL** (p90 = 1,34 SOL) | Un clip de 0,5 SOL nous place entre médiane et p90 : participant normal, pas outlier. |
| Graduations à quote non-SOL | 47 / 1426 (3,3 %) | À exclure de l'univers. |
| Program id PumpSwap | `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA` | Trigger live pour `event_parser.py`. |

## Le péage, chiffré

Pour un clip de 0,5 SOL sur un pool de 85 SOL, en produit constant :

- slippage ≈ 0,5 / 85,5 = **0,59 %** par jambe (0,89 % dans le décile mince à 55 SOL)
- frais = **0,30 %** par jambe
- **round-trip ≈ 1,8 %** (≈ 2,4 % décile mince)

**Contre ~40 % à t0 : facteur ~22.** La reformulation « l'edge est dans le
péage » est **confirmée quantitativement**, plus seulement plausible.

Le terme de coût cesse d'être dominant : il passe d'environ 0,170 SOL par
round-trip (≈ la perte moyenne mesurée en juin) à environ 0,009 SOL. La thèse
tient désormais entièrement sur le comportement réel des prix — ce qui est
exactement le but.

## Coût encore NON mesuré — le seul trou

**Priority fee + tip Jito.** Non mesurés par cette sonde. Le délai courbe→pool
étant de ~2 slots, la course est extrêmement serrée et ces frais y sont
disputés. Ordre de grandeur : 0,002 SOL sur un clip de 0,5 SOL = **0,4 %**,
soit potentiellement autant que frais + slippage réunis.

→ Tant qu'ils ne sont pas mesurés, le péage annoncé de 1,8 % est un **plancher**,
pas une estimation. Le test de sensibilité de la spec devient obligatoire, pas
optionnel.

## Modifications de spec induites

- **Fenêtre morte** : négligeable (~1 s). L'ancre d'entrée reste le pool, mais
  l'écart avec `completeevent` ne justifie plus de traitement particulier.
- **Balayage de latence** : inchangé et plus pertinent que jamais. Avec un pool
  live ~2 slots après la fin de courbe, les décalages +0/+1 slot sont la zone
  des bots Rust. Un edge qui n'existe que là compte comme **KILL**.
- **Slippage par trade** : `core.simulate_buy/sell` prend `strat.slippage_pct`
  (constante). Le calcul par trade sur `pool_quote_token_reserves` exige de
  passer le slippage en argument. Changement de signature à faire à l'étape
  extraction. La valeur en config est un **provisoire explicitement marqué**.

---

# Régimes — PREMIÈRE VALIDATION INVALIDÉE, refaite

## Ce qui s'est passé

Les trois fenêtres (avril-2025 / août-2025 / mars-2026) ont d'abord été validées
sur des **agrégats mensuels**. Cette validation est **fausse** : la moyenne
mensuelle masquait la structure quotidienne.

Distribution quotidienne des graduations (Dune 8637122 / 8637127) :

| Fenêtre | Structure réelle |
|---|---|
| avril 2025 | 183-409/j, variation continue, **homogène** ✅ |
| août 2025 | **rupture le 5 août** : ~25/j du 25 juil au 4 août, puis ~175/j jusqu'au 31. Deux régimes collés ❌ |
| mars 2026 | ~285/j, **pic du 11 au 20** (450-656/j), puis retour à ~290. Non homogène ❌ |

**Leçon** : le mois est la mauvaise unité. L'activité bouge sur une échelle de
~10 jours. Un régime doit être défini par une **fenêtre mesurée homogène**, pas
par le calendrier.

## Régimes refaits — trois niveaux d'activité, chacun homogène

| Régime | Fenêtre | Activité | n attendu |
|---|---|---|---|
| **BAS** | 2025-07-25 → 2025-08-04 | ~25 grad/j | ~277 |
| **MOYEN** | 4 jours espacés dans avril 2025 (8, 15, 22, 29) | ~300 grad/j | ~1 400 |
| **HAUT** | 4 jours dans le pic 2026-03-11 → 03-20 (11, 13, 15, 17) | ~510 grad/j | ~2 100 |

Contraste d'activité **20×** entre BAS et HAUT, contre 2,4× dans le plan initial —
et cette fois chaque fenêtre est interne­ment stable.

Les jours du MOYEN et du HAUT sont **espacés** dans leur fenêtre homogène plutôt
que consécutifs : évite qu'un artefact d'une journée porte tout le régime.

Le régime BAS est pris en entier (11 jours) car c'est tout ce qui existe à ce
niveau d'activité ; n=277 dépasse le plancher de 200 mais de peu — si le
remplissage des checkpoints en perd, il faudra étendre en amont dans juillet.

## Le choix des fenêtres ne fuite pas

Il repose uniquement sur le **nombre de graduations par jour** — une variable
d'activité, mesurée avant toute lecture de rendement. Aucun prix, aucun PnL n'a
été regardé à ce stade.

---

# Contraintes d'exécution Dune

- **Aucun tier payant n'est disponible** sur les datasets Solana de ce compte :
  `medium` et `large` renvoient tous deux « Performance X is not supported for
  this dataset 11 ». Seul `free` (plafond 2 min) est utilisable.
- Une journée entière de swaps ne passait pas **en ère 2026** (3 timeouts :
  7 j, 3 j, 1 j). Le coût est dans le scan de `pump_amm_evt_buyevent`/`sellevent`
  (~7,3 M lignes/jour chacun), indépendant de la taille de la cohorte.
- **MAIS le mur est propre à 2026.** Mesuré le 2026-09-07 : en ère 2025 une
  **journée entière passe** en free, ~1,1 crédit/jour. Le découpage en tranches de
  2 h n'a donc servi qu'à contourner un mur qui n'existe pas sur les fenêtres
  BAS/MOYEN. À re-vérifier avant le régime HAUT (mars 2026, ère dense).
- **3 exécutions parallèles maximum** en free — les lots plus larges sont refusés.
- Sur Dune, **exécuter coûte, relire ne coûte pas** : une exécution est
  récupérable indéfiniment par son `execution_id` sans dépenser un crédit.
  D'où `data/graduation/<REGIME>/manifest.json` + `dune_run.py --fetch-manifest`,
  qui rend la récupération rejouable à volonté.
- La CTE `breadth` (sur `pump_evt_tradeevent`, encore plus volumineuse) doit être
  une **requête séparée**, jointe en Python sur `mint`.

# Bugs à corriger avant extraction

1. **Doublons de pool** : au 2025-04-15, 409 graduations pour 416 lignes
   `createpoolevent` — certains mints ont plusieurs créations. Dédupliquer sur le
   premier pool par mint, sinon ces graduations comptent double.
2. **Mocks de `dune_adapter.py`** : `fdv_usd = 100000` dépasse `max_fdv_usd =
   60000` de `strategy.json`/`strategy.backtest.json` → `passes_filters` rejette
   **tous** les épisodes. Le mock bloque la gate au lieu de la passer.
   Correctif : neutraliser explicitement les filtres USD (hérités de la courbe de
   bonding, sans objet post-graduation) via une config dédiée, plutôt que
   d'injecter des valeurs qui « passent ».
3. **`parse_dune_time`** construit un `datetime` naïf puis appelle `.timestamp()`
   → interprété en heure **locale** alors que Dune renvoie de l'UTC. Décalage
   systématique. Sans effet sur le label de régime, faux pour toute analyse
   horaire.
4. **Épisodes à checkpoints manquants** : l'adaptateur saute les valeurs vides,
   donc un épisode sans `px_s0` verrait son `path` commencer à +300 s et serait
   traité comme une entrée normale. Les latences se mélangeraient silencieusement.
   Exiger la présence du checkpoint d'entrée, sinon écarter l'épisode.

**État au 2026-09-07 : les 4 corrigés et vérifiés** (dédup 39/39 mints uniques ;
`fdv/liq/vol = 1.0` contre `strategy.verdict.json` à bornes relâchées ; UTC exact
au parsing ; `path` qui démarre strictement au lag exigé).

---

## Bug 5 — le régime dérivé de la date (trouvé en vérifiant le correctif 2)

`dune_adapter.py` posait `regime = t_pool[:7]`, soit `YYYY-MM`. Or la fenêtre BAS
court du 25 juillet au 4 août : elle aurait produit **deux régimes fictifs**
`2025-07` et `2025-08`, et la gate « positive dans TOUS les régimes » de
`verdict.py` aurait tranché sur un découpage qui n'existe pas dans la spec.
Correctif : `--regime` est un argument **obligatoire** de la CLI. Un régime est un
choix de pré-inscription, jamais une propriété dérivable d'une ligne de données.

## Bug 6 — survivorship par checkpoint de sortie manquant (le plus coûteux)

Le correctif 4 traitait l'entrée. La **sortie** avait exactement le même défaut, en
pire, parce qu'un `NULL` tardif n'est pas une donnée manquante au hasard.

Mesuré sur le 2025-07-25 (39 graduations, 3 sans `px_t2700`) :

| | sortie présente | sortie manquante |
|---|---|---|
| réserve médiane à t1800 | 83,1 SOL | **20,0 SOL** |
| swaps médians sur 50 min | 3 551 | 728 |
| rendement s0→t1800 | — | **−0,95 / −0,95 / −0,96** |

Un `px_t2700` absent signifie « plus personne ne trade » — c'est-à-dire l'issue la
**pire**. Jeter ou raccourcir ces épisodes retire précisément les pires résultats :
du survivorship qui flatte la stratégie, sur 7,7 % de l'échantillon à −95 %.

Correctif : **report de la dernière marque connue**. Pas de trade depuis, donc le
prix ne bouge plus ; l'épisode conserve sa longueur et son rendement. Le compteur
`n_carried` par épisode rend le report auditable. La colonne SQL `px_last` /
`res_last` / `lag_last` expose le dernier état observé.

*Fuite de pré-inscription déclarée : trois rendements ont été lus pour établir ce
diagnostic. Contrôle d'intégrité sur la queue écartée, pas un test d'hypothèse —
mais c'est une lecture, elle est tracée ici.*

## Trou révélé au passage — réserves de sortie

Les réserves n'existaient qu'à `s0/t5/t30/t1800`. Le miroir placebo entre à t1800
et sort à t2700 : **sans `res_t2700`, son coût était incalculable**, et la spec
exige un slippage par trade à l'entrée *et* à la sortie. Le SQL expose désormais
une réserve à **chaque** checkpoint — même passe d'agrégation, zéro scan
supplémentaire.

---

# Extraction — régime BAS : FAITE (2026-09-07)

11 jours, **n = 277 graduations**, ~12,03 crédits, free tier, un CSV par jour.
Le n tombe exactement sur l'estimation de la spec (n≈277).

| jour | n | jour | n | jour | n |
|---|---|---|---|---|---|
| 07-25 | 39 | 07-29 | 39 | 08-02 | 19 |
| 07-26 | 31 | 07-30 | 30 | 08-03 | 9 |
| 07-27 | 11 | 07-31 | 28 | 08-04 | 28 |
| 07-28 | 26 | 08-01 | 17 | | |

**Nuance à porter au dossier** : j'avais écrit « ~25/j ». Le réel va de 9 à 39,
soit un facteur 4,3 dans la fenêtre. Sur des comptages aussi petits c'est du bruit
poissonnien plutôt qu'une rupture de structure, et le contraste avec MOYEN (~300)
et HAUT (~510) reste d'un ordre de grandeur — mais la fenêtre est « uniformément
basse », pas « plate ».

## Plomberie validée bout en bout

CSV → `dune_adapter.py` → `episodes.json` → `verdict.py` → gates → verdict.
Validée sur données **synthétiques** (dont un pool mort sans `px_t2700`, qui
ressort bien à 10 points, `n_carried=1`, −95 %, réserve de sortie 20 SOL).

Le choix du synthétique est délibéré : faire tourner `verdict.py` sur les 277
épisodes réels aurait exposé le PnL du régime BAS avant que l'extraction complète
existe — soit exactement la lecture que la pré-inscription interdit.

## Reste à faire avant le verdict

1. `DUNE_API_KEY` absente : les 11 CSV sont payés et récupérables gratuitement,
   mais rien ne peut atterrir sur disque sans la clé.
2. Requête `breadth` séparée (variable de conditionnement), jointe sur `mint`.
3. Régimes MOYEN et HAUT (~3 500 lignes) — impossibles à relayer autrement que
   par la clé API.
4. Slippage par trade dans `core.simulate_buy`/`simulate_sell` : la signature
   prend encore une constante de config, ce que la spec interdit. Les réserves
   sont maintenant disponibles à chaque checkpoint côté données.

---

# Verdict régime BAS — 2026-09-08

## s0 est écarté définitivement : ce n'est pas une cotation

`res_s0 == pool_sol_init` à l'exact sur **50,5 %** des 277 lignes. `px_s0` est
l'état du pool au moment où la liquidité y est déposée, pas un prix qu'on peut
frapper. Acheter « à s0 » revient à se remplir au prix du dépôt qui crée le pool.
**Le premier lag admissible est s1.** Tout résultat lu à s0 est nul et non avenu.

## Balayage de latence — la gate pré-inscrite tranche

| entrée | PnL/trade | t | miroir naïf | médiane | top-10 = % du PnL |
|---|---|---|---|---|---|
| s0 (écarté) | +0,272 | 3,12 | +0,288 | −0,0001 | 84 % |
| **s1** (+1 slot, ~400 ms) | +0,038 | 1,43 | +0,033 | −0,077 | **145 %** |
| t5 | +0,033 | 1,20 | +0,035 | −0,052 | **181 %** |
| t30 | +0,005 | 0,19 | +0,021 | — | — |

**86 % du PnL meurt en un slot.** La spec exigeait « survit ≥ +1 slot » : non.

Deux lectures à ne pas faire :
- « le miroir naïf bat la stratégie donc le signal est bon, c'est le SL/TP qui
  détruit » — faux : le miroir naïf **partage la même entrée**, il ne teste que la
  machinerie de sortie, jamais l'entrée.
- « tous_regimes>0 = True » — vide de sens sur un seul régime, la gate passe par
  construction. Elle ne vaudra qu'avec BAS + MOYEN + HAUT.

## Miroir placebo : l'edge n'est PAS du drift d'époque

Entrée t1800 → sortie t2700 : −0,025/trade, t=−1,92, win_rate 30,3 %. Le seul
point positif de la journée : contrairement au KILL de la thèse fade-vers-value
(étage 1 orderflow), ce qu'on mesure n'est pas la dérive du marché sous-jacent.

## Bug 7 — la détention comptée depuis le lancement

`_exit_schedule` passait `t` (secondes depuis le **lancement**) à `decide_exit`
comme durée de détention. Toute entrée retardée dépassait `max_hold_seconds` dès
son premier point et se time-stopait sur place. Le miroir placebo renvoyait donc
−péage pour chaque épisode (win_rate 0 %, t=−34) **en donnant l'illusion d'avoir
testé quelque chose**. Corrigé : `t - entry_t`. 113 tests verts.

C'est la troisième fois dans ce projet qu'un défaut ne casse rien et fausse
silencieusement : bug 4 (entrée), bug 6 (sortie), bug 7 (durée). Le motif commun
est qu'un backtest qui tourne sans erreur ne prouve rien sur ce qu'il a mesuré.

## Où en est la thèse : sous-alimentée, pas morte

À s1, +0,038/trade avec t=1,43 sur n=277 et **un seul** régime. Avec les trois
régimes (n≈3800) le t monterait mécaniquement vers ~5 *si* l'effet est réel et
homogène. Mais top-10 = 145 % du PnL : retirer les 10 meilleurs trades rend la
stratégie négative. La moyenne n'est pas un estimateur stable — on tient peut-être
un billet de loterie, pas un edge.

**C'est exactement la question que breadth tranche** : si la queue épaisse se
concentre sur les tokens à forte accumulation organique, la sélection transforme
la loterie en edge. Si elle est uniforme, la piste est close.

## Séquencement décidé par le coût de l'information

Breadth sur BAS **d'abord** (11 jours, ~28 crédits), avant MOYEN et HAUT (~50).
La question de la sélection est logiquement antérieure : sans elle, ajouter des
régimes n'ajoute que des billets de loterie. Et si breadth ne sépare pas la queue,
le KILL tombe pour ~28 crédits au lieu de ~78.

## Requêtes Dune figées

| objet | query_id | coût/jour |
|---|---|---|
| courbe post-graduation | 8637209 | ~1,1 |
| breadth pré-graduation | 8646887 | ~2,6 |

Piège de schéma n°4 : `pump_evt_tradeevent` porte **deux** colonnes pour le sens
du trade — `isBuy` (camelCase, ancien décodeur) et `is_buy` (snake_case). En ère
2025 seule la camelCase est peuplée ; filtrer sur `is_buy` seul renvoie 0 partout
sans lever d'erreur. Utiliser `COALESCE(t.is_buy, t."isBuy")`.

---

# VERDICT FINAL — piste 3 (breadth) et thèse graduation — 2026-09-08

## KILL

La sélection par accumulation pré-graduation ne sépare pas la queue. La thèse
graduation est close.

## Ce qui a été mesuré

Extraction breadth sur le régime BAS : 10 jours sur 11 (2025-08-04 perdu sur le
mur des 2 minutes du free tier), 249 mints sur 277 épisodes. Les 28 sans breadth
sont exclus par les défauts fail-closed de `core.py`
(`n_uniq_buyers` → 0, `curve_span_sec` → 999999, `buy_sell_ratio` → 0.0), donc
dans le sens conservateur.

### Le test à seuil est non concluant, pas concluant

Le filtre pré-inscrit (`min_uniq_buyers` 40 ∧ `max_curve_span_sec` 90 ∧
`min_buy_sell_ratio` 3.0) laisse **7 trades**, PnL −0,197, win_rate 0 %.

Ce résultat ne tranche rien. Sur une distribution où 10 trades sur 277 portent
145 % du PnL, un sous-échantillon de 7 contient 0,25 gagnant en espérance : un
win_rate de 0 % est **arithmétiquement attendu même si la sélection fonctionne**.
Conclure au KILL sur n=7 aurait été juste par accident.

> Règle : sur une distribution à queue de puissance, un filtre qui réduit
> l'échantillon d'un facteur 35 ne teste plus l'hypothèse — il teste la chance
> du tirage. Tester la sélection sans seuil.

### Le test sans seuil est concluant

Rang des 10 meilleurs trades dans le classement de chaque métrique, sur 249
(médiane attendue si aucun lien ≈ 124) :

| métrique | rangs du top-10 |
|---|---|
| `n_uniq_buyers` | 8, 26, 62, 86, 114, 143, 211, 234, 235 |
| `buy_sell_ratio` | 1, 32, 34, 71, 113, 124, 201, 228, 229 |
| `curve_span_sec` | 29, 32, 36, 110, 145, 162, 232, 234, 235 |

Uniformes sur toute l'étendue. **La queue n'habite nulle part dans l'espace
breadth.**

Dose-réponse par décile : plate, aucun gradient monotone sur les 3 métriques.
Seul `curve_span` D1 (graduations les plus rapides) est franchement négatif
(−0,150) — mais D2 est le meilleur décile (+0,212). Un godet pourri à l'extrême,
pas une pente. L'hypothèse « pump & dump coordonné sur les graduations
fulgurantes » tient donc localement, mais ne constitue pas un axe de sélection.

### Balayage de toutes les variables ex-ante (post-hoc, 6 tests)

p par permutation (2000 tirages) — le t est invalide sur ces queues.

| variable | n | ρ Spearman | p_perm |
|---|---|---|---|
| `pool_sol_init` | 277 | −0,021 | 0,738 |
| `res_entree` | 277 | +0,058 | 0,347 |
| `n_buyers_pre` | 277 | −0,100 | 0,091 |
| `n_uniq_buyers` | 249 | −0,042 | 0,488 |
| `buy_sell_ratio` | 249 | +0,016 | 0,807 |
| `curve_span_sec` | 249 | +0,035 | 0,566 |

Aucune ne passe (seuil Bonferroni à 6 tests : 0,008). La meilleure,
`n_buyers_pre`, est de **signe inverse** à la thèse.

## La raison du KILL

Échelle de retrait de la queue, à l'entrée s1 :

| | PnL total | par trade |
|---|---|---|
| tous (n=277) | +10,62 | +0,0383 |
| sans les 5 meilleurs | +1,21 | +0,0044 |
| sans les 10 meilleurs | −4,80 | −0,0180 |
| sans les 20 meilleurs | −12,66 | −0,0493 |

**Cinq trades sur 277 portent la totalité.** Avec t=1,44, l'effet n'est déjà pas
distinguable de zéro ; et même en le supposant réel, il est inexploitable faute
de tout trait ex-ante qui désigne ces cinq-là.

## Le péage n'est pas le facteur limitant ici

Balayage de la taille de position (le reste de la config inchangé) :

| taille | PnL/trade | rendement | t |
|---|---|---|---|
| 0,05 SOL | +0,0014 | +2,84 % | 0,53 |
| 0,25 SOL | +0,0190 | +7,59 % | 1,42 |
| 0,50 SOL | +0,0383 | +7,67 % | 1,44 |
| 1,00 SOL | +0,0685 | +6,85 % | 1,30 |
| 2,00 SOL | +0,0961 | +4,80 % | 0,93 |

Optimum plat vers 0,25–0,5 SOL, dégradé en bas par les frais fixes (priority fee
+ jito tip) et en haut par le slippage. Mais **le t ne dépasse 1,44 à aucune
taille** et le top-5 pèse ≥ 89 % partout.

C'est un résultat pour le programme, pas seulement pour cette thèse : contrairement
au KILL des lancements pump.fun (où le moat de +40 % tuait 94 % des trades), ici
réduire la taille ne sauve rien. Ce n'est pas le coût qui tue, c'est la forme de
la distribution.

## Nouveau sous-type de mort

Les kills précédents du programme étaient : *pas d'effet*, *effet mangé par le
coût*, *information déjà dans le prix*. Celui-ci en ajoute un :

> **Effet possiblement réel, mais entièrement logé dans une queue que rien
> d'observable ex-ante ne désigne.** Indistinguable d'une loterie à espérance
> légèrement positive. Non sizeable, non sélectionnable, estimateur instable.

## Ce qui n'a pas été dépensé

MOYEN et HAUT (~50 crédits) n'ont pas été extraits, et ne doivent pas l'être :
sans sélecteur, ajouter des régimes n'ajoute que des tirages de loterie et ne
stabilise pas un estimateur porté par 1,8 % des trades. Coût total de la
décision : ~28 crédits au lieu de ~78.

## Acquis conservés

- Le placebo temporel valide (−0,025, t=−1,92) : l'effet n'était pas de la
  dérive d'époque. Contraste net avec le KILL fade-vers-value.
- `px_s0` non exécutable (`res_s0 == pool_sol_init` sur 50,5 % des lignes) —
  tout backtest de graduation entrant à s0 est faux.
- Bugs 5, 6, 7 et leur motif commun : aucun ne levait d'erreur.
- Pipeline Dune day-paramétré, pattern manifest (relire une exécution est
  gratuit), `--days-list`, 4 pièges de schéma.

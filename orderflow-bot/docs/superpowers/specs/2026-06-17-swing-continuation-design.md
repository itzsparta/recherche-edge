# Spec — swing-continuation (étage 2b)

**Date** : 2026-06-17
**Statut** : pré-enregistrement gelé (seuils figés AVANT de voir le moindre résultat).
**Contexte** : suite directe du redeploy swing. L'intraday BTC-spot est gelé no-edge
([`FINDINGS.md`](../../FINDINGS.md)). L'étage 1 (fade-vers-value) a été **KILL** : sur
un smoke mono-régime (6 mois bear, BTC −29.6 %) `brut_fade −0.073R` et le miroir
`+0.271R` = **drift pur** (le short-biais gagne par la pente, pas par le niveau).
Leçon : un échantillon mono-régime ne sépare PAS un edge-de-niveau d'un drift
directionnel. L'étage 2a (ingestion klines, fondation data) est **mergé, gate
plomberie PASS**. Cet étage 2b teste le **hint directionnel** révélé par le miroir,
mais sur données **multi-régime** où le drift s'annule.

> **Discipline.** Hypothèse pré-spécifiée que le rerun confirme ou tue, jamais
> d'infra bâtie sur un espoir. Les seuils du gate ci-dessous sont figés ici, avant
> exécution. Tout assouplissement post-hoc = data-mining (cf. cellules trompeuses
> #9/#10/jeudi-#11 dans FINDINGS). Brut TOUJOURS via relabel frais=0, jamais
> `net + frais/risk0` (piège de décompo « ~7σ » documenté).

---

## 1. Hypothèse pré-enregistrée

**H2b (brut, scale + multi-régime).** L'**acceptance / breakout au-delà d'un bord de
value area** (clôture du corps qui traverse VAH par le haut / VAL par le bas, ou un
naked POC / LVN) porte une **information directionnelle de continuation** à l'échelle
swing : le prix poursuit vers le niveau structurel suivant. Cette information est un
**edge de niveau**, séparable du drift directionnel de BTC, donc présente **dans les
deux sens** (long ET short) et survivant sur **plusieurs régimes**.

**Ce qui distingue H2b du fade mort.** L'étage 1 fadait le rejet (retour vers value) ;
H2b joue la **cassure** (sortie de value). Le fade a été tué proprement (acheter les
creux dans un crash = mort) mais le miroir `+0.271R` a montré qu'un signal
**directionnel** existe dans la série — indissociable du drift sur 6 mois bear. H2b
isole l'edge-de-niveau du drift par : (a) données multi-régime (drift s'annule),
(b) exigence **brut_long>0 ∧ brut_short>0** (le drift ne peut pas faire gagner les
deux sens).

**Falsification.** Si `brut ≈ 0`, ou si l'edge ne tient que d'un seul côté (drift
déguisé), ou s'il ne survit pas à la déflation DSR/CV → **KILL**. Le swing dissout le
mur de *frais* (gros R), pas l'absence d'edge.

---

## 2. Signal & trigger

### Niveaux (réutilisé intact)
VP daily via le pipeline existant : `levels_from_profile` (POC/VAH/VAL/high/low),
`naked_pocs` (`npoc_lookback_days`), LVN composite (`profile_days`), zones via
`build_zones` (`zone_margin_pct`), résolution via `zone_at`.

### Trigger swing — `level_breakout_triggers(bar, zones)` (NEUF)
Complément géométrique exact de `level_rejection` : au lieu de *mèche pique + clôture
revient* (rejet), c'est **le corps qui traverse le bord** (acceptance). Évalué à la
clôture de chaque barre 4h :

- **Setup long** (cassure haussière) : `bar.open <= z.hi < bar.close` — le corps a
  ouvert au/sous le bord-haut de la zone et clôturé au-dessus → `Trigger(side=+1,
  price=z.hi, kind="level_breakout")`.
- **Setup short** (cassure baissière) : `bar.close < z.lo <= bar.open` →
  `Trigger(side=-1, price=z.lo, …)`.
- **Nearest-zone** identique à `level_rejection` : `max(longs, key=z.hi)` (bord cassé
  le plus proche sous la clôture) / `min(shorts, key=z.lo)` — évite les candidats
  corrélés d'un même grand mouvement. Un trigger par sens max.

Fichier `strategy/level_breakout.py` (sibling de `level_rejection.py`), fonction pure
`(bar, zones) -> list[Trigger]`, aucune I/O.

### Compatibilité de sens (réutilisé intact)
Déléguée à `ConfluenceEngine` mode `continuation`, qui existe déjà :
`eff_side = {"val": -1, "vah": 1}.get(z.kind, 0)` → cassure **au-dessus de VAH =
long**, **sous VAL = short** ; npoc/lvn (`side=0`) acceptent le sens du trigger. Un
long sur cassure au-dessus de VAL (re-entrée dans value, pas un breakout) a
`eff_side=-1 ∉ (0, +1)` → rejeté à la source. Aucune modif de cette logique.

### TF de la barre (paramètre figé)
**4h**, identique à l'étage 1 (≈6× plus de setups que daily, gros R préservé car hold
structurel multi-jours). Fork daily documenté étage 1, non rouvert ici.

### Entrée (réutilisé intact)
`entry_mode = "stop"` / `entry_confirm_frac = 0.0`. La clôture de cassure *est* la
confirmation. Au swing le surcoût taker de l'entrée stop ≈ négligeable devant R.

### Plan & cible structurelle (modif CIBLÉE de `ConfluenceEngine`)
Le mode continuation actuel cible `day_high`/`day_low` (extrême veille) — **cassé pour
swing** : reward<0 si la cassure a déjà dépassé l'extrême veille, et R souvent petit
→ ne dissout PAS le mur frais↔edge. Remplacé par une **cible structurelle** :

- **target = niveau structurel le plus proche AU-DELÀ de l'entrée, dans le sens du
  trade** (candidats = naked POC, VAH/VAL, extrêmes veille — passés à `update_day`).
- **fallback = mesure de range** `entry + side × (vah − val)` si aucun niveau au-delà.
- **stop = reclaim** (back inside) : `z.lo − buffer` (long) / `z.hi + buffer` (short),
  formule identique au fade.
- Filtre `RR ≥ min_rr` (2.0) **inchangé** → ne génère un plan QUE si le niveau suivant
  donne ≥ 2R. Sélection naturelle vers les gros-R **sans paramètre d'overfit**.
- Filtres `min_stop_friction_mult` et bias HTF (`market_bias`) conservés.

---

## 3. Horizon & exécution (réutilisé intact, étage 1)

- `eod_flat = False` : `OrderExecutor` / `simulate_isolated` ne force-closent plus au
  changement de jour → holds structurels multi-jours. Le rollover de **profil daily**
  reste finalisé (niveaux daily) ; seul le force-close de **position** est conditionné.
- Positions ouvertes en fin de fenêtre → force-close (kind `eod`), **label censuré**,
  exclu du brut, tracé au rapport.
- Signal jugé **nu** : `sessions` vidé, caps relâchés. Le sizing/risque se réintroduit
  seulement après validation (ne crée pas d'edge).

Chemin déjà prouvé par le gate plomberie 2a (`simulate_isolated(eod_flat=False)` sur
klines, labels=112, zéro violation).

---

## 4. Data & staging

Source : klines 1m BTCUSDT multi-années (data.binance.vision, gratuit, remonte
~2017), downloader & reader de l'étage 2a (`download_klines`, `read_market`,
`read_klines_as_ticks`, adaptateur synthetic-tick 4 ticks/kline). VP daily depuis les
barres 1m, barres 4h pour le trigger.

**Run étagé (kill-fast)** :
1. **Slice multi-régime** d'abord (≈ 2021 bull + 2022 bear + 2023 reprise = up ET
   down) → lecture kill-fast du **noyau** du gate (brut>0, both-sides>0, miroir). Si
   le noyau échoue → **KILL, ne pas étendre**.
2. **Full-history** ensuite (si le noyau survit) → stats déflatées **DSR / CSCV** qui
   exigent un grand N.

**Labeling SÉQUENTIEL** (`simulate_isolated`, eod_flat=False) — réutilisé tel quel, PAS
de labeler parallèle neuf (le `_isolated_block_worker` parallèle reste UNSAFE pour les
holds multi-jours : `tail_days=1`). La passe-1 signal reste parallélisable
(`generate_plans_parallel`, prouvée sûre sur klines en 2a via l'invariant
d'alignement-bloc). Perf full-history : mesurer d'abord, paralléliser le labeling
seulement si prouvé nécessaire (« jamais d'infra sur un espoir »).

---

## 5. Validation — gate 2b strict (pré-enregistré)

> Brut toujours mesuré en **relabelant à frais = 0** (`r = pnl/risk0_réel`).

### Plomberie d'abord (non-edge, réutilisé 2a)
`zone_violations` / `plan_violations` / `label_violations` (étage 2a) sur le run avant
toute lecture d'edge — sanity du nouveau trigger + cible. Violation ⇒ bug, pas verdict.

### Gate 2b — KILL durs (tous requis)
1. `brut > 0` avec **t > 2** (t sur la série de R par trade) ;
2. **`brut_long > 0` ∧ `brut_short > 0`** — *contrôle de drift central* : un edge qui
   gagne long ET short ne peut pas vivre du drift (BTC-histoire est net haussier → des
   shorts profitables prouvent un edge de niveau qui surmonte le vent contraire) ;
3. `brut > brut_miroir` — info directionnelle au-delà du pile-ou-face (miroir =
   `mirror_plan`, mêmes candidats sens inversé, géométrie d'exit reflétée, levier #5) ;
4. `net > 0` aux frais BTC-spot **atteignables** (plancher maker ≈ +0.01 %, taker
   0.05 %, slippage) — bornes **instrument-spécifiques** (leçon FINDINGS #13) ;
5. **DSR(best, N)** survit après déflation du nombre N de variantes essayées
   (`scripts/overfit_audit.py`) ;
6. **CSCV purged & embargoed** : `expectancy_r` positive sur la **majorité** des folds.
   Les holds swing sont multi-jours → labels chevauchants → purge + embargo **requis**
   (l'intraday EOD-flat les rendait moot). Exposition comparable → PBO recevable.

### Diagnostic (reporté, NON-gating)
**`regime_split`** par signe du retour 90j glissant (up vs down régime au moment de
l'ouverture) : brut / brut_long / brut_short / n par régime. Montre **où vit l'edge**
sans tuer un breakout légitimement régime-conditionnel (tendance > range) sur un
sous-échantillon. Un edge entièrement logé dans le régime qui coïncide avec le drift =
**drapeau rouge à évaluer**, mais pas un auto-KILL.

→ tous (1-6) vrais ⇒ edge validé → paper trading (protocole ROADMAP), sizing/Monte
Carlo au stade suivant. Sinon ⇒ **KILL** documenté, thèse swing-continuation gelée (et
le fade étant déjà mort, la thèse swing entière gèle).

---

## 6. Frontière de code

### Neuf
- `strategy/level_breakout.py` — `level_breakout_triggers(bar, zones)`.
- `backtest/swing_gate2.py` — `brut_by_side`, `t_stat`, `regime_split`, `gate2(...)`
  (réutilise `brut`/`mirror_plan`/`_realized` d'étage 1, DRY).
- `scripts/continuation_run.py` — orchestrateur (read_market → PlanGenerator
  level_breakout → simulate_isolated eod_flat=False ×2 relabels → plomberie → gate2,
  + branchement DSR/CSCV).
- `config.continuation.yaml` — `data_format: klines`, `trigger: level_breakout`,
  `signal_mode: continuation`, `eod_flat: false`, sessions [], caps relâchés.
- Branchement `trigger: "level_breakout"` dans `PlanGenerator` (mirroir de
  `level_rejection`).

### Modif ciblée
- `ConfluenceEngine` : cible continuation **structurelle** (niveau-suivant + fallback
  measured-move) au lieu de `day_high`/`day_low` ; `update_day` reçoit les niveaux
  structurels candidats + la largeur VA. La logique `eff_side`/stop/RR inchangée.

### Réutilisé intact
`read_market` / `read_klines_as_ticks` / `download_klines` (2a) ; `simulate_isolated`
eod_flat (étage 1) ; `VolumeProfile`, `levels_from_profile`, `naked_pocs`,
`build_zones`, `zone_at`, `market_bias`, `BarAggregator`, `PaperBroker`,
`generate_plans_parallel` ; `swing_gate` helpers ; `plumbing_checks` (2a) ;
`overfit_audit` (DSR) ; CSCV purged/embargo ; `montecarlo`.

---

## 7. Garde-fous anti-overfit (rappels FINDINGS)

- Règle + seuils du gate **figés dans ce spec avant** de voir le run.
- Brut via **relabel frais = 0**. Bornes frais **instrument-spécifiques** (plancher
  maker BTC-spot connu a priori).
- **Both-sides-positive** = contrôle de drift dur ; régime = diagnostic, jamais un
  filtre post-hoc promu en « validé ».
- Une **cellule visuelle ≠ hypothèse validée**.
- **Kill-fast** : slice multi-régime d'abord ; noyau du gate négatif → stop immédiat,
  pas de full-history.

---

## 8. Hors scope (explicite)

- **GEX / options** : proxy RV testé (#12, faux gradient), GEX payant rejeté.
- **DOM / L2** : tué Phase 0 (AUC 0.535 vs 0.521).
- **ML / meta-labeling** : v3+, conditionnel à des centaines de trades labellisés.
- **Optimisation de sizing** : moot tant que le gate 2b n'est pas franchi (edge ≤ 0 →
  Kelly = 0).
- **Labeler parallèle swing-safe** : seulement si la perf full-history séquentielle le
  prouve nécessaire (pas avant).

---

## 9. Condition de succès du projet (one-liner)

Le swing **vit** si le gate 2b passe en entier (brut t>2 + both-sides>0 + miroir battu
+ net>0 + DSR survit + folds majoritaires) sur klines multi-années. Sinon, KILL
documenté dans FINDINGS et thèse swing (fade + continuation) gelée.

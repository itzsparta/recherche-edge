# Spec — redeploy swing (fade-vers-value)

**Date** : 2026-06-17
**Statut** : pré-enregistrement gelé (à figer avant de voir le moindre résultat smoke).
**Contexte** : l'intraday BTC-spot est gelé no-edge (voir [`FINDINGS.md`](../../FINDINGS.md)).
Le redeploy swing est l'option #1 par EV ([`ROADMAP.md`](../../ROADMAP.md)) : seul move
qui **dissout** le mur structurel frais↔edge (gros R → fraction-frais → négligeable),
au lieu de le grignoter comme une venue moins chère.

> **Discipline.** Ce redeploy s'entre comme une **hypothèse pré-spécifiée que le
> rerun confirme ou tue**, jamais de l'infra bâtie sur un espoir. Les seuils des
> deux gates ci-dessous sont figés ici, avant exécution. Tout assouplissement
> post-hoc d'un seuil = data-mining (cf. cellule trompeuse #9/#10 dans FINDINGS).

---

## 1. Hypothèse pré-enregistrée

**H1 (brut, scale-dépendante).** Les niveaux de volume profile nus — naked POC,
bords de value area (VAH/VAL), LVN — sont défendus par des flux positionnels à
l'échelle swing. Le prix les rejette et revient vers value (POC) sur plusieurs
jours, produisant une **espérance brute positive**. Cette information directionnelle
est **absente au 1-min** (noyée dans le bruit microstructure / HFT).

**Ce qui distingue H1 de l'intraday mort.** Le verdict no-edge portait sur le
*footprint stacked-imbalance* comme déclencheur (brut ≈ 0, levier #5 : aucune info
directionnelle). H1 ne teste **pas** ce déclencheur. Elle teste la significativité
directionnelle du **niveau lui-même**, via un rejet observé à l'échelle swing. Le
footprint trigger est abandonné.

**Falsification.** Si le brut du fade swing ≈ 0 (comme l'intraday), H1 est fausse →
KILL. Le swing ne « sauve » pas un brut nul : il dissout le mur de *frais*, pas
l'absence d'edge.

---

## 2. Signal & trigger

### Niveaux (réutilisé intact)
VP daily via le pipeline existant : `levels_from_profile` (POC/VAH/VAL/high/low du
jour), `naked_pocs` (lookback `npoc_lookback_days`), LVN du composite
(`profile_days`), zones via `build_zones` (`zone_margin_pct`), résolution via
`zone_at`. Zones candidates au fade = naked POC, bords VA, LVN.

### Trigger swing — `LevelRejectionTrigger` (NEUF)
Évalué à la clôture de chaque barre resamplée au **TF swing** :

- **Setup long** : `bar.low` entre dans une zone ET `bar.close > zone.hi`
  (clôture revenue au-dessus de la zone) → rejet → `Trigger(side=+1,
  price=zone.hi, kind="level_rejection")` (entrée au bord reclaimé).
- **Setup short** : `bar.high` entre dans une zone ET `bar.close < zone.lo` →
  `Trigger(side=-1, price=zone.lo, …)`.
- « entre dans la zone » = l'extrême de la barre ∈ `[zone.lo, zone.hi]`.
- **Compatibilité de sens** déléguée à `ConfluenceEngine` : zones VAL (`side=+1`)
  et VAH (`side=-1`) ne s'engagent que dans leur sens ; npoc/lvn (`side=0`)
  acceptent le sens du trigger. Un long sur zone VAH est donc rejeté à la source
  (on ne fade pas un long sous une résistance).

### TF de la barre rejet (paramètre figé)
**4h** pour le smoke et le run klines. Justification : ≈6× plus de setups que le
daily (puissance du sample) tout en préservant un gros R (le hold reste structurel
multi-jours, cf. §3). **Alternative documentée** (fork pré-spécifié, à n'activer
que si gate 2 échoue *et* déclaré avant de voir gate-2) : **daily** (signal de
rejet plus propre, sample plus maigre).

### Entrée (réutilisé intact)
`entry_mode = "stop"` / confirmation (`entry_confirm_frac`). La clôture de rejet
*est* la confirmation → `entry_confirm_frac = 0.0` (entrée au reclaim du niveau sur
le mouvement confirmant). Au swing le surcoût taker de l'entrée stop ≈ négligeable
devant R, mais elle retire toujours l'adverse-selection qui plombait l'intraday →
quasi-gratuite. Figé pour le smoke.

### Plan (réutilisé intact)
`ConfluenceEngine` mode reversal : stop = `zone.lo − buffer` (long) /
`zone.hi + buffer` (short) ; target = POC (`zone.target`) ; R:R ≥ `min_rr` (2.0) ;
filtre de friction `min_stop_friction_mult` conservé (rarement liant au swing,
gros R). Filtre de bias HTF (`market_bias`) conservé en couche 1.

---

## 3. Horizon & exécution

- Nouveau flag config **`eod_flat: bool = True`**. L'intraday garde `True`. Le
  swing tourne en **`False`**.
- `eod_flat = False` : `OrderExecutor` et `simulate_isolated` **ne force-closent
  plus la position** au changement de jour → les positions courent jusqu'au
  stop/target **structurel**, sur plusieurs jours.
- **Découplage explicite** : le rollover de **profil daily** est TOUJOURS finalisé
  (les niveaux restent daily) ; seul le force-close de **position** est conditionné
  par `eod_flat`. Ne pas confondre les deux dans le code (`_maybe_rollover` reste,
  `_maybe_eod` devient conditionnel).
- **Positions ouvertes en fin de fenêtre data** → force-close au dernier tick,
  marquées **label censuré** (comptées, signalées dans le rapport — pas un win/loss
  structurel). Diagnostic, non éliminées du brut mais traçables.
- Pour le **gate brut**, le signal est jugé **nu** : `sessions` vidé, caps
  (`daily_stop_pct`, `max_trades_per_day`, `max_consecutive_losses`) relâchés. La
  gestion du risque se réintroduit seulement après validation du brut (le sizing ne
  crée pas d'edge).

---

## 4. Data & staging

### Étage 1 — smoke (stock existant, zéro download)
- Source : stock aggTrades BTCUSDT spot 6 mois (déc. 2025 → juin 2026).
- Barres 4h via `BarAggregator(240 * 60_000, …)`.
- VP daily construite depuis les **ticks** (exacte).
- ~30-60 setups attendus → read brut indicatif (sous-puissant pour DSR, suffit pour
  tuer).

### Étage 2 — run puissant (si gate 1 passe)
- Source : klines 1m multi-années (data.binance.vision, gratuit, BTCUSDT remonte à
  ~2017). Viser 2-3 ans → centaines de setups.
- **Nouveau parser/reader klines** dans `ingestion/` (seul ce module change ; le
  pipeline est agnostique du flux). Schéma klines ≠ aggTrades.
- VP daily construite depuis les barres 1m (volume approximé sur la barre —
  standard pour un VP basé klines). Barres 4h pour le trigger.

---

## 5. Validation — deux gates pré-enregistrés

> Brut toujours mesuré en **relabelant à frais = 0** (`r = pnl/risk0_réel`), jamais
> `net + frais/risk0` (piège de décompo documenté : faux brut « à 7σ » en mode stop).

### Gate 1 — smoke, permissif (greenlight klines)
Tous requis :
1. `brut_fade` (moyenne R, frais=0) **> 0** ;
2. `brut_fade > 0` sur **chacune des 2 moitiés** du sample (stabilité de signe) ;
3. `brut_fade > brut_continuation` — le rejet porte une **info directionnelle** au-delà
   du pile-ou-face. `brut_continuation` = **mêmes candidats, sens inversé, géométrie
   d'exit identique** (le miroir, comme levier #5).

Diagnostic non-gating : taux de morts-nés (MFE < 0.5R) reporté.
→ 1∧2∧3 vrai ⇒ **greenlight étage 2**. Sinon ⇒ **KILL, ne rien construire de plus**.

### Gate 2 — klines, strict (validation de l'edge)
Tous requis :
1. `brut > 0` avec **t > 2** (t sur la série de R par trade) ;
2. `net > 0` aux frais BTC-spot **atteignables** (plancher maker ≈ +0.01 %, taker
   0.05 %, slippage) — bornes **instrument-spécifiques** (leçon FINDINGS) ;
3. **DSR(best, N)** survit après déflation du nombre N de variantes essayées
   (`scripts/overfit_audit.py`) ;
4. **CSCV purged & embargoed** : expectancy_r positive sur la **majorité** des folds ;
   PBO recevable. *Note* : contrairement aux filtres intraday (exposition inégale →
   PBO contaminé), les holds swing ont une exposition comparable → PBO redevient
   valide ici.

→ tout vrai ⇒ edge validé, → paper trading (protocole ROADMAP). Sinon ⇒ KILL (ou
fork *daily* §2 uniquement si pré-déclaré).

### CV — pourquoi purgée maintenant
Les holds swing sont **multi-jours** → labels **chevauchants** entre trades. La purge
+ embargo (déjà implémentés dans le CSCV) deviennent **requis** — l'intraday était
EOD-flat (zéro overnight, labels disjoints → purge moot), ce n'est plus le cas.

### Monte Carlo
`validate` (dd_p99 / ruin_prob vs stop journalier) **au stade sizing seulement**,
après gate 2. Le sizing module la variance, ne crée pas d'edge.

---

## 6. Frontière de code

### Neuf
- `LevelRejectionTrigger` (déclencheur swing — `strategy/` ou `features/`).
- Flag `eod_flat` : `config.py` (+ défaut `True`), threadé dans `OrderExecutor._maybe_eod`
  et `simulate_isolated` (+ variantes blocked/parallel).
- Gestion **label censuré** en fin de fenêtre (rapport).
- Parser/reader **klines 1m** dans `ingestion/` (étage 2 uniquement).

### Réutilisé intact
`VolumeProfile`, `levels_from_profile`, `naked_pocs`, `build_zones`, `zone_at`,
`market_bias`, `ConfluenceEngine`, `PaperBroker`, `RiskManager`, `BarAggregator`
(juste reparamétré au TF swing), `simulate_isolated_parallel`, `metrics`,
`backtest/separation` (AUC), `scripts/overfit_audit` (DSR), `backtest/montecarlo`.

---

## 7. Garde-fous anti-overfit (rappels FINDINGS)

- Règle + seuils des deux gates **figés dans ce spec avant** de voir le smoke.
- Brut mesuré via **relabel frais = 0**.
- Bornes « réalistes » **instrument-spécifiques** (plancher maker BTC-spot connu a priori).
- Une **cellule visuelle ≠ hypothèse validée** → aucun filtre post-hoc non pré-déclaré.
- **Kill fast** : brut ≈ 0 au smoke → stop immédiat, pas d'ingestion klines.

---

## 8. Hors scope (explicite)

- **GEX / options** comme régime : proxy RV déjà testé (#12, faux gradient, plafond
  non récoltable) ; GEX payant rejeté. Non rouvert sans régime récoltable au proxy.
- **DOM / L2** : tué en Phase 0 (AUC 0.535 vs 0.521). Non re-supposé sans test
  pré-enregistré sur le nouvel instrument.
- **ML / meta-labeling** : v3+, conditionnel à des centaines de trades labellisés.
- **Optimisation de sizing** : moot tant que gate 2 n'est pas franchi (edge ≤ 0 → Kelly = 0).

---

## 9. Condition de succès du projet (one-liner)

Le swing **vit** si : gate 1 greenlight (brut directionnel sur smoke) **puis** gate 2
strict (brut t>2 + net>0 + DSR survit + folds majoritaires) sur klines multi-années.
Sinon, KILL documenté dans FINDINGS et thèse fade-vers-value gelée à son tour.

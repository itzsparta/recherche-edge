# Piste 4 — Volatility Risk Premium : pré-test (PRÉ-ENREGISTRÉ)

> Écrit **avant** de voir le moindre résultat. Tout changement de cette spec après avoir vu
> un chiffre = overfit, interdit. (Leçon FINDINGS orderflow.)

## Hypothèse

Vendre systématiquement de la variance/vol sur l'indice actions US récolte un premium
**positif et significatif** (la vol implicite excède la vol réalisée), ET le fait de manière
**worth-harvesting pour un solo** — c'est-à-dire en battant un SPY buy-hold passif en
risk-adjusted **une fois le risque de queue inclus**.

Les deux conditions sont requises. Une seule ⇒ pas un go.

Le null honnête : le VRP n'est *pas* un edge récoltable mais la **juste compensation d'un
risque de queue catastrophique** (skew très négatif). Vendre la vol = ramasser des pièces
devant un rouleau compresseur. Un solo qui ne peut modéliser/porter le moment (Feb-2018 :
short-vol ETN détruits en une séance) n'a pas d'edge net du tail.

## Univers (FIXE — aucun cherry-pick)

- **Implicite** : `^VIX` (vol implicite 30 j SPX, en points de vol annualisés).
- **Sous-jacent / réalisée** : `^GSPC` (S&P 500, pour la variance réalisée).
- **Benchmark passif** : `SPY` (rendement total, `auto_adjust`) — le « worth-it » bar.

Échantillon = **tout l'historique commun VIX+GSPC (~1990 →)**. Couvre **Dot-com, GFC 2008,
Volmageddon Feb-2018, COVID Mar-2020, 2022** = multi-régime par construction. **Aucune
exclusion de krach** : exclure les sinistres serait le mensonge canonique du short-vol.

## Mesure du premium — Phase 0 (FIXE)

- **Vol implicite** : `IV_vol_t = VIX_t / 100` (décimal annualisé), `IV_var_t = IV_vol_t²`.
- **Vol réalisée forward** : sur les **h = 21 jours de bourse** suivant `t` (≈ 30 j calendaires,
  horizon du VIX), `RV_var_t = 252 / h · Σ_{i=1..h} r_{t+i}²` où `r = Δln(GSPC)`.
  `RV_vol_t = √RV_var_t`. h = 21 **pré-spécifié**, pas de tuning.
- **Premium** : `VRP_var_t = IV_var_t − RV_var_t` (>0 = prime au vendeur),
  `VRP_vol_t = VIX_t − 100·RV_vol_t` (points de vol, pour l'intuition).
- **Échantillonnage** : **mensuel non-chevauchant** (point par fin de mois de bourse,
  fenêtre forward 21 j). Évite l'autocorrélation qui gonfle le t des fenêtres glissantes.

## Récolte tradable — Phase 1 (FIXE)

- **Rendement de récolte** mensuel d'un short-variance synthétique vega-flat, en points de
  vol : `pnl_t = VRP_vol_t − coût`. C'est le P&L (premier ordre) d'un vendeur de straddle/
  variance couvert en delta, normalisé en points de vol.
- **Coût pré-enregistré** : `coût = 0.5 point de vol / mois` (round-trip bid-ask + slippage
  vega, conservateur pour SPX/VIX listés). Jamais de brut en input de décision.
- **Sizing honnête** : série de P&L à **vega-notional constant (1×)**, pas de levier empilé.
  (Leçon piste 1 : le sizing levé a renversé un faux GO ; on lit le Sharpe au levier tenable.)

## Métriques + critères PRÉ-ENREGISTRÉS

### (A) Le premium existe — TOUT requis
- `mean(VRP_var) > 0` ET `t-stat > 2` sur l'échantillon mensuel non-chevauchant complet.
- `VRP_var` moyen **positif dans la majorité** des régimes
  (Dot-com&avant / GFC 2008-09 / reprise 2010-2017 / Volmageddon&fin-2010s 2018-2019 /
  COVID 2020 / 2021+).
- **DSR(best) > 0.95** sur les estimateurs de réalisée essayés {close-to-close 21 j ;
  h ∈ 15/21/30} — lancés en **diagnostic seulement**, jamais pour sélectionner ; DSR déflate
  par le nombre d'essais.

### (B) Le premium vaut le coup, tail-inclus — TOUT requis
- **Sharpe net de la récolte (Phase 1) annualisé > Sharpe de SPY buy-hold** sur la même
  fenêtre, ET `t-stat(pnl net) > 2`.
- **Survie au tail** : le P&L net reste **non catastrophique** sur les mois de krach —
  pré-enregistré comme : `max drawdown de la récolte ≤ max drawdown de SPY` **OU** worst-month
  de la récolte ≥ worst-month de SPY. (Un short-vol qui multiplie le drawdown de SPY pour un
  Sharpe à peine meilleur n'est **pas** worth-it pour un solo.)
- **Miroir** : être *long* vol (signe inversé) doit **perdre** (sinon le premium n'est pas la
  source du P&L).

## Décision pré-enregistrée

- **(A) ∧ (B) ⇒ GO** vers le protocole complet (vrais VIX futures / options delta-hedgées,
  walk-forward, Monte-Carlo, paper).
- **(A) ∧ ¬(B) ⇒ DOWNGRADE** : prime réelle mais = compensation d'un tail qu'un solo ne peut
  porter (pas worth net du risque). Documenter, ne pas builder plus loin. **Verdict attendu.**
- **¬(A) ⇒ KILL** : premium absent/instable cross-régime dans nos données (implausible — sanity).

## Données & implémentation

- **Source** : `^VIX`, `^GSPC`, `SPY` via yfinance, cache CSV local `data/` (réutilise le
  pattern `factor-harvest/data.py`).
- **Analyse** : pandas + numpy. Audit : `deflated_sharpe` porté tel quel depuis
  `factor-harvest/audit.py` (pur stdlib, Bailey-López de Prado).
- **Sortie** : verdict console + `docs/FINDINGS.md` au format orderflow/meme/factor.

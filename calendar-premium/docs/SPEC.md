# Piste 5 — Primes de calendrier : pré-test (PRÉ-ENREGISTRÉ)

> Écrit **avant** de voir le moindre résultat. Tout changement après avoir vu un chiffre =
> overfit, interdit. (Leçon FINDINGS orderflow.)

Deux sous-pistes, prime de calendrier = rendement concentré sur une fenêtre temporelle fixe,
pas uniforme. **5a overnight** (zéro calendrier externe — fait en premier). **5b pré-FOMC**
(nécessite le calendrier des annonces FOMC — à venir).

## 5a — Effet overnight

### Hypothèse
Le rendement actions US se concentre **overnight** (close→open) ; l'**intraday** (open→close)
est plat ou négatif. Prime de portage du risque nocturne (illiquidité, gap risk) — structurel,
pas une inefficience prédictive. (Lou-Polk-Skouras, JFE.)

Deux conditions requises :
1. l'effet **existe** (overnight >> intraday, significatif), ET
2. il est **capturable net** par un solo (bat le buy-hold après le coût du turnover quotidien).

### Univers (FIXE)
- **SPY** (primaire), **QQQ**, **IWM** (robustesse multi-instrument). OHLC ajusté yfinance.
- Échantillon = tout l'historique (SPY ~1993, QQQ ~1999, IWM ~2000 →). Couvre dot-com, GFC,
  COVID, 2022 = multi-régime. (Le split overnight/intraday est **intra-instrument** → le
  drift directionnel s'annule en grande partie ; le multi-instrument garde de l'idiosyncrasie.)

### Décomposition (FIXE)
- `overnight_d = Open_d / Close_{d-1} − 1`
- `intraday_d  = Close_d / Open_d − 1`
- `cc_d        = Close_d / Close_{d-1} − 1` (buy-hold de référence)

### Stratégie + coût (FIXE)
- Long overnight / flat intraday : détenir close→open, sortir à l'open.
- **Coût = 5 bps round-trip par cycle overnight** (achat MOC + vente MOO, slippage d'enchère
  incluse, conservateur pour un ETF ultra-liquide). `net_d = overnight_d − 0.0005`. Net d'office.

### Métriques + critères PRÉ-ENREGISTRÉS
**(A) l'effet existe — TOUT requis**
- `mean(overnight) > 0` ET `t-stat > 2`.
- `mean(overnight) > mean(intraday)` avec `t-stat(overnight − intraday) > 2`.
- Tient sur la **majorité** de {SPY, QQQ, IWM}.

**(B) capturable net — TOUT requis**
- Sharpe **net** (overnight − coût) annualisé **> Sharpe du SPY buy-hold** (cc), ET `t(net) > 2`.

### Décision pré-enregistrée
- **(A) ∧ (B) ⇒ GO**.
- **(A) ∧ ¬(B) ⇒ DOWNGRADE** : prime réelle mais mangée par le coût du turnover quotidien
  (252 cycles/an) → pas worth pour un solo. **Verdict attendu.**
- **¬(A) ⇒ KILL** : effet absent/non robuste cross-instrument.

## 5b — Pré-FOMC drift (À VENIR)

### Hypothèse
Rendement actions anormalement élevé dans les ~24 h **avant** les annonces FOMC programmées
(Lucca-Moench 2015, J. Finance) — prime de résolution d'incertitude.

### Plan (pré-spécifié)
- Event-study du rendement SPY sur la fenêtre [annonce−1, annonce] vs baseline non-FOMC.
- **Test du tueur priced-in** : l'effet **persiste-t-il post-publication (2015→)** ou s'est-il
  érodé/déplacé (comme les unlocks) ? Net de coûts.
- **Bloquant** : nécessite le calendrier des annonces FOMC programmées (≈8/an depuis 1994),
  à récupérer (Fed). Spec détaillée + gates écrits **avant** le run, comme 5a.

## Données & implémentation
- yfinance OHLC ajusté, cache `data/`. Audit : `deflated_sharpe` porté depuis factor-harvest.
- Sortie : verdict console + `docs/FINDINGS-overnight.md`, `docs/FINDINGS-fomc.md`.

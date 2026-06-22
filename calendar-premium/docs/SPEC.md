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

## 5b — Pré-FOMC drift (PRÉ-ENREGISTRÉ, run à venir)

### Hypothèse
Rendement actions anormalement élevé autour des annonces FOMC **programmées** (Lucca-Moench
2015, J. Finance : le gros de l'equity premium se réalise dans les ~24 h avant le statement) —
prime de résolution d'incertitude. Deux conditions :
1. le drift **existe** sur l'historique (rendement FOMC >> non-FOMC), ET
2. il **persiste après publication** (2015→) — sinon il est **priced-in/érodé** (tueur du
   programme, cf. unlocks) et non tradable.

### Univers & données (FIXE)
- **SPY** close-to-close. Calendrier des annonces FOMC programmées :
  - 1994-2018 : CSV public FOMCscrape (GitHub, urllib), colonne `End` = jour du statement.
  - 2019-2026 : dates vérifiées sur federalreserve.gov (réunions programmées uniquement).
  - **Urgences intermeeting exclues** (flag CSV incomplet → blocklist 1998-10-15, 2001×3,
    2008×2, etc. ; 2020 mars préempté par l'urgence du 15 → exclu). Premier event : fév 1994.
- Échantillon ~250 events, multi-régime. Post-2015 ~90 events (data propre).

### Fenêtres (FIXE — primaire + diagnostics)
- **Primaire : `announce_day` = close[d−1] → close[d]** (jour du statement).
- Diagnostics : `day_before` = close[d−2]→close[d−1] ; `window2` = close[d−2]→close[d].
- Caveat pré-enregistré : la donnée daily **ne peut pas** couper à 14 h (heure du statement) ;
  `announce_day` mêle drift pré-annonce ET réaction post. C'est la limite assumée du test gratuit.

### Métriques + critères PRÉ-ENREGISTRÉS
**(A) le drift existe — requis**
- Excès = `mean(ret FOMC announce_day) − mean(ret non-FOMC)` **> 0**, t-stat (Welch two-sample)
  **> 2** sur l'échantillon complet.

**(B) encore tradable post-publication — requis**
- L'excès reste **> 0 et t > 2** sur le sous-échantillon **2015→** (data propre).
- Coût négligeable ici (≈8 events/an, ~1-2 j d'exposition/event) → ce n'est PAS le tueur ;
  le tueur testé est l'**érosion / priced-in**.

### Décision pré-enregistrée
- **(A) ∧ (B) ⇒ GO**.
- **(A) ∧ ¬(B) ⇒ KILL priced-in** : drift réel historiquement mais mort/érodé après publication
  (comme les unlocks). **Verdict plausible.**
- **¬(A) ⇒ KILL** : pas de drift même historiquement dans nos données.

## Données & implémentation
- yfinance OHLC ajusté, cache `data/`. Audit : `deflated_sharpe` porté depuis factor-harvest.
- Sortie : verdict console + `docs/FINDINGS-overnight.md`, `docs/FINDINGS-fomc.md`.

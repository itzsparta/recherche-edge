# FINDINGS — Piste 7 : RV BTC/ETH cointegration daily

**Statut : KILL (Phase-1, 2026-06-23).** Spread non-stationnaire IS *et* OOS. Thèse invalide
avant tout backtest — le gate pré-enregistré a tranché en ~30 min comme prévu.

## Hypothèse testée

`log(BTC/ETH) = log(BTC) − log(ETH)` (ratio 1:1 pré-enregistré) serait I(0) : il existerait un
niveau d'équilibre économique entre les deux actifs, et chaque excursion > σ se corrigerait →
pairs-trading long/short exploitable. Edge présumé structurel (non-prédictif : on parie sur la
*relation*, pas la direction ; mandats ETF crypto séparés + leg-risk décourageraient les gros).

## Gate pré-enregistré (EDGE-IDEAS-LOG.md, piste D)

| Gate | Critère PASS | Critère KILL |
|------|-------------|--------------|
| (A) Stationnarité IS 2017-2021 | ADF p<0.05 sur `log(BTC/ETH)` | non-significatif → KILL immédiat |
| (B) Stationnarité OOS 2022-2026 | ADF p<0.05 | non-stationnaire → KILL (rupture régime) |

PASS Phase-1 = (A) **et** (B). Tout échec = KILL, on ne backteste pas. Le spread est **fixé à 1:1**
comme pré-enregistré — on ne ré-estime pas le hedge ratio pour sauver un kill.

## Résultats

Data : Binance daily spot, BTCUSDT + ETHUSDT, 3233 barres, 2017-08-17 → 2026-06-23 (gratuit, API publique).

ADF (`regression='c'`, autolag AIC) sur `log(BTC/ETH)` :

| Segment | n | ADF stat | p-value | crit 5 % | Verdict |
|---------|---|----------|---------|----------|---------|
| IS 2017-2021 | 1575 | −1.802 | **0.3795** | −2.863 | I(1) |
| OOS 2022-2026 | 1634 | −0.953 | **0.7700** | −2.863 | I(1) |
| FULL (réf.) | 3205 | −2.312 | 0.1681 | −2.862 | I(1) |

**Gate (A) : KILL** (p=0.38). **Gate (B) : KILL** (p=0.77, encore pire OOS).

## Pourquoi le KILL est décisif (pas un artefact du 1:1)

Diagnostics non-gating (n'entrent pas dans la décision, servent à interpréter) :

- **Engle-Granger avec hedge ratio estimé** — non-cointégré partout : IS p=0.25, OOS p=0.68, FULL
  p=0.33. Donc ce n'est **pas** une faiblesse spécifique au ratio 1:1 : **aucune** combinaison
  linéaire stationnaire BTC/ETH n'existe.
- **Hedge ratio instable** : 0.696 (IS) → 1.362 (OOS). La relation elle-même **dérive** entre les
  deux périodes (compatible avec le changement de modèle économique d'ETH post-Merge, anticipé dans
  la falsifiabilité). C'est exactement la rupture de régime que le Gate B était conçu pour attraper.
- **Half-life** (si on suspendait l'incrédulité sur la stationnarité) : 305 j (IS), 572 j (OOS),
  355 j (full). Même *si* le spread était marginalement I(0), une reversion à 300-570 jours est
  **intradable** : le carry de frais/financement sur ~1 an d'attente engloutirait toute convergence.
  Triple verrou : non-stationnaire, ET non-cointégré à ratio libre, ET trop lent même dans le doute.

## Conclusion

Le ratio BTC/ETH est une **marche aléatoire**, pas un processus à retour vers la moyenne. Il n'y a
pas de « niveau d'équilibre » à exploiter — la corrélation des deux actifs (qui est réelle) ne
fournit **pas** de spread stationnaire négociable. La thèse pairs-trading RV BTC/ETH daily est morte
à la stationnarité, sans qu'aucun backtest ne soit nécessaire.

**Coût total : ~30 min** (fetch + gate), conformément à l'estimation. Le pré-enregistrement a
fonctionné : un gate falsifiable cheap a tué la thèse avant tout investissement en harness de
backtest. Reproductible via `python run_phase1.py`.

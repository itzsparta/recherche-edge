# FINDINGS — index global de la chasse à l'edge

**Index pur. Zéro duplication.** Chaque ligne pointe vers le FINDINGS canonique qui
vit à côté de son code. Source de vérité = les fichiers liés ; ce document ne fait
que les recenser. Synthèse narrative complète = [`RESEARCH-ROADMAP.md`](RESEARCH-ROADMAP.md).

**Bilan : 15 études, 0 edge déployable.** Motif unifié — *à information/prix public,
un solo sans latence/infra/capital n'a pas d'edge récoltable*.

## Pré-reframe (edge prédictif)

| Étude | Verdict | Tueur | Fichier |
|---|---|---|---|
| orderflow level-edge | KILL | no-edge brut, DSR(N=50)=0.008 | [`orderflow-bot/docs/FINDINGS.md`](orderflow-bot/docs/FINDINGS.md) |
| meme-coin pump.fun | KILL | no-edge réel Dune, t=−35, −28 %/trade | [`bots/meme-coin-solana/FINDINGS.md`](bots/meme-coin-solana/FINDINGS.md) |

## V1 — edge structurel (capacité / flux forcé)

| Piste | Étang | Verdict | Tueur | Fichier |
|---|---|---|---|---|
| 1 — primes de risque | premium réel | KILL standalone | trop faible (t=1.87) ; sleeve +0.12 seul deliverable | [`factor-harvest/docs/FINDINGS.md`](factor-harvest/docs/FINDINGS.md) |
| 2 — flux forcés (unlocks) | non-contraint vs forcé | KILL | priced-in (dérive avant date publique, ≈0 après) | [`forced-flows/docs/FINDINGS-unlocks.md`](forced-flows/docs/FINDINGS-unlocks.md) |
| 3 — niche capacité | taille fonds | KILL | spread fantôme (persistant mais ~1 k$ profondeur) | [`capacity-niche/docs/FINDINGS-niche.md`](capacity-niche/docs/FINDINGS-niche.md) |

## V2 — prime d'assurance / calendrier / carry

| Piste | Verdict | Tueur | Fichier |
|---|---|---|---|
| 4 — VRP | DOWNGRADE (faux GO) | tail catastrophique (SVXY −95 %), Sharpe aveugle au skew | [`vol-risk-premium/docs/FINDINGS.md`](vol-risk-premium/docs/FINDINGS.md) |
| 5a — overnight | DOWNGRADE | prime réelle mangée par le turnover quotidien | [`calendar-premium/docs/FINDINGS-overnight.md`](calendar-premium/docs/FINDINGS-overnight.md) |
| 5b — pré-FOMC | KILL | priced-in post-2015 (+2.3 bps, t=0.20, −93 %) | [`calendar-premium/docs/FINDINGS-fomc.md`](calendar-premium/docs/FINDINGS-fomc.md) |
| 6 — carry crypto-funding | GO Phase-1 → KILL-FORWARD Phase-2 | OOS 24m +3.8 % < hurdle 8 % ; break-even default exchange 3.6 % < gate 5 % | [`carry/docs/FINDINGS-phase2.md`](carry/docs/FINDINGS-phase2.md) |
| 7 — RV BTC/ETH | KILL | non-stationnaire IS+OOS (marche aléatoire, pas de niveau) | [`relative-value/docs/FINDINGS-rv.md`](relative-value/docs/FINDINGS-rv.md) |
| 12 — VRP crypto (defined-risk) | KILL | prime fat = artefact early-market ; compressée au niveau actions en marché mûr (2023+ BTC +5.2 pts t=1.88 ns) | [`vol-risk-premium/docs/FINDINGS-crypto.md`](vol-risk-premium/docs/FINDINGS-crypto.md) |

## V2 — « changer l'étang » (contrepartie non-optimisatrice) : 0/2

| Piste | Verdict | Tueur | Fichier |
|---|---|---|---|
| 8 — CEF discount | KILL (faux GO t=7.13) | bid-ask bounce non-capturable ; lag +1m inverse l'alpha | [`cef-discount/docs/FINDINGS-cef.md`](cef-discount/docs/FINDINGS-cef.md) |
| 10 — favorite-longshot Polymarket | KILL | biais INVERSÉ (longshots sous-cotés) ; foule arbitrée/efficiente | [`prediction-markets/docs/FINDINGS-pm.md`](prediction-markets/docs/FINDINGS-pm.md) |

## Opportunistes (bolt-on)

| Piste | Verdict | Tueur | Fichier |
|---|---|---|---|
| 9 — LST convergence (stETH/ETH) | KILL | edge one-off pré-Shapella, n=1 régime ; pinné post-redemption | [`lst-convergence/docs/FINDINGS-lst.md`](lst-convergence/docs/FINDINGS-lst.md) |
| 11 — funding cross-sectionnel | KILL | brut +52 %/an réel → net −20.6 % (turnover 8h ≈72 %/an) | [`funding-xs/docs/FINDINGS-xs.md`](funding-xs/docs/FINDINGS-xs.md) |

## Les trois sous-types de mort

1. **No-edge brut** — orderflow, meme-coin, RV BTC/ETH. Pas même de signal.
2. **Brut réel mangé par la friction** — funding-XS (turnover 8h), niche capacity,
   CEF (bounce). L'edge ≈ son coût d'extraction.
3. **Brut réel mangé par le tail / non-répétabilité** — carry (default exchange),
   LST (pré-redemption n=1), VRP actions (tail SVXY), VRP crypto (prime fat = early-market
   2021-22, compressée au niveau actions en marché mûr). La prime ≈ le risque, ou un seul régime.

## Le seul deliverable & le vrai capital

- **Trading** : sleeve trend **+0.12 Sharpe** (piste 1, robuste sur 2 univers). Modeste,
  pas un edge autonome.
- **Méthode** : le **pipeline de 15 verdicts pré-enregistrés** — dont deux faux GO
  (VRP, CEF t=7.13) et un mirage in-sample (LST t=3.14) démasqués *avant* déploiement.
  La rigueur du kill ≫ le P&L.

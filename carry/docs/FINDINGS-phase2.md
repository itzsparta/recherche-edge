# Piste 6 — Carry Phase-2 (exécution réelle + tail) : FINDINGS

**Verdict (2026-06-23) : KILL-FORWARD.** Le carry est **réel** et la Phase-1 ne mentait pas (net
delta-neutre **vrai** = +10.5 %/an reproduit avec legs spot/perp séparés, basis ≈ 0, frais réels
1.14 %/an ≈ le forfait 1.2 % supposé). **Mais il n'est pas déployable aujourd'hui** : sur la
fenêtre forward réaliste (24 derniers mois) le net tombe à **+3.8 %** — sous le hurdle 8 % — et il
est **trop maigre pour le tail exchange** (break-even faillite p\* = 3.6 %/an < gate 5 %). Le
+10.5 % historique était de la **chance de régime** (2020-21), pas un edge déployable. (C) FAIL,
(D) FAIL.

> Reproduire : `python run_phase2.py`. Données : funding 8h (Phase-1) + **klines spot réels**
> (api.binance.com) + **perp réels** (fapi.binance.com) 1j & 8h, 2019-09 → 2026-06.

## Ce que la Phase-2 a corrigé vs Phase-1
| caveat Phase-1 | mesure Phase-2 | effet |
|---|---|---|
| markPrice proxy (legs circulaires) | P&L delta-neutre **vrai** : spot réel − perp réel | **basis = −0.10 %/an ≈ 0** → la neutralité tient avec de vrais legs, corr(pnl,btc) **−0.10** |
| frais forfait 1.2 % | taker spot 0.10 % + perp 0.04 % + slip + rééq. mensuel | **fee réel 1.14 %/an** → l'hypothèse Phase-1 était honnête |
| historique flatteur | walk-forward **OOS 24 mois** | net **+10.5 % → +3.8 %** |

## (C) Survie exécution — **FAIL**
- net_ann **full** +10.5 % reproduit (legs réels) — donc le GO Phase-1 n'était PAS un artefact proxy.
- **Compression brutale, frais réels inclus** : 2021 **+29.6 %** → 2024 +10.9 % → 2025 +4.0 %
  → 2026 **−0.5 %** (négatif YTD net).
- **OOS 24 mois (2024-06 → 2026-06) : net +3.8 %** (gross +4.9 %, t mensuel +4.18, dd −0.8 %).
  Le carry est **réel et lisse** sur le forward — juste **maigre**.
- delta-neutre confirmé legs réels (|corr| 0.08 < 0.20). ✓
- **net OOS +3.8 % > hurdle 8 % ? NON.** → (C) FAIL. Le forward ne paie pas le dérangement
  opérationnel + le tail pour un solo (≈ risk-free + 0, pas le doublement requis).

## (D) Survie tail — **FAIL**
- **(D1) liquidation = PAS le tueur.** Cross-margin (long spot offsete short perp 1:1) → équité
  plate → liquidation ≈ 0. Même **isolé/naïf** : le pire move 8h de l'histoire (**+36.2 %**) ne
  liquide pas à 2x ; 3x ne liquide que 0.013 % des barres. Gérable. ✓ (le seul gate qui passe)
- **(D2) risque exchange = le tueur.** net OOS +3.8 % → **break-even faillite exchange
  p\* = 3.62 %/an**. **< gate 5 %.** Un risque d'effondrement d'exchange de seulement 3.6 %/an
  suffit à annuler l'EV — et **post-FTX, 3.6 %/an n'est pas implausible**. Le carry n'est pas
  assez gras pour porter son propre tail. → (D2) FAIL.
- (D3, diag) pire drawdown OOS −0.8 % : lisse, recouvrable. Le problème n'est pas la volatilité,
  c'est la **maigreur** face au tail binaire.

## La leçon (qui aiguise la thèse du programme)
Phase-1 (GO) disait « le carry est réel, structurel, market-neutral, robuste régime » — **vrai**,
et confirmé ici avec de vrais legs. Phase-2 ajoute la couche déploiement : **réel ≠ déployable**.
L'arbitrage cash-and-carry a **compressé** la prime sous le seuil où elle paie son risque exchange
pour un solo. Donc :
- « edge **structurel** ≠ prédictif » **tient** : le carry survit là où les 6 edges info/prix-public
  sont morts (il est réel, +3.8 % net forward, pas zéro).
- **mais** « structurel ≠ gratuit » : la prime structurelle est **arbitrée jusqu'au coût** (ici le
  tail exchange). Le marché ne laisse pas un carry market-neutral à +10 % traîner — il l'a ramené
  à ~risk-free + peanuts.

## Décision
**KILL-FORWARD.** Pas de déploiement de capital réel. Le carry reste le seul phénomène réel du
programme (à documenter comme tel), mais sa magnitude forward (+3.8 %) ne franchit ni le hurdle de
dérangement (8 %) ni le test de tail (break-even 3.6 % < 5 %). Re-tester **seulement si** le funding
se ré-élargit durablement (nouveau cycle de levier long) — surveillable via `run_phase2.py` sur
fenêtre glissante, mais rien à déployer aujourd'hui.

## Bilan programme (V1 + V2, clos)
**7 pistes, 0 edge déployable.** Trend (KILL standalone), unlocks (KILL priced-in), niche (KILL
spread fantôme), VRP (DOWNGRADE tail), overnight (DOWNGRADE turnover), pré-FOMC (KILL priced-in),
**carry (GO Phase-1 → KILL-FORWARD Phase-2 : réel mais compressé sous le hurdle + tail-fragile).**
Motif final : tout edge à info/prix public est **mangé** ; le seul edge **structurel** est **arbitré
jusqu'au coût**. Le deliverable réel = le **pipeline de 7 kills pré-enregistrés**, pas un P&L.

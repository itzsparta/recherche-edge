# FINDINGS — Piste 8 : CEF discount mean-reversion

**Statut : KILL (2026-06-23) — faux GO démasqué par la microstructure (bid-ask bounce).**

La piste est allée **plus loin que les 8 autres** : Gate A franchi nettement, Phase-2 brut tout-vert
(le premier « GO » provisoire du programme). Elle meurt sous le test de robustesse — le runner naïf
rendait GO, le lag d'entrée a tué le mirage. Même motif que le faux GO VRP (Sharpe 1.86 aveugle au
tail) : ici le Sharpe net 1.32 / t=7.13 était aveugle au **bid-ask bounce**.

## Hypothèse

`discount(t) = (price − NAV)/NAV` des CEF est I(0) → acheter le décoté / shorter le premium, capter
la convergence. Inarbitrable par structure (pas d'AP, ≠ ETF) ; énigme Lee-Shleifer-Thaler.

## Ce qui a passé (et pourquoi c'était un mirage)

Data : CEFConnect, 354 fonds, panel mensuel 1996-2026 (premium hebdo → fin de mois).

**Gate A (stationnarité) — PASS net.** 62.1 % des fonds (210/338) rejettent la racine unitaire à 5 %,
pooled démoyenné ADF p≈0, half-life médiane 13 semaines. *Mais* cette half-life était **gonflée par le
bounce** : un AR(1) sur une série prix/NAV qui oscille bid↔ask montre une fausse réversion rapide.

**Phase-2 brut — tout-vert (faux GO).** L/S quintile sur z-score trailing 24m, rebal mensuel,
rendement market-neutral `Δlog(1+prem)` :

| Gate | Valeur | Statut |
|------|--------|--------|
| B brut | +17.75 %/an, t=14.85 | PASS |
| C net (30bps + borrow 4%) | +8.41 %/an, t=7.13 | PASS |
| D deux jambes | long +0.65 %/mois, short −0.83 %/mois | PASS |
| E intra-catégorie net | +4.74 %/an, t=3.80 | PASS |
| F régimes (2018/2020/2022) | +0.14 / +1.92 / +1.23 %/mois | PASS (3/3) |
| G DSR (N=6) | 1.000 | PASS |
| break-even cost | 77 bps one-way | (marge mince) |

## Ce qui l'a tuée — chasse au mirage (run_robust.py)

| Test | net base | net stressé | Verdict |
|------|----------|-------------|---------|
| **Lag d'entrée +1 mois** (bounce) | +8.41 % t=7.13 | **−4.01 % t=−4.00** (survie −48 %, **inversion**) | 🔴 alpha = bounce 1-période |
| Borrow short 15 %/an (réaliste) | +8.41 % | −2.59 % t=−2.19 | short = premium-CEF = hard-to-borrow |
| Borrow 30 %/an | +8.41 % | −17.59 % | short infaisable |
| **Déployable : intra-cat + lag1 + long-only** | — | **−0.64 % t=−0.64** | 🔴 **ZÉRO** |

**Le test du lag est décisif.** Une vraie convergence à half-life 3 mois garderait ~70 % de l'alpha
avec un lag d'entrée d'1 mois. Ici l'alpha **s'inverse** (−48 %) → toute la « réversion » vivait dans
le premier mois = **bid-ask bounce** : on sélectionne long les fonds dont le prix de clôture a imprimé
près du bid (premium bas → z bas), ils rebondissent au mid le mois suivant, on comptabilise un gain
**non-capturable en pratique** (on aurait acheté à l'ask). Les CEF sont illiquides → spreads larges →
bounce gros. Exactement l'illiquidité censée être le « moat » qui fabrique le faux signal.

## Caveats restants (n'auraient fait qu'empirer)

- **Survivorship bias non corrigé** : l'univers CEFConnect = fonds **vivants**. Les CEF liquidés /
  fusionnés (souvent les décotés qui n'ont jamais reconvergé = value-traps morts) sont **absents** →
  biaise « acheter décoté » vers le haut. Corriger exigerait une base point-in-time avec délistés
  (CRSP/Morningstar payant). Le vrai edge déployable est ≤ le −0.64 % déjà obtenu.
- **Short infaisable** : les CEF à premium portent la moitié de l'alpha brut mais sont précisément les
  hard-to-borrow ; borrow réaliste 15-30 % détruit la jambe.

## Conclusion

L'inefficience structurelle (discount inarbitrable, énigme réelle) **existe** mais n'est **pas
récoltable par un solo** : ce qui ressemble à une convergence tradable à fréquence mensuelle est
dominé par le bid-ask bounce non-capturable, et la forme proprement déployable (intra-catégorie, lag
réaliste, long-only) rend **zéro net de frais**. Le motif unifié tient : *structurel ≠ gratuit* — ici
la prime est mangée par la **friction de microstructure** (cousine du tail qui a mangé le carry).

**Valeur de ce kill** : c'est le faux positif le plus convaincant du programme. Un retail aurait tradé
le +8.41 % t=7.13. Le pré-enregistrement (lag, borrow stressé, long-only séparé) l'a démasqué en un
run. Reproductible : `run_phase1.py` (Gate A), `run_phase2.py` (faux GO), `run_robust.py` (kill).

# SPEC — Piste 13 : Momentum cross-sectionnel crypto (market-neutral, pré-enregistré)

> Écrit **avant** tout chiffre. Protocole partagé `RESEARCH-ROADMAP.md` : hypothèse + règle +
> critère de succès ET de kill fixés avant de voir le moindre résultat. (Leçon orderflow/VRP/CEF.)

## Hypothèse d'edge

Dans un univers **fixe** de cryptos liquides, le **classement par rendement passé** prédit la
coupe transversale des rendements futurs : long le tercile des plus forts / short le tercile des
plus faibles, equal-weight, **dollar-neutral**. On récolte un premium **cross-sectionnel**
(sous-réaction / continuation), documenté hors crypto (Jegadeesh-Titman) et en crypto
(Liu-Tsyvinski-Wu 2022, facteur momentum hebdo).

## Pourquoi distinct des pistes mortes (ne pas re-tuer un mort)

- **≠ piste 1 (trend time-series)** : ici c'est **cross-sectionnel** (rang relatif), pas le signe
  absolu du momentum d'un actif.
- **≠ piste 11 (funding-XS)** : le signal est le **rendement de prix passé**, pas la dispersion de
  funding (qui payait brut mais mourait au turnover 8h).
- **≠ piste 7 (RV BTC/ETH)** : panier de N actifs, pas une paire cointégrée.
- **La market-neutralité annule le drift** — exactement le confound qui a tué l'étage-1 orderflow
  (smoke mono-régime ne séparait pas l'edge du drift) et le swing-continuation (les deux jambes
  perdaient dans les deux régimes). Un L/S transversal soustrait le bêta de marché par construction.

## Le null honnête (= verdict attendu a priori)

Prior bas (13 kills). Les morts probables, pré-enregistrées :
1. **Le turnover mange le brut** — momentum crypto = rapide (hebdo) → rotation élevée → net négatif.
   **C'est le tueur le plus probable (motif funding-XS : brut +52 % → net −20 %).**
2. **Concentration** — le P&L vit sur 2-3 alts (funding-XS : 51 % sur ETC+BNB) → pas robuste.
3. **Jambe short morte / long-bêta déguisé** — seul le long paie (leçon swing : les DEUX jambes
   doivent payer en market-adjusted).
4. **Artefact early-market** — premium concentré en 2021, absent en marché mûr (leçon VRP crypto / LST).

## Univers (FIXE — déterministe, aucun cherry-pick)

- **Tous les perps USDT-margined Binance (fapi)** dont la **première kline daily est < 2021-06-01**
  ET qui ont des données continues jusqu'à la fin d'échantillon. Liste figée par cette règle, pas
  par un classement de cap actuel.
- **Perps** (pas spot) car la **jambe short doit être réellement exécutable** ; le funding sur un
  hold ~hebdo est petit (modélisé en coût, pas en signal).
- **⚠ Survivorship pré-enregistré** : les perps delistés (alts morts) sont **exclus de fait** →
  l'univers est **biaisé survivants** → les résultats sont **optimistes**. Conséquence pour la
  décision : un **net ≤ 0 est robuste** (le réel serait pire) ; un **net > 0 exigerait une
  correction survivorship AVANT tout GO** (même logique que CEF/unlocks).
- Bench passif = **BTC buy-hold** (le « market-neutral » se vérifie contre lui).

## Signal & exécution (FIXE)

- **Fréquence** : rebal **hebdomadaire** (horizon documenté du momentum crypto). Daily klines.
- **Formation** : à la fin de semaine `t`, rang par **rendement trailing L semaines**, **L = 4**
  pré-spécifié (≈ 28 j). DSR diagnostic sur L ∈ {1, 2, 4, 8} — jamais pour sélectionner.
- **Gap anti-bounce** : entrée au close de `t+1 jour`, pas au close de formation `t`. **Leçon CEF** :
  entrer sur le print de formation capture un bid-ask bounce non-réel ; le gap d'un jour le purge.
- **Portefeuille** : long tercile haut / short tercile bas, **equal-weight**, dollar-neutral.
  Univers de la semaine = perps avec ≥ L semaines d'historique à `t`.
- **Rendement** : forward hebdo de chaque jambe, `brut = mean(longs) − mean(shorts)`.
- **Coût pré-enregistré** : **10 bps/côté** × turnover (entrée+sortie des deux jambes) + **funding
  porté** (proxy 3 bps/semaine/côté). On reporte AUSSI le **break-even cost** (honnête, leçon CEF/funding-XS).

## Gates de décision (pré-enregistrés)

- **(A) brut > 0, t > 2** sur l'échantillon hebdo complet, multi-régime.
- **(B) net > 0, t > 2** après turnover + funding. ← **le combat se joue ici.**
- **(C) les DEUX jambes paient** : la jambe short **sous-performe** le marché (short market-adjusted
  > 0) ET la jambe long sur-performe — pas seulement du long-bêta. (Leçon swing.)
- **(D) market-neutral** : `|corr(pnl_net, rendement BTC)| < 0.2`.
- **(E) robustesse** : (i) **drop-top-3 noms** ne tue pas le signe (≠ concentration funding-XS) ;
  (ii) **split régime** ≥ majorité positive (bull-2021 / bear-2022 / 2023 / 2024+) ;
  (iii) **mirroir** (inverser le signe) doit **perdre**.
- **(F) DSR** : DSR(best, N = L ∈ {1,2,4,8}) > 0.95.
- **(G) marché mûr** : net > 0 sur le **sous-échantillon 2023+** (pas seulement 2021). Leçon VRP
  crypto / LST : un premium qui ne vit qu'en early-market n'est pas répétable.

## Décision pré-enregistrée

- **Tous (A)-(G) ⇒ GO PROVISOIRE** : correction survivorship (univers point-in-time, alts morts
  inclus) + Phase 2. Chasse au mirage post-GO obligatoire (leçon CEF).
- **(A) ∧ ¬(B) ⇒ KILL** : brut réel mangé par le turnover. **Verdict le plus probable** (motif funding-XS).
- **¬(C) ⇒ KILL** : long-bêta déguisé, pas un edge transversal.
- **¬(G) ⇒ KILL** : artefact early-market non-répétable.
- **¬(A) ⇒ KILL** : pas de signal cross-sectionnel (sanity).

## Falsifiabilité (comment ça meurt)

1. Net ≤ 0 au coût pré-enreg → KILL (B). 2. Signe porté par ≤ 3 alts → KILL (E-i). 3. Short ne paie
pas → KILL (C). 4. Positif seulement 2021 → KILL (G). 5. corr|BTC| ≥ 0.2 → c'est du bêta, pas neutre.

## Données & implémentation

- **Source** : klines daily Binance perp (fapi), fetch paginé réutilisé de `carry/data_prices.py`.
  Cache CSV `data/`, gratuit.
- **Audit** : `audit.py` (DSR Bailey-López de Prado) copié verbatim depuis `vol-risk-premium/`.
- **Sortie** : `run_xs_mom.py` (gates A-G) + verdict console + `docs/FINDINGS.md`. Index global + ROADMAP à jour.

## Verdict attendu a priori

Le brut momentum est probablement **réel** (documenté). Le programme prédit la mort en **(B)**
(turnover, le tueur funding-XS) ou **(G)** (early-market, le tueur VRP-crypto/LST). La seule raison
de dépenser ce run cheap : la market-neutralité **annule le drift** qui a contaminé les pistes
directionnelles — donc si un net survit au turnover ET au marché mûr ET aux deux jambes, ce serait
le profil le plus propre du programme. Falsifiable en un run free-data.

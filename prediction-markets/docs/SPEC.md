# SPEC — Piste 10 : favorite-longshot bias (Polymarket) — pré-enregistré

> Écrit AVANT tout chiffre. Étang structurellement ≠ : contrepartie récréative (parie pour le frisson,
> pas l'EV). Polymarket = CLOB **sans vig** (≠ bookmaker) → si le biais existe il est peut-être
> capturable, contrairement aux books classiques où la marge maison le mange.

## Hypothèse d'edge

Dans un marché à forte participation récréative, les **longshots** (issues à faible probabilité) sont
**surcotés** : leur prix implicite > leur fréquence de réalisation. Donc fade systématique des longshots
(vendre/shorter l'issue chère-et-improbable, ou backer le favori complémentaire) = EV > 0.

## Source de l'inefficience structurelle

Contrepartie ≠ fonds optimisateur. Le biais persiste car le participant marginal **ne maximise pas
l'EV** (biais cognitif lottery-like : on surpaie le ticket qui rapporte gros). Aucun desk quant ne
« corrige » (barrières régul/réput/capacité). Documenté massivement en paris hippiques/sportifs.

## Données (gratuites, publiques)

- **Gamma** `markets?closed=true&order=volumeNum` → marchés résolus : `outcomes`, `outcomePrices`
  (résolution : "1" = gagnant), `clobTokenIds`, `startDate`/`endDate`, `volumeNum`, `events[0].title/slug` (catégorie).
- **CLOB** `prices-history?market={tokenId}&interval=max&fidelity=1440` → `history:[{t,p}]` = prix mid quotidien.

## Snapshot ex-ante (pré-enregistré)

Prix implicite = prix du token au **midpoint temporel** du marché `t_mid = start + (end−start)/2`
(point d'historique le plus proche). Choisi car : toujours défini, jamais adjacent à la résolution (pas
de contamination de convergence), comparable entre marchés. Robustesse reportée : prix à endDate−24h.

Chaque marché binaire fournit **2 legs** : (p_mid, y0) pour token0 et (1−p_mid, 1−y0) pour token1, où
y0=1 si `outcomePrices[0]=="1"`. Pooling des legs sur tous marchés → couvre tout [0,1]. (Legs d'un même
marché tombent dans des buckets opposés ⇒ quasi-indépendants au sein d'un bucket donné.)

## Gates de décision (pré-enregistrés, cheap-first)

### Gate A — le biais existe (Phase-1, ce run)

Univers : marchés binaires résolus, volume ≥ 5 000 $, durée ≥ 1 j, ≥ 2 points d'historique. Cible N > 500.

- **(A) longshot overpricing** : sur les legs avec implied < 0.10, `mean(realized) < mean(implied)`
  avec t-stat de l'écart `(realized − implied)` **< −2** (longshots se réalisent SIGNIFICATIVEMENT moins
  que leur prix). PASS = biais réel exploitable en théorie.
- **KILL** : écart non-significatif (bien calibré) OU positif (biais inverse — Polymarket trop efficient).
- **(C dose-réponse)** : l'écart (realized−implied) doit être **monotone** (plus négatif quand implied
  ↓). Plat/non-monotone = bruit (cf. fantôme piste 3).
- **(E split catégorie)** : l'écart longshot doit apparaître dans **≥ 2 catégories** (politique / sport /
  crypto / autre). 1 seule = artefact.

### Gate B — net après friction (Phase-2, seulement si A PASS)

Tueur probable, analogue exact du bid-ask bounce CEF : **les longshots ont le spread relatif le plus
large**. Fader un longshot à 3¢ = vendre au bid ; l'edge brut doit dépasser le spread.

- Modèle de coût pré-enregistré : spread absolu 1¢ (demi-spread 0.5¢) + slippage, soit coût = 0.005 $/share
  par côté. Sur un longshot à p, le coût relatif = 0.005/p (énorme quand p petit). Gas Polygon ≈ négligeable.
- **(B) net > 0** : EV du fade-longshot après ce coût. net ≤ 0 = spread mange le biais → KILL.
- **(D) capacité** : profondeur réelle au prix ciblé (≠ fantôme piste 3). Ordre de grandeur $ exploitable.

## Falsifiabilité

1. Polymarket bien calibré / biais inverse → KILL Gate A (probable : traders crypto sophistiqués, arb présents).
2. Biais réel mais < spread du longshot → KILL Gate B (l'analogue du bounce CEF).
3. Biais dans 1 seule catégorie → artefact (Gate E).
4. Capacité dérisoire → pas worth it (Gate D).

## Verdict attendu a priori

Prior bas (9 kills). Deux issues plausibles : (a) Polymarket trop efficient → KILL Gate A propre ; (b)
biais réel mais mangé par le spread du longshot → KILL Gate B (rime avec CEF). Le « sans vig » donne une
chance réelle que (b) survive là où un book classique ne pourrait pas — c'est ce qui rend la piste digne
du test.

## Verdict RÉEL (2026-06-23) — KILL Gate A, hypothèse INVERSÉE

Issue (a) confirmée, en pire : non seulement pas de biais favorite-longshot, mais le **pattern inverse**
(favoris surcotés gap −0.08, longshots sous-cotés gap +0.011 t=+2.26). Fader les longshots perdrait.
Aucune catégorie ne sauve (Gate E). N=2793 marchés. Le pattern inverse n'est pas exploité (post-hoc +
même friction que CEF). Détail : [`FINDINGS-pm.md`](FINDINGS-pm.md).

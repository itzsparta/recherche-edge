# FINDINGS — Piste 3 : niche contrainte en capacité (spreads cross-exchange small-caps)

Verdict rendu 2026-06-22, contre la spec **pré-enregistrée** ([`SPEC-niche.md`](SPEC-niche.md)).
Aucun gate de décision modifié après résultats (seuls 2 filtres de **validité données** ajoutés
avant le run de persistance — collision de ticker —, documentés en §Amendement de la SPEC).

## Verdict : KILL — spread réel mais **fantôme** (top-of-book sur carnet vide)

Le spread cross-exchange sur small-caps **existe et persiste** (pas du flicker), mais il est
**non capturable** : ~1 $ de profondeur derrière les gros spreads, **pas** de signature
structurelle de capacité, et la capacité totale déployable ≈ **1 253 $** (sur-estimée). Même le
**meilleur cas** pré-enregistré (inventaire pré-positionné, frais seuls, zéro retrait) meurt sur
la profondeur. La seule arme structurelle d'un solo (capacité) est ici un mirage.

## Les chiffres qui tuent

Run : **25 snapshots × ~60 s** (3 venues Binance/MEXC/Gate), 902 paires avec ≥1 cross valide.

### (A) Le spread existe-t-il ET est-il solo-capturable ? — FAIL
| Test | Résultat | Verdict |
|---|---|---|
| Persistance (net>0 sur ≥60 % snaps) | **79 paires** (seuil ≥20) | PASS |
| t cross-paires du net moyen | **+7.07** (diagnostic) | spread **réel, pas flicker** |
| **Dose-réponse** (basse-liq > haute-liq) | Q1 +0.30 % **vs** Q4 +0.41 % | **FAIL** |
| Drop-top-3 robustesse | 76 restantes | PASS |

→ **(A) FAIL.** Le tueur pré-enregistré « flicker de quote périmée » est **réfuté** (le spread
persiste, t=7.07). Mais la **dose-réponse est plate/inversée** : le spread ne grandit **pas**
quand la liquidité baisse → ce n'est **pas** l'edge structurel « trop petit pour un fonds ». C'est
un spread quasi indépendant de la liquidité = pas la thèse capacité.

### (B) La capacité vaut-elle le coup ? — FAIL décisif
Profondeur réelle marchée (`/depth` 20 niveaux, jambe opposée supposée profonde = **borne haute**) :

| Paire | net moyen | capacité $ (net>0) |
|---|---|---|
| PIT | +3.01 % | **979** |
| SIS | +1.20 % | 152 |
| SKYA | +0.02 % | 118 |
| VENOM | +0.40 % | 2 |
| MEMEFI | +2.52 % | **1** |
| EDGEN | +2.30 % | **0** (rien derrière le top) |

- Paires qualifiées (cap>0) : **5** (seuil ≥10) → FAIL.
- Capacité agrégée : **1 253 $** (seuil ≥2 000) → FAIL, et c'est une **borne haute** (l'autre
  jambe n'est pas infiniment profonde).
- Les gros spreads (MEMEFI +2.52 %, EDGEN +2.30 %) ont **0-1 $** derrière le top-of-book : le
  spread est un **fantôme**, il s'évapore dès qu'on prend plus que la première unité.

→ **(B) FAIL.**

## Pourquoi c'est un KILL propre (pas de la data sale)

- **Sanity mega-caps** : BTC −0.189 %, ETH −0.184 %, XRP −0.200 %, BNB −0.192 % = ≈ −2·fee, gross≈0
  → parfaitement arbitrés. Le pipe mesure une **vraie efficience**, pas du bruit.
- **Collision de ticker** (faux +199 % : ELON/VON = tokens différents même symbole) retirée par
  filtre de validité a priori, **avant** le run. Sans ça → faux GO.
- **Persistance** réfute « c'était du bruit » : le spread est là sur 25 snapshots. Il est juste
  **vide derrière**.

## Limites honnêtes (pré-enregistrées)

- Testé 3 venues à **API gratuite** (Binance/MEXC/Gate), top-of-book + 20 niveaux. Une niche plus
  profonde pourrait exister sur des venues plus obscures, ou en **arb cross-chain** (transfert).
  MAIS : aller plus obscur = plus de risque opérationnel (retraits haltés, exit-scams, custody
  douteuse) pour le **même ~1 k$** de profondeur fantôme → exactement le « pas rentable pour un
  solo qui a un vrai métier à côté ».
- Capacité = **borne haute** (jambe opposée supposée profonde). Réel ≤ rapporté → renforce le KILL.
- Modèle inventaire pré-positionné = **meilleur cas** (zéro transfert). Le cas réel (rebalance,
  retraits, capital immobilisé 2×, tokens multi-chaînes non transférables) est **pire**.

## Conclusion

Piste 3 close. La capacité — dernière arme structurelle d'un solo — est ici un **fantôme
top-of-book** : le spread est réel et persistant mais adossé à ~1 $, sans gradient de liquidité,
≈1.25 k$ déployables (borne haute) sur des venues gratuites. Sur les venues plus obscures, le même
mince edge se paie en risque opérationnel. Capital conservé : pipeline cross-exchange (snapshots
multi-venue, persistance, profondeur marchée) réutilisable. **3/3 pistes du programme mortes** —
voir [`../RESEARCH-ROADMAP.md`](../RESEARCH-ROADMAP.md) §bilan.

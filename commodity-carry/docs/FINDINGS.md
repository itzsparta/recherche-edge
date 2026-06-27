# FINDINGS #30 — Carry commodités (énergie) : **DOWNGRADE** (carry symétrique KILL ; résidu sleeve faible sub-barre)

**Verdict : la prime carry commodité dans sa forme FAITHFULLE (symétrique, les 2 côtés paient) est
FALSIFIÉE en énergie. Le résidu = une prime long-backwardation à un seul côté, RÉELLE et orthogonale
aux actions ET au trend, mais qui (a) échoue la barre de significativité DSR>0.95, (b) a décayé à
plat 2009-2019, (c) est narrow (énergie seule). → Pas d'edge déployable standalone (KILL de l'edge) ;
candidat sleeve faible orthogonal (+0.04 Sharpe sur le méta) MAIS sous la barre que trend a passée
→ NON promu deliverable.**

Pré-enregistré : [`SPEC.md`](SPEC.md). Code : [`../run_carry.py`](../run_carry.py),
[`../carry_vs_meta.py`](../carry_vs_meta.py). Data : EIA v2 contrat 1&2, gelée 2024-04 (EIA a coupé
le feed futures daily). Construction 100% EIA, zéro splice (`ret=C1_{t+1}/C2_t−1`, `carry=C1/C2−1`).

## Univers (5 marchés énergie, term structure propre)

| marché | histo C1&C2 | note |
|---|---|---|
| WTI | 1983→2024 | brut |
| Heating oil | 1980→2024 | produit |
| NatGas (Henry Hub) | 1994→2024 | indépendant |
| Gasoline RBOB | 2005→2024 | produit |
| Propane (Mont Belvieu) | 1993→**2009** | discontinué 2009 |

Breadth effectif ~2-3 paris indépendants (produits corrélés au brut ; NatGas + Propane semi-indép.).
**Caveat breadth pré-enregistré** : t>2 = barre haute à ce breadth ; un t<2 n'est pas sur-interprété.

## Gates (pré-enregistrés)

| Gate | Résultat | |
|---|---|---|
| **A1** Sharpe>0 ∧ t>2 | Sharpe **0.31**, t=**1.96** | **FAIL** (d'un cheveu) |
| **A2** les 2 côtés paient | long-backw **+1.54%/mo** (t=3.3*, n=636) ∧ short-contango **+0.03%** (t=0.1, n=925) | **FAIL** |
| **A3** ≥3/5 régimes positifs | 4/5 (pré-GFC +276%, GFC08 +78%, 2010s **+3.4%**, COVID20 −30%, 2021+ +36%) | PASS |
| **A4** drop-one tous Sharpe>0 | 0.15 → 0.38 (WTI le + important) | PASS |
| **A5** DSR(best,N=4)>0.95 | **0.895** (N=10 : 0.814) | **FAIL** |
| **B1** \|corr actions\|<0.30 | corr(SPY) = **−0.12** | PASS |
| **B2** sleeve améliore | +0.04 sur le méta (voir ci-dessous) | PASS |

`*` Le t=3.3 du côté long est **clusterisé** (cellules market-mois corrélées : quand WTI est
backwardaté, heating/gasoline le sont aussi) → **surévalué**. Le t honnête, qui intègre la
corrélation, est celui du **portefeuille = 1.96**.

## A2 = le finding central : prime ASYMÉTRIQUE, pas un carry symétrique

- **Long-backwardation paie** : +1.54 %/mois (réel — prime de normal-backwardation de Keynes,
  le spéculateur long touche le roll yield que les producteurs-hedgers cèdent).
- **Short-contango ne paie RIEN** : +0.03 %/mois (t=0.1). Le contango **ne prédit pas** la baisse
  du sous-jacent (asymétrie storage / convenience yield : en glut, le spot peut quand même monter —
  2009, 2020). Shorter le contango = pur drag.
- → La thèse « carry = prime de risque symétrique récoltable long-short » est **falsifiée**. Ce qui
  reste est une **prime long-backwardation directionnelle** (long-only), pas un carry market-neutral.

## Décroissance régime (A3 nuance qui plombe)

Le gros de la performance est **pré-2009** (+276 %). La décennie **2010s = +3.4 % plat** : l'ère
shale a aplati/contangoïsé la courbe (les USA deviennent swing producer, la backwardation structurelle
disparaît). Revival **2021+ (+36 %)** = retour de la backwardation post-COVID. → La prime n'existe
**que dans les régimes de backwardation**, devenus rares post-shale. Difficile à séparer d'un timing
de beta énergie haussier, malgré la corr actions faible.

## B2 : le résidu EST un sleeve orthogonal (mais petit et sub-barre)

Échantillon commun 2003-2024 (255 mois), vs le méta 60/40 + trend :

| | corr(carry, ·) | Sharpe standalone |
|---|---|---|
| 60/40 (cœur) | −0.09 | 0.91 |
| trend (32 futures) | **+0.08** | 0.25 |
| carry énergie | — | 0.23 |

| portefeuille | Sharpe |
|---|---|
| 60/40 | 0.906 |
| + trend 20 % | 0.955 |
| + trend 20 % + carry 15 % | **0.997** |

**Increment du carry par-dessus (60/40+trend) = +0.042 Sharpe.** corr(carry,trend)=+0.08 → **pas
redondant** : c'est un vrai 3e axe orthogonal, additif comme l'est trend (+0.049). MAIS l'increment
est petit, et le standalone **échoue DSR 0.895 < 0.95** — la barre de significativité que **trend a
passée (0.988)**. Donc : orthogonal et additif, mais **sous la barre** → on ne le promeut PAS au rang
de deliverable robuste. [[feedback-gate-override]] (le « ooh, un 2e sleeve » cassé par la barre DSR).

## Verdict

**DOWNGRADE** (label pré-enregistré pour A2-fail) avec contenu disciplinné :

1. **Carry symétrique récoltable = KILL** : short-contango mort (t=0.1), portefeuille t=1.96<2,
   DSR 0.895<0.95, décayé post-shale. La prime de risque carry, faithfully, n'est pas là.
2. **Résidu long-backwardation = réel mais sub-barre** : orthogonal aux actions (−0.12) ET au trend
   (+0.08), +0.04 Sharpe sur le méta — un **candidat sleeve faible**, MAIS sous le seuil DSR et
   régime-dépendant → **non promu** au deliverable (reste dominé par / au niveau de trend qui, lui,
   passe la barre).
3. **NARROW** : énergie seule (~2-3 paris), le carry commodité large (grains/métaux/softs,
   Gorton-Rouwenhorst) reste **non testable en data libre** — ce verdict ne le confirme ni l'infirme.

**Bilan programme : pas de nouvel edge déployable** (30 études, 0 edge). Le deliverable trading reste
**mono-sleeve trend** ; le carry-backwardation énergie est un **2e axe orthogonal noté mais sub-barre**,
pas une promotion. Leçon : la prime carry énergie est **réelle mais à un seul côté et régime-dépendante**
— le côté short-contango, qui ferait d'elle un vrai carry market-neutral, n'existe pas.

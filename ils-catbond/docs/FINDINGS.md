# FINDINGS #31 — Prime ILS / cat-bond : **DOWNGRADE** (prime réelle + la mieux décorrélée, mais sub-hurdle + cyclique)

**Verdict : la prime ILS est RÉELLE et offre la MEILLEURE orthogonalité du programme (corr SPY +0.10,
increment sleeve +0.107) — elle esquive bien le mur d'accès (interval funds retail existent) et la
mort "arbitré jusqu'au coût". MAIS elle échoue le hurdle tail-approprié (excès EW +2.56 % < 3 %,
t=1.51 < 2), le flagship accessible SRRIX rend ~0 (t=0.17), et tout le positif est LOADÉ sur le
hard-market post-2022 (soft 2013-17 = +0.0 %/an), un pic de cycle qui mean-reverte. Skew −2.95 +
stress-corr +0.46 cavèrent la décorrélation dans la queue. → DOWNGRADE, NON promu deliverable.**

Pré-enregistré : [`SPEC.md`](SPEC.md). Code : [`../run_ils.py`](../run_ils.py). Data : NAV total-return
(fees inclus) interval funds ILS + BIL (T-bill) + SPY/IEF, yfinance free. 2013-2026, 160 mois.

## Résultat (excès sur T-bill, net de fees, par fund)

| fund | début | n | excès ann | t | vol | corr SPY | pire an |
|---|---|---|---|---|---|---|---|
| **SRRIX** (Stone Ridge, flagship) | 2014 | 150 | **+0.54 %** | **+0.17** | 11.5 % | +0.04 | −11.4 % |
| SHRIX | 2013 | 160 | +2.43 % | +1.46 | 6.1 % | +0.20 | −6.6 % |
| **XILSX** (Pioneer/Amundi) | 2015 | 138 | **+5.03 %** | **+3.81** | 4.5 % | +0.04 | −7.2 % |
| EMPIX (secondaire, court) | 2022 | 54 | +4.33 % | +3.63 | 2.6 % | +0.25 | +0.1 % |
| **ILS equal-weight (gating)** | 2013 | 160 | **+2.56 %** | **+1.51** | 6.2 % | +0.10 | — |

EW : Sharpe(ann) +0.41, **skew −2.95**.

## Gates

| Gate | Résultat | |
|---|---|---|
| **A1** excès>3 % ∧ t>2 | +2.56 %, t=1.51 | **FAIL** |
| **A2** survit au tail (années cat incl.) | 11/14 années +, full>0 | PASS |
| **B1** \|corr SPY\|<0.20 | corr **+0.10** (normal) / **+0.46 (stress)** | PASS (normal) ⚠️ stress |
| **B2** sleeve améliore le méta | increment **+0.107** sur 60/40+trend | PASS (mais régime-gonflé, voir infra) |

## Les 3 raisons de NE PAS sur-vendre (discipline 2 sens)

### 1. Le hurdle tombe — et le flagship le confirme
EW +2.56 % < 3 % (hurdle pré-enregistré sur principe : compense queue ouragan + illiquidité interval-
fund + fees). t=1.51 < 2. **SRRIX**, le fund le PLUS gros / accessible, rend **+0.54 % t=0.17 ≈ ZÉRO**
net — la réalité du retail médian. XILSX clear (+5 % t=3.8) mais **cherry-pick = survivorship** (yfinance
n'a que les funds survivants ; sélection de fund ≠ prime structurelle). L'equal-weight est la mesure
honnête, et elle échoue.

### 2. Tout le positif est un PIC DE CYCLE post-catastrophe (pas un steady-state)
Régime : **soft ≤2017 = +0.0 %/an** (58 mois) ; **hard 2023+ = +10.6 %/an** (42 mois). Années cal. :
2017 **−8.4 %**, 2018 −4.2 % (pertes cat / soft) ; 2023 **+20.5 %**, 2024 +14.8 %, 2025 +13.2 %. La
réassurance a un CYCLE : Hurricane Ian (2022) a fait spiker les spreads → hard market 2023-2025 → le
capital revient → compression à venir. Le +2.56 % full-sample = moyenne de [0 % soft] et [+10 % hard].
**Le steady-state net-de-fee ≈ T-bill** ; le récent est cycle-high, pas répétable. Symétrique de la
décroissance shale du carry #30, mais ici le régime FAVORABLE est le récent (donc trompeur à l'achat).

### 3. La décorrélation a des caveats exactement dans la queue
- **skew −2.95** = signature peso (ramasser des pennies, encaisser une année −8/−11 % sur cat). Le
  Sharpe 0.41 surévalue (queue gauche brutale, non gaussienne).
- **stress-corr +0.46** : sur les pires mois actions (décile bas SPY), l'ILS corrèle **+0.46**, pas 0
  (choc taux 2022 = mark-to-market simultané actions/bonds/ILS). Le diversificateur faiblit **quand on
  en a besoin**. corr +0.10 "normal" est honnête hors-stress seulement.

### Le sleeve +0.107 est RÉGIME-GONFLÉ
L'increment +0.107 sur (60/40+trend) couvre 2013-2026 **incluant** le hard-market +13-20 %/an 2023-26.
Hors ce régime (2013-2021, soft+cat), l'excès ILS ≈ 0 → increment ≈ 0. C'est le **même piège "faux
FORT"** que le méta-portefeuille (Sharpe absolu gonflé par un régime ≠ prime steady-state)
[[feedback-gate-override]]. → NON promu au rang de sleeve robuste.

## Verdict

**DOWNGRADE** (label pré-enregistré pour A2∧B1 OK ∧ A1 FAIL). Contenu :

- **Le mieux que le programme ait trouvé côté orthogonalité** : prime ILS réelle (XILSX t=3.8,
  EW +2.56 %), corr normale +0.10, véhicule retail déployable existant → esquive le mur d'accès ET
  l'arbitrage. C'est le candidat-sleeve le plus crédible à ce jour.
- **Mais pas promu** : sub-hurdle (EW <3 %, t<2 ; flagship SRRIX ~0), positif **cyclique** (hard-market
  post-cat, pas steady-state), décorrélation **caveatée** en stress (corr +0.46, skew −2.95). Le sleeve
  +0.107 est gonflé par 2023-26.
- **NOUVEAU sous-type de mort** : prime réelle + décorrélée + déployable, mais **(a) consommée par les
  fees pour le véhicule flagship accessible, (b) cyclique** (le prix du hard-market post-catastrophe ≠
  prime récoltable en régime normal). Ni arbitrage, ni mur d'accès — le **wrapper + le cycle** la mangent.

**Bilan : 31 études, 0 edge déployable standalone.** Deliverable trading = mono-sleeve trend. L'ILS est
le meilleur **candidat** de diversification orthogonale (à reconsidérer si on accepte l'illiquidité +
le timing de cycle + un fund bas-fee), mais ne clear pas la barre honnête en l'état. Leçon : une prime
vraiment décorrélée existe (ILS), mais le retail la touche **nette de fees et au mauvais moment du
cycle** — et sa décorrélation se dégrade dans la queue.

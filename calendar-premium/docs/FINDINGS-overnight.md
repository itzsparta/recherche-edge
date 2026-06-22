# Piste 5a — Effet overnight : FINDINGS

**Verdict (2026-06-22) : DOWNGRADE.** L'effet overnight est **réel et robuste** (le rendement
actions se concentre overnight, +10 à +14 %/an, t>5, sur SPY/QQQ/IWM ; l'intraday est ~nul) —
mais **non capturable net** par un solo : 252 cycles/an × coût d'exécution mangent toute la
prime. (A) PASS, (B) FAIL. Conforme au null pré-enregistré.

> Reproduire : `python run_overnight.py`. Données : SPY/QQQ/IWM OHLC ajusté yfinance, cache `data/`.

## (A) L'effet existe — PASS (3/3 instruments)

| | overnight ann | t | intraday ann | t | diff t |
|---|---|---|---|---|---|
| SPY | **+10.1 %** | +5.51 | +1.9 % | +0.72 | +2.56 |
| QQQ | **+14.1 %** | +5.16 | +0.0 % | +0.00 | +2.69 |
| IWM | **+13.5 %** | +5.19 | −2.1 % | −0.53 | +3.27 |

Le rendement actions est **intégralement** une prime overnight ; détenir l'indice en séance ne
paie quasi rien. Effet net, significatif, robuste cross-instrument et cross-régime (échantillons
couvrant dot-com, GFC, COVID, 2022). Sanity : overnight + intraday ≈ buy-hold (SPY +12.0 %). ✓

Le split étant **intra-instrument**, le drift directionnel ne peut pas le fabriquer (contraste
avec le confound qui a tué les swings étage-1). L'effet est réel — la littérature (Lou-Polk-
Skouras) tient dans nos données.

## (B) Capturable net — FAIL

Stratégie long-overnight / flat-intraday sur SPY, coût pré-enregistré **5 bps round-trip / cycle**
(achat MOC + vente MOO) :

| | ann | Sharpe |
|---|---|---|
| overnight BRUT | +10.1 % | **+0.95** (> buy-hold !) |
| coût (252 × 5 bps) | **−12.6 %** | — |
| overnight NET | **−2.5 %** | −0.23 (t −1.36) |
| SPY buy-hold | +12.0 % | +0.65 |

**Brut, l'effet est supérieur au buy-hold** (Sharpe 0.95 vs 0.65 : même prime, moins de vol).
**Net, il meurt** : la prime overnight (~10 %/an) est du même ordre que le coût d'un aller-retour
quotidien. On ne peut pas séparer les deux pour un solo.

### Sensibilité au coût (disclosure honnête, sans toucher le gate)
Le verdict est **cost-driven**. Breakeven (Sharpe net = buy-hold 0.65) ≈ **1.3 bps round-trip**.
- coût < ~1.3 bps ⇒ basculerait GO ; coût > ~1.3 bps ⇒ DOWNGRADE.
- 1.3 bps round-trip MOC+MOO est au **bord optimiste** d'une exécution retail réelle (le slippage
  d'enchère d'ouverture seul dépasse souvent 1 bp). Le 5 bps pré-enregistré est conservateur mais
  défendable → **DOWNGRADE tient**. Un trader avec exécution institutionnelle prouvée sub-1.3 bps
  pourrait revisiter ; ce n'est pas le profil solo.

## Leçon

Troisième variante du motif du programme : prime **réelle** (transfert du risque de portage
overnight — gap risk nocturne), mais **l'unique forme de récolte exige un turnover quotidien dont
le coût ≈ la prime**. Comme le VRP (piste 4 : prime = loyer d'un tail), comme la niche (piste 3 :
spread = sommet d'un carnet vide). L'effet est connu et publié ; la friction de récolte le rend
inexploitable pour un solo. Pas un free lunch.

## Caveat données
`auto_adjust=True` décale légèrement l'overnight les jours ex-dividende (l'ajustement passe par
le close) — effet de 2nd ordre, ~2 %/an étalés sur ~4 dates, négligeable devant les magnitudes
ci-dessus. Opens SPY disponibles depuis 1993.

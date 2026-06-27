# Piste #32 — Merger arbitrage small-cap cash deals : pré-test (PRÉ-ENREGISTRÉ)

> Écrit **avant** de voir le moindre résultat. Tout changement de cette spec après
> avoir vu un chiffre = overfit, interdit. (Leçon FINDINGS orderflow / carry #6.)

## Hypothèse d'edge

Après l'annonce d'un deal M&A (tout-cash, cible cotée US, EV < $500M), le prix de la
cible cote **sous** le prix de deal annoncé. Ce spread = prime de risque pour
l'incertitude **binaire et non-prédictible** de clôture (close vs. break).

En achetant la cible à la clôture du jour d'annonce et en tenant jusqu'à la résolution
(deal price si close ; retour ~prix pré-annonce si break), le rendement annualisé net
est **> 8 %** de façon robuste dans le segment small-cap, là où la concurrence
institutionnelle est structurellement absente.

Formellement :
`r_net = Σ_deals [ P(close)·spread_ann + P(break)·loss_break ] > 8 %` net de frais,
avec `loss_break ≈ −25 à −35 %` (retour pré-annonce) et `P(break) ∈ [5–20 %]`.

**Les deux conditions sont requises** : (1) la prime existe (edge réel), ET (2) elle
franchit le hurdle de 8 % qui couvre coût d'opportunité (T-bill ~5 %) + prime de tail
+ illiquidité small-cap. Une seule ⇒ pas un GO (probable DOWNGRADE, cf. SPAC #27 / ILS #31).

## Source de l'inefficience structurelle — pourquoi NON entièrement arbitrée

1. **Incertitude binaire non-prédictible.** Antitrust (ère FTC 2021-2024), clause MAC,
   vote actionnaire, financement PE — issues RÉELLEMENT incertaines, pas info publique
   ignorée. La prime compense un risque réel. Contraste net : unlocks #2 (date=résultat),
   PEAD #28 (surprise=info publique priceable).
2. **Mandats de taille institutionnels.** Elliott ($50Bn) / Pentwater ($5Bn) ne peuvent
   pas se positionner sur une cible à $200M market cap (liquidité). → segment <$500M EV
   structurellement sous-couvert par les acteurs qui compriment les méga-deals.
3. **Durée de détention incertaine** (2–18 mois). Gérants contraints par benchmark /
   redemptions quarterly ne tiennent pas. Solo patient peut (même avantage que SPAC #27).
4. **Complexité opérationnelle small-cap.** Moins de couverture sell-side / média / arb
   funds → le marché met plus de temps à pricer P(close) = spread d'entrée plus large.

## Univers (FIXE — aucun cherry-pick)

- Annonces 8-K "merger agreement" / "definitive agreement", 2010-2025.
- Cible = **société US cotée**.
- Deal **all-cash uniquement** (exclut stock + mix cash/stock pour isoler l'arb pur,
  sans risque de couverture de l'acquéreur).
- **EV < $500M** (market cap de la cible sur yfinance à J-30 avant annonce).
- IS = 2010-2019 ; OOS = 2020-2024 (ère FTC, break rate élevé = test de robustesse).

## Signal (FIXE)

- **Entry** = prix à la clôture du jour d'annonce.
- **Exit** = deal price (si close) OU prix marché à J+5 post-annonce de termination (break).
- Détection close/break = 8-K Item 8.01 "Completion of Acquisition" / "Termination".
- Pondération de base = **equal-weight inter-deal** (chaque deal = 1 observation).

## Gates pré-enregistrés (AVANT tout run)

| Gate | Critère PASS | Critère KILL |
|------|-------------|--------------|
| **(A) Spread brut > hurdle** | Rendement annualisé médian IS (2010-2019) > 8 % | ≤8 % → sub-hurdle, DOWNGRADE/KILL |
| **(B) t inter-deal > 2** | t-stat sur la série des rendements **par deal** (PAS pooled-jours, leçon carry #6) | t ≤ 2 → bruit |
| **(C) OOS mûr (ère FTC 2020-2024)** | Rendement > 0 ET t > 1.5 en OOS ; chute ≤30 % vs IS | Net négatif OOS → arbitré, non-répétable |
| **(D) Drop-top-5 deals** | Retire les 5 meilleurs deals → rendement reste positif | Meurt → 5 outliers portent tout = bruit |
| **(E) Miroir (short cible)** | Short cible à l'annonce = rendement négatif (le côté positif = prime de clôture, pas momentum) | Miroir positif → momentum, pas arb |
| **(F) Ajustement tail (EV gate)** | EV explicite > 0 : `P(close)·spread − P(break)·loss_break`, P mesurés IS | EV ≤ 0 → prime mangée par la tail |
| **(G) DSR(best, N=3)** | DSR > 0.95 (N=3 variantes : EV<200M / EV<500M / par deal-type) | DSR < 0.95 → overfit |

GO = tous les gates PASS. Sinon DOWNGRADE (prime réelle sub-hurdle) ou KILL (pas de prime).

## Prior honnête (avant data)

Stratégie connue depuis 1970 (Boesky). Fonds dédiés existent (MERFX, ARBFX) nettant
4-7 %/an post-2010, **probablement sous la barre 8 %** pour un solo. L'ère FTC 2021-2024
(break rate élevé) aggrave le bilan récent. Prior le plus probable = **DOWNGRADE/KILL
sub-hurdle**, même profil que SPAC #27 et ILS #31. Mais mécanisme STRUCTURELLEMENT
distinct des 31 pistes mortes (incertitude binaire ≠ info publique) → vaut le gate-kill.

## Data source

| Source | Données | Accès |
|--------|---------|-------|
| SEC EDGAR EFTS | 8-K full-text "merger agreement" / "definitive agreement" 2010-2025 | REST API gratuit (efts.sec.gov) |
| SEC EDGAR submissions | Ticker + CIK cible ; 8-K closing/termination | REST API gratuit (data.sec.gov) |
| Yahoo Finance / yfinance | Prix cible J-30 → J+deal, market cap pré-annonce | Python libre |

## Coût d'implémentation (si GO)

Long cible seul (pas de short acquéreur dans un cash deal). Levier 0x. Rotation lente
(1-3 deals simultanés, holding 2-12 mois). Frais transaction négligeables à horizon deal.
Tail −25 à −35 % par break → sizing Kelly faible (f* ≈ 0.27 brut avec p=0.90, b=0.08,
q=0.10, loss=0.30 ; appliquer fraction conservatrice).

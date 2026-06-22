# Piste 5b — Pré-FOMC drift : FINDINGS

**Verdict (2026-06-22) : KILL priced-in.** Le drift pré/autour-FOMC était **réel et fort**
1994-2014 (+31 bps/event, t=3.34) — puis **s'est effondré à la publication** (Lucca-Moench
2013-2015) : 2015→ = +2.3 bps/event, t=0.20, magnitude −93 %. (A) PASS, (B) FAIL. Même tueur
que les token unlocks (piste 2) : l'edge à information publique est mangé une fois connu.

> Reproduire : `python run_fomc.py`. Données : SPY (yfinance) + calendrier FOMC programmé
> (CSV FOMCscrape 1994-2018 via urllib + dates Fed vérifiées 2019-2026), cache `data/`.

## Échantillon
262 annonces FOMC programmées (~8.1/an), fév 1994 → juin 2026, urgences intermeeting exclues
(1998 LTCM, 2001×3, 2008×2, mars 2020 préempté). Baseline = 8 142 jours non-FOMC. Le
sous-échantillon post-2015 (n=91) repose sur la donnée la **plus fiable** (Fed vérifiée 2019-26
+ CSV propre 2015-18) — son effondrement n'est donc pas un artefact de qualité de dates.

## (A) Le drift existe (full 1994-2026) — PASS

| fenêtre | excès | FOMC vs base | t | ann≈ |
|---|---|---|---|---|
| **announce_day** (close[d−1]→close[d]) | **+21.1 bps** | +25.2 vs +4.1 | **+2.89** | +1.71 % |
| window2 (close[d−2]→close[d]) | +34.1 bps | +38.2 vs +4.1 | +3.44 | +2.76 % |
| day_before (close[d−2]→close[d−1]) | +9.1 bps | +13.2 vs +4.1 | +1.14 | +0.74 % |

Le drift est **réel** : le rendement SPY autour des annonces FOMC bat largement les jours
ordinaires (+21 bps sur le jour du statement, t≈2.9 ; +34 bps sur la fenêtre 2 jours, t≈3.4).
Conforme à Lucca-Moench. Concentré sur le jour de l'annonce (le jour d'avant seul est faible).

## (B) Encore tradable post-publication — FAIL (décisif)

| période | n | excès announce_day | t |
|---|---|---|---|
| pré-2015 | 171 | **+31.0 bps** | **+3.34** |
| **2015→** | 91 | **+2.3 bps** | **+0.20** |

Le drift **disparaît** après publication. Ce n'est **pas un manque de puissance** : à effet
constant (+31 bps), n=91 donnerait t ≈ 3.34·√(91/171) ≈ 2.4 (significatif). Or on observe
+2.3 bps / t=0.20 → c'est la **magnitude qui s'est effondrée (−93 %)**, pas seulement le bruit.

Le seuil 2015 = publication de Lucca-Moench (working paper 2013, J. Finance 2015). L'arbitrage
post-publication a mangé la prime — McLean-Pontiff (« Does Academic Research Destroy Stock
Return Predictability? ») observé en direct.

## Leçon

Quatrième confirmation du motif du programme, et la plus littérale : **un edge à information
publique meurt quand il devient connu.** Identique aux token unlocks (piste 2, priced-in avant
la date). Le coût n'était pas le tueur ici (8 events/an, exposition minime) — c'est la
**diffusion de l'information** elle-même. Un solo qui aurait tradé ce papier en 2016 aurait
récolté du bruit.

## Caveats (pré-enregistrés)
- **Donnée daily ne coupe pas à 14 h** (heure du statement) : `announce_day` mêle drift
  pré-annonce ET réaction post. La fenêtre exacte 24 h de Lucca-Moench exigerait de l'intraday
  (payant). Le test gratuit capte le drift *autour* de l'événement, suffisant pour le verdict
  érosion (la collapse pré/post est robuste à la définition de fenêtre).
- Calendrier 1994-2018 via CSV tiers (flag « scheduled » incomplet → blocklist d'urgences
  manuelle) ; un éventuel résidu d'événements non-programmés ajoute du bruit au **pré-2015**
  (le côté qui PASSE) — ne menace pas le verdict post-2015.

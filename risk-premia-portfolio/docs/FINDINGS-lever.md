# FINDINGS — Étude #34 : le deliverable #22 levé — EXTENSION-LEVIER (L\*=1.5)

**Verdict (2026-07-02) : EXTENSION-LEVIER — A, B, C, D tous PASS.** Le levier constant 1.5×
financé au taux réel ajoute **+2.7 pts/an** au deliverable (net **+10.0 %/an**, maxDD −29 %),
robuste aux deux moitiés d'échantillon ET au financement broker cher. C'est la réponse chiffrée
à « pourquoi le #22 plafonne bas » : le plafond se lève par la vol, pas par le Sharpe — et voilà
son nouveau niveau, avec ses limites.

Test contre [`SPEC-lever.md`](SPEC-lever.md) pré-enregistrée (commit `08810f4` avant tout code).
Reproduire : `python run_lever.py` (sleeves #22 + T-bill FRED TB3MS, cache `data/irx.csv`).

## Grille @ financement T3M+0.40 % (futures/box) — 2006-04→2026-02, 238 mois

| L | net/an | Sharpe | maxDD | 2008 | 2022 |
|---|---|---|---|---|---|
| 1.00 | +7.37 % | +1.01 | −19.4 % | −10.0 % | −11.7 % |
| 1.25 | +8.71 % | +0.95 | −24.3 % | −12.9 % | −15.1 % |
| **1.50** | **+10.04 %** | **+0.91** | **−29.0 %** | **−15.8 %** | **−18.5 %** |
| 2.00 | +12.72 % | +0.87 | −37.7 % ✗ ruine | −21.4 % | −25.0 % |
| 3.00 | +18.06 % | +0.82 | −52.9 % ✗ | −32.3 % | −37.3 % |

Contrainte de ruine (maxDD > −35 %) → **L\* = 1.5** (L=2 franchit à −37.7 %).

## Gates

| Gate | Critère | Résultat | Verdict |
|---|---|---|---|
| **A** le levier paie | net(L\*) ≥ net(1)+1 pt | +10.04 % vs +8.37 % | **PASS** |
| **B** levier tenable | L\* > 1 | 1.5 | **PASS** |
| **C** both-halves | incrément > 0 les 2 moitiés | **+2.59** (06-16) / **+2.75** (16-26) pts/an | **PASS** — robuste au régime de taux (ZIRP vs 5 %) |
| **D** sanity | Sharpe(L\*) ≥ Sharpe(1)−0.10 | 0.91 vs 0.91 (limite exacte) | **PASS** |

## Diagnostics (non-gating)

- **Broker T3M+1.5 %** : L=1.5 net **+9.49 %** — même le financement cher paie (+2.1 pts).
  Le deliverable n'exige donc pas les futures, ils restent préférables (+0.55 pt).
- **Vol-target 10 % (36 m, cap 3×)** : net **+11.48 %, Sharpe 1.16, maxDD −17.2 %**, L moyen
  1.46. **Domine le levier constant sur les trois axes** (rendement, Sharpe, DD) — mécanique
  connue : dé-lever quand la vol monte = éviter les crises à plein levier. Pré-enregistré comme
  diagnostic → **NON promu deliverable** (ce serait une promotion post-hoc) ; extension
  pré-enregistrable si voulu (un seul paramètre nouveau, la fenêtre 36 m, déjà celle du méta).
  > **ERRATUM (#36, 2026-09-11) : cette « domination » est un ARTEFACT DE FENÊTRE.** Le warmup
  > 36 m fait démarrer le VT en 2009-04 (sans 2008) alors que le constant ci-dessus inclut 2008.
  > Sur la même fenêtre, le constant 1,5 a le même Sharpe (1,16) ; à volatilité égale le VT fait
  > ΔSharpe −0,01 à −0,09 sur W∈{12,24,36,48}, et **pire en 2008** (W12 : −22,8 % vs −16,0 %).
  > KILL artefact → [`FINDINGS-voltarget.md`](FINDINGS-voltarget.md).
- Pire mois base −8.1 % → −12.2 % à L=1.5 (marge futures loin du call) ; −24.4 % à L=3
  (call intra-mois probable — la grille avait raison de l'exclure).

## Caveats (déclarés en SPEC, inchangés)

1. **Gap intra-mois non simulé** : le DD mensuel sous-estime le pire chemin intra-mois.
2. **Granularité petit compte** : MES ≈ 33 k$/contrat → sous ~50 k€, L réalisé ≠ L cible par
   paliers grossiers. Le levier propre commence avec du capital.
3. **Le levier multiplie l'excès FUTUR, pas l'historique** : +7.37 % de base contient le bull
   US post-GFC ; si l'excès forward est 4 %, L=1.5 rend ~5.5 % net. Le levier multiplie aussi
   les erreurs d'estimation — raison de plus pour L modéré.
4. **Toujours pas un edge** : même bêta, Sharpe légèrement inférieur (coût), plus de vol. Le
   plafond est levé, pas percé.

## Place dans le programme

Première **extension positive** depuis la construction #22 : les 4 gates passent, dont le
both-halves que presque tout le reste du programme échoue. Cohérent avec le motif unifié : ce
qui survit n'est jamais un edge — c'est du **bêta bien construit** (primes réelles + assurance
trend), et le levier modéré en est le multiplicateur arithmétique légitime. Réponse finale à
« plafonne bas » : **~10 %/an net à DD −29 % (constant 1.5×), ~11.5 % à DD −17 % si le
vol-target est validé à son tour**. Au-delà, la grille elle-même montre le mur (L=2 = ruine).
Le multiplicateur restant n'est pas dans le marché : c'est capital × temps.

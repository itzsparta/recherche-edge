# SPEC — Étude #40 : capture de dividende PEA sur les sociétés exonérées de TTF (< 1 Md€) — pré-enregistré

> Écrit le 2026-09-12, **AVANT tout pull de données** : aucune liste de petites valeurs, aucune liste
> TTF, aucun prix lus. Origine : branche pré-enregistrée de #39 (`SPEC.md`, cas A ∧ ¬B). Le segment
> y ≥ 3 % du SBF 120 capte +0,32 % net hors TTF (t = 4,55, 2015+), et −0,08 % avec TTF. La TTF est le
> seul obstacle ; les sociétés < 1 Md€ en sont exonérées. Gates figés ici ([[feedback-gate-override]]).

## Thèse

Même mécanisme que #39. En PEA, le dividende d'une société française est encaissé brut ; si le cours ex
baisse de ρ·D avec ρ < 1, un achat au dernier fixing de J−1 suivi d'une vente au premier fixing de J
capte (1 − ρ)·y. Nouveauté : l'univers **exonéré de TTF**, donc un coût de 0,40 % au lieu de 0,60 %.

## Le prior central : la borne d'arbitrage (tiré de #39, écrit avant les données)

Sur le SBF 120 depuis 2015, la capture brute du segment y ≥ 3 % vaut +0,52 %. C'est à peu près le coût
d'un arbitragiste exonéré d'impôt sur le dividende qui paie la TTF (0,30-0,40 % + exécution). Lecture :
**ρ n'est pas fixé par la fiscalité seule, mais borné par le coût des arbitragistes** :
(1 − ρ)·y ≈ leur coût. Deux prédictions opposées pour les petites valeurs :

- **Borne d'arbitrage (tueur).** Sans TTF, la borne descend au coût d'exécution. La capture brute tombe
  alors vers nos propres coûts, donc un net ≈ 0 pour tout le monde. S'y ajoute un price-setter plus
  **domestique** (moins de non-résidents au capital) → ρ → 1.
- **Capacité (thèse).** Les arbitragistes institutionnels (dealers, prêt-emprunt) ignorent des titres
  trop petits pour eux. La borne ne s'y exerce pas, et la capture reste grasse là où un particulier peut
  encore passer son ordre. C'est l'arme structurelle d'un solo, tuée en #3 par une profondeur fantôme.

## Données (pré-committées)

| Rôle | Source | Construction |
|---|---|---|
| Univers brut | Listes publiques Euronext : Paris réglementé (`XPAR`) + Euronext Growth Paris (`ALXP`) | Titres à **ISIN FR** (retenue étrangère non récupérable en PEA, cf. #39) |
| Exonération TTF | Liste officielle des sociétés françaises capitalisant > 1 Md€ au 1er décembre (la plus récente publiée) | **Exclues.** Si la liste est introuvable : capitalisation yfinance actuelle ≥ 1 Md€, et l'amendement est déclaré |
| Prix + dividendes | yfinance `history(auto_adjust=False, actions=True)`, `{symbole}.PA` | Comme #39 |
| Période | **2009-01 → dernier jour dispo** | #39 : dates yfinance `.PA` désalignées en 2005-08 |

L'exonération est celle **d'aujourd'hui**, appliquée à toute la période : on mesure le ρ des sociétés
qu'on pourrait trader aujourd'hui sans TTF, pas l'histoire de leur statut fiscal (même principe que
#37 et #39). Survivorship assumé (caveat 1).

**Benchmark `Rm_J`** : moyenne équipondérée de l'overnight C_{J−1} → O_J des titres de l'univers qui
versent au moins un dividende sur la période, sans date ex en J, nuit valide ; au moins 20 titres, sinon
la nuit est exclue. Restreindre aux payeurs écarte les BSA, les biotechs sans cotation continue et les
coquilles. Même type de titres, mêmes fixings (beaucoup de petites valeurs cotent au fixing, pas en
continu).

**Filtre de liquidité (ex ante, déployabilité)** : turnover médian (Close × Volume) sur [J−60, J−2]
≥ **200 k€**. Un ticket de 3-5 k€ reste ainsi ≤ ~2,5 % du volume quotidien.

**Validité des données (a priori, comme #39)** : nuit invalide si `O_J` manquant ou ≤ 0, `Volume_J = 0`,
ou `O_J == C_{J−1}` exactement ; y > 10 % exclu ; |AR| > 15 % exclu. Les exclusions sont rapportées.

## Coût (figé)

| Poste | Coût |
|---|---|
| TTF | 0 (exonéré) |
| Courtage PEA en ligne, ticket 3-5 k€ | 2 × 0,10 % |
| Écart au fixing / impact sur des fixings minces | 2 × 0,10 % |
| **Total `c`** | **0,40 %** |

## Statistique (inchangée depuis #39)

AR = (O_J + D)/C_{J−1} − 1 − Rm_J ; ρ̂ = 1 − Σ(AR·C_{J−1})/ΣD. La moyenne et le t d'un gate sont ceux
de la **série des cohortes mensuelles**. Segments de rendement fixes : y < 1,5 % ; 1,5-3 % ; ≥ 3 %.

## Gates (figés avant run)

**G0 par période** (leçon #39 : un G0 poolé a masqué une sous-période corrompue). Périodes :
P1 = 2009-2014, P2 = 2015-2020, P3 = 2021 → fin. Pour chaque période :
ρ̂ nuit J ∈ [0,5 ; 1,5] **et** |ρ̂| < 0,3 sur chacune des nuits J−3 … J−1 et J+1 … J+3.
Une période qui échoue est **exclue de tous les gates**, par une règle de données, pas un choix sur AR.

| Gate | Test | PASS si |
|---|---|---|
| **N** puissance (prérequis) | segment B (ci-dessous), 2015+ | ≥ 100 événements |
| **A** existence | tous événements des périodes retenues, AR brut | moyenne > 0 **et** t_cal > 2 **et** moyennes croissantes sur les 3 segments de y |
| **B** déployable | y ≥ 3 %, turnover ≥ 200 k€, **2015+**, AR − 0,40 % | moyenne > 0 **et** t_cal > 2 |
| **C** stabilité | segment B net, P2 et P3 séparément | moyenne > 0 dans **chacune** |
| **D** concentration | segment B net 2015+, hors les 5 noms à plus forte ΣAR | moyenne > 0 **et** t_cal > 2 |

B porte sur 2015+ parce que la question est ce qu'on déploierait maintenant ; dans #39, c'est ce
chiffre-là qui a tranché.

## Verdict (mapping pré-enregistré)

| Cas | Verdict et conséquence |
|---|---|
| G0 échoue en P3, ou moins de 2 périodes retenues, ou ¬N | **UNTESTABLE** : données petites valeurs non fiables ou sous-puissantes ; aucun autre gate lu. |
| ¬A | **KILL ρ ≈ 1** : price-setter domestique ou borne d'arbitrage serrée ; l'avantage PEA n'existe pas hors grandes valeurs. |
| A ∧ ¬B | **KILL borne d'arbitrage** : ρ < 1 mais la capture ≤ coût d'exécution, là où nous pouvons exécuter. Branche P2-P3 fermée. |
| A ∧ B ∧ (¬C ∨ ¬D) | **DOWNGRADE** : présent mais instable ou porté par quelques noms. |
| A ∧ B ∧ C ∧ D | **GO phase 2** : premier GO du programme. Phase 2 = saison de dividendes 2027 (avril-juin) en réel sur petits tickets : prix de remplissage aux fixings contre le fixing publié, avant toute taille. |

## Diagnostics non-gating

- **Liquidité, test de la thèse capacité** : AR net par tranche de turnover (< 200 k€, non tradable ;
  200 k€-1 M€ ; > 1 M€). Si la capture ne vit que sous 200 k€ → capacité fantôme (motif #3).
- Segment de marché : Euronext Growth vs réglementé.
- ρ̂ par segment de y et par période ; pente AR ~ y.
- Coût 0,20 % et 0,60 % ; variante clôture-clôture ; benchmark médian.
- Nuits placebo J−2 et J+2 : AR moyen de base de ces titres (anomalie overnight propre aux petites
  valeurs ?).
- Comparaison avec le SBF 120 de #39 sur 2015+, même segment : capture brute (prédiction de la borne
  d'arbitrage : petites < grandes).
- Nombre de nuits investies par an et net annuel du segment B.
- Événements par filtre ; top-5 noms ; sans le filtre |AR| > 15 %.

## Caveats déclarés d'avance

1. **Survivorship plus fort qu'en #39** : univers = cotés aujourd'hui. Les petites valeurs radiées
   (faillites, OPA) manquent. Direction du biais sur le ρ du jour ex a priori faible, mais non corrigé.
2. **Profondeur des fixings non observée** : yfinance ne donne pas le volume d'enchère. Le filtre de
   turnover est un proxy. Seule la phase 2 mesure le vrai remplissage.
3. **`Open` = premier fixing ou premier échange** : pour les titres cotés au fixing, l'« ouverture » est
   le fixing de 10 h 30. La mécanique de la stratégie est inchangée, et le benchmark est pris sur les
   mêmes titres.
4. **Exonération TTF actuelle appliquée au passé** (voir ci-dessus). Un nom qui franchit 1 Md€ redevient
   taxé : l'univers déployable se révise chaque décembre.
5. Coûts 2026 non revérifiés auprès d'un courtier. Hors prélèvements sociaux à la sortie du PEA.

## Prior honnête (écrit avant run)

- **G0 / N** : ~70 % testable. Les données petites valeurs yfinance sont la source la plus fragile du
  programme, et le segment B liquide 2015+ pourrait tomber sous 100 événements.
- **A** : ~50 %. ρ < 1 plausible (#39), mais un price-setter domestique pousse vers 1.
- **B** : **~10 %.** La borne d'arbitrage prédit une capture brute ≈ coût d'exécution. #39 montre qu'elle
  colle au coût des arbitragistes sur les grandes valeurs.
- **Issue la plus probable : KILL borne d'arbitrage**, ou A FAIL. La mesure qui a de la valeur même morte
  est la comparaison petites/grandes : si la capture brute baisse quand la TTF disparaît, la borne
  d'arbitrage est confirmée comme loi du jour ex en France, et l'axe « statut fiscal » est clos.

## Sortie

`dividend-pea/data.py` (fonction `universe_small`, caches `data/`), `run_small.py`,
`docs/FINDINGS-smallcap.md`. Commit de la spec avant tout pull et tout code ; findings après le run.

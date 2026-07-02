# SPEC — Étude #33 : inventaire free-rolls à payout réel (option gratuite)

**Pré-enregistré le 2026-07-02, AVANT toute recherche d'offre.** Suite directe de la clôture #26
(piste de sauvetage 3 : « free-roll / coût ≈ 0 = LEAD, pas edge — à time-boxer, jamais payant »).
Méthodo = ledger d'EV opérationnel (#14 airdrop, #24 prop), PAS un backtest.

## Objet

Recenser les voies **à coût monétaire strictement nul** vers un **payout réel retirable** liées au
trading (concours démo à prix cash, évaluations prop gratuites payout-eligible, compétitions
exchange sans capital requis). Chiffrer l'EV **par heure** de chaque offre. Rendre un verdict
d'offre ET un verdict d'axe.

## Ce que la base de connaissance impose (rappels contraignants)

- **#24** : challenge à barrière sous no-edge = P(pass/phase) ≈ 0.5 hors coûts (statique), < 0.5
  (trailing) ; médiane single-shot = −fee. À fee = 0 la médiane négative disparaît → option
  gratuite. Max-variance **nuit** dans une structure à barrière basse.
- **Structure tournoi rank-based ≠ challenge à barrière** : top-N sur classement sans barrière
  basse absorbante → stratégie de variance maximale **sur-pondère la queue droite** → P(top N) >
  1/field pour le joueur max-variance face à un field qui trade « normalement ». Seul « edge »
  structurel candidat ici. MAIS EV de base ≈ pool/field = souvent centimes.
- **#26 / règle permanente** : lire les **forbidden practices / clauses de void AVANT** d'investir
  la moindre heure. Si le seul chemin +EV de l'offre est interdit par ses règles → KILL offre,
  zéro heure investie. (Le void frappe aussi les comptes gagnés gratuitement.)
- **#14** : le vrai fee d'un free-roll = le **temps**. Seuil de labeur = **15 €/h** (repris tel
  quel de `airdrop-ev/docs/SPEC.md`).

## Gates (figés avant de voir la moindre offre)

| Gate | Critère PASS | Critère KILL (offre) |
|------|--------------|----------------------|
| **G0 — inclusion** | Coût monétaire **strictement 0** : pas de dépôt (même remboursable), pas d'achat, pas de volume réel requis (frais de trading sur capital propre = fee déguisé). Payout **cash retirable** contractuel (€/$/crypto withdrawable). | Tout coût > 0 → hors périmètre (re-litige #26 interdit). Prix non-cash → valoriser à l'EV réelle (cf. règle tickets). |
| **G1 — clauses** | Règlement lu ; il existe une config jouable **à la fois** autorisée ET à variance exploitable (tournoi) ou à espérance d'extraction > 0 (éval gratuite → compte financé). | Le seul chemin vers le prix est interdit (EA banni + pas le temps de trader manuel ; max-variance banni en tournoi ; harvest voidable en financé) → KILL. |
| **G2 — EV/heure** | `EV_nette / heures_totales > 15 €/h`. EV conservatrice : `P(prix) × valeur retirable` (P estimée par field/structure, arrondie vers le bas). Heures = inscription + KYC + trading minimum requis + monitoring + procédure de retrait. | ≤ 15 €/h → KILL offre. |
| **G3 — axe** | Somme des offres PASS répétables ≥ ~500 €/an d'EV pour ≤ 30 h/an. | En-dessous → l'axe free-roll entier = **DORMANT** (veille passive gratuite uniquement, zéro heure proactive récurrente). |

**Règle tickets** : un prix « challenge payant offert » se valorise à `EV(challenge single-shot
clause-safe)` mesurée par #24 (médiane −fee **hors** fee → EV faible positive, P(net>0) ≤ 0.295
conditionnel au style clause-safe), PAS au prix affiché du challenge. Un ticket de 500 € affichés
ne vaut pas 500 €.

**Règle EA** : `HarvestEA.mq5` (infra #26, sunk) réutilisable si et seulement si les règles de
l'offre autorisent les EA. EA autorisé → heures ≈ setup ; EA interdit → heures = temps d'écran
réel, sans triche d'estimation.

## Time-box

**3 h** pour l'inventaire complet (recherche + lecture clauses + ledger). Dépassement = signal
que l'axe ne vaut pas son coût de découverte → clore en l'état.

## Prior honnête (écrit avant recherche)

KILL/DORMANT probable : (a) les concours gratuits à gros pool ont des fields de milliers →
EV/participant en centimes ; (b) beaucoup de « prix » sont des tickets (règle tickets → EV
minuscule) ; (c) les évaluations gratuites payout-eligible sont rares et portent les mêmes
clauses de void que #26 ; (d) les démos sans chemin cash (type FTMO Free Trial) sont hors
périmètre par G0. Le test dit si une poche répétable existe malgré tout.

## Sortie

`FINDINGS-freeroll.md` : ledger par offre (coût, structure, field, P estimée, valeur, heures,
EV/h, clauses, verdict) + verdict d'axe G3. Commit spec avant run, commit findings après
(pré-enregistrement matérialisé git).

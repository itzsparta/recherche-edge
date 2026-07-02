# FINDINGS — Étude #33 : inventaire free-rolls à payout réel

**Verdict (2026-07-02) : KILL de l'axe — aucune offre ne passe G0+G1+G2 simultanément.
L'objectif « payout » est désormais fermé sur ses TROIS branches : payant single-shot (#24),
payant répété (#26), gratuit (#33).**

Test contre [`SPEC-freeroll.md`](SPEC-freeroll.md) pré-enregistrée (commit `cabb31e` avant toute
recherche). Time-box 3 h respecté (~1,5 h). Méthode : recherche web + lecture des structures de
prix et clauses d'éligibilité, bornes d'EV volontairement généreuses (si la borne haute absurde
tue, le réaliste tue a fortiori).

## Le ledger

| Offre | G0 coût 0 | Prix | G1 clauses/éligibilité FR | G2 EV/h (borne HAUTE) | Verdict |
|---|---|---|---|---|---|
| **FundedFast Open** (bi-hebdo, $100k virtuel) | ✓ | cash retirable **$25/$20/$15** (pool $60/round, PayPal après KYC vidéo) | ✓ mondial | field=50 (borne absurde basse) → $1,2/round pour ≥3 h → **$0,40/h** ; réaliste **<$0,05/h** | **KILL G2** (~40-300× sous le seuil 15 €/h) |
| **XM weekly demo comp** ($25k/sem, 100 gagnants) | ✓ | cash/crédit sur compte réel XM | ✗ **« Promotions and bonuses are not available for accounts registered under the EU-based entity »** (T&C XM) — résident FR = entité EU obligatoire (ESMA) | — | **KILL G1** (juridiction) |
| **Grand Capital Cup** (24 h, $10k virtuel) | ✓ | ✗ **crédit trading** : « $500 *for trading*, the profit from trading these funds can be withdrawn » — le prix lui-même n'est PAS retirable | broker offshore, FR non servi officiellement | extraire du crédit = re-mur no-edge ; ≤$100-200 pour le seul 1ᵉʳ d'un field de centaines | **KILL G0** |
| **Classe entière demo contests brokers** (InstaForex $55k, HF, LiteFinance, Vantage, Market Equity, trading.com…) | ✓ | ✗ crédit trading (structure identique) | offshore / FR douteux | — | **KILL G0** (classe) |
| **Prop giveaways/comps** (Funding Pips community, Breakout $100k eval, MFF, Maven points) | ✓ | ✗ **tickets** (challenge/éval gratuits) | clauses de void #26 intactes sur le compte gagné | règle tickets : EV(ticket) ≈ P(pass 0,21)·E[extraction clause-safe] ≈ $100-200 pour 10-30 h de trading ≈ **$5-10/h**, borne haute, AVANT void ; et il faut d'abord *gagner* le ticket (field social) → EV(giveaway) ≈ centimes | **KILL G0/G2** |
| **Compétitions quant étudiantes** (IMC Prosperity 4 : $50k pool, gratuit, équipes, ~17 j ; Optiver Ready Trader Go) | ✓ | ✓ cash réel | ✓ étudiant éligible | field ~10k équipes ; EV uniforme $5/équipe ; à skill généreux **50×** l'uniforme → ~$250/30 h ≈ **$8/h**, P spéculative | **KILL G2** *comme payout* (cf. note) |

## Les quatre mécanismes du kill (pourquoi c'est structurel, pas un manque d'offres)

1. **Le cash retirable existe, mais en montants marketing.** $25-$250, partagés sur des fields de
   centaines à milliers. Le concours gratuit est un **coût d'acquisition client** : le produit,
   c'est le participant (funnel vers challenge payant — FundedFast le dit : chaque participant
   reçoit « an exclusive discount code for a paid challenge »).
2. **Les montants matériels ne sont jamais du cash.** Crédit trading (retirable seulement via du
   profit généré dessus = re-mur no-edge, chez un B-book offshore) ou ticket challenge (valorisé
   à EV #24, pas au prix affiché ; clauses de void #26 intactes sur le compte gagné). Même
   structure que #26 : **la valeur affichée n'est pas la valeur extractible**.
3. **La juridiction ferme les gros pools.** ESMA/AMF interdit les incitations CFD retail → les
   pools matériels (XM $25k/sem) excluent l'entité EU verbatim. Le résident FR est hors-jeu par
   construction ; contourner en mentant sur la résidence = violation T&C = void garanti (leçon
   #26 : la clause bat l'edge).
4. **L'« edge de variance » de tournoi se dissipe.** La stratégie max-variance est connaissance
   commune (les agrégateurs l'écrivent : « les stratégies gagnantes impliquent des risques
   extrêmes ») → le field entier s'auto-sélectionne all-in → P → uniforme → EV = pool/field =
   centimes.

## G3 — verdict d'axe

**0 offre PASS → axe free-roll = KILL.** Résidu : veille **DORMANT à coût strictement nul** —
zéro heure proactive récurrente ; si une éval 100 % gratuite payout-eligible à petit field tombe
d'elle-même (promo ponctuelle), la passer aux gates G0-G2 avant d'y mettre une heure.

**Note hors-périmètre (honnêteté)** : les compétitions quant étudiantes (IMC Prosperity, Ready
Trader Go) sont la seule structure trouvée où P est **skill-déterminée** (algo, pas variance) et
où l'heure investie a une valeur secondaire réelle (apprentissage, signal recruteur). Elles
échouent **comme payout** (G2) mais relèvent d'un autre objectif que celui de cette étude — à
évaluer là-bas, pas ici.

## Place dans le programme

**Étude #33, KILL. L'objectif « obtenir un payout » est fermé sur toutes ses branches :**

| Branche | Étude | Tueur |
|---|---|---|
| Payant, single-shot | #24 | médiane = −fee, max P(net>0) = 0,295 — loterie à marge maison |
| Payant, répété (+EV réel) | #26 | tenaille : la config +EV est interdite, la config autorisée est −EV ; racine B-book partagée → aucun screener |
| **Gratuit** | **#33** | **cash = montants marketing ; matériel = crédit/ticket non-cash ; gros pools = interdits au résident FR (ESMA) ; variance de tournoi = dissipée** |

Extension du motif unifié à sa forme finale : *ce qui te laisse entrer gratuitement te paie en
produit marketing, pas en cash — et là où le cash est matériel, c'est la loi de ta juridiction
qui ferme la porte.* Le seul cash trading démontré du programme reste le **flux lent** :
déploiement du deliverable 60/40 + trend (#22). **Bilan : 33 études, 0 edge déployable, 0 voie
payout.**

## Sources

- [FundedFast — free prop firm challenge](https://fundedfast.com/compare/free-prop-firm-challenge)
- [XM Global — Competitions Program T&C](https://cloud.xm-cdn.com/static/pdf/System-PDFs/XMGlobal-Competitions-Program-Terms-and-Conditions-v5.pdf) · [XM social competitions](https://www.xmza.com/social-competitions)
- [Grand Capital Cup — T&C du tournoi](https://grandcapital.net/api/agreements/agreement/gc_cup/) · [TradingBrokers — Grand Capital demo contest](https://tradingbrokers.com/grand-capital-demo-contest/)
- [AllForexBonus — demo contests (agrégateur, juillet 2026)](https://allforexbonus.com/forex-competition/forex-demo-contest)
- [TheTrustedProp — prop competitions 2026](https://thetrustedprop.com/blogs/top-prop-firm-trading-competitons-of-2026-win-free-account)
- [IMC Prosperity 4](https://prosperity.imc.com/) · [Optiver Ready Trader Go](https://readytradergo.optiver.com/)

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

## Extension crypto (2026-07-02, même time-box — question post-verdict)

Question : « et sur le marché crypto ? ». Réponse : **chaque voie crypto à coût 0 tombe dans une
classe déjà tuée** — soit par une étude dédiée, soit par les gates de ce ledger. Verdict inchangé.

| Voie crypto | G0/G1/G2 | Tueur | Verdict |
|---|---|---|---|
| **Airdrop / points / testnet farming** (free-roll canonique crypto) | — | **#14 dédiée** : best-case généreux 8,4 €/h < 15 €/h ; base-case **−1 050 $** ; 53 % du $ = 2 jackpots non-répétables ; le clawback sybil plafonne tout scaling | **KILL** (déjà rendu) |
| **Comps exchange réelles** (Bybit BYUSDT 200k USDT, Wall Street Showdown 100k, Binance comps) | G0 | **double** : volume réel requis → frais sur capital propre = fee déguisé ; prix = bonus/vouchers « **non-withdrawable under any circumstances** » — seuls les profits tradés dessus se retirent = re-mur no-edge (structure Grand Capital) | **KILL G0** |
| **Demo comps « crypto »** (LiteFinance crypto contest, ZERO Markets WTC, Deriv, myfxbook) | G0/G2 | même classe que le ledger principal : brokers CFD offshore, funnel marketing, fields de centaines-milliers — le sous-jacent crypto ne change ni la structure du prix ni le field | **KILL** (classe déjà au ledger) |
| **Learn-to-earn** (Coinbase Earn, Binance/Bitget quizzes) | G1+G2 | France **non-éligible** Coinbase Earn (waitlist) ; montants $2-10/quiz, stock fini non-répétable | **KILL G1/G2** |
| **Crypto prop** (Breakout, HyroTrader) | — | re-#24/#26 : tenaille clauses + règle tickets, identique aux props FX | **KILL** (déjà au ledger) |

Nuance honnête : le mécanisme 3 (juridiction) est **plus faible en crypto** — MiCA n'interdit pas
les incitations comme ESMA le fait pour les CFD. Mais les mécanismes 1-2 suffisent, et la forme
crypto du mur est la plus pure du ledger : **le prix crypto est lui-même un mini-compte prop** —
un bonus non-retirable dont seuls les profits de trading s'extraient. Gagner le concours te donne
l'obligation d'avoir un edge pour toucher le prix. Le mur no-edge est encapsulé **dans la
récompense elle-même**.

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
- Extension crypto : [Bybit — Rewards T&C (bonus non-retirables)](https://www.bybit.com/en/help-center/article/Bonus-Terms-and-Conditions) · [Bybit BYUSDT 200k USDT](https://www.tradingview.com/news/chainwire:4f4e7809e094b:0-competitive-bonus-apr-bybit-introduces-byusdt-trade-earn-with-200-000-usdt-prize-pool/) · [Coinbase Earn — pays éligibles](https://www.coinbase.com/blog/coinbase-earn-now-allows-users-in-100-countries-to-earn-their-share-of) · [LiteFinance crypto contest](https://www.litefinance.org/contests/20th-anniversary-challenge/crypto-trading-competition/) · [ZERO Markets WTC](https://www.zeromarkets.com/wtc/) · [fxverify — demo contests](https://fxverify.com/contests)

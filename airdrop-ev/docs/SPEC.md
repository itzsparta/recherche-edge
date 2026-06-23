# SPEC — Piste 14 : Airdrop farming, EV-ledger opérationnel (pré-enregistré)

> Écrit **avant** tout chiffre. **Ce n'est PAS un backtest de prédiction** (les 13 pistes
> précédentes l'étaient) : c'est un **ledger d'espérance opérationnel**. La question n'est pas
> « un signal bat-il le marché ? » mais « le **$ net par unité de capital + labeur** d'un farming
> systématique bat-il un seuil, après les coûts et la queue HONNÊTES ? ». Même rigueur, autre objet.

## Hypothèse d'edge

Le farming systématique d'airdrops / points dégage une **EV nette positive et matérielle** pour un
solo — *après* avoir compté honnêtement (a) les protocoles farmés qui **ne paient jamais** (base rate),
(b) la **décroissance de prix post-TGE**, (c) gas + lockup de capital, (d) le **clawback sybil**.

## Pourquoi ça pourrait persister — la SEULE arme structurelle inédite du programme

Ce n'est ni de la prédiction de prix ni de l'arbitrage : c'est une **subvention d'acquisition
d'utilisateurs**. La contrepartie (protocole + VCs) **donne** délibérément de la valeur pour
bootstrapper. Et les institutions **ne peuvent pas** sybil-farmer (mandat, KYC, taille) → c'est le
seul étang du programme où le gros acteur est **structurellement absent**, pas juste plus lent.

## Le null honnête (= verdict attendu a priori)

Prior bas (13 kills). Les morts probables, pré-enregistrées :
1. **Mirage survivorship** — on se souvient de UNI (~1 200 $), ARB (~2 000 $) et on oublie la longue
   traîne de protocoles farmés qui airdroppent de la poussière ou **rien**. Base-rate EV ≈ break-even
   ou négatif une fois les zéros inclus. **C'est le tueur le plus probable (leçon meme-coin : mirage
   GeckoTerminal +0.223 sur n=4 démasqué).**
2. **Le moat coupe dans les deux sens** — le solo « organique » (1-quelques wallets) plafonne
   l'allocation à du petit $ ; la seule façon de rendre ça matériel (multi-wallets) est **exactement**
   ce que le clawback sybil détruit (Hop, LayerZero, zkSync ont exclu des centaines de milliers
   d'adresses). L'EV matérielle est **structurellement bornée**.
3. **Décroissance** — même qualifié, le token dump ; la valeur réalisable ≪ valeur TGE affichée.
4. **Seuil de labeur** — la vraie métrique est **EV / heure**, pas EV / $. Même si EV/$ > 0, EV/heure
   peut être sous le SMIC → pas « worth-it » pour l'objectif.

## Univers / basket (FIXE — déterministe, anti-cherry-pick winners)

Basket = **tous les airdrops de tokens à valeur distribuée ≥ 50 M$ au TGE, 2021-2025, réclamables
par un EOA de farming** (pas les distributions VC/équipe). Liste figée par cette règle — elle **inclut
les dust et les déceptions**, pas seulement les jackpots. Source liste : DefiLlama/CoinGecko airdrop
trackers + Dune. Pour chaque : allocation médiane par wallet éligible (Dune claim tables), prix TGE et
prix à horizon de vente, % d'adresses exclues sybil si documenté.

## Mesure (FIXE)

- **Allocation réalisable par wallet** `alloc_$ = tokens_médian_wallet × prix(horizon_vente)`.
  Horizon de vente pré-spécifié = **TGE+7 j close** (réaliste pour un farmer, pas le pic intraday TGE).
- **Coûts par campagne** `coût = gas_$ (multi-tx pour qualifier) + lockup (capital × durée × taux
  d'opportunité) + labeur (heures × seuil)`. Pré-enregistré : gas 150 $/campagne, lockup 1 000 $ × 6
  mois × 8 %/an, labeur estimé par campagne.
- **Base rate** `p_pay` = P(un protocole farmé paie un airdrop non-dust). Crux. Estimé honnêtement à
  partir du ratio (airdrops réels ≥ 50 M$) / (protocoles à programme de points/farming actifs sur la
  même période). Pré-enregistré : reporté tel quel, jamais ajusté pour faire passer un gate.
- **EV par campagne** `EV = p_pay × alloc_$_net_décroissance − coût`. **EV / heure** = EV / heures_campagne.

## Gates de décision (pré-enregistrés)

- **(A) Plafond best-case** : en **GARANTISSANT** la qualification au basket entier (borne haute),
  le $ réalisable total / période de farming. Si même ce plafond est **sous le seuil de labeur** → KILL
  (le plafond ne paie pas, inutile d'affiner).
- **(B) EV base-rate honnête** : EV incluant les zéros-farmés (`p_pay` réel). KILL si EV ≤ 0.
- **(C) Décroissance** : réalisable = alloc × fraction de prix à TGE+7 j (pas le pic). Reporter le
  haircut médian.
- **(D) Sybil/scaling** : le multi-wallet requis pour du $ matériel vs taux de clawback. Si le scaling
  est dominé par le clawback → edge plafonné au mono-wallet (petit), documenter.
- **(E) Seuil de labeur** : **EV / heure > 15 €/h** (plancher pré-enregistré, ordre du SMIC/coût
  d'opportunité) **ET** EV absolue > 500 €/trimestre sur capital tenable. Sinon DOWNGRADE (réel mais
  pas worth-it — un petit boulot opérationnel, pas un edge).

## Décision pré-enregistrée

- **(A) plafond > seuil ∧ (B) EV>0 ∧ (E) EV/h>15 € ⇒ GO** : le seul edge opérationnel du programme,
  à poursuivre comme **projet opérationnel séparé** (build de farming, pas recherche). Chasse au mirage
  obligatoire (vérifier que ce n'est pas 1-2 jackpots qui portent tout = leçon meme-coin/funding-XS).
- **(A) ∧ ¬(E) ⇒ DOWNGRADE** : EV réelle mais sous le seuil labeur → pas worth-it pour l'objectif.
- **¬(A) ∨ ¬(B) ⇒ KILL** : plafond trop bas, ou mirage survivorship (la traîne de zéros mange les jackpots).

## Falsifiabilité (comment ça meurt)

1. Plafond best-case < seuil labeur → KILL (A). 2. `p_pay` bas → EV base-rate ≤ 0 → KILL (B).
3. EV>0 mais EV/h < 15 € → DOWNGRADE (E). 4. Tout le $ sur 2-3 jackpots (UNI/ARB) → mirage (chasse).
5. Scaling tué par clawback → edge plafonné mono-wallet (D).

## Données & implémentation

- **Liste airdrops** : DefiLlama/CoinGecko trackers (≥ 50 M$, 2021-2025). **Allocations par wallet** :
  Dune (claim tables des majors). **Prix TGE / TGE+7 j** : CoinGecko/Dune. **Base rate** : compte des
  programmes de points actifs vs airdrops réalisés.
- **Sortie** : `ledger.py` (EV par campagne) + `run_airdrop.py` (gates A-E) + `docs/FINDINGS.md`.

## Verdict attendu a priori

L'edge est **réel** (subvention, moat sybil) — c'est la seule piste où le gros acteur est absent par
structure. Mais le programme prédit la mort en **(A)/(B)** (survivorship : la traîne de zéros, plus le
plafond mono-wallet borné par le clawback) ou un **DOWNGRADE (E)** (réel mais EV/heure sous le seuil =
un petit boulot, pas un edge d'investissement). La seule façon que ça survive = si même la base-rate
honnête, décroissance incluse, laisse une EV/heure matérielle — ce que le mirage survivorship rend improbable.

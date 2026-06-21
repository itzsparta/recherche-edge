# Research roadmap — chasse à l'edge (post-mortem orderflow / meme / rebate)

## Diagnostic : l'étang, pas la canne

Trois thèses tuées proprement — **orderflow** (level-edge fade+continuation mort,
DSR(N=50)=0.008), **meme-coin** (no-edge Dune réelle, t=−35, −28 %/trade),
**rebate-crypto** (mort) — plus **delta-neutral / prop firm** écarté (mismatch
structurel : carry impossible sur un compte CFD unique, profil rendement ⊥ profil
challenge). Voir les `FINDINGS.md` respectifs.

Point commun de **tous** ces échecs : ils chassaient un **edge prédictif** (deviner
le prix mieux que le marché) dans les **étangs les plus efficients et crowdés** qui
existent — intraday majors, meme pump.fun, funding arb. C'est là que se battent
chaque fonds quant, bot HFT, desk prop. Un solo sans edge latence / infra / data /
capital y perd **par construction**. La méthode était honnête ; le terrain de chasse
était condamné d'avance.

**La méthodologie n'est pas en cause** (DSR, López de Prado, multi-régime, miroir,
pré-enregistrement). Elle a fait son travail : elle a tué des mirages que la plupart
des retail auraient tradés. Le capital conservé = **l'infra + la méthode**, pas les
signaux.

## Le reframe : edge STRUCTUREL ≠ edge PRÉDICTIF

On arrête de chercher à être plus malin que le marché. On cherche où la **structure**
d'un petit acteur solo gagne — ce que les fonds **ne peuvent pas** répliquer :

- **Capacité** — déployer $5k là où un fonds *doit* placer des millions. Marchés
  illiquides = le seul monopole d'un solo.
- **Patience** — pas de LP, pas de benchmark, pas de redemption. Porter un drawdown
  qu'un fonds ne peut pas se permettre.
- **Pivot** — pas de comité, pas de mandat.

Les pistes ci-dessous sont classées par espérance **pour ce profil précis** (solo,
capital modeste, fort en build/data/méthode, zéro edge latence).

---

## Piste 1 — Primes de risque documentées, basse fréquence ★ top EV

**Thèse.** Récolter les premia *compensés* (pas de l'alpha) : trend-following
(time-series momentum), carry, momentum cross-sectionnel, sur un panier **cross-asset
diversifié**. Long/short selon le signe du momentum, vol-targeting, rééquilibrage
mensuel.

**Pourquoi ça persiste.** Ce sont des **risques rémunérés**, pas une inefficience à
arbitrer. Trend-following, carry et momentum sont documentés et robustes OOS depuis
40 ans (Moskowitz-Ooi-Pedersen 2012 ; AQR « A Century of Evidence »). Ils ne
disparaissent pas quand on les publie parce qu'ils paient pour porter un risque que
d'autres veulent fuir (le trend = « crisis alpha », positif en 2008 et 2022).

**Pourquoi toi.** Zéro besoin de latence / infra / capital. Scalable à n'importe
quelle taille. Et surtout : la **leçon étage-1** (*un smoke mono-régime / mono-marché
ne sépare pas l'edge du drift*) s'applique pile — un test trend honnête **exige** le
multi-marché multi-régime, exactement le harness anti-overfit déjà construit. Les
kills passés ont bâti le muscle requis.

**Tueur probable.** Pas « no-edge ever » (le premium est réel) — mais **« edge réel
mais pas worth it »** : trend a connu un hiver post-2009 (une décennie sous le
buy-and-hold). Le vrai risque = trop mince / lent / régime-dépendant pour battre un
simple 60/40 passif après coûts. → Le critère de kill doit être *bat le passif en
risk-adjusted*, pas juste *Sharpe > 0*.

**Pré-test cheap.** Panier ETF cross-asset (free data), TS momentum 12-1 pré-spécifié,
vol-targeting, ~2006-2024 (couvre GFC / COVID / 2022). Réutilise `deflated_sharpe`
+ `pbo_cscv` de l'orderflow tel quel. Spec pré-enregistrée → `factor-harvest/docs/SPEC.md`.

**Statut : KILL standalone (2026-06-21)** — premium **réel** mais **trop faible** sur
univers ETF : Sharpe 0.42, **t=1.87 < 2** (config pré-enreg. 12m), dominé par le 60/40
(0.93). ≠ mirage : 4/5 régimes positifs, drop-one robuste, **DSR(best,N=4)=0.988**,
crisis-alpha fort (2008 +21 %, 2022 +7 %, corr −0.12). Comme **sleeve** sur cœur passif
→ Sharpe 0.93→1.05 (+0.12, modeste, pas un edge). Leçon clé : le **sizing honnête
(gross=1x vs levier empilé 6.3x) a renversé un faux GO** (t=2.05→1.87). **Re-run univers
futures riche (32 marchés, 2026-06-21) = ne sauve PAS** : plus faible (Sharpe 0.25, t=1.22,
DSR 0.62 FAIL, lookbacks courts négatifs) — plombé par le **bruit de roll** (continus
gratuits non back-adjustés, caveat pré-enregistré) + faiblesse réelle post-2009 (reprise
+0.4 %/décennie). Sleeve **+0.12 Sharpe robuste sur les DEUX univers** = seul deliverable.
Settle propre = data payante Norgate, mais même un succès = sleeve, pas un edge → **piste 1
close pour l'objectif edge**. Détail : [`factor-harvest/docs/FINDINGS.md`](factor-harvest/docs/FINDINGS.md).

---

## Piste 2 — Flux forcés mécaniques ★ bon EV

**Thèse.** Se mettre du côté **non-contraint** d'un participant *forcé* : token
unlocks (vesting qui doit vendre), roll de futures, rebalancement d'indices (le fonds
indiciel *doit* acheter au close de reconstitution), pinning à l'expiration d'options.

**Pourquoi ça persiste.** L'edge n'est pas prédictif — c'est une **contrainte
structurelle** d'un autre acteur. Un unlock *doit* libérer de l'offre à date connue ;
un tracker *doit* répliquer l'indice. Tu fournis la liquidité qu'ils paient cher.

**Pourquoi toi.** Méthodo event-study = déjà maîtrisée. Pré-test très cheap
(rendement fenêtré [-Nj, +Nj] autour de l'événement, net de frais).

**Tueur probable.** Crowdé (tout le monde voit le calendrier d'unlock / la date de
rebal). Le edge peut être déjà arbitré dans le prix avant l'événement. Timing +
slippage. → Tester si un résidu net survit *après* le front-running connu.

**Pré-test cheap.** Event-study sur N unlocks / rebals historiques. Données :
unlocks via Dune/token vesting trackers ; rebals indices via dates publiques.

**Statut : EN ATTENTE.**

---

## Piste 3 — Niche capacity-constrained — EV moyen

**Thèse.** Marchés trop petits pour les fonds : petites paires cross-exchange,
inefficiences de chaînes récentes, spreads sur actifs sub-$1M ADV.

**Pourquoi ça persiste.** Les fonds **ne peuvent pas entrer** (leur taille bouge le
marché). Monopole pur du petit acteur.

**Pourquoi toi.** C'est littéralement la définition de l'avantage solo (capacité).

**Tueur probable.** Complexité opérationnelle (multi-exchange, custody), risque
exchange (le vrai tueur, cf. FTX), et surtout **capital petit ⇒ $ minuscules même si
% bon** : 30 % APR sur $5k = $1 500/an. Le ratio temps/EV peut ne pas valoir le coup.

**Pré-test cheap.** Mesurer les spreads cross-exchange réels nets de frais/retrait sur
un échantillon de petites paires ; estimer la capacité $ avant d'écrire une ligne.

**Statut : EN ATTENTE.**

---

## Protocole partagé (tout pré-test doit le franchir)

Repris de `orderflow-bot/docs/ROADMAP.md` — la partie réutilisable telle quelle :

1. **Pré-enregistrement.** Écrire l'hypothèse, la règle, le critère de **succès** ET
   de **kill** *avant* de voir le moindre résultat, à bornes spécifiques à la piste.
   (Leçon FINDINGS : les métriques brutes mentent ; DSR(N=50)=0.008 a tranché.)
2. **Multi-régime obligatoire.** Le test doit séparer l'edge du drift — jamais un
   total flatteur tiré par un seul sous-échantillon / marché. (Leçon étage-1.)
3. **Net de frais + slippage d'office.** Jamais de brut en input de décision.
4. **Audit anti-overfit dès le jour 1.** `deflated_sharpe` (déflate par le nombre
   d'essais) + `pbo_cscv`. Le meilleur Sharpe après k variantes doit battre le seuil
   de bruit SR0.
5. **Miroir / drop-one.** Le résultat survit-il en inversant le signe / en retirant
   le marché qui porte tout le P&L ?
6. **Kill franc.** Une espérance ≤ 0 ne se sauve par aucun sizing (Kelly d'un edge
   négatif = 0). On gèle et on documente, on ne version-hop pas sur un espoir.

## Note méta — quel est le but ?

La reco dépend de l'objectif réel, à clarifier avant d'engager du temps :

- **Cash maintenant** → Piste 1 (primes de risque). Accepter lent / borné / pas sexy.
- **Apprendre / portfolio alternance** → le *pipeline de recherche EST le produit*.
  La méthodo anti-overfit vaut plus sur un CV ingénieur que n'importe quel P&L.
- **Battre le marché pour le frisson** → mauvais ratio temps/EV pour un solo. À éviter.

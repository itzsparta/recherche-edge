# FINDINGS — bot meme-coin Solana (pump.fun snipe)

Journal de falsification, même discipline que l'orderflow-bot : on ne garde une
thèse que si elle survit à des gardes anti-overfit explicites.

## Thèse testée

Sniper les launches pump.fun pré-graduation (entrée ~t0), sortir sur SL −40 % /
TP +100 %/+300 % / time-stop 600 s. Coûts réalistes : slippage 15 %, AMM 0,25 %,
priority 0,0005 SOL, tip Jito 0,001 SOL, achat 0,5 SOL.

## VERDICT : KILL — no-edge, edge fortement NÉGATIF (2026-06-19)

Dataset Dune (événements natifs pump.fun, **rugs inclus**, échantillon par hash,
non biaisé survie), **2 régimes contrastés** :

```
1219 launches | bull euphorie (jan-2025, n=964) + bear crash (aug-2024, n=255)
win_rate   = 6,2 %
PnL/trade  = -0,141 SOL  (≈ -28 % de l'achat 0,5 SOL)
t-stat     = -35,06          significatif NÉGATIF
régimes    : aug_2024_crash -0,133  |  jan_2025 -0,143   (les DEUX négatifs)
naive miroir (buy+time-stop, sans SL/TP) = -0,145 SOL/trade
```

Gates : `mean>0=False · t>2=False · tous_régimes>0=False · bat_naive=True` → **KILL**.

### Pourquoi c'est concluant (pas un artefact)
- **Les deux régimes perdent** (bull ET bear) → espérance négative intrinsèque,
  PAS du drift/beta de marché (cf. leçon orderflow : un edge confiné à un régime
  = drift).
- **Effet énorme** (t=-35 sur n=1219) → contrairement à l'orderflow (effet
  minuscule, n=1,45 M requis), 2 régimes suffisent largement.
- **Miroir naive aussi négatif** → ce n'est PAS la logique SL/TP qui détruit ;
  c'est l'**entrée** qui n'a aucune EV. Le SL/TP ne récupère qu'un cheveu.
- **Mécanisme** = le *moat de coût* : round-trip ≈ +40 % de hausse requise juste
  pour rentrer dans les frais (slippage 15 %×2 + AMM + fees). 94 % des launches
  ne bougent pas assez en 15 min → ils saignent le stack. Marché le plus
  bot-saturé qui existe ; aucune raison structurelle qu'un snipe générique le batte.

### Sélectivité par FDV : testée, KILL dans TOUS les buckets (2026-06-19)
Réponse au « il faut être plus sélectif » : la FDV initiale (= prix 1er bucket
× supply) est le **seul vrai levier connu à t0** sur ce dataset (vol24/liq sont
du look-ahead : totaux 15 min). Split en quartiles, gate sur chacun :

```
ALL          n=1219  mean=-0,141  t=-35,1   [aug-0,133 jan-0,143]  KILL
Q1 bas       n= 305  mean=-0,138  t=-43,3   [aug-0,123 jan-0,140]  KILL
Q2           n= 306  mean=-0,143  t=-26,7   [aug-0,121 jan-0,148]  KILL
Q3           n= 306  mean=-0,149  t=-21,5   [aug-0,164 jan-0,144]  KILL
Q4 haut      n= 305  mean=-0,135  t=-10,3   [aug-0,117 jan-0,141]  KILL
```

Tous les quartiles négatifs, **les deux régimes négatifs dans chacun**, aucun ne
bat son miroir naive. La distribution de FDV est un pic (q25–q75 = 29,7k–32,8k,
±5 %) → la courbe de bonding démarre à params quasi identiques ; le « meilleur »
bucket (Q4 = déjà pumpé en 30 s) reste à −27 %, t=−10. **La sélectivité par FDV
ne sauve rien.** Dredger une queue extrême ne renverse pas un t=−10 en t>+2.

### Anatomie des gagnants : aucun trait t0 ne sauve (2026-06-19)
Réponse au « regardons les gagnants ». Décompo EV sur 1219 trades (76 gagnants) :
- gain moyen gagnant = **+0,295 SOL** ; perte moyenne = **−0,170 SOL** (capés par
  TP/SL + moat coût).
- **win-rate de breakeven requis = 36,5 % ; réel = 6,2 %** → il faudrait ~6× plus
  de gagnants. Aucun filtre t0 ne franchit un tel gouffre.

Traits t0 des gagnants (conditionner sur l'outcome = **data-snooping** ; ceci
GÉNÈRE une hypothèse, seul un test hors-échantillon prouverait) :
- FDV médiane gagnants 35,5k vs perdants 30,5k → cohérent avec le sweep quartile,
  inerte (Q4 « haut » reste −27 %).
- heure : meilleur bloc 06–12h UTC = win 11,2 %, EV −0,113 → meilleur mais
  toujours **négatif**, et 11 % ≪ 36,5 % breakeven.
- noms : « trump » sur-représenté (24 gagnants) mais 9 % de win sur n=257 (jour
  euphorie jan-2025) ; les taux « 100 % » (« 47th » 3 gagnants/0 perdant) sont du
  bruit n→0 — illustration parfaite du piège.

Le seul vrai point commun des gagnants = avoir pumpé +100 % vite = l'**outcome**,
pas un signal d'entrée. KILL triple-confirmé (baseline + sweep FDV + anatomie).

### La leçon data (centrale)
La 1re passe sur **GeckoTerminal `new_pools`** donnait n=4 et un *backtest* à
**+0,223 SOL** d'apparence positive. C'était un **mirage de survivorship** : les
rugs morts sont absents de `new_pools`, et le filtre de liquidité excluait les
morts restants. Relu par les gardes : t=+0,50 (bruit) et la strat perdait contre
le buy-hold naive. **Un backtest biaisé ne peut que confirmer no-edge, jamais le
prouver.** Dune (univers = `pump_evt_createevent` = toutes les créations) corrige
survivorship + look-ahead et rend le vrai verdict : −0,141 SOL/trade.

## Pipeline (reproductible)

```
sql/verdict_pumpfun.sql   un régime/run (le 4-en-1 dépasse le free tier Dune)
   ↓ dune_run.py          REST Dune : .sql -> exécution -> CSV (clé via $DUNE_API_KEY)
data/dune_pumpfun.csv
   ↓ dune_adapter.py      CSV -> episodes.json (transforms purs testés)
data/episodes.dune.json
   ↓ verdict.py           t-stat + split régime + miroir naive -> KILL/PASS
```

Pièges Trino documentés dans `sql/verdict_pumpfun.sql` (evt_block_time, hash→bigint
via `from_big_endian_64`, `coalesce(snake,"camelCase")` amounts, cast double avant
division). Prix = `sol_amount/token_amount` (échelle relative → % SL/TP exacts ;
les colonnes « usd » sont des stand-ins SOL, filtres USD relâchés au verdict).

## NON testé (ne sauverait pas la thèse)
- **Sweep de slippage** : baisser le slippage améliore, mais réduit le moat
  proportionnellement et ne touche pas le win-rate 6 %. Un marché à 6 % de
  gagnants après coûts ne se sauve pas par le tuning.
- **Vélocité early** (n_trades / volume du 1er bucket 30 s) : seul levier t0
  encore non testé ; demande un patch SQL/adapter + re-run Dune. Prior fortement
  négatif (le proxy momentum Q4-FDV perd déjà à −27 %), long-shot.
- Régimes supplémentaires : bloqués par le rate-limit free tier (429) ce jour ;
  inutiles vu l'ampleur de l'effet.

## Statut
**Thèse snipe-keyword / snipe-pré-grad pump.fun MORTE.** Projet au repos. Infra
(core pur + backtester + pipeline Dune + verdict, 87 tests) préservée.

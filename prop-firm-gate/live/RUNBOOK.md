# RUNBOOK — harvest sur FTMO 2-Step (étude #26, step live)

Objet : brancher l'EA buffer-harvest sur un **FTMO 2-Step** (Free Trial d'abord). Deux portages
exposent la **même** logique (étude #26) :

- **`HarvestEA.mq5`** — EA **natif MQL5**, tourne sur le **VPS MetaQuotes sans terminal ouvert**
  (✅ compile 0 erreur / 0 warning). **Voie recommandée** (et plus discrète pour le résidu voiding).
- **`harvest_ea.py`** — version Python (package `MetaTrader5`) : utile pour le **test de logique
  hors-ligne** (dry-run GBM) et comme alternative si tu gardes une machine Windows allumée.

> ⚠️ Ce n'est **pas** un bot d'alpha. Sous no-edge, **le funding est de la chance** (le constat
> #26 lui-même). L'EA récolte un buffer statique, il ne prédit aucune direction.
>
> ⚠️ Le **Free Trial n'a PAS de payout** → il valide la **MÉCANIQUE** (phases, σ/coût réels, ordres
> qui partent) mais **ne lève PAS** le résidu **voiding discrétionnaire** — seul résidu du GO. Ça,
> seul un challenge **payant → funded → payout** le tranche. Cf. [`../docs/FINDINGS-repeated.md`](../docs/FINDINGS-repeated.md).

---

## 0. Prérequis (déjà OK ici)

- MT5 installé : `C:\Program Files\MetaTrader 5` ; MetaEditor présent.
- `HarvestEA.mq5` **compile proprement** (0 err / 0 warn → `HarvestEA.ex5`).
- venv : `C:\Projets\code python\venv` — `MetaTrader5 5.0.5735` (pour la voie Python).

---

## 1. Compte FTMO Free Trial 2-Step — choisir **SWING**

1. ftmo.com → **Free Trial** → **2-Step**, taille **100 000**, plateforme **MT5**, **type Swing**.
2. **Pourquoi Swing et pas Normal** : l'EA tient une position en continu et re-size 1×/jour. Le
   compte **Normal** interdit (a) d'ouvrir/fermer dans une fenêtre ±2 min autour des news, (b) de
   tenir le week-end → un EA automatisé **violerait** ces règles tout seul. Le **Swing** lève les
   deux. Coût = levier **1:30** (vs 1:100), **non contraignant** ici (le harvest ne tient que ~2×
   le notionnel → marge ≪ équité).
3. FTMO envoie **login** / **password** / **server** (ex. `FTMO-Demo`). Garder les 3.

---

## 2. Terminal MT5 (installer + login + algo)

1. Installer/ouvrir **MetaTrader 5** (celui de FTMO, ou MT5 générique).
2. **Login** avec login/password/server du §1.
3. **Allow algorithmic trading** : Tools → Options → Expert Advisors → cocher ; et bouton
   **Algo Trading** de la barre = **vert**.

---

## 3. VOIE RECOMMANDÉE — EA MQL5 + MetaQuotes VPS (**sans** terminal ouvert)

Tu ne peux pas laisser un terminal allumé → le VPS MetaQuotes (hébergement intégré MT5) fait
tourner l'EA 24/7, ton PC éteint.

1. **Compiler** : MT5 → File → *Open Data Folder* → copier `HarvestEA.mq5` dans `MQL5\Experts\`.
   L'ouvrir dans **MetaEditor**, **F7**. → `HarvestEA.ex5`. (Déjà fait ici : 0 erreur.)
2. **Attacher** : ouvrir un graphe **EURUSD**, glisser l'EA dessus. Onglet **Inputs**, régler :
   - **`InpInitialBalance` = taille réelle du compte** (ex. `100000`). **CRITIQUE** : c'est l'ancre
     du plancher statique (max loss = 10 % de CE nombre, **fixe**). `0` = lit le solde au démarrage
     (OK compte neuf, **faux** après des trades / un restart sur compte entamé → mets le nombre).
   - `InpDirection` : défaut **`-1` (short)** — vérifié live sur le compte : EURUSD short = swap
     ~+0.28 vs long −11.4/lot/nuit (long paie le différentiel de taux). Arbitraire pour le P&L sous
     no-edge → on prend le côté swap-positif. À revérifier (`swap_long`/`swap_short`) par symbole.
   - `InpAlreadyFunded` = `false` pour un challenge, `true` pour un compte déjà financé.
   - reste = défauts du modèle (σ 2 %, garde 3σ, payout 14 j, flat week-end ON).
   - cocher **Allow Algo Trading** dans la fenêtre de l'EA.
3. Bouton **AutoTrading** = vert. L'EA logge `[HarvestEA] INIT : A=$… plancher_statique=$… …`.
4. **Migrer sur le VPS** : clic droit sur le graphe → **Rent a Virtual Server** (ou Tools → Rent a
   Virtual Server). Choisir le datacenter le plus proche du serveur FTMO → **Migrate**
   (environnement + EA). L'EA tourne **sans ton terminal**.

**Robustesse restart/migration** : l'état (phase / funded / skim / jour) est **persisté** en
GlobalVariables (clés `HARV_EURUSD_260626_*`) → survit aux redémarrages et à la migration VPS.

**Bank en live** : à chaque cycle l'EA logge `[BANK]` + **Alerte** « demander payout $X ». Le
mouvement d'argent est **manuel** (dashboard FTMO, pas MT5). Sur Free Trial : pas de payout,
`[BANK]` n'est qu'un marqueur mécanique.

---

## 4. Test de LOGIQUE hors-ligne (Python dry-run, optionnel)

Vérifie la machine d'état sans argent ni ordre (GBM driftless) :
```powershell
cd "C:\Projets\code python\prop-firm-gate\live"
..\..\venv\Scripts\python.exe harvest_ea.py --runs 50
```
Distribution `BREACH / EVAL_INCOMPLETE / FUNDED` + rappel « test de LOGIQUE, pas une preuve
d'edge ». `FUNDED` faible/nul en driftless = **normal** (no-edge).

---

## 5. Alternative — Python en direct (si tu gardes un VPS Windows allumé)

Si tu préfères Python sur une machine Windows toujours ON (VPS Windows loué, pas MetaQuotes VPS) :
```powershell
cd "C:\Projets\code python\prop-firm-gate\live"
..\..\venv\Scripts\python.exe harvest_ea.py --live --confirm-live --symbol EURUSD
```
Exige le **terminal MT5 ouvert et loggé** sur la même machine (`mt5.initialize()` s'y attache).
`Ctrl+C` = flat + stop propre.

---

## 6. À surveiller (mécanique, pas P&L)

| Vérifier | Pourquoi |
|---|---|
| σ réalisée ≈ σ cible (2 %) | sizing correct (vol-cible, pas martingale-après-perte) |
| coût/jour réel (spread+swap+slip) | le GO casse au-delà de **14.9 bp/j** (v2 levier) ; réaliste ≈ 5–7 bp |
| la position **fond** près du plancher | la garde anti-breach marche |
| `InpInitialBalance` = vraie taille | sinon le plancher statique est mal ancré (faux breach / faux survie) |
| jamais de **double-après-perte** | l'EA ne le fait pas ; contre-vérif visuelle (flag FTMO #1) |

---

## 7. Limites — à garder en tête

- **Free Trial ≠ payout** → ne tranche pas le **voiding discrétionnaire** (seul résidu du GO).
  Pour ça : challenge **payant** → funded → tenter 1–3 payouts réels.
- Le harvest (tenir une position, banker par cycle) **ressemble à du variance-farming** → risque
  de void. L'EA natif MQL5 sur VPS MetaQuotes (vs bot Python externe) est **moins suspect**.
  Décision camouflage/automatisation fine = **reportée au compte payant**, pas au Free Trial.
- L'EA ne retire **pas** d'argent ; le payout est une action manuelle sur le dashboard FTMO.
- Calibré pour majors à quote USD (EURUSD). Autre symbole → ajuster la devise du P&L (la garde
  suppose P&L ≈ notionnel × variation fractionnaire).

# RUNBOOK — harvest_ea sur FTMO Free Trial (étude #26, step live)

Objet : brancher l'EA buffer-harvest sur un **FTMO Free Trial 2-Step** via MT5. Le Free Trial
valide la **MÉCANIQUE** (les phases se passent ? σ/coût réels ? allure de l'equity curve ?
les ordres partent ?). Il n'a **PAS de payout** → il **ne lève PAS** le résidu voiding ; seul
un challenge **payant → funded → payout** le fait. Cf. [`../docs/FINDINGS-repeated.md`](../docs/FINDINGS-repeated.md).

> ⚠️ Ce n'est pas un bot d'alpha. Sous no-edge, **le funding est de la chance** (le dry-run
> driftless funde rarement — c'est le constat #26, pas un bug). L'EA récolte un buffer
> statique, il ne prédit rien.

---

## 0. Prérequis (déjà OK ici)

- venv : `C:\Projets\code python\venv` — `MetaTrader5 5.0.5735` installé ✓
- EA : `harvest_ea.py` (ce dossier), dry-run logique vérifié ✓
- OS : Windows (le package `MetaTrader5` est Windows-only) ✓

---

## 1. Compte FTMO Free Trial 2-Step

1. ftmo.com → **Free Trial** → choisir **2-Step**, taille 100 000, plateforme **MT5**.
   (l'EA est calé sur 100k / max loss 10 % **statique** / daily 5 % / cibles +10 % puis +5 %.)
2. FTMO envoie par mail + dashboard : **login** (numéro), **password**, **server** (ex.
   `FTMO-Demo`). Garder ces 3 valeurs.

---

## 2. Terminal MT5 (installer + login + algo ON)

1. Installer **MetaTrader 5** (celui de FTMO, ou MT5 générique : File → Open an Account →
   chercher « FTMO »).
2. **Login** avec les 3 valeurs du §1 (File → Login to Trade Account).
3. **Activer l'algo** : bouton **Algo Trading** de la barre d'outils doit être **vert** ; et
   Tools → Options → Expert Advisors → cocher **Allow algorithmic trading**.
4. Laisser le terminal **ouvert et connecté** : le package Python s'**attache au terminal en
   cours** (`mt5.initialize()`), il ne le pilote pas tout seul.
5. Vérifier que le symbole est visible : Market Watch → clic droit → Show All (l'EA fait un
   `symbol_select`, mais autant l'avoir).

Sanity connexion (terminal ouvert + loggé) :
```powershell
cd "C:\Projets\code python\prop-firm-gate\live"
..\..\venv\Scripts\python.exe -c "import MetaTrader5 as m; print(m.initialize(), m.account_info())"
```
Attendu : `True` + une ligne `account_info(...)` avec ton solde 100k. Si `False` → terminal
fermé / pas loggé / algo off.

---

## 3. Dry-run d'abord (zéro argent, zéro ordre)

Toujours relancer le dry-run avant le live — confirme que la machine d'état tourne :
```powershell
cd "C:\Projets\code python\prop-firm-gate\live"
..\..\venv\Scripts\python.exe harvest_ea.py --runs 50
```
Attendu : une distribution `BREACH / EVAL_INCOMPLETE / FUNDED` + un rappel « test de LOGIQUE,
pas une preuve d'edge ». `FUNDED` faible/nul en driftless = **normal**.

---

## 4. LIVE sur le Free Trial

Garde-fou : `--live` **exige** `--confirm-live` (sinon refus).
```powershell
cd "C:\Projets\code python\prop-firm-gate\live"
..\..\venv\Scripts\python.exe harvest_ea.py --live --confirm-live --symbol EURUSD
```
Options : `--sigma 0.02` (vol P&L quotidienne cible ; défaut 0.02), symbole au choix.

Au démarrage il imprime : compte, plancher statique, σ cible. Puis, en boucle (poll 30 s) :
`eq=$... phase=.. funded=.. pv=$...` + un tag `<PHASE>` / `<BANK>` / `<BREACH>` quand ça arrive.

**Ce que fait l'EA en live :**
- tient **une** position (long EURUSD par défaut), **re-dimensionnée 1×/jour** à σ-cible,
  **plafonnée** pour qu'un move de 3σ ne casse aucun plancher (la taille fond près du plancher) ;
- passe phase 0 (+10 %) → reset → phase 1 (+5 %) → **FUNDED** ;
- une fois funded, tous les 14 jours il logge **`[BANK]`** = signal de **retirer l'excès
  MANUELLEMENT sur le dashboard FTMO** (le retrait n'est pas automatisable ; sur Free Trial il
  n'y a de toute façon **pas de payout** — c'est juste le signal mécanique) ;
- sur **`[BREACH]`** il met flat + s'arrête.

**Kill switch :** `Ctrl+C` → flat + `shutdown()` propre.

---

## 5. À surveiller (mécanique, pas P&L)

| Vérifier | Pourquoi |
|---|---|
| σ réalisée ≈ σ cible (2 %) | sizing correct (vol-cible, pas martingale) |
| coût/jour réel (spread+swap+slip) | le GO casse au-delà de **16.5 bp/j** ; réaliste ≈ 5–7 bp |
| la position **fond** près du plancher | la garde anti-breach marche |
| les ordres partent (`retcode` sans `[WARN]`) | filling IOC / volume_step OK sur ce broker |
| jamais de **double-après-perte** | l'EA ne le fait pas ; sert de contre-vérif visuelle |

---

## 6. Limites — à garder en tête

- **Free Trial ≠ payout** → ne tranche pas le **voiding discrétionnaire** (seul résidu du GO).
  Pour ça : challenge **payant** → funded → tenter 1–3 payouts réels.
- L'EA tient une position et banke par cycle → **ressemble à du variance-farming**. Risque de
  void. Sur compte payant, le faire **discret** (turnover bas, pas de pattern mécanique évident)
  réduit le risque. Décision camouflage/automatisation = **reportée au compte payant**, pas ici.
- Bank = action **manuelle** sur le dashboard. L'EA ne retire pas d'argent tout seul.

# Bot meme-coin Solana (paper-trading)

Bot **simulé** : détecte les nouvelles pools Raydium, applique filtres + sécurité,
ouvre/ferme des positions **fictives**. Aucun ordre réel n'est envoyé.

## Architecture

| Fichier | Rôle |
|---|---|
| `core.py` | **Noyau pur** : décisions de trading, zéro dépendance réseau. 100% testé. |
| `scanner.py` | Glue live : websocket Helius → RPC → DexScreener/RugCheck → `core`. |
| `backtester.py` | **Vrai backtest offline** (replay discret-événement sur `core`). |
| `verdict.py` | **Gardes anti-overfit** (t-stat + split régime + miroir naive) → KILL/PASS. |
| `sql/verdict_pumpfun.sql` | Extraction Dune (événements natifs pump.fun, univers non biaisé). |
| `dune_run.py` | Driver REST Dune : `.sql` → exécution → CSV (clé via `$DUNE_API_KEY`). |
| `dune_adapter.py` | CSV Dune → `episodes.json` (transforms purs testés). |
| `strategy.json` / `strategy.backtest.json` / `strategy.verdict.json` | Configs (live / mécanique / verdict). |
| `test_*.py` | Suites pytest (**87 tests**). |
| `The Winner Analyzer.py` | Outil d'analyse des tokens <24h (calibrage des filtres). |
| `api.py` | Mock dashboard FastAPI (démo UI). |

Toute la logique de décision vit dans `core` et sert **à la fois** le live et le
backtest → ce que tu backtestes est exactement ce qui tourne en live.

## Ce qui a été corrigé

- **Stop-loss** ajouté (était défini dans le JSON, jamais implémenté → tenait
  jusqu'au time-stop même à -90%).
- **Détection du mint** : via les soldes post-transaction (`meta`) au lieu de
  `account_keys[8]` codé en dur.
- **Modèle de fills réaliste** : slippage + AMM 0.25% + priority fee + tip Jito.
  Fini le round-trip de quotes qui faisait croire à du profit gratuit.
- **Cap de positions + garde solde** (plus d'achats illimités / solde négatif).
- **Comptabilité PnL** centralisée (`core.Portfolio`).
- **Config unifiée** (`strategy.json`), fini le drift scanner vs JSON.
- **`pick_pair`** : meilleure paire Raydium/SOL au lieu de `pairs[0]` aveugle.
- **`except: pass`** remplacés par du logging.
- **Latence** : worker non-bloquant (plus de `sleep(1s)` sérialisé par signature).
- Bug `keywords:[""]` (matchait tous les tokens) géré explicitement.

## Lancer

```bash
# secrets
cp .env.example .env   # remplir HELIUS_RPC_URL, HELIUS_WSS_URL, TELEGRAM_*

# tests
python -m pytest -q

# backtest sur un dataset d'épisodes
python backtester.py data/episodes.sample.json strategy.json

# live (paper)
python scanner.py
```

## Verdict : KILL — no-edge (voir `FINDINGS.md`)

**Edge TRANCHÉ (2026-06-19).** Sur data Dune réelle non biaisée (1219 launches
pump.fun, rugs inclus, 2 régimes bull+bear) : **PnL −0,141 SOL/trade, t=−35,
win-rate 6 %, négatif dans les DEUX régimes**. Edge fortement négatif. Le moat de
coût (~+40 % round-trip) tue 94 % des launches. Le « profit » antérieur (+0,223
sur n=4 GeckoTerminal) était un **mirage de survivorship**. Détails + pipeline :
`FINDINGS.md`. Thèse morte, projet au repos.

## Autres points ouverts
- **Live non vérifié ici** : `solana` n'est pas installé dans l'env de dev ;
  `scanner.py` est validé en syntaxe + délègue au `core` testé, mais le bout-à-bout
  réseau reste à valider sur machine. (Sans objet vu le verdict.)
- Pas de persistance d'état (crash = portefeuille perdu).

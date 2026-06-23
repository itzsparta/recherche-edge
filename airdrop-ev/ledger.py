"""Ledger EV airdrop farming — pré-enregistré docs/SPEC.md (Piste 14).

Basket FIXE des airdrops majors 2020-2025 (les PAYEURS, survivants sur 5 ans).
Allocations = $ médian par wallet éligible, valorisé au prix ~TGE+7j (GÉNÉREUX
pour la thèse : near-peak pour la plupart). Figures publiques approximatives,
sourcées en commentaire. Le tueur ne vient PAS de ces chiffres mais du labeur +
de la concentration jackpots + des zéros farmés (gas payé sans payout).
"""
from __future__ import annotations

import json
import urllib.request

# name, coingecko id, année TGE, alloc médian éligible $ au TGE (généreux), prix TGE $ (pour décroissance)
# Figures publiques post-airdrop (post-mortems communautaires). Valorisation TGE = best-case réalisable.
BASKET = [
    ("Uniswap UNI",   "uniswap",       2020,  1200,   3.0),    # 400 UNI flat × ~$3
    ("dYdX",          "dydx-chain",    2021,  5000,   10.0),   # tiered traders, médiane élevée = JACKPOT
    ("ENS",           "ethereum-name-service", 2021, 1500, 30.0),  # variable durée d'enregistrement
    ("Optimism OP",   "optimism",      2022,  700,    1.8),    # round-1 ~$600-800
    ("Arbitrum ARB",  "arbitrum",      2023,  1000,   1.2),    # 625-1250 ARB × ~$1.2
    ("Blur",          "blur",          2023,  1500,   0.8),    # traders NFT, variable
    ("Celestia TIA",  "celestia",      2023,  1000,   2.0),    # stakers/devs, généreux
    ("Jupiter JUP",   "jupiter-exchange-solana", 2024, 700, 0.5),  # tiered, médiane modeste
    ("Starknet STRK", "starknet",      2024,  1000,   2.0),    # controversé éligibilité
    ("Wormhole W",    "wormhole",      2024,  1800,   1.3),    # généreux
    ("zkSync ZK",     "zksync",        2024,  500,    0.18),   # décevant pour beaucoup
    ("LayerZero ZRO", "layerzero",     2024,  400,    4.0),    # donation-to-claim, net faible
    ("EigenLayer EIGEN","eigenlayer",  2024,  800,    3.5),    # locké/illiquide au départ
    ("Ethena ENA",    "ethena",        2024,  1000,   0.7),    # sats farmers
    ("Hyperliquid HYPE","hyperliquid", 2024,  10000,  3.5),    # JACKPOT, médiane active très élevée
]

JACKPOTS = {"dYdX", "Hyperliquid HYPE"}  # non-répétables (chance/timing), retirés en base-case


def fetch_current_prices() -> dict[str, float]:
    """Prix spot actuels CoinGecko (gratuit) pour la décroissance hold-to-now."""
    ids = ",".join(c for _, c, *_ in BASKET)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=30).read())
        return {c: float(d.get(c, {}).get("usd", float("nan"))) for _, c, *_ in BASKET}
    except Exception as e:
        print(f"  CoinGecko indispo ({e}) — décroissance non affichée.")
        return {}


def total_alloc(exclude: set | None = None) -> float:
    exclude = exclude or set()
    return sum(a for n, _c, _y, a, _p in BASKET if n not in exclude)

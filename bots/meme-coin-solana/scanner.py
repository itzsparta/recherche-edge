"""Scanner LIVE (paper-trading) de nouvelles pools Raydium sur Solana.

Toute la logique de DÉCISION est déléguée au noyau pur `core` (testé hors-ligne) :
filtres, sécurité, cap de positions, modèle de fills/frais, STOP-LOSS, take-profit,
comptabilité PnL. Ce fichier ne contient plus que la glue réseau (websocket Helius,
RPC, DexScreener, RugCheck, Telegram).

C'est un bot SIMULÉ : aucun ordre réel n'est envoyé. Les fills sont modélisés par
core.simulate_buy / simulate_sell (slippage + frais réalistes), pas par des quotes
round-trip fantaisistes.

Secrets via .env : HELIUS_RPC_URL, HELIUS_WSS_URL, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID.
Stratégie via strategy.json (source unique, voir core.Strategy.from_dict).
"""
import asyncio
import json
import logging
import os
import time

import aiohttp
from dotenv import load_dotenv
from solana.rpc.async_api import AsyncClient
from solders.signature import Signature
from websockets import connect

import core

load_dotenv()

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("memebot")

# ----------------------------- config / secrets -----------------------------
RPC_URL = os.getenv("HELIUS_RPC_URL")
WSS_URL = os.getenv("HELIUS_WSS_URL")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID")
START_BALANCE = float(os.getenv("START_BALANCE_SOL", "100"))

# Venue de LAUNCH = pump.fun (en 2026 ~80% des memecoins y naissent ; Raydium AMM
# v4 ne reçoit plus de launches). On écoute le programme pump.fun et son
# instruction "Create" (nouveau token).
# /!\ A VALIDER EN LIVE : program id + chaîne de log exacts non vérifiables hors
# machine (pas de `solana` dans l'env de dev). Ancien Raydium garde en repli.
PUMPFUN_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
LAUNCH_TRIGGER = "Instruction: Create"
RAYDIUM_LP_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"   # repli AMM (gradués)
WATCH_PROGRAM = PUMPFUN_PROGRAM
SOL_MINT = core.WSOL

POLL_SECONDS = 10               # cadence de surveillance du portefeuille
GET_TX_CONCURRENCY = 5          # appels get_transaction concurrents (anti-latence)
HEALTH_SECONDS = 30

# état global
TX_QUEUE = asyncio.Queue()
SEM = asyncio.Semaphore(GET_TX_CONCURRENCY)


def load_strategy(path="strategy.json"):
    with open(path, "r", encoding="utf-8") as f:
        return core.Strategy.from_dict(json.load(f))


STRATEGY = load_strategy()
PORTFOLIO = core.Portfolio(balance_sol=START_BALANCE)


# ------------------------------- Telegram -----------------------------------
async def send_tg(session, msg):
    if not (TG_TOKEN and TG_CHAT):
        return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML",
                   "disable_web_page_preview": True}
        async with session.post(url, json=payload, timeout=5) as resp:
            await resp.text()
    except Exception as e:
        log.warning("Telegram KO: %s", e)


# ------------------------------- data fetch ---------------------------------
async def fetch_pair(session, mint):
    """Paire Raydium/SOL la plus liquide pour ce mint (None si rien d'exploitable)."""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
        async with session.get(url, timeout=3) as response:
            if response.status != 200:
                return None
            data = await response.json()
    except Exception as e:
        log.debug("DexScreener KO %s: %s", mint, e)
        return None
    return core.pick_pair(data.get("pairs") or [])


def price_native(pair):
    """Prix en SOL par token (priceNative DexScreener), 0.0 si indisponible."""
    try:
        return float(pair.get("priceNative", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


async def fetch_rug(session, mint):
    """(score, risks) RugCheck. Score neutre 500 si l'appel échoue."""
    try:
        url = f"https://api.rugcheck.xyz/v1/tokens/{mint}/report/summary"
        async with session.get(url, timeout=5) as response:
            if response.status != 200:
                return 500, []
            data = await response.json()
        return data.get("score", 1000), [r["name"] for r in data.get("risks", [])]
    except Exception as e:
        log.debug("RugCheck KO %s: %s", mint, e)
        return 500, []


def extract_base_mint(tx):
    """Isole le mint du token via les soldes post-transaction (meta), bien plus
    fiable que l'ancien account_keys[8] codé en dur. core.select_base_mint écarte
    les quotes (WSOL/USDC/USDT)."""
    meta = getattr(tx.value, "meta", None)
    balances = getattr(meta, "post_token_balances", None) or []
    mints = list(dict.fromkeys(str(b.mint) for b in balances))
    return core.select_base_mint(mints)


# ------------------------------ entrée (achat) ------------------------------
async def evaluate(session, mint):
    if PORTFOLIO.has(mint):
        return
    pair = await fetch_pair(session, mint)
    if not pair:
        return

    fdv = float(pair.get("fdv", 0) or 0)
    liq = float(pair.get("liquidity", {}).get("usd", 0) or 0)
    vol = float(pair.get("volume", {}).get("h24", 0) or 0)
    name = pair.get("baseToken", {}).get("name", "Unknown")

    if not core.passes_filters(liq, fdv, vol, STRATEGY):
        return
    matched = core.match_keyword(name, STRATEGY.keywords)
    if matched is None:
        return
    price = price_native(pair)
    if price <= 0:
        return

    score, risks = await fetch_rug(session, mint)
    if not core.security_ok(score, risks, STRATEGY):
        log.info("REFUS securite %s (score=%s risks=%s)", name, score, risks)
        return
    if not core.can_open(PORTFOLIO.n_open, PORTFOLIO.balance_sol, STRATEGY):
        log.info("SKIP %s : cap positions atteint ou solde insuffisant", name)
        return

    fill = core.simulate_buy(STRATEGY.buy_amount_sol, price, STRATEGY)
    PORTFOLIO.open(mint, name, fill, buy_timestamp=time.time())
    log.info("ACHAT %s | kw=%s | liq=%.0f$ | cout=%.4f SOL | solde=%.3f",
             name, matched or "(no-filter)", liq, fill.cost_basis_sol, PORTFOLIO.balance_sol)
    await send_tg(session, f"🚀 <b>ACHAT</b>\nToken: {name}\nLiq: {liq:.0f}$\n"
                           f"Solde: {PORTFOLIO.balance_sol:.3f} SOL")


# --------------------------- sortie (surveillance) --------------------------
async def monitor_portfolio(session):
    log.info("Surveillance portefeuille (SL=%s%% | TP=%s | time=%ss)",
             STRATEGY.stop_loss_percent, STRATEGY.take_profit_steps, STRATEGY.max_hold_seconds)
    while True:
        await asyncio.sleep(POLL_SECONDS)
        for mint, pos in list(PORTFOLIO.positions.items()):
            try:
                pair = await fetch_pair(session, mint)
                price = price_native(pair) if pair else 0.0
                if price <= 0:
                    continue
                pct = (price - pos.entry_market_price) / pos.entry_market_price * 100
                held = time.time() - pos.buy_timestamp
                d = core.decide_exit(pct, held, pos.steps_reached, STRATEGY)
                if d.action == "HOLD":
                    continue

                fraction = 1.0 if d.action == "SELL_ALL" else d.sell_ratio
                tokens_sold = pos.tokens * fraction
                proceeds = core.simulate_sell(tokens_sold, price, STRATEGY)
                if d.action == "SELL_PARTIAL":
                    pos.steps_reached.append(d.step_percent)
                PORTFOLIO.sell(mint, fraction, proceeds)

                log.info("VENTE %s | %s | %.1f%% | +%.4f SOL | solde=%.3f | PnL cumul=%.3f",
                         pos.name, d.reason, pct, proceeds, PORTFOLIO.balance_sol,
                         PORTFOLIO.realized_pnl_sol)
                await send_tg(session, f"💰 <b>{d.reason}</b>\nToken: {pos.name}\n"
                                       f"Perf: {pct:.1f}%\nSolde: {PORTFOLIO.balance_sol:.3f} SOL")
            except Exception:
                log.exception("Erreur surveillance %s", mint)


# ------------------------------- monitoring ---------------------------------
async def health_check():
    while True:
        await asyncio.sleep(HEALTH_SECONDS)
        log.info("STATUS | queue=%d | positions=%d | solde=%.3f | PnL=%.3f",
                 TX_QUEUE.qsize(), PORTFOLIO.n_open, PORTFOLIO.balance_sol,
                 PORTFOLIO.realized_pnl_sol)


# ------------------------------- workers ------------------------------------
async def handle_sig(client, session, sig_str):
    async with SEM:
        try:
            signature = Signature.from_string(sig_str)
            tx = await client.get_transaction(signature, max_supported_transaction_version=0)
        except Exception as e:
            if "429" in str(e):
                await asyncio.sleep(2)
            else:
                log.debug("get_transaction KO: %s", e)
            return
    try:
        if not (tx and tx.value):
            return
        mint = extract_base_mint(tx)
        if mint:
            await evaluate(session, mint)
    except Exception:
        log.exception("Erreur traitement signature")


async def worker(client, session):
    log.info("Worker pret (concurrence=%d).", GET_TX_CONCURRENCY)
    while True:
        sig = await TX_QUEUE.get()
        # non-bloquant : ne sérialise plus la queue (corrige la latence)
        asyncio.create_task(handle_sig(client, session, sig))
        TX_QUEUE.task_done()


async def run_scanner():
    if not (RPC_URL and WSS_URL):
        log.error("HELIUS_RPC_URL / HELIUS_WSS_URL manquants dans .env")
        return
    log.info("BOT meme-coin (paper) | profil=%s | cibles=%s",
             STRATEGY.keywords, STRATEGY.keywords)
    log.info("Filtres: ratio[%.1f-%.1f]%% liq[%.0f-%.0f]$ | SL=%s%% | cap=%d",
             STRATEGY.min_ratio_liq_fdv, STRATEGY.max_ratio_liq_fdv,
             STRATEGY.min_liquidity_usd, STRATEGY.max_liquidity_usd,
             STRATEGY.stop_loss_percent, STRATEGY.max_open_positions)
    if not core.match_keyword("xxx", STRATEGY.keywords):
        log.warning("Aucun mot-cle non-vide : FILTRE NOM DESACTIVE (achat large).")

    async with aiohttp.ClientSession() as session:
        asyncio.create_task(health_check())
        asyncio.create_task(monitor_portfolio(session))
        async with AsyncClient(RPC_URL) as client:
            asyncio.create_task(worker(client, session))
            while True:
                try:
                    async with connect(WSS_URL) as ws:
                        await ws.send(json.dumps({
                            "jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                            "params": [{"mentions": [WATCH_PROGRAM]},
                                       {"commitment": "processed"}]}))
                        log.info("Radar pump.fun connecte (%s).", WATCH_PROGRAM)
                        while True:
                            data = json.loads(await ws.recv())
                            if "params" not in data:
                                continue
                            value = data["params"]["result"]["value"]
                            if any(LAUNCH_TRIGGER in l for l in value["logs"]):
                                TX_QUEUE.put_nowait(value["signature"])
                except Exception as e:
                    log.warning("Reconnexion WSS (%s)", e)
                    await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(run_scanner())

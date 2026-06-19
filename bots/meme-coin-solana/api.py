from fastapi import FastAPI
from pydantic import BaseModel
import random
from typing import Optional

app = FastAPI()

# Simulation DB
bots_db = [
    {"id": 1, "name": "ALPHA.ETH [SAFE]", "balance": 10.542, "pnl": 0.23, "strategy": "MEV_PROTECT"},
    {"id": 2, "name": "BETA.SOL [DEGEN]", "balance": 4.210, "pnl": -0.55, "strategy": "SNIPER_V2"},
    {"id": 3, "name": "GAMMA.ARB [AI]", "balance": 50.005, "pnl": 1.20, "strategy": "ARBITRAGE"},
]

# --- CONFIGURATION TECHNIQUE COMPLÈTE ---
class BotConfig(BaseModel):
    # --- EXECUTION ---
    rpc_endpoint: str         # ex: Helius, QuickNode
    priority_fee: float       # Jito Tip
    slippage_bps: int         # En points de base (ex: 500 = 5%)
    engine_mode: str          # "Spam" ou "Bundle"
    
    # --- RISK MANAGEMENT ---
    invest_amount: float
    take_profit_pct: float
    stop_loss_pct: float
    trailing_stop_pct: float
    max_open_positions: int   # Nouveau
    
    # --- ANTI-RUG / SAFETY ---
    min_liquidity_usd: int
    max_dev_holding_pct: int  # Max % détenu par le dev
    max_top10_holding_pct: int # Max % détenu par les 10 plus gros
    min_volume_5m: int        # Volume min sur 5 min
    require_verified: bool    # Token vérifié seulement
    
    # --- STRATEGY ---
    keywords_include: str
    keywords_exclude: str     # Nouveau : Mots à bannir

@app.get("/bots")
def get_all_bots():
    for bot in bots_db:
        change = random.uniform(-0.01, 0.02)
        bot["balance"] += change
        bot["pnl"] += change
    return bots_db

@app.post("/bot/{bot_id}/update")
def update_bot(bot_id: int, config: BotConfig):
    print(f"\n[BOT {bot_id}] CONFIG UPDATED VIA TERMINAL")
    print(f">> EXEC: {config.engine_mode} | RPC: {config.rpc_endpoint} | FEE: {config.priority_fee} SOL")
    print(f">> RISK: TP +{config.take_profit_pct}% | SL -{config.stop_loss_pct}% | MAX_POS: {config.max_open_positions}")
    print(f">> FILTERS: Dev<{config.max_dev_holding_pct}% | Top10<{config.max_top10_holding_pct}% | Vol5m>${config.min_volume_5m}")
    return {"status": "ok", "msg": "CONFIG_SYNCED"}
#uvicorn api:app --host 0.0.0.0 --port 8000 --reload
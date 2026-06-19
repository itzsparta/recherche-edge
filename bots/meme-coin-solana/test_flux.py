import asyncio
import json
from websockets import connect
from colorama import init, Fore
import os
from dotenv import load_dotenv

init()
load_dotenv()

# Tes clés (je les ai remises pour toi)
WSS_URL = os.getenv("HELIUS_WSS_URL")
RAYDIUM_LP_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"

async def test_flux():
    print(f"{Fore.CYAN}📡 TEST DE FLUX HELIUS...{Fore.RESET}")
    async with connect(WSS_URL) as ws:
        await ws.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "logsSubscribe",
            "params": [
                {"mentions": [RAYDIUM_LP_V4]},
                {"commitment": "processed"}
            ]
        }))
        print(f"{Fore.GREEN}✅ Connecté ! En attente de données brutes...{Fore.RESET}")
        
        while True:
            msg = await ws.recv()
            # On affiche tout sans réfléchir
            if "initialize2" in msg:
                print(f"{Fore.YELLOW}🔔 PING ! Pool détectée{Fore.RESET}")
            else:
                # Affiche un point pour dire "je suis en vie" sur les autres logs
                print(".", end="", flush=True)

if __name__ == "__main__":
    asyncio.run(test_flux())
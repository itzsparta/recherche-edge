import asyncio
from solana.rpc.async_api import AsyncClient
from colorama import init, Fore, Style

init()

async def main():
    print(f"{Fore.CYAN}--- TEST DU BOT CRYPTO ---{Style.RESET_ALL}")
    
    # Utilisation d'un bloc try/except pour gérer les erreurs proprement
    try:
        async with AsyncClient("https://api.mainnet-beta.solana.com") as client:
            if await client.is_connected():
                print(f"{Fore.GREEN}✅ SUCCÈS : Connecté au réseau Solana !{Style.RESET_ALL}")
                
                bloc = await client.get_slot()
                print(f"📦 Bloc actuel : {bloc.value}") # .value est nécessaire ici
                
                version = await client.get_version()
                # Correction du TypeError : on accède à l'attribut solana_core
                print(f"ℹ️  Version du Nœud : {version.value.solana_core}")
            else:
                print(f"{Fore.RED}❌ ÉCHEC : Impossible de joindre le réseau.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}❌ ERREUR TECHNIQUE : {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    asyncio.run(main())

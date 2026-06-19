import requests
import pandas as pd
import datetime
from colorama import init, Fore

init()

# On cherche large pour attraper tout ce qui bouge sur Solana
SEARCH_KEYWORDS = ["solana", "pump", "raydium", "ai", "meme", "cat", "dog"]

def get_fresh_winners():
    print(f"{Fore.CYAN}📡 Scan des tokens nés il y a moins de 24h...{Fore.RESET}")
    fresh_winners = []
    seen_addresses = set()
    
    for term in SEARCH_KEYWORDS:
        try:
            url = f"https://api.dexscreener.com/latest/dex/search?q={term}"
            data = requests.get(url, timeout=5).json()
            
            if 'pairs' in data:
                for p in data['pairs']:
                    # 1. FILTRE CHAIN : Solana uniquement
                    if p['chainId'] != 'solana': continue
                    
                    # 2. FILTRE DOUBLONS
                    addr = p['pairAddress']
                    if addr in seen_addresses: continue
                    seen_addresses.add(addr)

                    # 3. FILTRE ÂGE (Le plus important)
                    created_at = p.get('pairCreatedAt', 0) / 1000
                    age_hours = (datetime.datetime.now().timestamp() - created_at) / 3600
                    
                    # On veut les tokens nés entre 1h et 24h (pas les trop vieux, pas les instantanés)
                    if 1.0 <= age_hours <= 24.0:
                        
                        # 4. FILTRE SUCCÈS (Il faut qu'il y ait de l'activité)
                        vol = float(p.get('volume', {}).get('h24', 0))
                        liq = float(p.get('liquidity', {}).get('usd', 0))
                        
                        # Si volume > 50k$ et Liq > 5k$ (C'est un lancement réussi)
                        if vol > 50000 and liq > 5000:
                            p['age_hours'] = age_hours # On stocke l'âge calculé
                            fresh_winners.append(p)
                            print(".", end="", flush=True)
        except Exception as e:
            print(f"{Fore.LIGHTBLACK_EX}({term} KO: {e}){Fore.RESET}")

    print(f"\n{Fore.GREEN}✅ {len(fresh_winners)} pépites récentes (<24h) trouvées.{Fore.RESET}")
    return fresh_winners

def analyze_fresh_patterns(pairs):
    data = []
    for p in pairs:
        try:
            fdv = float(p.get('fdv', 0))
            if fdv == 0: continue
            
            liq = float(p.get('liquidity', {}).get('usd', 0))
            vol = float(p.get('volume', {}).get('h24', 0))
            
            # Calculs
            liq_ratio = (liq / fdv) * 100
            vol_liq_ratio = vol / liq
            
            data.append({
                "Name": p['baseToken']['name'],
                "Age": p['age_hours'],
                "Liquidity": liq,
                "FDV": fdv,
                "Liq_Ratio": liq_ratio,
                "Hype_Ratio": vol_liq_ratio
            })
        except Exception:
            continue
        
    return pd.DataFrame(data)

def report(df):
    if df.empty:
        print("Pas assez de données récentes.")
        return

    print(f"\n{Fore.YELLOW}=== PROFIL DU GAGNANT 'DAY 1' ({len(df)} tokens) ==={Fore.RESET}")
    
    # On utilise la médiane
    print(f"\n{Fore.CYAN}📊 PARAMÈTRES À COPIER DANS TON BOT :{Fore.RESET}")
    
    ideal_liq = df['Liquidity'].median()
    ideal_fdv = df['FDV'].median()
    ideal_ratio = df['Liq_Ratio'].median()
    
    print(f"• Liquidité Moyenne : ${ideal_liq:,.0f}")
    print(f"• FDV (Cap) Moyenne : ${ideal_fdv:,.0f}")
    print(f"• Ratio Santé (Liq/FDV) : {ideal_ratio:.2f}%")
    print(f"• Hype (Volume/Liq) : {df['Hype_Ratio'].median():.1f}x")
    
    print(f"\n{Fore.WHITE}💡 INTERPRÉTATION :{Fore.RESET}")
    print(f"-> Un token qui sort avec moins de {ideal_ratio/2:.1f}% de ratio Liq/FDV est suspect.")
    print(f"-> Un vrai winner brasse {df['Hype_Ratio'].median():.1f} fois sa liquidité en volume par jour.")

    # Top Mots
    print(f"\n{Fore.CYAN}🔤 MOTS CLÉS DU JOUR (<24h) :{Fore.RESET}")
    names = " ".join(df['Name'].astype(str)).upper()
    ignore = ["SOLANA", "COIN", "THE", "PUMP", "TOKEN"]
    from collections import Counter
    words = [w for w in names.split() if len(w) > 3 and w not in ignore]
    for w, c in Counter(words).most_common(8):
        print(f"• {w}: {c}")

if __name__ == "__main__":
    pairs = get_fresh_winners()
    df = analyze_fresh_patterns(pairs)
    report(df)
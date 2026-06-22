import time
from datetime import datetime
import pandas as pd
import numpy as np
from scipy.signal import find_peaks
import MetaTrader5 as mt5

# ==========================================
# 1. PARAMÈTRES GLOBAUX (CONFIGURATION)
# ==========================================
SYMBOL = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_M15
VOLUME_LOT = 0.10
MAGIC_NUMBER = 2006 # ID unique du bot

# Paramètres Mathématiques (SciPy & Range)
DISTANCE_MIN = 10 
PROEMINENCE_MIN = 0.0005 
TOLERANCE_RANGE = 0.05

# ==========================================
# 2. MOTEUR D'ANALYSE (DATA & MATHS)
# ==========================================
def analyser_structure_marche():
    """Télécharge l'historique, lisse les prix et cherche un range."""
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 1000)
    if rates is None:
        print("❌ Erreur d'extraction des données.")
        return False, None, None
    
    df = pd.DataFrame(rates)
    
    # Lissage EMA 10
    df['lisse'] = df['close'].ewm(span=10, adjust=False).mean()
    
    # Détection des pivots
    sommets_idx, _ = find_peaks(df['lisse'], distance=DISTANCE_MIN, prominence=PROEMINENCE_MIN)
    creux_idx, _ = find_peaks(-df['lisse'], distance=DISTANCE_MIN, prominence=PROEMINENCE_MIN)
    
    # Vérification des données suffisantes
    if len(sommets_idx) < 2 or len(creux_idx) < 2:
        return False, None, None
        
    derniers_sommets = df['lisse'].iloc[sommets_idx].tail(2).values
    derniers_creux = df['lisse'].iloc[creux_idx].tail(2).values
    
    # Calcul de l'écartement
    ecart_plafond = abs(derniers_sommets[1] - derniers_sommets[0]) / derniers_sommets[0] * 100
    ecart_plancher = abs(derniers_creux[1] - derniers_creux[0]) / derniers_creux[0] * 100
    
    range_propre = (ecart_plafond <= TOLERANCE_RANGE) and (ecart_plancher <= TOLERANCE_RANGE)
    
    # Retourne le statut booléen et les niveaux de prix récents
    return range_propre, derniers_sommets[1], derniers_creux[1]

# ==========================================
# 3. MOTEUR D'EXÉCUTION (ORDRES MT5)
# ==========================================
def tenter_execution(plafond, plancher):
    """Vérifie le tick actuel et déclenche l'ordre si les conditions sont remplies."""
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        print("❌ Impossible de lire le prix en direct.")
        return
        
    prix_ask = tick.ask
    heure_actuelle = datetime.now().hour
    
    # Filtres logiques
    session_active = 8 <= heure_actuelle <= 17
    cassure_haussiere = prix_ask > plafond

    if session_active and cassure_haussiere:
        print(f"🚀 Cassure confirmée à {prix_ask}. Envoi de l'ordre...")
        
        distance_stop = prix_ask - plancher
        prix_sl = plancher - 0.0002
        prix_tp = prix_ask + (distance_stop * 3)
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": SYMBOL,
            "volume": VOLUME_LOT,
            "type": mt5.ORDER_TYPE_BUY,
            "price": prix_ask,
            "sl": prix_sl,
            "tp": prix_tp,
            "deviation": 10,
            "magic": MAGIC_NUMBER,
            "comment": "Bot_Breakout",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Échec de l'ordre. Code : {result.retcode}")
        else:
            print(f"✅ Trade ouvert ! Ticket: {result.order}")
    else:
        print(f"⏳ Attente... (Prix actuel: {prix_ask:.5f} | Plafond: {plafond:.5f})")

# ==========================================
# 4. BOUCLE PRINCIPALE (MAIN)
# ==========================================
def main():
    if not mt5.initialize():
        print("❌ Échec de l'initialisation MT5")
        return
        
    print("✅ Connecté à MT5. Démarrage de l'analyse...")
    
    try:
        # Étape 1 : Analyse structurelle
        range_valide, plafond, plancher = analyser_structure_marche()
        
        if range_valide:
            print(f"✅ Range détecté. Plafond: {plafond:.5f} | Plancher: {plancher:.5f}")
            # Étape 2 : Tentative d'exécution
            tenter_execution(plafond, plancher)
        else:
            print("❌ Structure invalide. Pas de range propre en cours.")
            
    finally:
        # Garantie de fermeture de la connexion API quoi qu'il arrive
        mt5.shutdown()
        print("🔌 Déconnecté de MT5.")

if __name__ == "__main__":
    main()
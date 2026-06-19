"""Tests des transforms purs du pipeline data (GeckoTerminal -> episodes).
Aucune dépendance réseau : fixtures = vrai schéma API v2 capturé en live."""
import pytest
from core import WSOL
from fetch_episodes import (mint_from_token_id, pool_to_meta, is_target_pool,
                            ohlcv_to_path, build_episode)


def _pool(dex="raydium", quote_mint=WSOL, **attr_over):
    attrs = {
        "address": "H44EkUFS8rviKo4GpcyknXEV545KtTVttbxQZuMcEXkS",
        "name": "WAIFU / SOL",
        "pool_created_at": "2026-06-19T09:13:56Z",
        "reserve_in_usd": "6338.12117660491",   # l'API renvoie des strings
        "fdv_usd": "143775.0272",
        "volume_usd": {"h24": "6072.4292651974"},
    }
    attrs.update(attr_over)
    return {
        "type": "pool",
        "attributes": attrs,
        "relationships": {
            "base_token": {"data": {"id": "solana_J1CwfeLCNSNwfh4FTbuL9gr1Z3CAtx8E5Jkmj2RdNufK"}},
            "quote_token": {"data": {"id": f"solana_{quote_mint}"}},
            "dex": {"data": {"id": dex}},
        },
    }


# ---------------- mint_from_token_id ----------------
def test_mint_retire_le_prefixe_reseau():
    assert mint_from_token_id("solana_ABC123") == "ABC123"


def test_mint_sans_prefixe_inchange():
    assert mint_from_token_id("ABC123") == "ABC123"


# ---------------- pool_to_meta ----------------
def test_pool_to_meta_parse_les_champs():
    m = pool_to_meta(_pool())
    assert m["mint"] == "J1CwfeLCNSNwfh4FTbuL9gr1Z3CAtx8E5Jkmj2RdNufK"
    assert m["name"] == "WAIFU / SOL"
    assert m["liq_usd"] == pytest.approx(6338.12, abs=0.1)
    assert m["fdv_usd"] == pytest.approx(143775.03, abs=0.1)
    assert m["vol24_usd"] == pytest.approx(6072.43, abs=0.1)
    assert m["dex"] == "raydium"
    assert m["quote_mint"] == WSOL


def test_pool_to_meta_launch_time_en_epoch():
    m = pool_to_meta(_pool())
    # 2026-06-19T09:13:56Z = 1781860436 epoch
    assert m["launch_time"] == 1781860436


def test_pool_to_meta_tolere_valeurs_manquantes():
    p = _pool()
    del p["attributes"]["volume_usd"]
    p["attributes"]["fdv_usd"] = None
    m = pool_to_meta(p)
    assert m["vol24_usd"] == 0.0
    assert m["fdv_usd"] == 0.0


# ---------------- is_target_pool ----------------
def test_target_raydium_sol_accepte():
    assert is_target_pool(pool_to_meta(_pool(dex="raydium", quote_mint=WSOL))) is True


def test_target_pumpfun_sol_accepte():
    # univers réel 2026 : les memecoins lancent sur pump-fun / pumpswap, pas raydium
    assert is_target_pool(pool_to_meta(_pool(dex="pump-fun", quote_mint=WSOL))) is True
    assert is_target_pool(pool_to_meta(_pool(dex="pumpswap", quote_mint=WSOL))) is True


def test_target_dex_hors_liste_refuse():
    assert is_target_pool(pool_to_meta(_pool(dex="orca"))) is False


def test_target_quote_non_sol_refuse():
    usdc = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    assert is_target_pool(pool_to_meta(_pool(quote_mint=usdc))) is False


# ---------------- ohlcv_to_path ----------------
def test_ohlcv_descendant_devient_path_ascendant_relatif():
    launch = 1000
    # API renvoie du plus récent au plus ancien
    ohlcv = [
        [1120, 2e-6, 2e-6, 2e-6, 2.5e-6, 9],
        [1060, 1.5e-6, 1.5e-6, 1.5e-6, 1.8e-6, 8],
        [1000, 1e-6, 1e-6, 1e-6, 1.1e-6, 7],
    ]
    path = ohlcv_to_path(ohlcv, launch)
    assert path == [[0, 1.1e-6], [60, 1.8e-6], [120, 2.5e-6]]  # close, t relatif, trié


def test_ohlcv_drop_bougies_avant_launch():
    launch = 1000
    ohlcv = [[1060, 1, 1, 1, 1.8e-6, 8], [940, 1, 1, 1, 9e-7, 5]]  # 940 < launch
    path = ohlcv_to_path(ohlcv, launch)
    assert path == [[60, 1.8e-6]]


def test_ohlcv_vide_donne_path_vide():
    assert ohlcv_to_path([], 1000) == []


# ---------------- build_episode ----------------
def test_build_episode_complet_pour_backtester():
    # launch_time + t=0 calés sur la PREMIERE bougie (début négociable réel),
    # pas sur pool_created_at (sinon held mal compté)
    ohlcv = [[5060, 1, 1, 1, 1.8e-6, 8], [5000, 1, 1, 1, 1.1e-6, 7]]
    ep = build_episode(_pool(), ohlcv)
    assert ep["mint"] == "J1CwfeLCNSNwfh4FTbuL9gr1Z3CAtx8E5Jkmj2RdNufK"
    assert ep["name"] == "WAIFU / SOL"
    assert ep["launch_time"] == 5000          # ts de la 1re bougie
    assert ep["liq_usd"] == pytest.approx(6338.12, abs=0.1)
    assert ep["rug_score"] == 0               # pas de rug historique
    assert ep["risks"] == []
    assert ep["path"][0] == [0, 1.1e-6]       # t relatif à la 1re bougie
    assert ep["path"][1] == [60, 1.8e-6]

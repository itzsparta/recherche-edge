"""Tests du noyau pur (aucune dépendance réseau/solana)."""
import pytest
import core
from core import (Strategy, decide_exit, simulate_buy, simulate_sell,
                  can_open, passes_filters, security_ok, pick_pair,
                  Fill, Portfolio, select_base_mint, WSOL, match_keyword)


def _strat(**over):
    base = dict(stop_loss_percent=-50.0, max_hold_seconds=600.0,
                take_profit_steps=[(100.0, 0.5), (300.0, 0.5)])
    base.update(over)
    return Strategy(**base)


def _costs(**over):
    base = dict(amm_fee_pct=0.0, slippage_pct=0.0, priority_fee_sol=0.0, jito_tip_sol=0.0)
    base.update(over)
    return _strat(**base)


# ---------------- decide_exit : STOP LOSS ----------------
def test_stop_loss_declenche_sous_le_seuil():
    d = decide_exit(pct_gain=-60.0, held_seconds=10, steps_reached=[], strat=_strat())
    assert d.action == "SELL_ALL"
    assert d.reason == "STOP_LOSS"


def test_stop_loss_declenche_pile_au_seuil():
    d = decide_exit(pct_gain=-50.0, held_seconds=10, steps_reached=[], strat=_strat())
    assert d.reason == "STOP_LOSS"


def test_stop_loss_prioritaire_sur_time_stop():
    # gap baissier ET vieux : SL doit primer
    d = decide_exit(pct_gain=-90.0, held_seconds=9999, steps_reached=[], strat=_strat())
    assert d.reason == "STOP_LOSS"


# ---------------- decide_exit : TIME STOP ----------------
def test_time_stop_apres_duree_max():
    d = decide_exit(pct_gain=10.0, held_seconds=601, steps_reached=[], strat=_strat())
    assert d.action == "SELL_ALL"
    assert d.reason == "TIME_STOP"


# ---------------- decide_exit : TAKE PROFIT ----------------
def test_tp_premier_palier_non_atteint():
    d = decide_exit(pct_gain=120.0, held_seconds=10, steps_reached=[], strat=_strat())
    assert d.action == "SELL_PARTIAL"
    assert d.reason == "TAKE_PROFIT"
    assert d.step_percent == 100.0
    assert d.sell_ratio == 0.5


def test_tp_saute_palier_deja_atteint():
    d = decide_exit(pct_gain=350.0, held_seconds=10, steps_reached=[100.0], strat=_strat())
    assert d.step_percent == 300.0


def test_tp_palier_le_plus_bas_non_atteint_dabord():
    # gain franchit les deux paliers : on prend le plus bas non atteint
    d = decide_exit(pct_gain=350.0, held_seconds=10, steps_reached=[], strat=_strat())
    assert d.step_percent == 100.0


# ---------------- decide_exit : HOLD ----------------
def test_hold_si_rien_ne_declenche():
    d = decide_exit(pct_gain=20.0, held_seconds=10, steps_reached=[], strat=_strat())
    assert d.action == "HOLD"
    assert d.reason == "HOLD"


# ---------------- simulate_buy ----------------
def test_buy_sans_frais():
    f = simulate_buy(amount_sol=2.0, entry_price=0.5, strat=_costs())
    assert f.tokens == pytest.approx(4.0)
    assert f.cost_basis_sol == pytest.approx(2.0)
    assert f.price_per_token == pytest.approx(0.5)


def test_buy_amm_et_slippage_reduisent_les_tokens():
    f = simulate_buy(amount_sol=1.0, entry_price=0.001,
                     strat=_costs(amm_fee_pct=0.0025, slippage_pct=0.10))
    # 1 * (1-0.0025) * (1-0.10) / 0.001
    assert f.tokens == pytest.approx(897.75)


def test_buy_priority_et_tip_gonflent_le_cout():
    f = simulate_buy(amount_sol=1.0, entry_price=0.001,
                     strat=_costs(priority_fee_sol=0.001, jito_tip_sol=0.002))
    assert f.cost_basis_sol == pytest.approx(1.003)


def test_buy_memorise_le_prix_marche_dentree():
    f = simulate_buy(amount_sol=1.0, entry_price=0.0007, strat=_costs())
    assert f.entry_price == pytest.approx(0.0007)


def test_open_stocke_le_prix_marche_dentree():
    pf = Portfolio(balance_sol=10.0)
    f = simulate_buy(amount_sol=1.0, entry_price=0.0007, strat=_costs())
    pf.open("M", "DOGE", f, buy_timestamp=0.0)
    assert pf.positions["M"].entry_market_price == pytest.approx(0.0007)


# ---------------- simulate_sell ----------------
def test_sell_sans_frais():
    net = simulate_sell(tokens=4.0, exit_price=0.5, strat=_costs())
    assert net == pytest.approx(2.0)


def test_sell_retranche_amm_slippage_priority_tip():
    net = simulate_sell(tokens=897.75, exit_price=0.002,
                        strat=_costs(amm_fee_pct=0.0025, slippage_pct=0.10,
                                     priority_fee_sol=0.001, jito_tip_sol=0.002))
    # 897.75*0.002*0.9975*0.9 - 0.003
    assert net == pytest.approx(1.608909, abs=1e-5)


def test_roundtrip_meme_prix_perd_de_largent():
    # Acheter puis revendre au MEME prix DOIT perdre (fin du round-trip fantaisie)
    s = _costs(amm_fee_pct=0.0025, slippage_pct=0.05, priority_fee_sol=0.001, jito_tip_sol=0.001)
    f = simulate_buy(amount_sol=1.0, entry_price=0.001, strat=s)
    net = simulate_sell(tokens=f.tokens, exit_price=0.001, strat=s)
    assert net < f.cost_basis_sol


# ---------------- can_open : cap positions + garde solde ----------------
def test_can_open_sous_cap_et_solde_ok():
    s = _strat(max_open_positions=3, buy_amount_sol=1.0, priority_fee_sol=0.001, jito_tip_sol=0.001)
    assert can_open(n_open=2, balance_sol=50.0, strat=s) is True


def test_can_open_refuse_au_cap():
    s = _strat(max_open_positions=3, buy_amount_sol=1.0)
    assert can_open(n_open=3, balance_sol=50.0, strat=s) is False


def test_can_open_refuse_solde_insuffisant():
    s = _strat(max_open_positions=3, buy_amount_sol=1.0, priority_fee_sol=0.01, jito_tip_sol=0.01)
    assert can_open(n_open=0, balance_sol=1.005, strat=s) is False  # < 1.02


# ---------------- passes_filters ----------------
def test_filters_ok_dans_les_bornes():
    s = _strat(min_liquidity_usd=5000, max_liquidity_usd=200000,
               min_ratio_liq_fdv=10.0, max_ratio_liq_fdv=70.0, min_volume_24h=1000)
    assert passes_filters({"liq_usd": 20000, "fdv_usd": 100000, "vol24_usd": 5000}, s) is True  # ratio 20%


def test_filters_fdv_zero_refuse():
    assert passes_filters({"liq_usd": 20000, "fdv_usd": 0, "vol24_usd": 5000}, _strat()) is False


def test_filters_ratio_trop_bas_refuse():
    s = _strat(min_ratio_liq_fdv=10.0, max_ratio_liq_fdv=70.0,
               min_liquidity_usd=0, max_liquidity_usd=1e12, min_volume_24h=0)
    assert passes_filters({"liq_usd": 5000, "fdv_usd": 100000, "vol24_usd": 5000}, s) is False  # 5%


def test_filters_volume_trop_bas_refuse():
    s = _strat(min_volume_24h=10000, min_liquidity_usd=0, max_liquidity_usd=1e12,
               min_ratio_liq_fdv=0, max_ratio_liq_fdv=100)
    assert passes_filters({"liq_usd": 20000, "fdv_usd": 100000, "vol24_usd": 500}, s) is False

def _nofilter(**kwargs):
    s = _strat(min_liquidity_usd=0, max_liquidity_usd=1e12,
               min_ratio_liq_fdv=0, max_ratio_liq_fdv=100, min_volume_24h=0)
    for k, v in kwargs.items():
        setattr(s, k, v)
    return s

def test_filters_bande_fdv_dans_zone_passe():
    # pump.fun : acheter pré-graduation (~69k). FDV 30k dans [5k, 60k]
    s = _nofilter(min_fdv_usd=5000, max_fdv_usd=60000)
    assert passes_filters({"liq_usd": 10, "fdv_usd": 30000, "vol24_usd": 0}, s) is True

def test_filters_fdv_sous_plancher_refuse():
    s = _nofilter(min_fdv_usd=5000, max_fdv_usd=60000)
    assert passes_filters({"liq_usd": 10, "fdv_usd": 2000, "vol24_usd": 0}, s) is False

def test_filters_fdv_au_dessus_plafond_refuse():
    # déjà gradué / trop gros : on ne veut pas entrer
    s = _nofilter(min_fdv_usd=5000, max_fdv_usd=60000)
    assert passes_filters({"liq_usd": 10, "fdv_usd": 120000, "vol24_usd": 0}, s) is False


# ---------------- security_ok ----------------
def test_security_desactivee_passe_toujours():
    s = _strat(check_rug=False, max_rug_score=500)
    assert security_ok(score=9999, risks=["Mint Authority"], strat=s) is True


def test_security_score_trop_haut_refuse():
    s = _strat(check_rug=True, max_rug_score=500)
    assert security_ok(score=600, risks=[], strat=s) is False


def test_security_mint_authority_refuse():
    s = _strat(check_rug=True, max_rug_score=500, allow_mint_authority=False)
    assert security_ok(score=10, risks=["Mint Authority"], strat=s) is False


def test_security_freeze_authority_refuse():
    s = _strat(check_rug=True, max_rug_score=500, allow_freeze_authority=False)
    assert security_ok(score=10, risks=["Freeze Authority"], strat=s) is False


def test_security_propre_passe():
    s = _strat(check_rug=True, max_rug_score=500)
    assert security_ok(score=10, risks=[], strat=s) is True


# ---------------- pick_pair : choisir la bonne paire Raydium/SOL ----------------
def _pair(dex, quote, liq):
    return {"dexId": dex, "quoteToken": {"symbol": quote}, "liquidity": {"usd": liq}}


def test_pick_pair_vide_retourne_none():
    assert pick_pair([]) is None


def test_pick_pair_choisit_raydium_sol_plus_liquide():
    pairs = [_pair("raydium", "SOL", 10000), _pair("raydium", "SOL", 50000)]
    assert pick_pair(pairs)["liquidity"]["usd"] == 50000


def test_pick_pair_accepte_pumpfun():
    # univers réel : pump.fun / pumpswap doivent être acceptés côté DexScreener
    assert pick_pair([_pair("pumpfun", "SOL", 10000)])["liquidity"]["usd"] == 10000
    assert pick_pair([_pair("pumpswap", "SOL", 10000)])["liquidity"]["usd"] == 10000


def test_pick_pair_ignore_venue_hors_liste():
    pairs = [_pair("orca", "SOL", 99999), _pair("raydium", "SOL", 10000)]
    assert pick_pair(pairs)["liquidity"]["usd"] == 10000


def test_pick_pair_ignore_quote_non_sol():
    pairs = [_pair("raydium", "USDC", 99999), _pair("raydium", "WSOL", 10000)]
    assert pick_pair(pairs)["liquidity"]["usd"] == 10000  # WSOL accepté, USDC non


def test_pick_pair_aucune_valide_retourne_none():
    pairs = [_pair("orca", "USDC", 99999)]
    assert pick_pair(pairs) is None


# ---------------- Strategy.from_dict : unification config ----------------
def _full_cfg():
    return {
        "targeting": {"keywords": ["AI", "DOGE"]},
        "filters": {"min_liquidity_usd": 5000, "max_liquidity_usd": 200000,
                    "min_ratio_liq_fdv": 12.5, "max_ratio_liq_fdv": 70.0, "min_volume_24h": 1000},
        "security": {"check_rug": True, "max_rug_score": 500,
                     "allow_mint_authority": False, "allow_freeze_authority": False},
        "execution": {"amm_fee_pct": 0.0025, "slippage_pct": 0.15,
                      "priority_fee_sol": 0.002, "jito_tip_sol": 0.003},
        "trading": {"buy_amount_sol": 0.5, "stop_loss_percent": -40,
                    "max_hold_seconds": 900, "max_open_positions": 4,
                    "take_profit_steps": [{"percent": 100, "sell_ratio": 0.5},
                                          {"percent": 300, "sell_ratio": 0.5}]},
    }


def test_from_dict_mappe_trading():
    s = Strategy.from_dict(_full_cfg())
    assert s.stop_loss_percent == -40
    assert s.max_hold_seconds == 900
    assert s.max_open_positions == 4
    assert s.buy_amount_sol == 0.5


def test_from_dict_convertit_tp_steps_en_tuples():
    s = Strategy.from_dict(_full_cfg())
    assert s.take_profit_steps == [(100.0, 0.5), (300.0, 0.5)]


def test_from_dict_charge_keywords_filtres_securite_execution():
    s = Strategy.from_dict(_full_cfg())
    assert s.keywords == ["AI", "DOGE"]
    assert s.min_ratio_liq_fdv == 12.5
    assert s.max_rug_score == 500
    assert s.slippage_pct == 0.15
    assert s.jito_tip_sol == 0.003


def test_from_dict_blocs_manquants_utilisent_defauts():
    # config minimale : ne doit pas planter, applique les défauts
    s = Strategy.from_dict({"trading": {"stop_loss_percent": -50}})
    assert s.stop_loss_percent == -50
    assert s.max_open_positions == 5          # défaut
    assert s.keywords == []                    # défaut
    assert s.amm_fee_pct == 0.0025             # défaut


# ---------------- Portfolio : comptabilité solde + PnL ----------------
def _fill(tokens=1000.0, cost=1.0):
    return Fill(tokens=tokens, cost_basis_sol=cost, price_per_token=cost / tokens)


def test_open_reduit_le_solde_et_ajoute_position():
    pf = Portfolio(balance_sol=100.0)
    pf.open("MINT1", "DOGE", _fill(cost=1.0), buy_timestamp=123.0)
    assert pf.balance_sol == pytest.approx(99.0)
    assert pf.n_open == 1
    assert pf.has("MINT1")
    assert pf.positions["MINT1"].steps_reached == []


def test_sell_total_credite_solde_et_ferme():
    pf = Portfolio(balance_sol=100.0)
    pf.open("MINT1", "DOGE", _fill(cost=1.0), buy_timestamp=0.0)
    pf.sell("MINT1", fraction=1.0, proceeds_sol=2.5)
    assert pf.balance_sol == pytest.approx(101.5)   # 99 + 2.5
    assert pf.realized_pnl_sol == pytest.approx(1.5)  # 2.5 - 1.0
    assert not pf.has("MINT1")
    assert pf.n_open == 0


def test_sell_partiel_garde_position_reduite():
    pf = Portfolio(balance_sol=100.0)
    pf.open("MINT1", "DOGE", _fill(tokens=1000.0, cost=1.0), buy_timestamp=0.0)
    pf.sell("MINT1", fraction=0.5, proceeds_sol=1.2)
    pos = pf.positions["MINT1"]
    assert pos.tokens == pytest.approx(500.0)
    assert pos.cost_basis_sol == pytest.approx(0.5)
    assert pf.realized_pnl_sol == pytest.approx(0.7)  # 1.2 - 0.5
    assert pf.has("MINT1")


def test_deux_ventes_partielles_ferment_la_position():
    pf = Portfolio(balance_sol=100.0)
    pf.open("MINT1", "DOGE", _fill(tokens=1000.0, cost=1.0), buy_timestamp=0.0)
    pf.sell("MINT1", fraction=0.5, proceeds_sol=1.0)   # reste 500
    pf.sell("MINT1", fraction=1.0, proceeds_sol=1.0)   # solde le reste
    assert not pf.has("MINT1")


def test_sell_mint_inconnu_ne_fait_rien():
    pf = Portfolio(balance_sol=100.0)
    assert pf.sell("ABSENT", fraction=1.0, proceeds_sol=5.0) is False
    assert pf.balance_sol == pytest.approx(100.0)


# ---------------- select_base_mint : remplace keys[8] aveugle ----------------
def test_base_mint_renvoie_le_non_wsol():
    assert select_base_mint([WSOL, "TOKENXYZ"]) == "TOKENXYZ"
    assert select_base_mint(["TOKENXYZ", WSOL]) == "TOKENXYZ"


def test_base_mint_quote_usdc_aussi_reconnu():
    usdc = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    assert select_base_mint(["TOKENXYZ", usdc]) == "TOKENXYZ"


def test_base_mint_aucun_non_quote_renvoie_none():
    assert select_base_mint([WSOL]) is None
    assert select_base_mint([]) is None


def test_base_mint_ambigu_renvoie_none():
    # deux non-quote : on ne sait pas trancher -> None (sécurité)
    assert select_base_mint(["AAA", "BBB"]) is None


# ---------------- match_keyword ----------------
def test_match_keyword_trouve_sous_chaine_insensible_casse():
    assert match_keyword("CUTE DOGE COIN", ["doge"]) == "doge"


def test_match_keyword_aucun_match_renvoie_none():
    assert match_keyword("CAT TOKEN", ["DOGE", "PEPE"]) is None


def test_match_keyword_sans_mots_cles_pas_de_filtre_renvoie_vide():
    # [] ou [""] => filtre désactivé => "" (truthy-différent de None = on passe)
    assert match_keyword("N IMPORTE QUOI", []) == ""
    assert match_keyword("N IMPORTE QUOI", ["", "  "]) == ""


def test_defauts_de_filtre_sont_neutres():
    """Un Strategy() nu ne doit JAMAIS jeter d'episode.

    Regression : les defauts de la dataclass avaient ete mis a la bande
    pre-graduation (min_fdv 5000, max_fdv 60000). Comme les quatre configs
    fixent ces cles explicitement, le changement n'apportait rien en production
    mais faisait jeter en silence tout episode hors bande des qu'une config
    omettait la cle -- dont 100% des episodes graduation, qui portent un
    fdv_usd mocke a 1.0. Un filtre qui jette tout sans lever d'erreur est la
    signature de bug la plus couteuse de ce projet.
    """
    s = Strategy(check_rug=False)
    # ratio liq/fdv garde a 20% pour isoler la bande FDV des autres filtres
    for fdv in (1.0, 100_000.0, 1e9):
        ep = {"liq_usd": fdv * 0.2, "fdv_usd": fdv, "vol24_usd": 5_000.0}
        assert passes_filters(ep, s) is True, f"defaut non neutre a fdv={fdv}"

    # cas reel : les episodes graduation portent des mocks a 1.0 (ratio 100%)
    mock = {"liq_usd": 1.0, "fdv_usd": 1.0, "vol24_usd": 1.0}
    assert passes_filters(mock, s) is True

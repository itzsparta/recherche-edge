"""TDD verdict : gardes anti-overfit (t-stat, split regime, miroir naive)."""
import math

import pytest

from core import Strategy
from verdict import tstat, by_regime, decide_verdict, naive_variant, run_verdict


def test_tstat_zero_quand_moins_de_deux_points():
    assert tstat([]) == 0.0
    assert tstat([0.5]) == 0.0


def test_tstat_zero_quand_variance_nulle_indetermine():
    # std=0 -> t indefini -> 0.0 (pas d'inf)
    assert tstat([0.3, 0.3, 0.3]) == 0.0


def test_tstat_formule_mean_sur_erreur_standard():
    data = [1.0, 2.0, 3.0, 4.0]
    mean = 2.5
    sd = math.sqrt(sum((x - mean) ** 2 for x in data) / (len(data) - 1))  # ddof=1
    expected = mean / (sd / math.sqrt(len(data)))
    assert tstat(data) == pytest.approx(expected)


def test_by_regime_agrege_n_et_moyenne_par_regime():
    pnls =    [1.0, 3.0, -2.0]
    regimes = ["bull", "bull", "bear"]
    out = by_regime(pnls, regimes)
    assert out["bull"]["n"] == 2
    assert out["bull"]["mean"] == pytest.approx(2.0)
    assert out["bear"]["n"] == 1
    assert out["bear"]["mean"] == pytest.approx(-2.0)


def test_verdict_pass_quand_tous_gardes_ok():
    pnls =    [0.5, 0.6, 0.4, 0.55]
    regimes = ["bull", "bear", "bull", "bear"]   # chaque regime > 0
    v = decide_verdict(pnls, regimes, naive_mean=0.1)
    assert v["verdict"] == "PASS"
    assert all(v["gates"].values())


def test_verdict_kill_si_un_regime_negatif_meme_si_moyenne_positive():
    # moyenne globale > 0 mais bear < 0 => drift/beta, pas edge => KILL
    pnls =    [3.0, 3.0, -1.0]
    regimes = ["bull", "bull", "bear"]
    v = decide_verdict(pnls, regimes, naive_mean=-5.0)
    assert v["verdict"] == "KILL"
    assert v["gates"]["mean"] is True
    assert v["gates"]["regimes"] is False


def test_verdict_kill_si_ne_bat_pas_le_miroir_naive():
    # strat positive et significative, mais un simple buy+time-stop fait mieux
    pnls =    [0.5, 0.6, 0.4, 0.55]
    regimes = ["bull", "bear", "bull", "bear"]
    v = decide_verdict(pnls, regimes, naive_mean=10.0)
    assert v["verdict"] == "KILL"
    assert v["gates"]["mirror"] is False


def _strat(**over):
    base = dict(stop_loss_percent=-50.0, max_hold_seconds=10_000.0,
                take_profit_steps=[(100.0, 0.5)], amm_fee_pct=0.0, slippage_pct=0.0,
                priority_fee_sol=0.0, jito_tip_sol=0.0, buy_amount_sol=1.0,
                max_open_positions=50, min_volume_24h=0.0, check_rug=False, keywords=[])
    base.update(over)
    return Strategy(**base)


def _ep(mint, path, regime, fdv=100000):
    return {"mint": mint, "name": "tok", "launch_time": 0.0, "liq_usd": 20000,
            "fdv_usd": fdv, "vol24_usd": 5000, "rug_score": 0, "risks": [],
            "regime": regime, "path": path}


def test_naive_variant_desactive_sl_et_tp():
    nv = naive_variant(_strat())
    assert nv.take_profit_steps == []
    assert nv.stop_loss_percent < -1e8


def test_run_verdict_bout_a_bout_renvoie_gate_complet():
    # 2 episodes qui entrent, 2 regimes -> structure de verdict complete
    eps = [_ep("A", [[0, 1.0], [10, 2.0], [20, 2.0]], "bull"),
           _ep("B", [[0, 1.0], [10, 0.4]], "bear")]
    v = run_verdict(eps, _strat(), start_balance=100.0)
    assert v["n"] == 2
    assert set(v["regimes"]) == {"bull", "bear"}
    assert v["verdict"] in ("PASS", "KILL")
    assert set(v["gates"]) == {"mean", "tstat", "regimes", "mirror"}

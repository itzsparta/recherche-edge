"""Tests du backtester offline (replay sur le noyau, aucune dépendance réseau)."""
import pytest
from core import Strategy
from backtester import run_backtest


def _strat(**over):
    base = dict(
        stop_loss_percent=-50.0, max_hold_seconds=10_000.0,
        take_profit_steps=[(100.0, 0.5)],
        amm_fee_pct=0.0, slippage_pct=0.0, priority_fee_sol=0.0, jito_tip_sol=0.0,
        buy_amount_sol=1.0, max_open_positions=5,
        min_liquidity_usd=0.0, max_liquidity_usd=1e12,
        min_ratio_liq_fdv=0.0, max_ratio_liq_fdv=100.0, min_volume_24h=0.0,
        check_rug=False, keywords=["DOGE"],
    )
    base.update(over)
    return Strategy(**base)


def _ep(mint, name, path, launch=0.0, liq=20000, fdv=100000, vol=5000):
    return {"mint": mint, "name": name, "launch_time": launch,
            "liq_usd": liq, "fdv_usd": fdv, "vol24_usd": vol,
            "rug_score": 0, "risks": [], "path": path}


def test_episode_gagnant_rapporte():
    # prix x2 puis stable : TP +100% vend la moitié, liquidation finale solde le reste
    ep = _ep("M1", "CUTE DOGE", [[0, 0.001], [10, 0.002], [20, 0.002]])
    r = run_backtest([ep], _strat(), start_balance=100.0)
    assert r.n_entered == 1
    assert r.n_trades == 1
    assert r.wins == 1
    assert r.final_balance > 100.0
    assert r.realized_pnl > 0


def test_stop_loss_coupe_au_premier_franchissement():
    # dip -55% (déclenche SL) PUIS -90% : on doit sortir à -55%, pas -90%
    ep = _ep("M1", "DOGE PUMP", [[0, 0.001], [10, 0.00045], [20, 0.0001]])
    r = run_backtest([ep], _strat(), start_balance=100.0)
    # sortie SL au prix 0.00045 -> proceeds 1000*0.00045=0.45 -> 100 -1 +0.45
    assert r.final_balance == pytest.approx(99.45, abs=1e-6)
    assert r.losses == 1


def test_cap_positions_respecte():
    eps = [_ep(f"M{i}", "DOGE", [[0, 0.001], [9999, 0.001]], launch=0.0) for i in range(3)]
    r = run_backtest(eps, _strat(max_open_positions=2), start_balance=100.0)
    assert r.n_candidates == 3
    assert r.n_entered == 2


def test_keyword_hors_cible_rejete():
    ep = _ep("M1", "BORING CAT", [[0, 0.001], [10, 0.002]])
    r = run_backtest([ep], _strat(keywords=["DOGE"]), start_balance=100.0)
    assert r.n_entered == 0
    assert r.final_balance == pytest.approx(100.0)


def test_filtre_liquidite_rejete():
    ep = _ep("M1", "DOGE", [[0, 0.001], [10, 0.002]], liq=100)  # liq trop basse
    r = run_backtest([ep], _strat(min_liquidity_usd=5000), start_balance=100.0)
    assert r.n_entered == 0


def test_expose_pnl_et_regime_par_trade():
    # 1 gagnant (bull), 1 perdant (bear) -> verdict a besoin du detail par trade
    win = _ep("W", "DOGE UP", [[0, 0.001], [10, 0.002], [20, 0.002]])
    win["regime"] = "bull"
    loss = _ep("L", "DOGE DN", [[0, 0.001], [10, 0.00045], [20, 0.0001]])
    loss["regime"] = "bear"
    r = run_backtest([win, loss], _strat(), start_balance=100.0)
    assert len(r.trade_pnls) == 2
    assert len(r.trade_regimes) == 2
    detail = dict(zip(r.trade_regimes, r.trade_pnls))
    assert detail["bull"] > 0
    assert detail["bear"] < 0

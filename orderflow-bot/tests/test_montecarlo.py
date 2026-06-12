from orderflow_bot.backtest.montecarlo import simulate


def test_empty_journal():
    assert simulate([], risk_pct=0.01) == {"sims": 0}


def test_all_winners_no_drawdown():
    out = simulate([2.0, 2.0, 2.0], risk_pct=0.01, n_sims=200, seed=1)
    assert out["dd_p99"] == 0.0
    assert out["ruin_prob"] == 0.0
    assert out["final_p50"] > 1.0


def test_all_losers_hits_ruin():
    # -1R a chaque trade, risque 10 %, horizon 100 : DD depasse 50 % a coup sur
    out = simulate([-1.0], risk_pct=0.10, n_sims=200, horizon=100, ruin_dd=0.5, seed=1)
    assert out["ruin_prob"] == 1.0
    assert out["final_p50"] < 0.5


def test_deterministic_with_seed():
    rs = [2.0, -1.0, 1.5, -1.0, 3.0]
    a = simulate(rs, risk_pct=0.0075, n_sims=500, seed=42)
    b = simulate(rs, risk_pct=0.0075, n_sims=500, seed=42)
    assert a == b


def test_percentiles_ordered():
    rs = [2.0, -1.0, 1.5, -1.0, 3.0, -1.0]
    out = simulate(rs, risk_pct=0.0075, n_sims=1000, horizon=200, seed=7)
    assert 0.0 <= out["dd_p50"] <= out["dd_p90"] <= out["dd_p99"] <= 1.0

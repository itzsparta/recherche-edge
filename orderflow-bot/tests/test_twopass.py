"""Backtest 2-passes : passe 1 (generation de plans, parallelisable) +
passe 2 (execution sequentielle). Doit produire un resultat identique au
replay mono-passe (Pipeline), qui sert de reference."""
import pytest

from orderflow_bot.execution.journal import TradeJournal
from orderflow_bot.models import OrderPlan
from orderflow_bot.pipeline import (
    _day_blocks, execute_plans, generate_plans, generate_plans_blocked,
    run_backtest, simulate_isolated, simulate_isolated_blocked,
)

from .test_backtest import DAY1, DAY_MS, _cfg, synth_trades


def _mem_reader(trades):
    """Reader en memoire pour tester le decoupage sans Parquet."""
    def read(start_ms, end_ms):
        return [t for t in trades
                if (start_ms is None or t.ts >= start_ms)
                and (end_ms is None or t.ts < end_ms)]
    return read


def test_generate_plans_returns_candidates(tmp_path):
    cfg = _cfg(tmp_path)
    plans = generate_plans(cfg, synth_trades())
    assert len(plans) >= 1
    assert plans[0].meta["trigger"] == "absorption"
    assert plans[0].meta["zone"] == "val"


def test_generate_plans_no_candidates_during_warmup(tmp_path):
    # jour 1 seul : zones pas encore calculees -> aucun candidat
    cfg = _cfg(tmp_path)
    jour1 = [t for t in synth_trades() if t.ts < DAY1 + DAY_MS]
    assert generate_plans(cfg, jour1) == []


def test_two_pass_matches_single_pass(tmp_path):
    cfg = _cfg(tmp_path)
    trades = synth_trades()
    ref = run_backtest(cfg, trades)                 # reference mono-passe
    plans = generate_plans(cfg, trades)
    rep = execute_plans(cfg, plans, trades)         # 2-passes
    assert rep == ref
    rows = TradeJournal.load(cfg.journal_path)
    assert len(rows) == ref["trades"]


def test_day_blocks_cover_window_with_warmup():
    DAY = 86_400_000
    # [10j, 14j) en 2 blocs de 2 jours, warmup 2 jours en amont
    blocks = _day_blocks(10 * DAY, 14 * DAY, n_blocks=2, warmup_ms=2 * DAY)
    # (read_from, block_start, block_end)
    assert blocks == [
        (8 * DAY, 10 * DAY, 12 * DAY),
        (10 * DAY, 12 * DAY, 14 * DAY),
    ]


def test_day_blocks_last_block_absorbs_remainder():
    DAY = 86_400_000
    # span 5 jours en 2 blocs : 3 puis 2 (le dernier prend le reste)
    blocks = _day_blocks(0, 5 * DAY, n_blocks=2, warmup_ms=0)
    assert blocks[0] == (0, 0, 3 * DAY)
    assert blocks[-1][2] == 5 * DAY


def test_blocked_generation_matches_global(tmp_path):
    cfg = _cfg(tmp_path)
    trades = synth_trades()
    ref = generate_plans(cfg, trades)
    # 2 blocs (jour1, jour2), warmup 1 jour : le bloc jour2 rejoue jour1 ->
    # memes zones -> meme plan d'absorption. Le bloc jour1 ne produit rien.
    blocked = generate_plans_blocked(
        cfg, DAY1, DAY1 + 2 * DAY_MS, _mem_reader(trades),
        n_blocks=2, warmup_days=1)
    assert blocked == ref
    assert len(blocked) >= 1


def test_isolated_matches_portfolio_for_executed_plan(tmp_path):
    # un plan pris isolement doit donner le meme outcome (r/mfe/mae/exit) que
    # ce plan execute en portefeuille quand rien ne le precede. qty s'annule
    # dans r -> tolerance 1e-9 sur r (arrondis de qty), exact sur mfe/mae/exit.
    cfg = _cfg(tmp_path)
    trades = synth_trades()
    plans = generate_plans(cfg, trades)
    execute_plans(cfg, plans, trades)
    journal = TradeJournal.load(cfg.journal_path)
    assert journal, "le synthetique doit produire au moins un trade execute"
    op = OrderPlan(**journal[0]["plan"])
    iso = simulate_isolated(cfg, [op], trades)
    assert len(iso) == 1
    ct, j = iso[0], journal[0]
    assert ct.mfe_r == j["mfe_r"]
    assert ct.mae_r == j["mae_r"]
    assert ct.r_multiple == pytest.approx(j["r_multiple"], abs=1e-9)
    assert ct.fills[-1].kind == j["fills"][-1]["kind"]


def test_isolated_takes_at_least_as_many_as_portfolio(tmp_path):
    # sans contrainte de slot/risque, l'isole remplit >= ce que prend le portefeuille
    cfg = _cfg(tmp_path)
    trades = synth_trades()
    plans = generate_plans(cfg, trades)
    execute_plans(cfg, plans, trades)
    executed = len(TradeJournal.load(cfg.journal_path))
    iso = simulate_isolated(cfg, plans, trades)
    assert len(iso) >= executed >= 1


def _iso_key(rows):
    return sorted((c.plan.ts, c.plan.side, round(c.r_multiple, 9),
                   round(c.mfe_r, 9), round(c.mae_r, 9), c.fills[-1].kind)
                  for c in rows)


def test_isolated_blocked_matches_mono(tmp_path):
    # decoupage par jour (tail 1j pour fermer l'EOD du dernier jour, zero warmup)
    # -> outcomes identiques au stream mono.
    cfg = _cfg(tmp_path)
    trades = synth_trades()
    plans = generate_plans(cfg, trades)
    mono = simulate_isolated(cfg, plans, trades)
    blocked = simulate_isolated_blocked(
        cfg, DAY1, DAY1 + 2 * DAY_MS, plans, _mem_reader(trades),
        n_blocks=2, tail_days=1)
    assert _iso_key(blocked) == _iso_key(mono)
    assert len(blocked) == len(mono) >= 1

"""Verdict edge — gardes anti-overfit facon orderflow-bot.

Le backtester sort un PnL agrege ; insuffisant pour conclure (un seul gros
gagnant peut le porter, cf. mirage survivorship n=2). Ce module applique les
memes gardes que le gate noyau de l'orderflow-bot :

  - t-stat sur le PnL/trade   : la moyenne est-elle significativement > 0 ?
  - split par regime          : positive dans TOUS les regimes (sinon = drift/beta,
                                pas un edge) -- equivalent du both_halves.
  - miroir naive              : la strat bat-elle un simple buy + time-stop
                                (memes entrees, sans SL/TP) ? sinon SL/TP = bruit.

Gate PASS (candidat edge) ssi : mean>0 ET t>2 ET tous regimes>0 ET strat>naive.
Sinon KILL.
"""
import json
import math
import sys
from dataclasses import replace

from core import Strategy
from backtester import run_backtest


def tstat(pnls):
    """t de Student du PnL/trade vs 0 : mean / (std_echantillon / sqrt(n)).
    0.0 si < 2 points ou variance nulle (indetermine, pas d'inf)."""
    n = len(pnls)
    if n < 2:
        return 0.0
    mean = sum(pnls) / n
    var = sum((x - mean) ** 2 for x in pnls) / (n - 1)   # ddof=1
    if var <= 0:
        return 0.0
    return mean / (math.sqrt(var) / math.sqrt(n))


def by_regime(pnls, regimes):
    """{regime: {'n': int, 'mean': float}} — PnL/trade moyen par regime.
    Sert au garde 'positive dans TOUS les regimes' (anti-drift)."""
    groups = {}
    for pnl, reg in zip(pnls, regimes):
        groups.setdefault(reg, []).append(pnl)
    return {reg: {"n": len(v), "mean": sum(v) / len(v)} for reg, v in groups.items()}


def decide_verdict(trade_pnls, trade_regimes, naive_mean, t_min=2.0):
    """Applique le gate noyau. Retourne un dict diagnostique + 'PASS'/'KILL'.

    PASS ssi : mean>0 ET t>t_min ET tous regimes>0 ET strat>naive.
    """
    n = len(trade_pnls)
    mean = sum(trade_pnls) / n if n else 0.0
    t = tstat(trade_pnls)
    regimes = by_regime(trade_pnls, trade_regimes)
    gates = {
        "mean": mean > 0,
        "tstat": t > t_min,
        "regimes": bool(regimes) and all(r["mean"] > 0 for r in regimes.values()),
        "mirror": mean > naive_mean,
    }
    return {
        "n": n, "mean": mean, "tstat": t,
        "naive_mean": naive_mean, "regimes": regimes,
        "gates": gates,
        "verdict": "PASS" if all(gates.values()) else "KILL",
    }


def naive_variant(strat):
    """Miroir naive : memes entrees/frais, mais AUCUN SL/TP -> sortie au seul
    time-stop. Mesure le drift/beta des entrees, hors machinerie de sortie."""
    return replace(strat, stop_loss_percent=-1e9, take_profit_steps=[])


def run_verdict(episodes, strat, start_balance=100.0, t_min=2.0):
    """Backtest strat + miroir naive sur les MEMES episodes -> verdict gate."""
    res = run_backtest(episodes, strat, start_balance)
    naive = run_backtest(episodes, naive_variant(strat), start_balance)
    naive_mean = (sum(naive.trade_pnls) / len(naive.trade_pnls)
                  if naive.trade_pnls else 0.0)
    v = decide_verdict(res.trade_pnls, res.trade_regimes, naive_mean, t_min)
    v["n_candidates"] = res.n_candidates
    v["realized_pnl"] = res.realized_pnl
    v["win_rate"] = res.win_rate
    return v


def _report(v):
    lines = [
        "=== VERDICT EDGE (gardes anti-overfit) ===",
        f"candidats={v['n_candidates']}  trades={v['n']}  win_rate={v['win_rate']*100:.1f}%",
        f"PnL/trade moyen = {v['mean']:+.5f} SOL   t-stat = {v['tstat']:+.2f}",
        f"miroir naive (buy+time-stop) = {v['naive_mean']:+.5f} SOL/trade",
        "regimes :",
    ]
    for reg, r in sorted(v["regimes"].items()):
        lines.append(f"  {reg:16s} n={r['n']:5d}  mean={r['mean']:+.5f}")
    g = v["gates"]
    lines.append(f"gates : mean>{0}={g['mean']}  t>2={g['tstat']}  "
                 f"tous_regimes>0={g['regimes']}  bat_naive={g['mirror']}")
    lines.append(f">>> {v['verdict']}")
    return "\n".join(lines)


def main(argv):
    if not argv:
        print("Usage: python verdict.py <episodes.json> [strategy.json]")
        return 1
    with open(argv[0], "r", encoding="utf-8") as f:
        episodes = json.load(f)
    cfg = {}
    if len(argv) > 1:
        with open(argv[1], "r", encoding="utf-8") as f:
            cfg = json.load(f)
    # start_balance enorme : le verdict mesure l'EV PAR TRADE, pas une contrainte
    # de capital -> ni le solde ni le cap ne doivent bloquer d'entree.
    v = run_verdict(episodes, Strategy.from_dict(cfg), start_balance=1e9)
    print(_report(v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

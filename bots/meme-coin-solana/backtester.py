"""Backtester OFFLINE — replay discret-événement sur le noyau pur (core).

Ce N'EST PLUS un scanner live (l'ancien fichier mal nommé l'était). Il répond à
la seule question qui compte : « cette stratégie a-t-elle un edge ? », en
rejouant des épisodes de tokens historiques à travers EXACTEMENT la même logique
de décision que le bot live (core.decide_exit / simulate_buy / simulate_sell...).

Modèle :
- chaque épisode = un token candidat + une trajectoire de prix.
- file d'événements globale (heap) => le solde et le cap de positions sont
  partagés dans le temps (concurrence réaliste), pas évalués token par token.

Format épisode (dict, voir data/episodes.sample.json) :
  {
    "mint": str, "name": str, "launch_time": float (s),
    "liq_usd": float, "fdv_usd": float, "vol24_usd": float,
    "rug_score": int, "risks": [str], "path": [[t_s_depuis_launch, prix_sol], ...]
  }
"""
import heapq
import json
import sys
from dataclasses import dataclass, field

from core import (Strategy, passes_filters, match_keyword, security_ok,
                  can_open, simulate_buy, simulate_sell, decide_exit, Portfolio)


@dataclass
class BacktestResult:
    n_candidates: int
    n_entered: int
    n_trades: int            # positions clôturées
    wins: int
    losses: int
    start_balance: float
    final_balance: float
    realized_pnl: float
    trade_pnls: list = field(default_factory=list)      # PnL realise par trade cloture
    trade_regimes: list = field(default_factory=list)   # regime aligne sur trade_pnls

    @property
    def win_rate(self):
        return self.wins / self.n_trades if self.n_trades else 0.0

    @property
    def return_pct(self):
        return (self.final_balance - self.start_balance) / self.start_balance * 100

    def summary(self):
        return (f"trades={self.n_trades} (sur {self.n_candidates} candidats) | "
                f"win_rate={self.win_rate*100:.1f}% | "
                f"PnL={self.realized_pnl:+.3f} SOL | "
                f"retour={self.return_pct:+.2f}% | "
                f"solde {self.start_balance:.2f}->{self.final_balance:.2f}")


def _exit_schedule(entry_price, strat, path, launch_time, reserves=None):
    """Pré-calcule la suite des ventes en marchant la trajectoire à travers
    decide_exit. Chaque vente = (temps_absolu, fraction_des_tokens_restants,
    raison, prix, reserve_pool). Termine TOUJOURS par une clôture (SL/TIME ou liquidation FINAL)."""
    reserves = reserves or {}
    steps = []
    events = []
    closed = False
    # La duree de detention se compte depuis l'ENTREE, pas depuis le lancement.
    # Sinon toute entree retardee (balayage de latence, miroir placebo a t1800)
    # depasse max_hold_seconds des son premier point et se time-stope sur place :
    # le backtest renvoie alors -peage pour chaque episode (win_rate 0%, t=-34)
    # en donnant l'illusion d'avoir teste quelque chose.
    entry_t = path[0][0] if path else 0.0
    for t, price in path:
        pct_gain = (price - entry_price) / entry_price * 100
        d = decide_exit(pct_gain, t - entry_t, steps, strat)
        res = reserves.get(str(t), 0.0)
        if d.action == "SELL_ALL":
            events.append((launch_time + t, 1.0, d.reason, price, res))
            closed = True
            break
        if d.action == "SELL_PARTIAL":
            events.append((launch_time + t, d.sell_ratio, d.reason, price, res))
            steps.append(d.step_percent)
    if not closed and path:
        t_last, price_last = path[-1]
        res_last = reserves.get(str(t_last), 0.0)
        events.append((launch_time + t_last, 1.0, "FINAL", price_last, res_last))
    return events


# priorités d'événement à temps égal : on traite les VENTES avant les ENTRÉES
# (libère le capital/les slots avant d'évaluer une nouvelle entrée)
_PRIO_SELL, _PRIO_ENTRY = 0, 1


def run_backtest(episodes, strat, start_balance=100.0):
    pf = Portfolio(start_balance)
    heap = []
    seq = 0
    for ep in episodes:
        heapq.heappush(heap, (ep["launch_time"], _PRIO_ENTRY, seq, "ENTRY", ep))
        seq += 1

    n_candidates = len(episodes)
    n_entered = 0
    pnl_by_mint = {}
    regime_by_mint = {}
    closed_pnls = []
    closed_regimes = []

    while heap:
        item = heapq.heappop(heap)
        type_evt = item[3]
        payload = item[4]

        if type_evt == "ENTRY":
            ep = payload
            if not passes_filters(ep, strat):
                continue
            if match_keyword(ep["name"], strat.keywords) is None:
                continue
            if not security_ok(ep.get("rug_score", 0), ep.get("risks", []), strat):
                continue
            if not can_open(pf.n_open, pf.balance_sol, strat):
                continue
            path = ep.get("path") or []
            if not path:
                continue
            entry_t = path[0][0]
            entry_price = path[0][1]
            if entry_price <= 0:
                continue
                
            entry_reserve = ep.get("reserves", {}).get(str(entry_t), 0.0)
            fill = simulate_buy(strat.buy_amount_sol, entry_price, strat, pool_reserve_sol=entry_reserve)
            pf.open(ep["mint"], ep["name"], fill, buy_timestamp=ep["launch_time"])
            pnl_by_mint[ep["mint"]] = 0.0
            regime_by_mint[ep["mint"]] = ep.get("regime", "")
            n_entered += 1

            for abs_t, fraction, reason, price, res in _exit_schedule(
                    entry_price, strat, path, ep["launch_time"], ep.get("reserves")):
                heapq.heappush(heap, (abs_t, _PRIO_SELL, seq, "SELL",
                                      (ep["mint"], fraction, reason, price, res)))
                seq += 1

        else:  # SELL
            mint, fraction, reason, price, res = payload
            pos = pf.positions.get(mint)
            if pos is None:
                continue  # déjà clôturée (ex : SL avant un TP programmé plus tard)
            tokens_sold = pos.tokens * fraction
            proceeds = simulate_sell(tokens_sold, price, strat, pool_reserve_sol=res)
            cost_alloc = pos.cost_basis_sol * fraction
            pnl_by_mint[mint] += proceeds - cost_alloc
            pf.sell(mint, fraction, proceeds)
            if not pf.has(mint):
                closed_pnls.append(pnl_by_mint.pop(mint))
                closed_regimes.append(regime_by_mint.pop(mint, ""))

    wins = sum(1 for p in closed_pnls if p > 0)
    losses = sum(1 for p in closed_pnls if p <= 0)
    return BacktestResult(
        n_candidates=n_candidates, n_entered=n_entered, n_trades=len(closed_pnls),
        wins=wins, losses=losses, start_balance=start_balance,
        final_balance=pf.balance_sol, realized_pnl=pf.realized_pnl_sol,
        trade_pnls=closed_pnls, trade_regimes=closed_regimes)


def main(argv):
    """Usage : python backtester.py <episodes.json> [strategy.json]"""
    if not argv:
        print("Usage: python backtester.py <episodes.json> [strategy.json]")
        return 1
    with open(argv[0], "r", encoding="utf-8") as f:
        episodes = json.load(f)
    cfg = {}
    if len(argv) > 1:
        with open(argv[1], "r", encoding="utf-8") as f:
            cfg = json.load(f)
    strat = Strategy.from_dict(cfg)
    result = run_backtest(episodes, strat)
    print(result.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

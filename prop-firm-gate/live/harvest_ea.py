"""
Buffer-harvest EXECUTOR (constant-vol, taille constante) — étude #26 GO-pending-live.

Ce N'EST PAS un bot d'alpha. Il ne prédit aucune direction. Il récolte le buffer STATIQUE
qu'une firme à plancher fixe (FTMO 2-Step) offre : tenir une exposition à vol constante
(sigma_day cible), banker l'excès par cycle, reset. Sous drift nul, equity+skim est une
martingale => E[skim] = m (le buffer). Cf. ../repeated_ev.py (modèle) + ../docs/FINDINGS-repeated.md.

Conception (décisions clés) :
  - TAILLE CONSTANTE (PAS martingale-après-perte) : sizing par vol cible, jamais "double après
    perte" => évite le pire flag FTMO ("disproportionate sizing after loss").
  - GARDE anti-breach : la taille est plafonnée pour qu'un mouvement de `guard_sigma` σ ne casse
    NI le daily-DD NI le max-DD statique. La position se réduit toute seule près du plancher.
  - Broker ABSTRAIT : SimBroker (dry-run, GBM, zéro MT5) et MT5Broker (live) exposent la même
    interface => la logique stratégie est identique en test et en réel.

DRY-RUN par défaut (aucun ordre, aucune connexion). LIVE exige --live explicite.
Cible step-0 = Free Trial FTMO 2-Step : valide la MÉCANIQUE (passe les phases ? sigma/coût réel ?
allure de l'equity curve ?). Le Free Trial n'a PAS de payout => il ne lève PAS le résidu voiding ;
ça, seul un challenge PAYANT -> funded -> payout le fait.

Usage :
  python harvest_ea.py                      # dry-run, archetype FTMO 2-step, 1 run simulé
  python harvest_ea.py --dry-run --runs 20  # 20 runs simulés (distribution pass/breach)
  python harvest_ea.py --live --symbol EURUSD --confirm-live   # RÉEL sur le terminal MT5 connecté
"""
from __future__ import annotations
from dataclasses import dataclass, field
import argparse
import math
import time

import numpy as np


# --------------------------------------------------------------------------- config
@dataclass
class Config:
    # compte (FTMO 2-Step : plancher STATIQUE — vérifié 2026)
    account_size: float = 100_000.0
    max_dd: float = 0.10            # max loss 10% STATIQUE (ne trail pas)
    daily_dd: float = 0.05          # daily loss 5%
    phase_targets: tuple = (0.10, 0.05)   # +10% puis +5% ; () si compte déjà financé

    # récolte
    target_sigma_day: float = 0.020   # vol P&L quotidienne cible (sizing) — σ* du modèle
    direction: int = -1               # -1 short / +1 long. EURUSD live : short swap ~+0.28 vs long ~-11.4/lot/nuit. Arbitraire pour le P&L sous no-edge => cote swap-positif (le swap tranche).
    guard_sigma: float = 3.0          # la taille tient un move de N σ sans casser le plancher
    payout_days: int = 14             # cadence de bank (funded uniquement)

    # instrument / exécution
    symbol: str = "EURUSD"
    vol_lookback: int = 20            # jours pour estimer la vol de l'instrument
    poll_seconds: float = 30.0        # cadence en LIVE
    magic: int = 260626
    deviation: int = 20

    # dry-run
    dry_run: bool = True
    sim_days: int = 60                # horizon d'un run simulé
    sim_steps_per_day: int = 24       # sous-pas intraday (daily-DD)
    sim_instrument_vol: float = 0.010 # vol quotidienne de l'instrument simulé (1%)
    sim_drift: float = 0.0            # drift nul = le cas modèle (conservateur)
    seed: int | None = None


# --------------------------------------------------------------------------- brokers
class SimBroker:
    """Feed GBM + compte simulé. Exerce TOUTE la logique sans MT5 ni argent."""
    def __init__(self, cfg: Config, rng: np.random.Generator):
        self.cfg = cfg
        self.rng = rng
        self.price = 1.0
        self.inst_vol = cfg.sim_instrument_vol
        self.contract_size = 100_000.0          # 1 lot ≈ 100k (FX)
        self._equity = cfg.account_size
        self.balance = cfg.account_size
        self.lots = 0.0
        self.entry = self.price
        self._dt = 1.0 / cfg.sim_steps_per_day

    def daily_vol(self) -> float:
        return self.inst_vol

    def equity(self) -> float:
        return self._equity

    def position_value(self) -> float:
        return abs(self.lots) * self.contract_size * self.price

    def set_target_lots(self, lots: float, direction: int):
        # réalise le P&L courant dans le solde, ré-ouvre à la nouvelle taille
        self.balance = self._equity
        self.lots = direction * abs(lots)
        self.entry = self.price

    def withdraw(self, amount: float):
        # bank réel : retire l'excès de l'equity (skim-and-reset, comme le modèle eq -= excess)
        self.balance = self._equity - amount
        self._equity = self.balance
        self.entry = self.price

    def step(self):
        z = self.rng.standard_normal()
        ret = self.cfg.sim_drift * self._dt + self.inst_vol * math.sqrt(self._dt) * z
        self.price *= math.exp(ret)
        pnl = self.lots * self.contract_size * (self.price - self.entry)
        self._equity = self.balance + pnl

    def connect(self):  # no-op
        return True

    def shutdown(self):
        pass


class MT5Broker:
    """Connecteur réel via le package MetaTrader5 (Windows, terminal FTMO connecté)."""
    def __init__(self, cfg: Config):
        import MetaTrader5 as mt5   # import paresseux : dry-run n'en a pas besoin
        self.mt5 = mt5
        self.cfg = cfg
        self._info = None

    def connect(self) -> bool:
        if not self.mt5.initialize():
            raise RuntimeError(f"MT5 initialize FAILED: {self.mt5.last_error()} "
                               "(terminal MT5 ouvert + connecté au compte FTMO ?)")
        self._info = self.mt5.symbol_info(self.cfg.symbol)
        if self._info is None or not self.mt5.symbol_select(self.cfg.symbol, True):
            raise RuntimeError(f"symbole {self.cfg.symbol} indisponible")
        return True

    def daily_vol(self) -> float:
        rates = self.mt5.copy_rates_from_pos(self.cfg.symbol, self.mt5.TIMEFRAME_D1,
                                             0, self.cfg.vol_lookback + 1)
        c = np.array([r["close"] for r in rates], float)
        return float(np.std(np.diff(np.log(c)))) or 0.01

    def equity(self) -> float:
        return float(self.mt5.account_info().equity)

    def _price(self) -> float:
        t = self.mt5.symbol_info_tick(self.cfg.symbol)
        return (t.ask + t.bid) / 2.0

    def position_value(self) -> float:
        pos = self.mt5.positions_get(symbol=self.cfg.symbol) or []
        return sum(abs(p.volume) * self._info.trade_contract_size * self._price() for p in pos)

    def set_target_lots(self, lots: float, direction: int):
        step = self._info.volume_step
        lots = max(self._info.volume_min, min(self._info.volume_max,
                   round(lots / step) * step))
        cur = self.mt5.positions_get(symbol=self.cfg.symbol) or []
        cur_signed = sum((1 if p.type == self.mt5.POSITION_TYPE_BUY else -1) * p.volume
                         for p in cur)
        want = direction * lots
        delta = want - cur_signed
        if abs(delta) < step:
            return
        side = self.mt5.ORDER_TYPE_BUY if delta > 0 else self.mt5.ORDER_TYPE_SELL
        t = self.mt5.symbol_info_tick(self.cfg.symbol)
        req = {"action": self.mt5.TRADE_ACTION_DEAL, "symbol": self.cfg.symbol,
               "volume": round(abs(delta), 2), "type": side,
               "price": t.ask if delta > 0 else t.bid,
               "deviation": self.cfg.deviation, "magic": self.cfg.magic,
               "comment": "harvest", "type_filling": self.mt5.ORDER_FILLING_IOC}
        r = self.mt5.order_send(req)
        if r.retcode != self.mt5.TRADE_RETCODE_DONE:
            print(f"  [WARN] order_send retcode={r.retcode} {r.comment}")

    def withdraw(self, amount: float):
        # réel : le retrait est une action MANUELLE sur le dashboard FTMO (no-op côté EA)
        pass

    def step(self):
        time.sleep(self.cfg.poll_seconds)

    def shutdown(self):
        self.mt5.shutdown()


# --------------------------------------------------------------------------- stratégie
class Harvest:
    """Machine d'état : eval (phase 1..n) -> funded (bank par cycle). Sizing constant-vol +
    garde anti-breach. AUCUNE prédiction de direction."""
    def __init__(self, cfg: Config, broker):
        self.cfg = cfg
        self.b = broker
        self.A = cfg.account_size
        self.static_floor = self.A * (1 - cfg.max_dd)
        self.phase = 0                       # index dans phase_targets ; >=len => funded
        self.funded = len(cfg.phase_targets) == 0
        self.day = 0
        self.day_start_equity = self.A
        self.skim_total = 0.0
        self.bank_baseline = self.A
        self.log = []

    # -- sizing : taille = vol-cible, PLAFONNÉE par la distance au plancher (garde) --
    def target_lots(self, equity: float) -> float:
        inst_vol = max(self.b.daily_vol(), 1e-4)
        # 1) taille par vol cible
        pv_vol = self.cfg.target_sigma_day * equity / inst_vol
        # 2) plafond garde : un move de guard_sigma σ ne doit casser aucun plancher
        daily_floor = self.day_start_equity - self.A * self.cfg.daily_dd
        floor = max(self.static_floor, daily_floor)
        headroom = max(equity - floor, 0.0)
        pv_guard = headroom / (self.cfg.guard_sigma * inst_vol)
        pv = min(pv_vol, pv_guard)
        contract = getattr(self.b, "contract_size", None) or self.b._info.trade_contract_size
        price = getattr(self.b, "price", None) or self.b._price()
        return pv / (contract * price)

    def on_new_day(self, equity: float):
        self.day += 1
        self.day_start_equity = equity
        # bank (funded) : tous les payout_days, sortir l'excès au-dessus de la baseline
        if self.funded and self.day % self.cfg.payout_days == 0 and equity > self.bank_baseline:
            excess = equity - self.bank_baseline
            self.skim_total += excess
            self.b.withdraw(excess)       # retire l'excès (sim) / no-op + dashboard (live)
            self.log.append(("BANK", self.day, round(excess, 2),
                             "=> RETIRER l'excès sur le dashboard FTMO, puis reset"))
            self.bank_baseline = self.A   # reset à l'initial (skim-and-reset)

    def check_targets(self, equity: float) -> str | None:
        floor = max(self.static_floor, self.day_start_equity - self.A * self.cfg.daily_dd)
        if equity <= floor:
            return "BREACH"
        if not self.funded:
            tgt = self.A * (1 + self.cfg.phase_targets[self.phase])
            if equity >= tgt:
                self.phase += 1
                self.log.append(("PHASE_PASS", self.day, self.phase, round(equity, 2)))
                if self.phase >= len(self.cfg.phase_targets):
                    self.funded = True
                    self.bank_baseline = self.A
                    self.log.append(("FUNDED", self.day, round(equity, 2), ""))
                else:
                    self.b.set_target_lots(0, self.cfg.direction)   # reset entre phases
                return "PHASE"
        return None

    def rebalance(self, equity: float):
        lots = self.target_lots(equity)
        self.b.set_target_lots(lots, self.cfg.direction)


# --------------------------------------------------------------------------- runners
def run_sim(cfg: Config, rng: np.random.Generator) -> dict:
    b = SimBroker(cfg, rng)
    h = Harvest(cfg, b)
    h.rebalance(b.equity())
    steps = cfg.sim_days * cfg.sim_steps_per_day
    outcome = "TIMEOUT"
    for i in range(steps):
        b.step()
        eq = b.equity()
        if i % cfg.sim_steps_per_day == 0:
            h.on_new_day(eq)
            h.rebalance(eq)            # re-size 1×/jour (taille constante intra-jour)
        ev = h.check_targets(eq)
        if ev == "BREACH":
            outcome = "BREACH"
            break
        if ev == "PHASE" and not h.funded:
            h.rebalance(eq)
    if outcome != "BREACH":
        outcome = "FUNDED" if h.funded else "EVAL_INCOMPLETE"
    return {"outcome": outcome, "equity": round(b.equity(), 2), "phase": h.phase,
            "skim": round(h.skim_total, 2), "days": h.day, "log": h.log}


def run_live(cfg: Config):
    b = MT5Broker(cfg)
    b.connect()
    h = Harvest(cfg, b)
    print(f"[LIVE] {cfg.symbol} | compte ${b.equity():,.0f} | plancher statique "
          f"${h.static_floor:,.0f} | σ cible {cfg.target_sigma_day:.1%}")
    last_day = time.gmtime().tm_yday
    h.rebalance(b.equity())
    try:
        while True:
            b.step()
            eq = b.equity()
            d = time.gmtime().tm_yday
            if d != last_day:
                last_day = d
                h.on_new_day(eq)
                h.rebalance(eq)
            ev = h.check_targets(eq)
            print(f"  eq=${eq:,.0f} phase={h.phase} funded={h.funded} pv=${b.position_value():,.0f}"
                  + (f" <{ev}>" if ev else ""))
            if ev == "BREACH":
                b.set_target_lots(0, cfg.direction)
                print("  [BREACH] plancher cassé — flat + stop.")
                break
            if ev == "PHASE":
                h.rebalance(eq)
            for tag, *rest in h.log[-1:]:
                if tag == "BANK":
                    print(f"  [BANK] {rest}")
    finally:
        b.shutdown()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="exécute en RÉEL sur le terminal MT5")
    ap.add_argument("--confirm-live", action="store_true", help="garde-fou obligatoire pour --live")
    ap.add_argument("--symbol", default=None)
    ap.add_argument("--sigma", type=float, default=None, help="σ_day cible (défaut 0.02)")
    ap.add_argument("--runs", type=int, default=1, help="dry-run : nb de runs simulés")
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()

    cfg = Config(dry_run=not a.live)
    if a.symbol:
        cfg.symbol = a.symbol
    if a.sigma:
        cfg.target_sigma_day = a.sigma
    if a.seed is not None:
        cfg.seed = a.seed

    if a.live:
        if not a.confirm_live:
            print("REFUS : --live exige --confirm-live (garde-fou). "
                  "Le Free Trial n'a pas d'argent réel mais confirme l'intention.")
            return
        run_live(cfg)
        return

    # dry-run
    rng = np.random.default_rng(cfg.seed)
    print(f"DRY-RUN | archetype FTMO 2-Step static | σ cible {cfg.target_sigma_day:.1%} | "
          f"instrument σ {cfg.sim_instrument_vol:.1%} drift {cfg.sim_drift:.1%} | {a.runs} run(s)")
    outcomes = {}
    skims = []
    for k in range(a.runs):
        r = run_sim(cfg, rng)
        outcomes[r["outcome"]] = outcomes.get(r["outcome"], 0) + 1
        if r["outcome"] == "FUNDED":
            skims.append(r["skim"])
        if a.runs == 1:
            print(f"  outcome={r['outcome']} equity=${r['equity']:,.0f} phase={r['phase']} "
                  f"jours={r['days']} skim=${r['skim']:,.0f}")
            for e in r["log"]:
                print("   ", e)
    if a.runs > 1:
        tot = a.runs
        print("  distribution :")
        for k, v in sorted(outcomes.items()):
            print(f"    {k:16s} {v:4d}  ({v/tot:.1%})")
        pf = outcomes.get("FUNDED", 0) / tot
        print(f"  P(funded) simulé = {pf:.1%}"
              + (f" | skim moyen|funded = ${np.mean(skims):,.0f}" if skims else ""))
    print("\n  NB : dry-run = test de LOGIQUE (sizing/garde/machine d'état), PAS une preuve d'edge.")
    print("  Le GBM driftless reproduit le cas modèle ; le réel a coût + microstructure.")


if __name__ == "__main__":
    main()

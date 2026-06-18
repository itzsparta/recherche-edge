# scripts/continuation_run.py
"""Gate 2b swing-continuation : lit les klines, genere les plans (cassure de
niveau + continuation), etiquette a frais=0 (brut), miroir et frais reels (net)
sur le MEME jeu de candidats, verifie la plomberie, puis tranche via
backtest.swing_gate2.gate2 (noyau drift-controle + diagnostic regime).
Usage: .venv/Scripts/python.exe -u scripts/continuation_run.py

Verdict pre-enregistre (spec 2026-06-17-swing-continuation, NE PAS rationaliser
apres coup) :
- core_greenlight True  -> noyau passe ; lancer le DSR/CSCV full-history
  (scripts/overfit_audit.py) pour le verdict final.
- core_greenlight False -> KILL ; documenter dans FINDINGS, geler la these swing.
ATTENTION : un run mono-regime / petit echantillon ne PROUVE rien (cf. etage 1).
Le verdict reel exige la slice multi-regime (>= bull + bear)."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from orderflow_bot.backtest.plumbing_checks import (
    label_violations, plan_violations, zone_violations,
)
from orderflow_bot.backtest.swing_gate import mirror_plan
from orderflow_bot.backtest.swing_gate2 import gate2, regime_fn_from_closes
from orderflow_bot.config import BotConfig, load_config
from orderflow_bot.ingestion.reader import available_days, read_klines_as_ticks
from orderflow_bot.pipeline import PlanGenerator, simulate_isolated

_DAY_MS = 86_400_000


def _zero_fees(cfg: BotConfig) -> BotConfig:
    d = cfg.model_dump()
    d["fees"] = {"maker_pct": 0.0, "taker_pct": 0.0, "slippage_ticks": 0}
    return BotConfig(**d)


def _collect(cfg: BotConfig):
    """Une passe sequentielle : DailyLevels finalises, plans candidats, et close
    journalier (dernier prix du jour) pour la fonction regime."""
    gen = PlanGenerator(cfg)
    plans = []
    closes: dict[int, float] = {}
    for t in read_klines_as_ticks(cfg.kline_data_dir, cfg.symbol):
        plans.extend(gen.on_trade(t))
        closes[t.ts // _DAY_MS] = t.price
    return gen._levels, plans, closes


def main() -> int:
    logging.basicConfig(level=logging.WARNING)
    cfg = load_config("config.continuation.yaml")
    cfg0 = _zero_fees(cfg)                      # brut = frais=0
    days = available_days(cfg.kline_data_dir, cfg.symbol)
    if not days:
        print("FAIL: aucune kline dans", cfg.kline_data_dir, "/", cfg.symbol)
        return 1

    # plans generes a frais=0 (le filtre de friction ne doit pas culler le jeu),
    # puis relabel du MEME jeu a frais=0 (brut), miroir, et frais reels (net).
    levels, plans, closes = _collect(cfg0)

    def ticks():
        return read_klines_as_ticks(cfg.kline_data_dir, cfg.symbol)

    brut_l = simulate_isolated(cfg0, plans, ticks(), eod_flat=False)
    mirror = simulate_isolated(cfg0, [mirror_plan(p) for p in plans], ticks(), eod_flat=False)
    net_l = simulate_isolated(cfg, plans, ticks(), eod_flat=False)

    problems = (zone_violations(levels)
                + plan_violations(plans, cfg.risk.min_rr)
                + label_violations(brut_l))

    verdict = gate2(brut_l, mirror, net_l, regime_fn_from_closes(closes))

    print(f"jours={len(days)} plans={len(plans)} labels={len(brut_l)}")
    if problems:
        print("PLOMBERIE FAIL — violations:")
        for p in problems[:20]:
            print("  -", p)
        return 1
    print("PLOMBERIE PASS")
    print(f"gate 2b (noyau)    : {verdict}")
    print("VERDICT            :",
          "CORE GREENLIGHT (lancer DSR/CSCV full-history)" if verdict["core_greenlight"]
          else "KILL (noyau drift-controle echoue)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

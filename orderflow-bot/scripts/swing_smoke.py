"""Gate 1 du redeploy swing (cf. spec 2026-06-17). Orchestration : lit le stock,
genere les plans fade-vers-value, etiquette a frais=0 (brut), puis tranche via
backtest.swing_gate.gate1. Lancer : python -u scripts/swing_smoke.py

Verdict pre-enregistre (ne pas rationaliser apres coup) :
- GREENLIGHT klines : brut directionnel positif et stable -> etage 2 justifie.
- KILL : brut ~ 0 / non directionnel -> these fade-vers-value morte comme
  l'intraday. NE PAS construire l'ingestion klines ; documenter dans FINDINGS."""

from orderflow_bot.backtest.swing_gate import gate1, mirror_plan
from orderflow_bot.config import BotConfig, load_config
from orderflow_bot.ingestion.reader import read_trades
from orderflow_bot.pipeline import generate_plans, simulate_isolated


def _zero_fees(cfg: BotConfig) -> BotConfig:
    d = cfg.model_dump()
    d["fees"] = {"maker_pct": 0.0, "taker_pct": 0.0, "slippage_ticks": 0}
    return BotConfig(**d)


def main() -> None:
    cfg = _zero_fees(load_config("config.swing.yaml"))   # brut = frais=0

    def ticks():
        return read_trades(cfg.market_data_dir, cfg.symbol)

    plans = generate_plans(cfg, ticks())
    fade = simulate_isolated(cfg, plans, ticks(), eod_flat=cfg.eod_flat)
    mirror = simulate_isolated(cfg, [mirror_plan(p) for p in plans], ticks(),
                               eod_flat=cfg.eod_flat)
    verdict = gate1(fade, mirror)
    print(f"plans generes      : {len(plans)}")
    print(f"gate 1             : {verdict}")
    print("VERDICT            :",
          "GREENLIGHT klines" if verdict["greenlight"] else "KILL (brut non directionnel)")


if __name__ == "__main__":
    main()

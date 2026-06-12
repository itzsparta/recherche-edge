"""Walk-forward out-of-sample : decoupe les jours disponibles en folds
consecutifs ; chaque fold est rejoue avec un warmup de warmup_days jours
(profils/zones alimentes, trading coupe), puis trading actif dans le fold.
Robustesse = stabilite de l'expectancy d'un fold a l'autre, pas le total."""

from orderflow_bot.config import BotConfig
from orderflow_bot.ingestion.reader import available_days, read_trades
from orderflow_bot.pipeline import run_backtest_window

_DAY_MS = 86_400_000


def fold_bounds(days: list[int], n_folds: int) -> list[tuple[int, int]]:
    """Decoupe les jours en n_folds consecutifs ~egaux.
    Retourne [(premier_jour, dernier_jour_exclu)] en jours epoch."""
    assert n_folds >= 1 and len(days) >= n_folds
    days = sorted(days)
    base, extra = divmod(len(days), n_folds)
    bounds: list[tuple[int, int]] = []
    i = 0
    for k in range(n_folds):
        n = base + (1 if k < extra else 0)
        chunk = days[i:i + n]
        bounds.append((chunk[0], chunk[-1] + 1))
        i += n
    return bounds


def walk_forward(cfg: BotConfig, n_folds: int = 4, warmup_days: int = 20) -> dict:
    days = available_days(cfg.data_dir, cfg.symbol)
    if len(days) < n_folds:
        return {"folds": [],
                "error": f"{len(days)} jours disponibles < {n_folds} folds"}
    # journal dedie : ne jamais ecraser le journal paper/backtest courant
    wf_cfg = cfg.model_copy(update={"journal_path": cfg.journal_path + ".wf"},
                            deep=True)
    folds: list[dict] = []
    for start_day, end_day in fold_bounds(days, n_folds):
        trades = read_trades(cfg.data_dir, cfg.symbol,
                             start_ms=(start_day - warmup_days) * _DAY_MS,
                             end_ms=end_day * _DAY_MS)
        m = run_backtest_window(wf_cfg, trades, trade_from_ts=start_day * _DAY_MS)
        m["from_day"], m["to_day"] = start_day, end_day
        folds.append(m)
    exps = [f["expectancy_r"] for f in folds if f["trades"] > 0]
    return {
        "folds": folds,
        "folds_with_trades": len(exps),
        "folds_positive": sum(1 for e in exps if e > 0),
        "expectancy_mean": sum(exps) / len(exps) if exps else 0.0,
        "expectancy_spread": (max(exps) - min(exps)) if exps else 0.0,
    }

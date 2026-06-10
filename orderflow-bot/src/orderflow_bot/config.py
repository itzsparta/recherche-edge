from pathlib import Path

import yaml
from pydantic import BaseModel


class AbsorptionCfg(BaseModel):
    window_ms: int = 30_000
    vol_factor: float = 3.0          # volume fenetre >= facteur x mediane baseline
    max_range_ticks: int = 15        # le prix ne progresse plus
    min_delta_frac: float = 0.3      # |delta| >= frac x volume fenetre
    baseline_windows: int = 20


class ImbalanceCfg(BaseModel):
    ratio: float = 3.0
    min_stack: int = 3


class StrategyCfg(BaseModel):
    zone_margin_pct: float = 0.001       # demi-largeur de zone, en % du prix
    stop_buffer_ticks: int = 20          # stop derriere la zone
    entry_expire_minutes: int = 15       # ordre limit non rempli -> annule
    profile_days: int = 5                # composite pour LVN
    npoc_lookback_days: int = 20
    absorption: AbsorptionCfg = AbsorptionCfg()
    imbalance: ImbalanceCfg = ImbalanceCfg()


class RiskCfg(BaseModel):
    risk_pct: float = 0.0075             # 0.75 % par trade
    daily_stop_pct: float = 0.02         # -2 % -> stop jusqu'au lendemain
    max_consecutive_losses: int = 3      # 3 pertes -> pause jusqu'au lendemain
    max_trades_per_day: int = 3
    min_rr: float = 2.0
    partial_at_r: float = 1.0            # partiel a 1R
    partial_fraction: float = 0.5        # 50 % de la position
    qty_step: float = 0.001


class SessionCfg(BaseModel):
    start: str   # "HH:MM" UTC
    end: str


class BotConfig(BaseModel):
    symbol: str = "BTCUSDT"
    tick_size: float = 0.1
    bin_size: float = 1.0
    bar_minutes: int = 1
    data_dir: str = "data"
    journal_path: str = "journal.jsonl"
    equity: float = 10_000.0
    risk: RiskCfg = RiskCfg()
    strategy: StrategyCfg = StrategyCfg()
    sessions: list[SessionCfg] = [SessionCfg(start="13:00", end="17:00")]


def load_config(path: str | Path) -> BotConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return BotConfig(**data)

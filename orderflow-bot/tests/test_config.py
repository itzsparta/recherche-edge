import pytest
from pydantic import ValidationError

from orderflow_bot.config import BotConfig, load_config


def test_defaults():
    cfg = BotConfig()
    assert cfg.symbol == "BTCUSDT"
    assert cfg.risk.risk_pct == 0.0075
    assert cfg.risk.daily_stop_pct == 0.02
    assert cfg.risk.max_consecutive_losses == 3
    assert cfg.risk.min_rr == 2.0
    assert cfg.strategy.absorption.window_ms == 30_000


def test_move_to_be_default_true():
    assert BotConfig().risk.move_to_be is True


def test_load_yaml(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("symbol: ETHUSDT\nrisk:\n  risk_pct: 0.005\n", encoding="utf-8")
    cfg = load_config(p)
    assert cfg.symbol == "ETHUSDT"
    assert cfg.risk.risk_pct == 0.005
    assert cfg.risk.min_rr == 2.0   # defaut conserve


def test_unknown_key_rejected(tmp_path):
    # une typo dans la config doit faire planter le demarrage, pas etre ignoree
    p = tmp_path / "c.yaml"
    p.write_text("symbol: BTCUSDT\nriskk:\n  risk_pct: 0.005\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config(p)


def test_fees_defaults():
    from orderflow_bot.config import BotConfig
    cfg = BotConfig()
    assert cfg.fees.maker_pct == 0.0002
    assert cfg.fees.taker_pct == 0.0005
    assert cfg.fees.slippage_ticks == 2


def test_market_default_is_spot():
    cfg = BotConfig()
    assert cfg.market == "spot"


def test_market_data_dir_spot():
    cfg = BotConfig(data_dir="data")
    assert cfg.market_data_dir == "data/spot"


def test_market_data_dir_futures():
    cfg = BotConfig(data_dir="data", market="futures")
    assert cfg.market_data_dir == "data/futures"


def test_market_invalid():
    with pytest.raises(Exception):
        BotConfig(market="perp")


def test_signal_mode_default_reversal():
    from orderflow_bot.config import StrategyCfg
    assert StrategyCfg().signal_mode == "reversal"


def test_signal_mode_accepts_continuation():
    from orderflow_bot.config import StrategyCfg
    assert StrategyCfg(signal_mode="continuation").signal_mode == "continuation"


def test_signal_mode_rejects_unknown():
    from orderflow_bot.config import StrategyCfg
    with pytest.raises(Exception):
        StrategyCfg(signal_mode="momentum")


def test_entry_mode_default_limit():
    from orderflow_bot.config import StrategyCfg
    assert StrategyCfg().entry_mode == "limit"


def test_entry_mode_accepts_stop():
    from orderflow_bot.config import StrategyCfg
    assert StrategyCfg(entry_mode="stop").entry_mode == "stop"


def test_entry_mode_rejects_unknown():
    from orderflow_bot.config import StrategyCfg
    with pytest.raises(ValidationError):
        StrategyCfg(entry_mode="market")


def test_entry_confirm_frac_default_zero():
    from orderflow_bot.config import StrategyCfg
    assert StrategyCfg().entry_confirm_frac == 0.0

import pyarrow as pa
import pyarrow.parquet as pq

from orderflow_bot.backtest.walkforward import fold_bounds, walk_forward
from orderflow_bot.config import BotConfig, FeesCfg
from orderflow_bot.ingestion.reader import available_days
from orderflow_bot.pipeline import window_active

_DAY = 86_400_000


def _write_parquet(tmp_path, symbol="BTCUSDT"):
    folder = tmp_path / symbol
    folder.mkdir()
    t = pa.table({
        "ts": [5 * _DAY + 1, 5 * _DAY + 2, 7 * _DAY + 1],
        "price": [100.0, 101.0, 102.0],
        "qty": [1.0, 1.0, 1.0],
        "is_buyer_maker": [False, True, False],
    })
    pq.write_table(t, folder / "x.parquet")


def test_available_days(tmp_path):
    _write_parquet(tmp_path)
    assert available_days(tmp_path, "BTCUSDT") == [5, 7]


def test_available_days_empty(tmp_path):
    assert available_days(tmp_path, "BTCUSDT") == []


def test_fold_bounds_consecutive():
    # 10 jours en 3 folds : tailles 4, 3, 3 — bornes [debut, fin_exclu)
    b = fold_bounds(list(range(100, 110)), 3)
    assert b == [(100, 104), (104, 107), (107, 110)]


def test_window_active():
    assert window_active(50, None, None) is True
    assert window_active(50, 100, None) is False
    assert window_active(150, 100, 200) is True
    assert window_active(200, 100, 200) is False


def test_walk_forward_smoke(tmp_path):
    _write_parquet(tmp_path)
    cfg = BotConfig(data_dir=str(tmp_path), journal_path=str(tmp_path / "j.jsonl"),
                    fees=FeesCfg(maker_pct=0.0, taker_pct=0.0, slippage_ticks=0))
    out = walk_forward(cfg, n_folds=2, warmup_days=0)
    assert len(out["folds"]) == 2
    assert out["folds"][0]["from_day"] == 5
    assert out["folds"][1]["from_day"] == 7
    assert all(f["trades"] == 0 for f in out["folds"])    # 3 ticks ne produisent rien


def test_walk_forward_not_enough_days(tmp_path):
    _write_parquet(tmp_path)
    out = walk_forward(BotConfig(data_dir=str(tmp_path)), n_folds=5)
    assert out["folds"] == []
    assert "error" in out

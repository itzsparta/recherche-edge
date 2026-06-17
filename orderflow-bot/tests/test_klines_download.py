import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orderflow_bot.config import BotConfig

from scripts.download_klines import kline_archive_url, month_range


def test_kline_url_spot():
    assert kline_archive_url("spot", "BTCUSDT", 2020, 1) == (
        "https://data.binance.vision/data/spot/monthly/klines/"
        "BTCUSDT/1m/BTCUSDT-1m-2020-01.zip"
    )


def test_kline_url_futures():
    assert kline_archive_url("futures", "BTCUSDT", 2023, 12) == (
        "https://data.binance.vision/data/futures/um/monthly/klines/"
        "BTCUSDT/1m/BTCUSDT-1m-2023-12.zip"
    )


def test_month_range_inclusive():
    assert month_range(2019, 11, 2020, 2) == [(2019, 11), (2019, 12), (2020, 1), (2020, 2)]


def test_month_range_single():
    assert month_range(2020, 5, 2020, 5) == [(2020, 5)]

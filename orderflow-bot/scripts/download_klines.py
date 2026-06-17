"""Telecharge les archives klines 1m mensuelles data.binance.vision (gratuites)
-> un Parquet/mois dans kline_data_dir/symbol. Idempotent : un mois deja present
est saute. Usage: python scripts/download_klines.py 2017 8 2026 5"""

import io
import logging
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from orderflow_bot.config import load_config
from orderflow_bot.ingestion.klines import convert_kline_csv

log = logging.getLogger(__name__)
_BASE = "https://data.binance.vision/data"


def kline_archive_url(market: str, symbol: str, year: int, month: int) -> str:
    root = "spot" if market == "spot" else "futures/um"
    return (f"{_BASE}/{root}/monthly/klines/{symbol}/1m/"
            f"{symbol}-1m-{year:04d}-{month:02d}.zip")


def month_range(y0: int, m0: int, y1: int, m1: int) -> list[tuple[int, int]]:
    """Liste [(annee, mois)] de (y0,m0) a (y1,m1) inclus."""
    out, y, m = [], y0, m0
    while (y, m) <= (y1, m1):
        out.append((y, m))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def download_klines(config_path: str, y0: int, m0: int, y1: int, m1: int) -> dict:
    cfg = load_config(config_path)
    out_dir = Path(cfg.kline_data_dir) / cfg.symbol
    out_dir.mkdir(parents=True, exist_ok=True)
    got = skipped = missing = bars = 0
    for y, m in month_range(y0, m0, y1, m1):
        out = out_dir / f"{cfg.symbol}-1m-{y:04d}-{m:02d}.parquet"
        if out.exists():
            skipped += 1
            continue
        url = kline_archive_url(cfg.market, cfg.symbol, y, m)
        try:
            with urlopen(url, timeout=180) as resp:
                blob = resp.read()
        except HTTPError as e:
            if e.code == 404:
                log.warning("archive absente: %s", url)
                missing += 1
                continue
            raise
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            name = z.namelist()[0]
            with tempfile.TemporaryDirectory() as td:
                bars += convert_kline_csv(z.extract(name, td), out)
        got += 1
        log.info("%04d-%02d importe", y, m)
    return {"months_imported": got, "months_skipped": skipped,
            "months_missing": missing, "bars": bars}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cfg_path = sys.argv[1] if len(sys.argv) >= 6 else "config.klines.yaml"
    args = [int(a) for a in sys.argv[-4:]]
    print(download_klines(cfg_path, *args))

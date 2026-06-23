"""Prix daily stETH + ETH (CoinGecko, USD), cache data/. discount = stETH/ETH - 1.

Fallback DeFiLlama si CoinGecko rate-limit (clé non requise, mais quota bas)."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

_DATA = Path(__file__).parent / "data"
# CRITIQUE : sampler stETH et ETH au MÊME timestamp, sinon le ratio fabrique de faux discounts
# (les deux prix pris à des instants intraday différents un jour volatil => artefact ±13%, cf. v1).
# prices/historical/{ts}/{coins} résout TOUS les coins au même ts cible (searchWidth serré).
_HIST = "https://coins.llama.fi/prices/historical/{ts}/{coins}?searchWidth=2h"
_START = 1609459200   # 2021-01-01 UTC (post-lancement stETH déc-2020)
_STETH = "ethereum:0xae7ab96520de3a18e5e111b5eaab095312d7fe84"
_ETH = "coingecko:ethereum"
_COINS = f"{_STETH},{_ETH}"


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode())


def discount(refresh: bool = False) -> pd.DataFrame:
    """DataFrame daily aligné : steth, eth, ratio, discount = ratio-1.

    Les deux prix sont résolus au MÊME timestamp cible (00:00 UTC chaque jour) => ratio non-artefactuel.
    """
    _DATA.mkdir(exist_ok=True)
    path = _DATA / "aligned.csv"
    if refresh or not path.exists():
        now = int(time.time())
        rows = []
        ts = _START
        while ts < now:
            try:
                d = _get(_HIST.format(ts=ts, coins=_COINS))["coins"]
            except Exception:
                ts += 86400
                continue
            st, et = d.get(_STETH), d.get(_ETH)
            if st and et:
                # n'accepter que si les deux prints sont proches du ts cible ET entre eux (<2h)
                if abs(st["timestamp"] - et["timestamp"]) <= 7200:
                    rows.append({"date": pd.Timestamp(ts, unit="s").floor("D"),
                                 "steth": st["price"], "eth": et["price"],
                                 "skew_s": st["timestamp"] - ts, "skew_e": et["timestamp"] - ts})
            ts += 86400
            time.sleep(0.08)
        out = pd.DataFrame(rows)
        out.to_csv(path, index=False)
        print(f"  {len(out)} jours alignés, skew médian stETH={out.skew_s.abs().median():.0f}s "
              f"ETH={out.skew_e.abs().median():.0f}s")
    df = pd.read_csv(path, parse_dates=["date"]).set_index("date")
    df = df[~df.index.duplicated()].sort_index()
    df["ratio"] = df["steth"] / df["eth"]
    df["discount"] = df["ratio"] - 1.0
    return df


if __name__ == "__main__":
    df = discount()
    print(f"\n{len(df)} jours, {df.index.min().date()} -> {df.index.max().date()}")
    print(f"discount: min={df['discount'].min():.4f}  max={df['discount'].max():.4f}  "
          f"mean={df['discount'].mean():.4f}  std={df['discount'].std():.4f}")

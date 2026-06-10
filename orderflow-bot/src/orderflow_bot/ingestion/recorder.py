from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from orderflow_bot.models import Trade

_SCHEMA = pa.schema([
    ("ts", pa.int64()),
    ("price", pa.float64()),
    ("qty", pa.float64()),
    ("is_buyer_maker", pa.bool_()),
])


class TradeRecorder:
    """Bufferise puis ecrit des fichiers Parquet immuables nommes par plage de ts.
    Pas d'append Parquet : un fichier par flush, le reader recolle via ORDER BY."""

    def __init__(self, data_dir: str | Path, symbol: str, flush_every: int = 5000):
        self.flush_every = flush_every
        self._dir = Path(data_dir) / symbol
        self._dir.mkdir(parents=True, exist_ok=True)
        self._buf: list[Trade] = []

    def append(self, t: Trade) -> None:
        self._buf.append(t)
        if len(self._buf) >= self.flush_every:
            self.flush()

    def flush(self) -> None:
        if not self._buf:
            return
        table = pa.table(
            {
                "ts": [t.ts for t in self._buf],
                "price": [t.price for t in self._buf],
                "qty": [t.qty for t in self._buf],
                "is_buyer_maker": [t.is_buyer_maker for t in self._buf],
            },
            schema=_SCHEMA,
        )
        name = f"{self._buf[0].ts}_{self._buf[-1].ts}.parquet"
        pq.write_table(table, self._dir / name)
        self._buf.clear()

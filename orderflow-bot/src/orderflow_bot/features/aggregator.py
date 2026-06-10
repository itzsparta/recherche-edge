from orderflow_bot.binning import bin_of
from orderflow_bot.models import FootprintBar, Trade


class BarAggregator:
    """Agrege les trades en bougies temps avec footprint bid/ask par bin.
    on_trade retourne la bougie precedente quand une nouvelle fenetre demarre."""

    def __init__(self, bar_ms: int, bin_size: float):
        self.bar_ms = bar_ms
        self.bin_size = bin_size
        self._cur: FootprintBar | None = None

    def on_trade(self, t: Trade) -> FootprintBar | None:
        start = t.ts - t.ts % self.bar_ms
        closed = None
        if self._cur is not None and start > self._cur.open_ts:
            closed = self._cur
            self._cur = None
        if self._cur is None:
            self._cur = FootprintBar(
                open_ts=start, close_ts=start + self.bar_ms,
                open=t.price, high=t.price, low=t.price, close=t.price,
                volume=0.0, delta=0.0, ask_vol={}, bid_vol={},
            )
        b = self._cur
        b.high = max(b.high, t.price)
        b.low = min(b.low, t.price)
        b.close = t.price
        b.volume += t.qty
        b.delta += t.qty * t.aggressor
        side = b.ask_vol if t.aggressor > 0 else b.bid_vol
        k = bin_of(t.price, self.bin_size)
        side[k] = side.get(k, 0.0) + t.qty
        return closed

    def flush(self) -> FootprintBar | None:
        closed, self._cur = self._cur, None
        return closed

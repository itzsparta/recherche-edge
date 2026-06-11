from orderflow_bot.models import FootprintBar


class CvdTracker:
    """Cumulative Volume Delta par bougie + divergences prix/CVD sur les deux
    derniers swings (fractale 1-1 : extreme strictement au-dela de ses voisins)."""

    def __init__(self):
        self.cvd = 0.0
        self._hist: list[tuple[float, float, float]] = []   # (low, high, cvd_close)

    def reset(self) -> None:
        self.cvd = 0.0
        self._hist.clear()

    def on_bar(self, bar: FootprintBar) -> None:
        self.cvd += bar.delta
        self._hist.append((bar.low, bar.high, self.cvd))

    def _swings(self, key: int, is_low: bool) -> list[tuple[float, float]]:
        h = self._hist
        out = []
        for i in range(1, len(h) - 1):
            if is_low and h[i][key] < h[i - 1][key] and h[i][key] < h[i + 1][key]:
                out.append((h[i][key], h[i][2]))
            if not is_low and h[i][key] > h[i - 1][key] and h[i][key] > h[i + 1][key]:
                out.append((h[i][key], h[i][2]))
        return out

    def bullish_divergence(self) -> bool:
        s = self._swings(0, is_low=True)
        if len(s) < 2:
            return False
        (p1, c1), (p2, c2) = s[-2], s[-1]
        return p2 < p1 and c2 > c1

    def bearish_divergence(self) -> bool:
        s = self._swings(1, is_low=False)
        if len(s) < 2:
            return False
        (p1, c1), (p2, c2) = s[-2], s[-1]
        return p2 > p1 and c2 < c1

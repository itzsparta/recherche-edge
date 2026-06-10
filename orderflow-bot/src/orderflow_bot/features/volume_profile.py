from orderflow_bot.binning import bin_of


class VolumeProfile:
    """Volume par bin de prix. POC, value area (expansion depuis le POC),
    LVN/HVN relatifs au volume moyen du range."""

    def __init__(self, bin_size: float):
        self.bin_size = bin_size
        self.vol: dict[int, float] = {}
        self.total = 0.0

    def add(self, price: float, qty: float) -> None:
        b = bin_of(price, self.bin_size)
        self.vol[b] = self.vol.get(b, 0.0) + qty
        self.total += qty

    def merge(self, other: "VolumeProfile") -> None:
        for b, q in other.vol.items():
            self.vol[b] = self.vol.get(b, 0.0) + q
            self.total += q

    def poc(self) -> int:
        return max(self.vol, key=lambda b: self.vol[b])

    def value_area(self, pct: float = 0.70) -> tuple[int, int]:
        """(val_bin, vah_bin) : etend depuis le POC vers le voisin le plus
        volumineux jusqu'a couvrir pct du volume total."""
        bins = sorted(self.vol)
        lo = hi = bins.index(self.poc())
        acc = self.vol[bins[lo]]
        while acc < pct * self.total and (lo > 0 or hi < len(bins) - 1):
            up = self.vol[bins[hi + 1]] if hi < len(bins) - 1 else -1.0
            down = self.vol[bins[lo - 1]] if lo > 0 else -1.0
            if up >= down:
                hi += 1
                acc += up
            else:
                lo -= 1
                acc += down
        return bins[lo], bins[hi]

    def _mean_per_bin(self) -> float:
        lo, hi = min(self.vol), max(self.vol)
        return self.total / (hi - lo + 1)

    def lvns(self, frac: float = 0.3) -> list[int]:
        """Vallees internes (< frac x volume moyen), groupees ; un bin
        representant (centre) par vallee. Bords du range exclus."""
        m = self._mean_per_bin()
        lo, hi = min(self.vol), max(self.vol)
        out: list[int] = []
        run: list[int] = []
        for b in range(lo + 1, hi):
            if self.vol.get(b, 0.0) < frac * m:
                run.append(b)
            elif run:
                out.append(run[len(run) // 2])
                run = []
        if run:
            out.append(run[len(run) // 2])
        return out

    def hvns(self, frac: float = 1.5) -> list[int]:
        m = self._mean_per_bin()
        return sorted(b for b, q in self.vol.items() if q >= frac * m)

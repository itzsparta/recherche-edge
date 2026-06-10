"""Conversion prix <-> bin entier. Toutes les structures de volume sont indexees
par bin entier pour eviter les comparaisons de floats."""


def bin_of(price: float, bin_size: float) -> int:
    return int(round(price / bin_size))


def price_of(b: int, bin_size: float) -> float:
    return round(b * bin_size, 10)

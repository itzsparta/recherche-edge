from orderflow_bot.models import FootprintBar


def stacked_imbalances(
    bar: FootprintBar, ratio: float = 3.0, min_stack: int = 3
) -> dict[str, list[int]]:
    """Imbalances diagonales footprint : achat = ask(b) >= ratio x bid(b-1),
    vente = bid(b) >= ratio x ask(b+1). Denominateur nul + numerateur > 0 compte.
    Retourne uniquement les bins appartenant a une pile >= min_stack consecutifs."""

    def imb(num: float, den: float) -> bool:
        if num <= 0:
            return False
        return den == 0 or num / den >= ratio

    buys, sells = [], []
    for b in set(bar.ask_vol) | set(bar.bid_vol):
        if imb(bar.ask_vol.get(b, 0.0), bar.bid_vol.get(b - 1, 0.0)):
            buys.append(b)
        if imb(bar.bid_vol.get(b, 0.0), bar.ask_vol.get(b + 1, 0.0)):
            sells.append(b)

    def stacks(xs: list[int]) -> list[int]:
        out: list[int] = []
        run: list[int] = []
        for b in sorted(xs):
            run = run + [b] if run and b == run[-1] + 1 else [b]
            if len(run) == min_stack:
                out.extend(run)
            elif len(run) > min_stack:
                out.append(b)
        return out

    return {"buy": stacks(buys), "sell": stacks(sells)}

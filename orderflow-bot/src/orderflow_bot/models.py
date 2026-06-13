from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Trade:
    ts: int                # epoch ms
    price: float
    qty: float
    is_buyer_maker: bool   # True => l'agresseur est vendeur

    @property
    def aggressor(self) -> int:
        """+1 achat agressif, -1 vente agressive."""
        return -1 if self.is_buyer_maker else 1


@dataclass(slots=True)
class FootprintBar:
    open_ts: int
    close_ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    delta: float                       # somme qty * aggressor
    ask_vol: dict[int, float]          # volume achat agressif par bin
    bid_vol: dict[int, float]          # volume vente agressive par bin


@dataclass(frozen=True, slots=True)
class OrderPlan:
    ts: int
    side: int          # +1 long, -1 short
    entry: float       # ordre limit
    stop: float
    target: float
    meta: dict = field(default_factory=dict)   # zone/trigger/bias pour le journal


@dataclass(frozen=True, slots=True)
class Fill:
    ts: int
    price: float
    qty: float
    kind: str          # entry | partial | stop | target | eod


@dataclass(slots=True)
class ClosedTrade:
    plan: OrderPlan
    qty: float
    fills: list[Fill]
    pnl: float                         # NET de frais
    r_multiple: float                 # calcule sur le pnl net
    opened_ts: int
    closed_ts: int
    fees: float = 0.0                 # total des frais payes sur tous les fills
    mfe_r: float = 0.0                # excursion max favorable, en R du risque initial
    mae_r: float = 0.0                # excursion max defavorable (negatif), en R


@dataclass(frozen=True, slots=True)
class Cancelled:
    """Ordre d'entree expire sans fill."""
    ts: int

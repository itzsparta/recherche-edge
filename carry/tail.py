"""Risque exchange (FTX = -100 %) — (D2) pré-enregistré.

Break-even : à quelle proba annuelle de faillite exchange l'EV du carry tombe à zéro ?
EV = net·(1-p) - p·1 = 0  =>  p* = net / (net + 1).
Gate : p* > 5 %/an pour un GO (sinon le carry n'est pas assez gras pour le tail exchange).
"""
from __future__ import annotations

GATE_PSTAR = 0.05  # proba annuelle de faillite exchange — seuil GO


def breakeven_p(net_ann: float) -> float:
    """Proba annuelle de faillite exchange annulant l'EV."""
    if net_ann <= 0:
        return 0.0
    return net_ann / (net_ann + 1.0)


def report(net_ann: float) -> dict:
    p = breakeven_p(net_ann)
    ok = p > GATE_PSTAR
    print(f"  net_ann (OOS) {net_ann:+.1%}  ->  break-even faillite exchange p* = {p:.2%}/an")
    print(f"  gate (D2) p* > {GATE_PSTAR:.0%}/an ? {ok}")
    if not ok:
        print(f"    => un risque exchange de seulement {p:.1%}/an suffit à annuler l'EV "
              "= pas assez gras pour le tail.")
    return {"pstar": p, "ok": ok}

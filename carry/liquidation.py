"""Modèle de liquidation du short perp — (D1) pré-enregistré.

Cross-margin (setup compétent) : le gain de la jambe spot compense la perte de la jambe perp →
l'équité reste delta-neutre → pas de liquidation. Isolé/naïf : la jambe perp peut être liquidée
seule sur un squeeze. On mesure la magnitude des squeezes 8h et le levier qui liquide.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MAINT = 0.005  # marge de maintenance ~0.5 % (Binance, gros notional)


def squeeze_stats(perp8h: pd.DataFrame) -> dict:
    """Pire move adverse pour un SHORT dans une barre 8h = (high/open - 1)."""
    adverse = (perp8h["high"] / perp8h["open"] - 1.0).dropna()
    return {
        "worst_8h_up": float(adverse.max()),
        "p999_8h_up": float(adverse.quantile(0.999)),
        "p99_8h_up": float(adverse.quantile(0.99)),
        "n_bars": int(len(adverse)),
        "adverse": adverse,
    }


def liq_threshold(L: float) -> float:
    """Move adverse qui liquide un short isolé au levier L."""
    return 1.0 / L - MAINT


def isolated_liq_freq(adverse: pd.Series, L: float) -> float:
    """Fraction de barres 8h où un short isolé au levier L serait liquidé."""
    thr = liq_threshold(L)
    return float((adverse > thr).mean())


def report(perp8h: pd.DataFrame, levers=(2, 3, 5, 10)) -> dict:
    s = squeeze_stats(perp8h)
    print(f"  squeeze 8h : pire move up {s['worst_8h_up']:+.1%}, "
          f"p99.9 {s['p999_8h_up']:+.1%}, p99 {s['p99_8h_up']:+.1%} (n={s['n_bars']})")
    print("  liquidation ISOLÉ (le naïf) — fréquence de barres 8h liquidantes :")
    freqs = {}
    for L in levers:
        f = isolated_liq_freq(s["adverse"], L)
        freqs[L] = f
        thr = liq_threshold(L)
        print(f"    L={L:>2}x  seuil {thr:+.1%}  freq {f:.4%}"
              + ("   <- pire move NE liquide PAS" if s["worst_8h_up"] < thr else ""))
    # cross-margin : equité delta-neutre, le spot offsete le perp -> pas de liquidation
    safe_cross = True  # par construction (long spot 1:1 contre short perp 1:1)
    print("  CROSS-MARGIN (setup compétent) : jambe spot offsete la jambe perp 1:1 → "
          "équité ~plate → liquidation ≈ 0 quel que soit le move.")
    return {"squeeze": {k: v for k, v in s.items() if k != "adverse"},
            "iso_freq": freqs, "cross_safe": safe_cross}

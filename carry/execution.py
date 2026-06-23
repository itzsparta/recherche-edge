"""P&L delta-neutre RÉEL : funding + (spot_ret - perp_ret) - frais 2-jambes. Pré-enreg SPEC-phase2.

Phase-1 = funding seul, markPrice proxy. Ici legs réels (spot vs perp séparés) + frais taker réels.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# --- frais réels (FIXE, pré-enregistré dans SPEC-phase2.md) ---
SPOT_TAKER = 0.0010   # 0.10 %
PERP_TAKER = 0.0004   # 0.04 %
SLIP = 0.0002         # 2 bps / jambe
MONTHLY_TURNOVER = 0.25  # fraction de notional round-trip re-tradée / mois (gestion delta+marge)

OPEN_BOTH = SPOT_TAKER + PERP_TAKER + 2 * SLIP   # ouvrir les 2 jambes
ROUNDTRIP = 2 * OPEN_BOTH                          # ouvrir + fermer


def build(funding_daily: pd.DataFrame, spot: pd.DataFrame, perp: pd.DataFrame) -> pd.DataFrame:
    """DataFrame quotidien : carry, basis (spot_ret-perp_ret), fees, pnl, btc_ret, regime.

    funding_daily = sortie de carry.daily() (a 'carry' et 'regime').
    """
    spot_ret = spot["close"].pct_change()
    perp_ret = perp["close"].pct_change()
    df = pd.DataFrame(index=funding_daily.index)
    df["carry"] = funding_daily["carry"]
    df["regime"] = funding_daily["regime"]
    df["spot_ret"] = spot_ret.reindex(df.index)
    df["perp_ret"] = perp_ret.reindex(df.index)
    df["btc_ret"] = df["spot_ret"]                      # exposition prix = la jambe longue spot
    df["basis"] = df["spot_ret"] - df["perp_ret"]       # delta-neutre => ~0
    df = df.dropna(subset=["carry", "spot_ret", "perp_ret"])

    # frais : rééq. mensuel (1er jour de chaque mois) re-trade MONTHLY_TURNOVER round-trip
    month = df.index.to_period("M")
    is_rebal = pd.Series(month, index=df.index).ne(pd.Series(month, index=df.index).shift())
    fee = pd.Series(0.0, index=df.index)
    fee[is_rebal] = ROUNDTRIP * MONTHLY_TURNOVER
    fee.iloc[0] = fee.iloc[0] + OPEN_BOTH               # ouverture initiale
    fee.iloc[-1] = fee.iloc[-1] + OPEN_BOTH             # fermeture finale
    df["fee"] = fee
    df["pnl"] = df["carry"] + df["basis"] - df["fee"]
    return df


def ann(xs) -> float:
    return float(np.mean(xs)) * 365.0


def stats(df: pd.DataFrame) -> dict:
    pnl = df["pnl"].dropna()
    gross = ann(df["carry"].dropna())
    net = ann(pnl)
    corr = df[["pnl", "btc_ret"]].dropna().corr().iloc[0, 1]
    return {"gross_ann": gross, "net_ann": net, "corr": float(corr),
            "fee_ann": ann(df["fee"]), "basis_ann": ann(df["basis"].dropna()), "n": len(pnl)}


def max_drawdown(pnl: pd.Series) -> float:
    """Pire drawdown du cumulé (somme arithmétique des rendements quotidiens)."""
    cum = pnl.cumsum()
    return float((cum - cum.cummax()).min())

"""Moteur time-series momentum cross-asset, vol-targeté, rebal mensuel, net de frais.

Aucun lookahead : poids calculés au close du jour de rebal d (données ≤ d), appliqués
aux rendements de d+1 onward (shift(1)). Frais = turnover * cost_bps au changement de
poids. Sharpe est scale-invariant → le niveau de levier (leg_vol) est cosmétique ;
on reporte la vol réalisée pour sanity.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252
MONTH_DAYS = 21


def _month_end_index(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Dernier jour de bourse de chaque mois (sous-ensemble garanti de idx)."""
    return idx[~idx.to_period("M").duplicated(keep="last")]


def run_strategy(
    prices: pd.DataFrame,
    lookback_months: int = 12,
    leg_vol: float = 0.10,
    vol_window: int = 60,
    cost_bps: float = 10.0,
    require_all: bool = True,
) -> dict:
    """Renvoie dict: net (Series daily), gross, equity, monthly, turnover, realized_vol.

    require_all=True  : intersection (tous les actifs présents) — univers ETF.
    require_all=False : union — un actif entre quand il a son historique (signal/vol),
                        gross=1x normalisé sur les actifs actifs. Univers futures où les
                        dates de départ diffèrent (RTY 2017, BZ 2007…).
    """
    prices = prices.dropna() if require_all else prices.dropna(how="all")
    rets = prices.pct_change(fill_method=None)

    # signal : signe du momentum trailing (lookback en jours de bourse)
    lb = lookback_months * MONTH_DAYS
    mom = prices / prices.shift(lb) - 1.0
    signal = np.sign(mom)

    # vol annualisée trailing → poids vol-targetés par jambe
    vol = rets.rolling(vol_window).std() * np.sqrt(TRADING_DAYS)
    raw_w = signal * (leg_vol / vol)
    raw_w = raw_w.replace([np.inf, -np.inf], np.nan)

    # rebal mensuel : on ne garde les poids qu'aux derniers jours de bourse du mois
    rebal_idx = _month_end_index(prices.index)
    w_rebal = raw_w.loc[rebal_idx].dropna(how="all")
    w_rebal = w_rebal.fillna(0.0)  # un actif sans signal/vol encore = flat

    # normalisation gross = 1x (risk-parity pur) : pas de levier empilé, donc pas de
    # coût de financement. leg_vol se simplifie ici → poids = (signe/vol)/Σ|signe/vol|.
    gross_lev = w_rebal.abs().sum(axis=1).replace(0.0, np.nan)
    w_rebal = w_rebal.div(gross_lev, axis=0).fillna(0.0)

    # poids journaliers (ffill entre rebals), appliqués au rendement du LENDEMAIN
    weights_daily = w_rebal.reindex(prices.index, method="ffill")
    eff_w = weights_daily.shift(1)
    gross = (eff_w * rets.fillna(0.0)).sum(axis=1)  # poids 0 sur actif absent → 0*0

    # frais : turnover au rebal, imputé au jour où les nouveaux poids prennent effet
    turnover = w_rebal.diff().abs().sum(axis=1)
    if len(w_rebal):
        turnover.iloc[0] = w_rebal.iloc[0].abs().sum()
    cost_daily = pd.Series(0.0, index=prices.index)
    pos = prices.index.get_indexer(w_rebal.index)
    for p, to in zip(pos, turnover.values):
        if 0 <= p + 1 < len(prices.index):
            cost_daily.iloc[p + 1] += (cost_bps / 1e4) * to

    net = (gross - cost_daily).dropna()
    equity = (1 + net).cumprod()
    monthly = net.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    realized_vol = net.std() * np.sqrt(TRADING_DAYS)

    return {
        "net": net,
        "gross": gross.dropna(),
        "equity": equity,
        "monthly": monthly,
        "turnover": turnover,
        "realized_vol": float(realized_vol),
        "leverage_mean": float(weights_daily.abs().sum(axis=1).mean()),
    }


def benchmark_6040(prices: pd.DataFrame, spy: str = "SPY", bond: str = "IEF",
                   cost_bps: float = 10.0) -> dict:
    """60/40 passif (rebal mensuel) sur le même échantillon, pour comparaison risk-adj."""
    px = prices[[spy, bond]].dropna()
    rets = px.pct_change(fill_method=None)
    w = pd.DataFrame(index=rets.index, columns=[spy, bond], dtype=float)
    w[spy], w[bond] = 0.6, 0.4
    rebal_idx = _month_end_index(px.index)
    w_rebal = w.loc[rebal_idx]
    weights_daily = w_rebal.reindex(px.index, method="ffill")
    net = (weights_daily.shift(1) * rets).sum(axis=1).dropna()
    monthly = net.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    return {"net": net, "monthly": monthly,
            "realized_vol": float(net.std() * np.sqrt(TRADING_DAYS))}

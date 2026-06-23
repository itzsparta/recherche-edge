"""Piste 7 — RV BTC/ETH cointegration daily — PHASE 1 : stationnarité uniquement.

Gate pré-enregistré (EDGE-IDEAS-LOG.md, piste D) :
  (A) ADF p<0.05 sur log(BTC/ETH), IS 2017-2021      -> sinon KILL immédiat
  (B) ADF p<0.05 sur log(BTC/ETH), OOS 2022-2026      -> sinon KILL (rupture régime)
PASS Phase-1 = (A) ET (B). Toute non-significativité = KILL, on ne backteste pas.

Le spread est FIXÉ à log(BTC) - log(ETH) (ratio 1:1) comme pré-enregistré : on ne
ré-estime PAS le hedge ratio pour sauver un kill. L'Engle-Granger ci-dessous est un
DIAGNOSTIC non-gating (interprète un kill : 1:1-spécifique vs non-cointégré tout court).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, coint

from data_rv import spot_daily

IS_END = "2021-12-31"
OOS_START = "2022-01-01"
ALPHA = 0.05


def _adf(x: pd.Series) -> dict:
    x = x.dropna()
    stat, p, lag, nobs, crit, _ = adfuller(x, regression="c", autolag="AIC")
    return {"stat": stat, "p": p, "lag": lag, "nobs": nobs, "crit5": crit["5%"]}


def _half_life(spread: pd.Series) -> float:
    """AR(1) sur Δs_t = α + β·s_{t-1} ; half-life = -ln2/ln(1+β). Diagnostic non-gating."""
    s = spread.dropna()
    s_lag = s.shift(1).dropna()
    ds = (s - s.shift(1)).dropna()
    s_lag, ds = s_lag.align(ds, join="inner")
    X = np.column_stack([np.ones(len(s_lag)), s_lag.values])
    beta = np.linalg.lstsq(X, ds.values, rcond=None)[0][1]
    if beta >= 0:
        return float("inf")
    return float(-np.log(2) / np.log(1 + beta))


def _coint(logb: pd.Series, loge: pd.Series) -> dict:
    """Engle-Granger 2-step, hedge ratio estimé. DIAGNOSTIC non-gating."""
    df = pd.concat([logb, loge], axis=1).dropna()
    t, p, _ = coint(df.iloc[:, 0], df.iloc[:, 1])
    # hedge ratio OLS logb ~ a + h*loge
    X = np.column_stack([np.ones(len(df)), df.iloc[:, 1].values])
    h = np.linalg.lstsq(X, df.iloc[:, 0].values, rcond=None)[0][1]
    return {"t": t, "p": p, "hedge": h}


def main() -> None:
    print("Piste 7 RV BTC/ETH — Phase-1 stationnarité\n" + "=" * 60)
    print("Fetch Binance daily spot (cache CSV)…")
    btc = spot_daily("BTCUSDT")["close"].rename("BTC")
    eth = spot_daily("ETHUSDT")["close"].rename("ETH")

    px = pd.concat([btc, eth], axis=1).dropna()
    spread = np.log(px["BTC"]) - np.log(px["ETH"])  # = log(BTC/ETH), 1:1 pré-enregistré
    spread.name = "log(BTC/ETH)"

    seg = {
        "IS  2017-2021": spread.loc[:IS_END],
        "OOS 2022-2026": spread.loc[OOS_START:],
        "FULL (réf.)":   spread,
    }

    print("\n--- GATE pré-enregistré : ADF sur log(BTC/ETH), regression='c' ---")
    print(f"{'segment':<16}{'n':>6}{'ADF stat':>11}{'p-value':>11}{'crit5%':>10}{'verdict':>12}")
    res = {}
    for name, s in seg.items():
        a = _adf(s)
        res[name] = a
        stationary = a["p"] < ALPHA
        verdict = "stationary" if stationary else "I(1)"
        print(f"{name:<16}{a['nobs']:>6}{a['stat']:>11.3f}{a['p']:>11.4f}"
              f"{a['crit5']:>10.3f}{verdict:>12}")

    print("\n--- DIAGNOSTICS (non-gating) ---")
    for name, s in seg.items():
        hl = _half_life(s)
        hl_str = "∞ (pas de rev.)" if hl == float("inf") else f"{hl:.0f} j"
        print(f"  half-life {name:<16}: {hl_str}")
    logb, loge = np.log(px["BTC"]), np.log(px["ETH"])
    for name, sl in {"IS": slice(None, IS_END), "OOS": slice(OOS_START, None),
                     "FULL": slice(None)}.items():
        c = _coint(logb.loc[sl], loge.loc[sl])
        print(f"  Engle-Granger {name:<5}: t={c['t']:.3f}  p={c['p']:.4f}  "
              f"hedge_ratio={c['hedge']:.3f}  ({'coint.' if c['p'] < ALPHA else 'non-coint.'})")

    # ---- VERDICT pré-enregistré ----
    gate_a = res["IS  2017-2021"]["p"] < ALPHA
    gate_b = res["OOS 2022-2026"]["p"] < ALPHA
    print("\n" + "=" * 60)
    print(f"Gate (A) IS  stationnaire : {'PASS' if gate_a else 'KILL'}  "
          f"(p={res['IS  2017-2021']['p']:.4f})")
    print(f"Gate (B) OOS stationnaire : {'PASS' if gate_b else 'KILL'}  "
          f"(p={res['OOS 2022-2026']['p']:.4f})")
    if gate_a and gate_b:
        print("\nVERDICT Phase-1 : PASS — log(BTC/ETH) I(0) sur IS ET OOS.")
        print("  -> Autorisé à passer en Phase-2 (backtest z-score, gates C-G).")
    else:
        print("\nVERDICT Phase-1 : KILL — spread non-stationnaire (pas de niveau d'équilibre 1:1).")
        print("  -> Thèse RV 1:1 invalide. NE PAS backtester. Voir diagnostic E-G ci-dessus")
        print("     pour savoir si un hedge ratio ≠1 serait cointégré (info, pas un sauvetage).")


if __name__ == "__main__":
    main()

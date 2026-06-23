"""Piste 8 — CEF discount mean-reversion — PHASE 1 : Gate A (stationnarité du discount).

Critère PASS pré-enregistré (docs/SPEC.md) :
  (A1) ≥ 50 % des fonds (≥156 obs hebdo) rejettent la racine unitaire ADF à 5 %
  (A2) ADF du pooled démoyenné (par fonds) p < 0.05
  PASS = A1 ET A2. Sinon KILL : discount = marche aléatoire, pas de convergence à capter.
Diagnostic non-gating : half-life médiane (tradabilité < ~1 an).
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

from data_cef import universe, fetch_all

warnings.simplefilter("ignore")
MIN_OBS = 156   # ≈ 3 ans hebdo
ALPHA = 0.05


def _adf_p(x: np.ndarray) -> float | None:
    x = x[~np.isnan(x)]
    if len(x) < 30 or np.nanstd(x) < 1e-9:
        return None
    try:
        return adfuller(x, regression="c", autolag="AIC")[1]
    except Exception:
        return None


def _half_life(x: pd.Series) -> float:
    s = x.dropna()
    if len(s) < 30:
        return float("nan")
    lag = s.shift(1).dropna()
    ds = (s - s.shift(1)).dropna()
    lag, ds = lag.align(ds, join="inner")
    if len(lag) < 10:
        return float("nan")
    X = np.column_stack([np.ones(len(lag)), lag.values])
    beta = np.linalg.lstsq(X, ds.values, rcond=None)[0][1]
    if beta >= 0:
        return float("inf")
    return float(-np.log(2) / np.log(1 + beta))


def main() -> None:
    print("Piste 8 CEF discount — Phase-1 Gate A (stationnarité discount)\n" + "=" * 64)
    uni = universe()
    tickers = uni["Ticker"].dropna().unique().tolist()
    print(f"Univers CEFConnect : {len(tickers)} fonds. Fetch historiques hebdo (cache)…")
    hist = fetch_all(tickers)
    print(f"Historiques valides : {len(hist)} fonds.")

    rows, pooled_parts, hls = [], [], []
    for t, df in hist.items():
        prem = df["prem"]
        if len(prem) < MIN_OBS:
            continue
        p = _adf_p(prem.values)
        if p is None:
            continue
        rows.append({"ticker": t, "n": len(prem), "adf_p": p,
                     "mean_prem": prem.mean()})
        pooled_parts.append((prem - prem.mean()).values)
        hls.append(_half_life(prem))

    res = pd.DataFrame(rows)
    n_funds = len(res)
    print(f"\nFonds avec ≥{MIN_OBS} obs hebdo testés : {n_funds}")
    if n_funds == 0:
        print("Aucun fonds éligible — abort.")
        return

    # ---- A1 : fraction stationnaire ----
    frac_stat = (res["adf_p"] < ALPHA).mean()
    n_stat = int((res["adf_p"] < ALPHA).sum())

    # ---- A2 : pooled démoyenné ----
    pooled = np.concatenate(pooled_parts)
    pooled_p = _adf_p(pooled)

    # ---- diagnostic half-life ----
    hl_arr = np.array([h for h in hls if np.isfinite(h)])
    med_hl_w = float(np.median(hl_arr)) if len(hl_arr) else float("nan")

    print("\n--- Gate A (pré-enregistré) ---")
    print(f"(A1) fonds stationnaires (ADF p<0.05) : {n_stat}/{n_funds} = {frac_stat:.1%}"
          f"   [PASS si ≥50%]")
    print(f"(A2) pooled démoyenné ADF p          : {pooled_p:.6f}   [PASS si <0.05]")
    print(f"     médiane adf_p par fonds         : {res['adf_p'].median():.4f}")
    print("\n--- Diagnostic non-gating ---")
    print(f"  half-life médiane : {med_hl_w:.0f} semaines = {med_hl_w/52:.2f} an(s)"
          f"   [tradable si <~1 an]")
    print(f"  premium médian univers : {res['mean_prem'].median():+.2f}%  "
          f"(négatif = discount structurel)")

    a1 = frac_stat >= 0.50
    a2 = pooled_p is not None and pooled_p < ALPHA
    print("\n" + "=" * 64)
    print(f"Gate A1 : {'PASS' if a1 else 'KILL'}   Gate A2 : {'PASS' if a2 else 'KILL'}")
    if a1 and a2:
        print("\nVERDICT Phase-1 : PASS — le discount CEF est I(0) (mean-reverting).")
        if np.isfinite(med_hl_w) and med_hl_w / 52 > 1.0:
            print(f"  ⚠ half-life {med_hl_w/52:.1f} an > 1 an : stationnaire mais lent — "
                  f"le drag (expense ratio) sera le vrai combat en Gate C.")
        print("  -> Autorisé à passer en Phase-2 (L/S quintile, gates B-G).")
    else:
        print("\nVERDICT Phase-1 : KILL — discount non-stationnaire (pas de convergence à capter).")
        print("  -> Thèse RV CEF morte à la précondition. NE PAS backtester.")


if __name__ == "__main__":
    main()

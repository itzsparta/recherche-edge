"""
Moteur de simulation Monte Carlo d'une evaluation prop firm.

Pur-sim, zero data marche. Modelise les phases d'evaluation + le compte finance,
les barrieres (max drawdown statique/trailing, daily drawdown, cible, min trading
days, time limit, consistance) et le ledger d'EV.

Modele additif en unites de compte (E0 = 1.0) : les limites des firmes sont
definies vs la balance initiale, donc une perte de 10% = equity < 0.90.

Pre-enregistre : voir docs/SPEC.md.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

HARD_CAP_DAYS = 750  # borne dure de jours pour une phase sans time-limit


@dataclass
class ChallengeConfig:
    name: str = "FTMO-static"
    account: float = 100_000.0      # $ notionnel (sert a convertir l'extraction en $)
    fee: float = 540.0              # $ paye d'avance
    refund_frac: float = 1.0        # fraction de la fee remboursee au 1er payout (si finance)
    phases: tuple = (0.10, 0.05)    # cibles de profit par phase
    max_dd: float = 0.10            # max drawdown (fraction de compte)
    daily_dd: float = 0.05          # daily loss limit (fraction du start-of-day)
    trailing: bool = False          # max_dd trailing (vs high-water) sinon statique
    min_trading_days: int = 0
    max_days: int = 0               # 0 = pas de time-limit (borne interne HARD_CAP_DAYS)
    consistency: float = 0.0        # 0 = pas de regle ; sinon part max d'un seul jour dans le profit
    split: float = 0.80             # part du trader sur le compte finance
    payout_days: int = 14           # intervalle de payout (compte finance)
    funded_horizon_days: int = 504  # ~2 ans de trading : horizon de vie max du compte finance


def _first_true_idx(mask: np.ndarray, fill: int) -> np.ndarray:
    """Index du premier True par ligne ; `fill` si aucun."""
    any_true = mask.any(axis=1)
    idx = mask.argmax(axis=1)
    return np.where(any_true, idx, fill)


def simulate_phase(n, target, cfg: ChallengeConfig, mu_t, sigma_t, k, rng):
    """Simule n traders sur une phase d'evaluation.

    Retourne (passed: bool[n], n_days: int[n], peak_profit_day: float[n]).
    peak_profit_day = plus gros profit realise en un seul jour (pour la regle de consistance).
    """
    eq = np.ones(n)
    peak = np.ones(n)
    status = np.zeros(n, dtype=np.int8)       # 0 actif, 1 passe, -1 echec
    n_days = np.zeros(n, dtype=np.int32)
    best_day = np.zeros(n)                     # plus gros gain en un jour
    cap = cfg.max_days if cfg.max_days > 0 else HARD_CAP_DAYS
    tgt = 1.0 + target
    big = k + 5

    for _ in range(cap):
        act = status == 0
        if not act.any():
            break
        idx = np.where(act)[0]
        m = idx.size
        z = rng.standard_normal((m, k))
        trades = mu_t + sigma_t * z
        cum = np.cumsum(trades, axis=1)
        s = eq[idx]
        path = s[:, None] + cum                # equity intraday apres chaque trade

        if cfg.trailing:
            ofloor = peak[idx] - cfg.max_dd
        else:
            ofloor = np.full(m, 1.0 - cfg.max_dd)
        dfloor = s - cfg.daily_dd
        floor = np.maximum(ofloor, dfloor)     # plancher contraignant (le plus haut)

        hit_t = path >= tgt
        hit_b = path < floor[:, None]
        ti = _first_true_idx(hit_t, big)
        bi = _first_true_idx(hit_b, big)

        end_eq = path[:, -1]
        day_gain = end_eq - s
        n_days[idx] += 1

        reached = (ti < bi)                    # cible avant breach (intraday)
        breached = hit_b.any(axis=1) & ~reached
        # consistance : le jour du pass, le gain du jour ne doit pas exceder consistency * profit total
        passed = reached & (n_days[idx] >= cfg.min_trading_days)

        new = np.zeros(m, dtype=np.int8)
        new[passed] = 1
        new[breached] = -1
        status[idx] = new

        # met a jour equity/peak/best_day pour TOUS (les passes/echecs seront figes au prochain tour)
        eq[idx] = end_eq
        peak[idx] = np.maximum(peak[idx], end_eq)
        best_day[idx] = np.maximum(best_day[idx], day_gain)

    passed_mask = status == 1

    # regle de consistance : si activee, invalide les pass dont un jour porte trop du profit
    if cfg.consistency > 0:
        total_profit = np.maximum(eq - 1.0, 1e-9)
        too_concentrated = best_day > cfg.consistency * total_profit
        passed_mask = passed_mask & ~too_concentrated

    return passed_mask, n_days, best_day


def simulate_funded(n, cfg: ChallengeConfig, mu_t, sigma_t, k, rng):
    """Simule n comptes finances jusqu'a la mort (breach) ou l'horizon.

    Retourne extraction (fraction de compte, AVANT split) par sim.
    """
    eq = np.ones(n)
    peak = np.ones(n)
    alive = np.ones(n, dtype=bool)
    extracted = np.zeros(n)

    for day in range(cfg.funded_horizon_days):
        idx = np.where(alive)[0]
        m = idx.size
        if m == 0:
            break
        z = rng.standard_normal((m, k))
        trades = mu_t + sigma_t * z
        cum = np.cumsum(trades, axis=1)
        s = eq[idx]
        path = s[:, None] + cum

        if cfg.trailing:
            ofloor = peak[idx] - cfg.max_dd
        else:
            ofloor = np.full(m, 1.0 - cfg.max_dd)
        dfloor = s - cfg.daily_dd
        floor = np.maximum(ofloor, dfloor)

        breach = (path < floor[:, None]).any(axis=1)
        end_eq = path[:, -1]
        eq[idx] = end_eq
        peak[idx] = np.maximum(peak[idx], end_eq)

        # payout : retire le profit au-dessus de 1.0, equity revient a 1.0
        if (day + 1) % cfg.payout_days == 0:
            prof = np.maximum(eq[idx] - 1.0, 0.0)
            extracted[idx] += prof
            eq[idx] -= prof
            if cfg.trailing:
                peak[idx] = np.maximum(1.0, eq[idx])  # reset trailing apres retrait (approx)

        # tue les comptes ayant breach ce jour (apres le trading du jour)
        alive[idx[breach]] = False

    return extracted


def ev_ledger(cfg: ChallengeConfig, mu_t, sigma_t, k, n=200_000, seed=0, with_funded=True):
    """Ledger d'EV complet pour un drift mu_t / une sizing (sigma_t, k).

    with_funded=False : saute la simulation du compte finance (504 jours, cher) ;
    utile quand seul P(both) compte (sweep de sizing, canal daily-DD). EV alors
    non significatif (extraction=0) -- ne lire que P1/P2/Pboth dans ce cas.
    """
    rng = np.random.default_rng(seed)
    p1, _, _ = simulate_phase(n, cfg.phases[0], cfg, mu_t, sigma_t, k, rng)
    if len(cfg.phases) > 1:
        p2, _, _ = simulate_phase(n, cfg.phases[1], cfg, mu_t, sigma_t, k, rng)
        P2 = p2.mean()
    else:
        P2 = 1.0  # une seule phase d'evaluation (ex. Topstep)
    P1 = p1.mean()
    Pboth = P1 * P2

    if with_funded:
        ext = simulate_funded(n, cfg, mu_t, sigma_t, k, rng)
        E_ext_dollars = ext.mean() * cfg.account * cfg.split
        P_payout = (ext > 0).mean()
    else:
        E_ext_dollars = 0.0
        P_payout = 0.0

    refund_term = Pboth * P_payout * cfg.refund_frac * cfg.fee
    ev = Pboth * E_ext_dollars + refund_term - cfg.fee

    return {
        "P1": float(P1), "P2": float(P2), "Pboth": float(Pboth),
        "E_ext_dollars": float(E_ext_dollars), "P_payout_funded": float(P_payout),
        "refund_term": float(refund_term), "EV": float(ev),
        "mu_t": float(mu_t), "sigma_t": float(sigma_t), "k": int(k),
    }


def annualized_sharpe(mu_t, sigma_t, k, trading_days=252):
    """Convertit un drift/trade en Sharpe annualise (mu_t par trade, sigma_t par trade)."""
    if sigma_t <= 0:
        return float("nan")
    per_trade_sr = mu_t / sigma_t
    return per_trade_sr * np.sqrt(k * trading_days)


# --------------------------------------------------------------------------
# Pipeline complet par trader + parallelisation CPU
# --------------------------------------------------------------------------

def simulate_pipeline(n, cfg: ChallengeConfig, mu_t, sigma_t, k, rng, with_funded=True):
    """Pipeline complet PAR trader : phase1 -> phase2 -> compte finance.

    Lie les etapes (meme trader), donc retourne la DISTRIBUTION du net $ par achat
    de challenge -> expose mean (=EV) VS mediane (forme loterie, lecon airdrop #14).
    """
    net = np.full(n, -cfg.fee, dtype=np.float64)
    p1, _, _ = simulate_phase(n, cfg.phases[0], cfg, mu_t, sigma_t, k, rng)
    idx1 = np.where(p1)[0]
    if len(cfg.phases) > 1 and idx1.size:
        p2, _, _ = simulate_phase(idx1.size, cfg.phases[1], cfg, mu_t, sigma_t, k, rng)
        funded_idx = idx1[p2]
    else:
        funded_idx = idx1
    n_pay = 0
    if with_funded and funded_idx.size:
        ext = simulate_funded(funded_idx.size, cfg, mu_t, sigma_t, k, rng)
        payout = ext > 0
        n_pay = int(payout.sum())
        gain = ext * cfg.account * cfg.split
        refund = np.where(payout, cfg.refund_frac * cfg.fee, 0.0)
        net[funded_idx] += gain + refund
    return net, int(p1.sum()), int(funded_idx.size), n_pay


def _pipe_worker(args):
    """Worker multiprocessing : un chunk de traders. Retourne (net float32, compteurs)."""
    cfg, mu_t, sigma_t, k, n, seed, with_funded = args
    rng = np.random.default_rng(seed)
    net, n_p1, n_fund, n_pay = simulate_pipeline(n, cfg, mu_t, sigma_t, k, rng, with_funded)
    return net.astype(np.float32), n_p1, n_fund, n_pay, n


def parallel_pipeline(cfg, mu_t, sigma_t, k, n=200_000, seed=0,
                      with_funded=True, pool=None, n_workers=1):
    """Decoupe n traders en chunks parallelises (sims independantes = exact)."""
    if n_workers < 1:
        n_workers = 1
    base = n // n_workers
    sizes = [base + (1 if i < n % n_workers else 0) for i in range(n_workers)]
    args = [(cfg, mu_t, sigma_t, k, s, seed * 131 + i, with_funded)
            for i, s in enumerate(sizes) if s > 0]
    if pool is not None and len(args) > 1:
        parts = pool.map(_pipe_worker, args)
    else:
        parts = [_pipe_worker(a) for a in args]
    nets = np.concatenate([p[0] for p in parts])
    n_p1 = sum(p[1] for p in parts)
    n_fund = sum(p[2] for p in parts)
    n_pay = sum(p[3] for p in parts)
    ntot = sum(p[4] for p in parts)
    return {
        "EV": float(nets.mean()), "median": float(np.median(nets)),
        "p_pos": float((nets > 0).mean()),
        "P1": n_p1 / ntot, "Pboth": n_fund / ntot,
        "P_payout_funded": (n_pay / n_fund) if n_fund else 0.0,
        "sigma_t": float(sigma_t), "k": int(k), "mu_t": float(mu_t), "n": int(ntot),
    }

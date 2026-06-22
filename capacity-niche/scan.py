"""Analyse cross-exchange : net spread exécutable, persistance, buckets liquidité.

Spread round-trip = acheter min(ask) / vendre max(bid) sur venues différentes,
net de 2·fee. Capacité top-of-book = min des qty des 2 jambes (nan si une jambe Gate,
qty inconnue → résolue au /depth). Régime ciblé = persistance sur minutes.
"""
from __future__ import annotations

import json
from pathlib import Path

import data

_SNAP = Path(__file__).parent / "data" / "snapshots"
FEE = 0.001  # 0.10 %/jambe taker (pré-enregistré)

# Filtres de VALIDITÉ données (amendement post-sanity 2026-06-21, principe a priori,
# PAS un seuil de décision). Justif marché : aucun vrai arb cross-venue ne survit à 5 %+
# sur des minutes (serait instantanément pris) → gross>5 % = collision de ticker / quote
# gelée / marché halté. Volume<$1k/24h = marché mort, quote non hittable. Voir SPEC §Amendement.
ARTIFACT_MAX_GROSS = 0.05
MIN_VOL_USD = 1_000.0


def load_snapshots() -> list[dict]:
    snaps = []
    for p in sorted(_SNAP.glob("*.json")):
        try:
            snaps.append(json.loads(p.read_bytes()))
        except Exception:
            pass
    return snaps


def cross(base: str, snap: dict, volmap: dict, fee: float = FEE) -> dict | None:
    """Meilleur cross-venue pour une base sur un snapshot. None si <2 venues ou pas de cross."""
    q = {v: snap[v][base] for v in data.VENUES if base in snap.get(v, {})}
    if len(q) < 2:
        return None
    ask_v = min(q, key=lambda v: q[v]["ask"])
    bid_v = max(q, key=lambda v: q[v]["bid"])
    if ask_v == bid_v:  # best bid & best ask même venue → pas de cross-venue
        return None
    min_ask, max_bid = q[ask_v]["ask"], q[bid_v]["bid"]
    mid = (min_ask + max_bid) / 2
    gross = (max_bid - min_ask) / mid
    if gross > ARTIFACT_MAX_GROSS:  # collision ticker / quote gelée / halt — invalide
        return None
    small_vol = min(volmap.get(ask_v, {}).get(base, 0.0),
                    volmap.get(bid_v, {}).get(base, 0.0))
    if small_vol < MIN_VOL_USD:  # marché mort, quote non hittable
        return None
    net = gross - 2 * fee
    aq, bq = q[ask_v]["askq"], q[bid_v]["bidq"]
    cap_units = min(aq, bq) if (aq > 0 and bq > 0) else float("nan")
    cap_usd = cap_units * mid
    return {"base": base, "ask_v": ask_v, "bid_v": bid_v, "net": net,
            "cap_usd": cap_usd, "small_vol": small_vol, "mid": mid}


def all_bases(snaps: list[dict]) -> set:
    bs = set()
    for s in snaps:
        for v in data.VENUES:
            bs |= set(s.get(v, {}))
    return bs


def persistence(snaps: list[dict], volmap: dict, fee: float = FEE) -> list[dict]:
    """Par base : net moyen (sur apparitions), frac de snapshots avec net>0, capacité médiane."""
    N = len(snaps)
    rows = []
    for base in all_bases(snaps):
        nets, caps, vols = [], [], []
        for s in snaps:
            c = cross(base, s, volmap, fee)
            if c is None:
                continue
            nets.append(c["net"])
            if c["cap_usd"] == c["cap_usd"]:  # not nan
                caps.append(c["cap_usd"])
            vols.append(c["small_vol"])
        if not nets:
            continue
        npos = sum(1 for x in nets if x > 0)
        med_cap = sorted(caps)[len(caps) // 2] if caps else float("nan")
        rows.append({
            "base": base,
            "appear": len(nets),
            "frac_pos": npos / N,           # dénominateur = total snapshots (flicker pénalisé)
            "mean_net": sum(nets) / len(nets),
            "med_net": sorted(nets)[len(nets) // 2],
            "med_cap_usd": med_cap,
            "small_vol": sorted(vols)[len(vols) // 2] if vols else 0.0,
        })
    return rows


def book_capacity_usd(venue: str, base: str, side: str, target_net: float,
                      ref_other: float, fee: float = FEE) -> float:
    """$ exécutable en marchant le carnet jusqu'à ce que le net retombe sous target_net.

    side='ask' (on achète, on marche les asks), ref_other = best bid de l'autre venue (fixe).
    side='bid' (on vend, on marche les bids), ref_other = best ask de l'autre venue (fixe).
    Approx : l'autre jambe est supposée profonde (souvent Binance) ; borne la petite venue.
    """
    d = data.depth(venue, base)
    if not d:
        return 0.0
    levels = d["asks"] if side == "ask" else d["bids"]
    usd = 0.0
    for px, qty in levels:
        if px <= 0 or qty <= 0:
            continue
        if side == "ask":
            mid = (px + ref_other) / 2
            net = (ref_other - px) / mid - 2 * fee
        else:
            mid = (ref_other + px) / 2
            net = (px - ref_other) / mid - 2 * fee
        if net < target_net:
            break
        usd += px * qty
    return usd

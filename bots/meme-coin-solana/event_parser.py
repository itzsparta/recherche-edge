"""Parseur d'événements on-chain pour le tracking des wallets ruggers.

Détecte :
1. Financement de sous-comptes (FUNDING) : transfert de SOL d'un wallet surveillé vers un nouveau wallet.
2. Déploiement de token (CREATE_TOKEN) : instruction Create Pump.fun ou création de pool Raydium par un wallet surveillé.
3. Vente / Retrait massif (DUMP) : dump de supply ou retrait de liquidité par un wallet surveillé.
"""
from dataclasses import dataclass, field
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import core

log = logging.getLogger("event_parser")

PUMPFUN_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
PUMPSWAP_AMM = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
RAYDIUM_LP_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
SYSTEM_PROGRAM = "11111111111111111111111111111111"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
WSOL_MINT = core.WSOL

# Adresses de programmes & comptes système à ignorer pour les détections de sous-comptes
SYSTEM_ACCOUNTS = {
    SYSTEM_PROGRAM,
    TOKEN_PROGRAM,
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
    "SysvarRent111111111111111111111111111111111",
    "SysvarC1ock11111111111111111111111111111111",
    "ComputeBudget111111111111111111111111111111",
    PUMPFUN_PROGRAM,
    PUMPSWAP_AMM,
    RAYDIUM_LP_V4,
    WSOL_MINT,
    "So11111111111111111111111111111111111111111",
}


@dataclass
class OnChainEvent:
    event_type: str  # "FUNDING", "CREATE_TOKEN", "DUMP", "SWAP"
    wallet: str
    target_wallet: Optional[str] = None
    mint: Optional[str] = None
    amount_sol: float = 0.0
    signature: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_bundled: bool = False


def _get_val(obj: Any, attr: str, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def extract_sol_transfers(
    tx_meta: Any,
    account_keys: List[str],
    watched_wallets: Set[str],
    signature: str = "",
    min_funding_sol: float = 0.05,
) -> List[OnChainEvent]:
    """Détecte si un wallet surveillé a transféré des SOL à un autre compte (funding)."""
    events = []
    if not tx_meta or not account_keys:
        return events

    pre_balances = _get_val(tx_meta, "pre_balances") or _get_val(tx_meta, "preBalances") or []
    post_balances = _get_val(tx_meta, "post_balances") or _get_val(tx_meta, "postBalances") or []

    if len(pre_balances) != len(account_keys) or len(post_balances) != len(account_keys):
        return events

    # Vérifie chaque wallet surveillé
    for i, acc in enumerate(account_keys):
        if acc in watched_wallets:
            diff_lamports = pre_balances[i] - post_balances[i]
            # Si le wallet a perdu plus de min_funding_sol (+ prise en compte des frais tx)
            if diff_lamports > int(min_funding_sol * 1e9):
                # Cherche quel autre compte a reçu des SOL
                for j, dest_acc in enumerate(account_keys):
                    if i != j and dest_acc not in SYSTEM_ACCOUNTS:
                        received_lamports = post_balances[j] - pre_balances[j]
                        if received_lamports >= int(min_funding_sol * 1e9):
                            received_sol = received_lamports / 1e9
                            events.append(
                                OnChainEvent(
                                    event_type="FUNDING",
                                    wallet=acc,
                                    target_wallet=dest_acc,
                                    amount_sol=received_sol,
                                    signature=signature,
                                    metadata={"pre_balance_dest": pre_balances[j] / 1e9},
                                )
                            )
    return events


def extract_swap_events(
    tx_meta: Any,
    account_keys: List[str],
    watched_wallets: Set[str],
    signature: str = "",
) -> List[OnChainEvent]:
    """Détecte si un wallet surveillé a swap du SOL contre un Token."""
    events = []
    if not tx_meta or not account_keys:
        return events

    pre_balances = _get_val(tx_meta, "pre_balances") or _get_val(tx_meta, "preBalances") or []
    post_balances = _get_val(tx_meta, "post_balances") or _get_val(tx_meta, "postBalances") or []
    if len(pre_balances) != len(account_keys) or len(post_balances) != len(account_keys):
        return events

    pre_token = _get_val(tx_meta, "pre_token_balances") or _get_val(tx_meta, "preTokenBalances") or []
    post_token = _get_val(tx_meta, "post_token_balances") or _get_val(tx_meta, "postTokenBalances") or []

    def build_token_map(balances):
        res = {}
        for b in balances:
            owner = _get_val(b, "owner")
            mint = str(_get_val(b, "mint") or "")
            ui_token_amt = _get_val(b, "uiTokenAmount") or {}
            amt = float(_get_val(ui_token_amt, "uiAmount") or 0.0)
            if owner and mint:
                res[(owner, mint)] = amt
        return res

    pre_map = build_token_map(pre_token)
    post_map = build_token_map(post_token)

    for i, acc in enumerate(account_keys):
        if acc in watched_wallets:
            diff_sol = (pre_balances[i] - post_balances[i]) / 1e9
            if diff_sol > 0:
                for (owner, mint), post_amt in post_map.items():
                    if owner == acc and mint not in core.QUOTE_MINTS and mint not in SYSTEM_ACCOUNTS:
                        pre_amt = pre_map.get((owner, mint), 0.0)
                        if post_amt > pre_amt:
                            events.append(
                                OnChainEvent(
                                    event_type="SWAP",
                                    wallet=acc,
                                    mint=mint,
                                    amount_sol=diff_sol,
                                    signature=signature,
                                    metadata={"amount_token": post_amt - pre_amt}
                                )
                            )
    return events


def extract_dev_and_bundle_allocation(
    tx_meta: Any,
    account_keys: List[str],
    deployer_address: str,
    target_mint: Optional[str] = None,
) -> Tuple[float, float, bool]:
    """Analyse les post_token_balances du bloc 0 pour évaluer l'allocation du dev et des insiders (bundles).

    Retourne :
        (dev_pct, total_insider_pct, is_bundle_detected)
    """
    if not tx_meta:
        return 0.0, 0.0, False

    balances = _get_val(tx_meta, "post_token_balances") or _get_val(tx_meta, "postTokenBalances") or []
    if not balances:
        return 0.0, 0.0, False

    relevant = []
    for b in balances:
        b_mint = str(_get_val(b, "mint") or "")
        if target_mint:
            if b_mint == target_mint:
                relevant.append(b)
        else:
            if b_mint and b_mint not in core.QUOTE_MINTS:
                relevant.append(b)

    if not relevant:
        return 0.0, 0.0, False

    TOTAL_SUPPLY = 1_000_000_000.0
    dev_tokens = 0.0
    holders = {}

    for b in relevant:
        owner = _get_val(b, "owner")
        if not owner:
            acc_idx = _get_val(b, "account_index") or _get_val(b, "accountIndex")
            if acc_idx is not None and 0 <= acc_idx < len(account_keys):
                owner = account_keys[acc_idx]

        owner_str = str(owner or "")
        ui_amount_info = _get_val(b, "ui_token_amount") or _get_val(b, "uiTokenAmount") or {}
        ui_amount = float(_get_val(ui_amount_info, "ui_amount") or _get_val(ui_amount_info, "uiAmount") or 0.0)

        if ui_amount > 0:
            holders[owner_str] = ui_amount
            if owner_str == deployer_address:
                dev_tokens = ui_amount

    if not holders:
        return 0.0, 0.0, False

    curve_owner = max(holders, key=holders.get)
    non_curve_holders = {k: v for k, v in holders.items() if k != curve_owner or k == deployer_address}

    dev_pct = (dev_tokens / TOTAL_SUPPLY) * 100.0
    total_insider_tokens = sum(non_curve_holders.values())
    total_insider_pct = (total_insider_tokens / TOTAL_SUPPLY) * 100.0
    is_bundle = len(non_curve_holders) > 1

    return dev_pct, total_insider_pct, is_bundle


def extract_token_launches(
    tx_meta: Any,
    account_keys: List[str],
    log_messages: List[str],
    watched_wallets: Optional[Set[str]] = None,
    signature: str = "",
    watch_all_creates: bool = False,
) -> List[OnChainEvent]:
    """Détecte les créations de tokens sur Pump.fun ou Raydium (ciblées ou globales)."""
    events = []
    if not tx_meta:
        return events

    # Vérifie si un des comptes est dans la watchlist ou si écoute globale
    if watch_all_creates:
        deployer = account_keys[0] if account_keys else ""
        involved = [deployer] if deployer else []
    else:
        if not watched_wallets:
            return events
        involved = [acc for acc in account_keys if acc in watched_wallets]

    if not involved:
        return events

    # Vérifie si c'est un create token
    is_create = False
    program_name = "unknown"

    logs_text = " ".join(log_messages or [])
    if "Instruction: Create" in logs_text and PUMPFUN_PROGRAM in account_keys:
        is_create = True
        program_name = "pump.fun"
    elif "CreatePoolEvent" in logs_text and PUMPSWAP_AMM in account_keys:
        is_create = True
        program_name = "pumpswap"
    elif "initialize2" in logs_text and RAYDIUM_LP_V4 in account_keys:
        is_create = True
        program_name = "raydium"

    if not is_create:
        return events

    # Extraction du mint
    post_token_balances = _get_val(tx_meta, "post_token_balances") or _get_val(tx_meta, "postTokenBalances") or []
    mints = []
    for b in post_token_balances:
        mint = _get_val(b, "mint")
        if mint:
            mints.append(str(mint))
    mints = list(dict.fromkeys(mints))
    base_mint = core.select_base_mint(mints)

    deployer_addr = account_keys[0] if account_keys else ""
    dev_pct, insider_pct, is_bundle = extract_dev_and_bundle_allocation(
        tx_meta=tx_meta,
        account_keys=account_keys,
        deployer_address=deployer_addr,
        target_mint=base_mint,
    )

    for target in involved:
        events.append(
            OnChainEvent(
                event_type="CREATE_TOKEN",
                wallet=target,
                mint=base_mint,
                signature=signature,
                metadata={
                    "program": program_name,
                    "account_keys": account_keys,
                    "mints": mints,
                    "dev_allocation_pct": dev_pct,
                    "insider_allocation_pct": insider_pct,
                    "is_bundle": is_bundle,
                },
                is_bundled=is_bundle,
            )
        )
    return events


def parse_transaction_data(
    tx: Any,
    watched_wallets: Set[str],
    min_funding_sol: float = 0.05,
    watch_all_creates: bool = False,
) -> List[OnChainEvent]:
    """Parse une transaction Solana complète et extrait tous les événements pertinents."""
    if not tx:
        return []

    # Extraction sécurisée selon la structure de la réponse RPC (objet ou dict)
    meta = getattr(tx, "meta", None)
    if meta is None and isinstance(tx, dict):
        meta = tx.get("meta")

    tx_value = getattr(tx, "transaction", None)
    if tx_value is None and isinstance(tx, dict):
        tx_value = tx.get("transaction")

    # Clés de comptes
    account_keys = []
    if tx_value:
        msg = getattr(tx_value, "message", None)
        if msg is None and isinstance(tx_value, dict):
            msg = tx_value.get("message")
        if msg:
            if isinstance(msg, dict):
                keys = msg.get("account_keys") or msg.get("accountKeys") or []
            else:
                keys = getattr(msg, "account_keys", []) or []
            if isinstance(keys, list):
                account_keys = [str(k.get("pubkey") if isinstance(k, dict) else k) for k in keys]

    signature = ""
    signatures = getattr(tx_value, "signatures", []) if tx_value and not isinstance(tx_value, dict) else (tx_value.get("signatures", []) if isinstance(tx_value, dict) else [])
    if signatures:
        signature = str(signatures[0])
    elif isinstance(tx, dict) and tx.get("signature"):
        signature = str(tx["signature"])

    log_messages = []
    if meta:
        if isinstance(meta, dict):
            log_messages = meta.get("logMessages") or meta.get("log_messages") or []
        else:
            log_messages = getattr(meta, "log_messages", []) or []

    events = []

    # 1. Analyse des transferts SOL (Funding)
    events.extend(
        extract_sol_transfers(
            tx_meta=meta,
            account_keys=account_keys,
            watched_wallets=watched_wallets,
            signature=signature,
            min_funding_sol=min_funding_sol,
        )
    )

    # 2. Analyse des lancements de token
    events.extend(
        extract_token_launches(
            tx_meta=meta,
            account_keys=account_keys,
            log_messages=log_messages,
            watched_wallets=watched_wallets,
            signature=signature,
            watch_all_creates=watch_all_creates,
        )
    )

    # 3. Analyse des Swaps (Copy-trade Smart Money)
    events.extend(
        extract_swap_events(
            tx_meta=meta,
            account_keys=account_keys,
            watched_wallets=watched_wallets,
            signature=signature,
        )
    )

    return events

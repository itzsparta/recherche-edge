"""Tests unitaires pour event_parser.py."""
from types import SimpleNamespace
import pytest

from event_parser import (
    OnChainEvent,
    extract_sol_transfers,
    extract_token_launches,
    parse_transaction_data,
    PUMPFUN_PROGRAM,
    PUMPSWAP_AMM,
    RAYDIUM_LP_V4,
    SYSTEM_PROGRAM,
)


def test_extract_sol_transfers():
    watched = {"RuggerBoss1111111111111111111111111111111111"}
    fresh_child = "FreshChild2222222222222222222222222222222222"
    system_acc = SYSTEM_PROGRAM

    account_keys = [
        "RuggerBoss1111111111111111111111111111111111",
        fresh_child,
        system_acc,
    ]

    # Pre balances: Boss has 5 SOL, Child has 0 SOL, System has 1 SOL
    # Post balances: Boss has 2.995 SOL (sent 2 SOL + fees), Child has 2.0 SOL
    meta = SimpleNamespace(
        pre_balances=[5_000_000_000, 0, 1_000_000_000],
        post_balances=[2_995_000_000, 2_000_000_000, 1_000_000_000],
    )

    events = extract_sol_transfers(
        tx_meta=meta,
        account_keys=account_keys,
        watched_wallets=watched,
        signature="sig123",
        min_funding_sol=0.1,
    )

    assert len(events) == 1
    ev = events[0]
    assert ev.event_type == "FUNDING"
    assert ev.wallet == "RuggerBoss1111111111111111111111111111111111"
    assert ev.target_wallet == fresh_child
    assert ev.amount_sol == 2.0
    assert ev.signature == "sig123"


def test_extract_sol_transfers_ignores_system_program_and_small_amounts():
    watched = {"RuggerBoss1111111111111111111111111111111111"}
    account_keys = [
        "RuggerBoss1111111111111111111111111111111111",
        SYSTEM_PROGRAM,
    ]
    meta = SimpleNamespace(
        pre_balances=[5_000_000_000, 1_000_000_000],
        post_balances=[4_000_000_000, 2_000_000_000],
    )

    # Transfer to SYSTEM_PROGRAM should not be marked as a child wallet
    events = extract_sol_transfers(
        tx_meta=meta,
        account_keys=account_keys,
        watched_wallets=watched,
        signature="sig1",
    )
    assert len(events) == 0


def test_extract_token_launches_pumpfun():
    watched = {"RuggerDev11111111111111111111111111111111111"}
    token_mint = "ScamTokenMint111111111111111111111111111111"

    account_keys = [
        "RuggerDev11111111111111111111111111111111111",
        PUMPFUN_PROGRAM,
        token_mint,
    ]

    log_messages = [
        "Program 6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P invoke [1]",
        "Program log: Instruction: Create",
        "Program 6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P success",
    ]

    meta = SimpleNamespace(
        post_token_balances=[
            SimpleNamespace(mint=token_mint),
            SimpleNamespace(mint="So11111111111111111111111111111111111111112"),  # WSOL
        ]
    )

    events = extract_token_launches(
        tx_meta=meta,
        account_keys=account_keys,
        log_messages=log_messages,
        watched_wallets=watched,
        signature="sig_launch",
    )

    assert len(events) == 1
    ev = events[0]
    assert ev.event_type == "CREATE_TOKEN"
    assert ev.wallet == "RuggerDev11111111111111111111111111111111111"
    assert ev.mint == token_mint
    assert ev.metadata["program"] == "pump.fun"


def test_parse_transaction_data_dict_format():
    watched = {"WatchedDev11111111111111111111111111111111111"}
    token_mint = "CoinMint111111111111111111111111111111111111"

    tx_dict = {
        "signature": "sig_dict",
        "transaction": {
            "signatures": ["sig_dict"],
            "message": {
                "account_keys": [
                    "WatchedDev11111111111111111111111111111111111",
                    PUMPFUN_PROGRAM,
                ]
            }
        },
        "meta": {
            "pre_balances": [1000, 1000],
            "post_balances": [1000, 1000],
            "logMessages": ["Instruction: Create"],
            "post_token_balances": [
                SimpleNamespace(mint=token_mint)
            ]
        }
    }

    events = parse_transaction_data(tx_dict, watched_wallets=watched)
    assert len(events) == 1
    assert events[0].event_type == "CREATE_TOKEN"
    assert events[0].wallet == "WatchedDev11111111111111111111111111111111111"
    assert events[0].mint == token_mint

def test_extract_token_launches_pumpswap():
    watched = {"RuggerDev11111111111111111111111111111111111"}
    token_mint = "ScamTokenMint111111111111111111111111111111"

    account_keys = [
        "RuggerDev11111111111111111111111111111111111",
        PUMPSWAP_AMM,
        token_mint,
    ]

    log_messages = [
        f"Program {PUMPSWAP_AMM} invoke [1]",
        "Program log: CreatePoolEvent",
        f"Program {PUMPSWAP_AMM} success",
    ]

    meta = SimpleNamespace(
        post_token_balances=[
            SimpleNamespace(mint=token_mint),
            SimpleNamespace(mint="So11111111111111111111111111111111111111112"),  # WSOL
        ]
    )

    events = extract_token_launches(
        tx_meta=meta,
        account_keys=account_keys,
        log_messages=log_messages,
        watched_wallets=watched,
        signature="sig_pumpswap_launch",
    )

    assert len(events) == 1
    ev = events[0]
    assert ev.event_type == "CREATE_TOKEN"
    assert ev.metadata["program"] == "pumpswap"


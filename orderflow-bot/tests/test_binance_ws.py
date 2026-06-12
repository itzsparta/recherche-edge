"""Tests pour binance_ws.ws_url — routing spot vs futures."""
import pytest

from orderflow_bot.ingestion.binance_ws import FUTURES_WS, SPOT_WS, ws_url


def test_ws_url_spot():
    assert ws_url("spot") == SPOT_WS


def test_ws_url_futures():
    assert ws_url("futures") == FUTURES_WS


def test_ws_url_invalid():
    with pytest.raises(ValueError, match="spot|futures"):
        ws_url("perp")  # type: ignore[arg-type]

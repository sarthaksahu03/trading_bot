import pytest
from bot.validators import (
    validate_symbol,
    validate_side,
    validate_type,
    validate_quantity,
    validate_price,
    validate_notional
)

def test_validate_symbol_valid():
    assert validate_symbol("BTCUSDT") == "BTCUSDT"
    assert validate_symbol("ETHUSDT") == "ETHUSDT"

def test_validate_symbol_invalid():
    with pytest.raises(ValueError, match="uppercase"):
        validate_symbol("btcusdt")
    with pytest.raises(ValueError, match="empty"):
        validate_symbol("")
    with pytest.raises(ValueError, match="alphanumeric"):
        validate_symbol("BTC-USDT")

def test_validate_side_valid():
    assert validate_side("BUY") == "BUY"
    assert validate_side("SELL") == "SELL"
    assert validate_side("buy") == "BUY"
    assert validate_side("sell") == "SELL"

def test_validate_side_invalid():
    with pytest.raises(ValueError, match="Side must be 'BUY' or 'SELL'"):
        validate_side("HOLD")

def test_validate_type_valid():
    assert validate_type("LIMIT") == "LIMIT"
    assert validate_type("MARKET") == "MARKET"
    assert validate_type("limit") == "LIMIT"
    assert validate_type("market") == "MARKET"

def test_validate_type_invalid():
    with pytest.raises(ValueError, match="Order type must be 'LIMIT' or 'MARKET'"):
        validate_type("STOP_LOSS")

def test_validate_quantity_valid():
    assert validate_quantity(1) == 1.0
    assert validate_quantity(0.005) == 0.005
    assert validate_quantity("0.1") == 0.1

def test_validate_quantity_invalid():
    with pytest.raises(ValueError, match="positive number"):
        validate_quantity(0)
    with pytest.raises(ValueError, match="positive number"):
        validate_quantity(-1.5)
    with pytest.raises(ValueError, match="valid number"):
        validate_quantity("abc")

def test_validate_price_valid_limit():
    assert validate_price(100.5, "LIMIT") == 100.5
    assert validate_price("20000", "limit") == 20000.0

def test_validate_price_invalid_limit():
    with pytest.raises(ValueError, match="required for LIMIT"):
        validate_price(None, "LIMIT")
    with pytest.raises(ValueError, match="positive number"):
        validate_price(-50, "LIMIT")
    with pytest.raises(ValueError, match="positive number"):
        validate_price(0, "limit")

def test_validate_price_valid_market():
    assert validate_price(None, "MARKET") is None
    assert validate_price(None, "market") is None

def test_validate_price_invalid_market():
    with pytest.raises(ValueError, match="must not be specified for MARKET"):
        validate_price(100.0, "MARKET")


def test_validate_notional_valid():
    symbol_info = {
        "symbol": "BTCUSDT",
        "filters": [
            {"filterType": "MIN_NOTIONAL", "notional": "50"}
        ]
    }
    # Should not raise ValueError
    validate_notional(symbol_info, 0.001, 60000.0)
    validate_notional(symbol_info, 1.0, 50.0)


def test_validate_notional_invalid():
    symbol_info = {
        "symbol": "BTCUSDT",
        "filters": [
            {"filterType": "MIN_NOTIONAL", "notional": "50"}
        ]
    }
    with pytest.raises(ValueError, match="Order notional .* is less than the minimum required notional"):
        validate_notional(symbol_info, 0.0001, 60000.0)

    with pytest.raises(ValueError, match="Order notional .* is less than the minimum required notional"):
        validate_notional(symbol_info, 0.5, 90.0)

import pytest
from unittest.mock import MagicMock
from bot.client import BinanceClient
from bot.orders import place_order, place_market_order, place_limit_order

@pytest.fixture
def mock_client():
    client = MagicMock(spec=BinanceClient)
    client.time_drift = 0
    client._request = MagicMock(return_value={"orderId": 12345, "status": "NEW"})
    
    # Mock dynamic symbol info and ticker price
    client.get_symbol_info = MagicMock(side_effect=lambda symbol: {
        "symbol": symbol,
        "filters": [
            {"filterType": "MIN_NOTIONAL", "notional": "50"}
        ]
    })
    client.get_ticker_price = MagicMock(return_value=60000.0)
    return client

def test_place_market_order_parameters(mock_client):
    response = place_market_order(mock_client, "BTCUSDT", "BUY", 0.005)
    
    assert response == {"orderId": 12345, "status": "NEW"}
    mock_client._request.assert_called_once_with(
        "POST",
        "/fapi/v1/order",
        {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "MARKET",
            "quantity": "0.005"
        },
        signed=True
    )

def test_place_limit_order_parameters(mock_client):
    response = place_limit_order(mock_client, "ETHUSDT", "SELL", 1.2, 3500.5)
    
    assert response == {"orderId": 12345, "status": "NEW"}
    mock_client._request.assert_called_once_with(
        "POST",
        "/fapi/v1/order",
        {
            "symbol": "ETHUSDT",
            "side": "SELL",
            "type": "LIMIT",
            "quantity": "1.2",
            "price": "3500.5",
            "timeInForce": "GTC"
        },
        signed=True
    )

def test_place_order_invalid_inputs(mock_client):
    # Invalid symbol
    with pytest.raises(ValueError, match="uppercase"):
        place_order(mock_client, "btcusdt", "BUY", "MARKET", 0.001)

    # Invalid side
    with pytest.raises(ValueError, match="Side must be 'BUY' or 'SELL'"):
        place_order(mock_client, "BTCUSDT", "HOLD", "MARKET", 0.001)

    # Price provided for MARKET
    with pytest.raises(ValueError, match="Price must not be specified for MARKET"):
        place_order(mock_client, "BTCUSDT", "BUY", "MARKET", 0.001, price=50000.0)

    # Price missing for LIMIT
    with pytest.raises(ValueError, match="Price is required for LIMIT"):
        place_order(mock_client, "BTCUSDT", "BUY", "LIMIT", 0.001, price=None)

    # Negative quantity
    with pytest.raises(ValueError, match="Quantity must be a positive number"):
        place_order(mock_client, "BTCUSDT", "BUY", "MARKET", -0.01)

    # Check client was never called for invalid inputs
    assert mock_client._request.call_count == 0


def test_place_order_notional_validation_market(mock_client):
    # Mock lower price so that 0.0001 * 10,000 = 1 USDT < 50 USDT
    mock_client.get_ticker_price = MagicMock(return_value=10000.0)
    
    with pytest.raises(ValueError, match="Order notional .* is less than the minimum required notional"):
        place_order(mock_client, "BTCUSDT", "BUY", "MARKET", 0.0001)

    assert mock_client._request.call_count == 0


def test_place_order_notional_validation_limit(mock_client):
    # limit price = 10,000 USDT -> 0.001 * 10,000 = 10 USDT < 50 USDT
    with pytest.raises(ValueError, match="Order notional .* is less than the minimum required notional"):
        place_order(mock_client, "BTCUSDT", "BUY", "LIMIT", 0.001, price=10000.0)

    assert mock_client._request.call_count == 0

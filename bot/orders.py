import logging
from typing import Dict, Any
from bot.client import BinanceClient
from bot.validators import (
    validate_symbol,
    validate_side,
    validate_type,
    validate_quantity,
    validate_price,
    validate_notional
)

logger = logging.getLogger(__name__)

def place_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float | None = None,
    time_in_force: str = "GTC"
) -> Dict[str, Any]:
    """
    Validates and places an order on Binance Futures Testnet.
    
    :param client: An instance of BinanceClient.
    :param symbol: Trading symbol (e.g. 'BTCUSDT').
    :param side: 'BUY' or 'SELL'.
    :param order_type: 'MARKET' or 'LIMIT'.
    :param quantity: Quantity to buy or sell.
    :param price: Price for LIMIT orders. Must be None for MARKET.
    :param time_in_force: Time in force policy (default 'GTC'). Used for LIMIT.
    :return: Dict containing the API response.
    """
    # Validate all inputs before sending request
    validated_symbol = validate_symbol(symbol)
    validated_side = validate_side(side)
    validated_type = validate_type(order_type)
    validated_qty = validate_quantity(quantity)
    validated_price = validate_price(price, validated_type)

    logger.info(
        f"Preparing order parameters - Symbol: {validated_symbol}, Side: {validated_side}, "
        f"Type: {validated_type}, Qty: {validated_qty}, Price: {validated_price}"
    )

    # Perform client-side notional value validation
    symbol_info = client.get_symbol_info(validated_symbol)
    if not symbol_info:
        raise ValueError(f"Symbol '{validated_symbol}' not found on Binance Futures.")

    chk_price = validated_price
    if chk_price is None:
        chk_price = client.get_ticker_price(validated_symbol)

    validate_notional(symbol_info, validated_qty, chk_price)

    # Construct the request payload parameters
    params: Dict[str, Any] = {
        "symbol": validated_symbol,
        "side": validated_side,
        "type": validated_type,
        "quantity": str(validated_qty)  # Convert quantity to string to prevent floating-point serialization errors
    }

    if validated_type == "LIMIT":
        params["price"] = str(validated_price)
        params["timeInForce"] = time_in_force

    # Send request through the Binance client
    logger.debug(f"Dispatching order params to client: {params}")
    response = client._request("POST", "/fapi/v1/order", params, signed=True)
    return response


def place_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: float
) -> Dict[str, Any]:
    """
    Helper function to place a MARKET order.
    """
    return place_order(client, symbol, side, "MARKET", quantity)


def place_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    time_in_force: str = "GTC"
) -> Dict[str, Any]:
    """
    Helper function to place a LIMIT order.
    """
    return place_order(client, symbol, side, "LIMIT", quantity, price, time_in_force)

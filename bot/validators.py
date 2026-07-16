def validate_symbol(symbol: str) -> str:
    """
    Validates the symbol is non-empty, uppercase, and alphanumeric.
    """
    if not symbol:
        raise ValueError("Symbol must not be empty.")
    if not isinstance(symbol, str):
        raise ValueError("Symbol must be a string.")
    if not symbol.isupper():
        raise ValueError(f"Symbol '{symbol}' must be uppercase.")
    if not symbol.isalnum():
        raise ValueError(f"Symbol '{symbol}' must be alphanumeric.")
    return symbol


def validate_side(side: str) -> str:
    """
    Validates that the side is either 'BUY' or 'SELL'.
    """
    if not isinstance(side, str):
        raise ValueError("Side must be a string.")
    upper_side = side.upper()
    if upper_side not in ("BUY", "SELL"):
        raise ValueError(f"Side must be 'BUY' or 'SELL'. Got: '{side}'")
    return upper_side


def validate_type(order_type: str) -> str:
    """
    Validates that the order type is either 'LIMIT' or 'MARKET'.
    """
    if not isinstance(order_type, str):
        raise ValueError("Order type must be a string.")
    upper_type = order_type.upper()
    if upper_type not in ("LIMIT", "MARKET"):
        raise ValueError(f"Order type must be 'LIMIT' or 'MARKET'. Got: '{order_type}'")
    return upper_type


def validate_quantity(quantity: float) -> float:
    """
    Validates that quantity is a positive number.
    """
    try:
        qty_val = float(quantity)
    except (ValueError, TypeError):
        raise ValueError(f"Quantity must be a valid number. Got: '{quantity}'")
    
    if qty_val <= 0:
        raise ValueError(f"Quantity must be a positive number. Got: {qty_val}")
    
    return qty_val


def validate_price(price: float | None, order_type: str) -> float | None:
    """
    Validates price based on the order type.
    - If LIMIT, price is required and must be a positive number.
    - If MARKET, price must be None.
    """
    upper_type = validate_type(order_type)

    if upper_type == "LIMIT":
        if price is None:
            raise ValueError("Price is required for LIMIT orders.")
        try:
            price_val = float(price)
        except (ValueError, TypeError):
            raise ValueError(f"Price must be a valid number. Got: '{price}'")
        
        if price_val <= 0:
            raise ValueError(f"Price must be a positive number. Got: {price_val}")
        return price_val

    elif upper_type == "MARKET":
        if price is not None:
            raise ValueError("Price must not be specified for MARKET orders.")
        return None

    return None


def validate_notional(symbol_info: dict, quantity: float, price: float) -> None:
    """
    Validates that the order's notional value is at least the MIN_NOTIONAL value defined by the exchange.
    """
    if not isinstance(symbol_info, dict):
        raise ValueError("Symbol info must be a dictionary.")

    min_notional = None
    for f in symbol_info.get("filters", []):
        if f.get("filterType") == "MIN_NOTIONAL":
            min_notional = float(f.get("notional", 0))
            break
            
    if min_notional is not None:
        notional = quantity * price
        if notional < min_notional:
            symbol = symbol_info.get("symbol", "unknown")
            raise ValueError(
                f"Order notional ({notional:.4f}) is less than the minimum required notional ({min_notional}) "
                f"for symbol {symbol}."
            )

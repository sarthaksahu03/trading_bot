import os
import sys
import logging
import click
from dotenv import load_dotenv

# Ensure we can import from bot package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.logging_config import setup_logging
from bot.client import BinanceClient, BinanceAPIError
from bot.orders import place_order
from bot.validators import (
    validate_symbol,
    validate_side,
    validate_type,
    validate_quantity,
    validate_price
)

# Initialize logger (gets overridden in main after loading API keys for redaction)
logger = logging.getLogger("trading_bot_cli")

@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option("--symbol", required=True, help="Trading symbol (e.g. BTCUSDT). Must be uppercase alphanumeric.")
@click.option("--side", required=True, type=click.Choice(["BUY", "SELL", "buy", "sell"], case_sensitive=False), help="Order side (BUY/SELL).")
@click.option("--type", "order_type", required=True, type=click.Choice(["MARKET", "LIMIT", "market", "limit"], case_sensitive=False), help="Order type (MARKET/LIMIT).")
@click.option("--quantity", required=True, type=float, help="Order quantity. Must be positive.")
@click.option("--price", type=float, default=None, help="Limit price. Required for LIMIT, must be omitted for MARKET.")
def main(symbol: str, side: str, order_type: str, quantity: float, price: float | None):
    """
    Binance Futures Testnet Trading Bot CLI.
    Places MARKET or LIMIT orders on Binance Futures Testnet securely.
    """
    # 1. Load environment variables
    load_dotenv()
    
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")

    # 2. Setup Centralized Logging with redaction filter using loaded keys
    global logger
    setup_logging(api_key=api_key, api_secret=api_secret)
    logger = logging.getLogger("trading_bot_cli")

    logger.info("CLI invoked with parameters: symbol=%s, side=%s, type=%s, quantity=%s, price=%s",
                symbol, side, order_type, quantity, price)

    # 3. Pre-flight Validation
    try:
        symbol = validate_symbol(symbol)
        side = validate_side(side)
        order_type = validate_type(order_type)
        quantity = validate_quantity(quantity)
        price = validate_price(price, order_type)
    except ValueError as e:
        click.secho(f"\n[Validation Error] {e}", fg="red", err=True)
        logger.error(f"Pre-flight validation failed: {e}")
        click.secho("----------------------------------------", fg="yellow")
        click.secho("FAILURE: Order was not placed.", fg="red", bold=True)
        sys.exit(1)

    # 4. Display Order Summary
    click.secho("\n========================================", fg="cyan", bold=True)
    click.secho("        ORDER REQUEST SUMMARY", fg="cyan", bold=True)
    click.secho("========================================", fg="cyan")
    click.echo(f"  Symbol:      {symbol}")
    click.echo(f"  Side:        {side}")
    click.echo(f"  Type:        {order_type}")
    click.echo(f"  Quantity:    {quantity}")
    if price is not None:
        click.echo(f"  Price:       {price}")
    click.secho("========================================", fg="cyan")

    # 5. Interactive Confirmation (Bonus Feature - Enhanced CLI UX)
    confirm_msg = f"Are you sure you want to place this {side} order for {quantity} {symbol}?"
    if not click.confirm(click.style(confirm_msg, fg="yellow", bold=True), default=False):
        click.secho("\nOrder placement cancelled by user.", fg="magenta")
        logger.info("Order placement cancelled by user at confirmation prompt.")
        click.secho("----------------------------------------", fg="yellow")
        click.secho("FAILURE: Order cancelled.", fg="red", bold=True)
        sys.exit(0)

    # 6. Initialize Client & Execute Order
    try:
        if not api_key or not api_secret:
            raise ValueError(
                "Binance API credentials missing from environment. "
                "Please configure BINANCE_API_KEY and BINANCE_API_SECRET in your .env file."
            )

        client = BinanceClient(api_key=api_key, api_secret=api_secret)
        
        click.secho("\nSubmitting order to Binance Futures Testnet...", fg="cyan")
        response = place_order(
            client=client,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price
        )

        # 7. Print Response Details
        click.secho("\n========================================", fg="green", bold=True)
        click.secho("        ORDER RESPONSE DETAILS", fg="green", bold=True)
        click.secho("========================================", fg="green")
        click.echo(f"  Order ID:     {response.get('orderId')}")
        click.echo(f"  Status:       {response.get('status')}")
        click.echo(f"  Executed Qty: {response.get('executedQty')}")
        click.echo(f"  Avg Price:    {response.get('avgPrice', 'N/A')} USDT")
        click.echo(f"  Type:         {response.get('type')}")
        click.echo(f"  Side:         {response.get('side')}")
        click.secho("========================================", fg="green")
        
        logger.info("Order successfully placed. ID: %s, Status: %s", response.get('orderId'), response.get('status'))
        
        click.secho("\nSUCCESS: Order placed successfully.", fg="green", bold=True)

    except BinanceAPIError as e:
        # Handled API failure (e.g. insufficient funds, bad price filter)
        click.secho(f"\n[Binance API Error] Code {e.error_code}: {e.message}", fg="red", err=True)
        logger.error(f"Binance API Error occurred during order placement: {e}")
        click.secho("----------------------------------------", fg="yellow")
        click.secho("FAILURE: Order rejected by server.", fg="red", bold=True)
        sys.exit(1)

    except Exception as e:
        # Unexpected errors (network connection, parsing, etc)
        click.secho(f"\n[Unexpected Error] {e}", fg="red", err=True)
        # Log the full exception with traceback to the log file for developers
        logger.exception("An unexpected error occurred during execution:")
        click.secho("----------------------------------------", fg="yellow")
        click.secho("FAILURE: Request failed due to unexpected error.", fg="red", bold=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

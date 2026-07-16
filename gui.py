import os
import sys
import logging
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk
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

# Global Logger instance
logger = logging.getLogger("trading_bot_gui")

class TradingBotGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Binance Futures Testnet Trading Bot")
        self.root.geometry("950x650")
        self.root.minsize(850, 550)
        self.root.configure(bg="#121214")

        # Load env keys for logger setup and clients
        load_dotenv()
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.api_secret = os.getenv("BINANCE_API_SECRET")

        setup_logging(api_key=self.api_key, api_secret=self.api_secret)
        global logger
        logger = logging.getLogger("trading_bot_gui")
        logger.info("GUI application starting...")

        # Setup custom dark themes/styles for TTK
        self._setup_styles()

        # Build GUI Layout
        self._create_widgets()

        # Automatically trigger the first trace on order type to set Price visibility
        self._on_type_change()

    def _setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Color palette
        self.bg_main = "#121214"
        self.bg_card = "#1C1D21"
        self.text_light = "#E4E6EB"
        self.text_dark = "#121214"
        self.accent_blue = "#00B4D8"
        self.accent_green = "#10B981"
        self.accent_red = "#EF4444"
        self.border_color = "#2D3139"

        # Frame styles
        self.style.configure("TFrame", background=self.bg_main)
        self.style.configure("Card.TFrame", background=self.bg_card, relief="flat")
        
        # Label styles
        self.style.configure("TLabel", background=self.bg_main, foreground=self.text_light, font=("Segoe UI", 10))
        self.style.configure("CardLabel.TLabel", background=self.bg_card, foreground=self.text_light, font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", background=self.bg_card, foreground=self.accent_blue, font=("Segoe UI", 12, "bold"))
        self.style.configure("Title.TLabel", background=self.bg_main, foreground=self.accent_blue, font=("Segoe UI", 16, "bold"))
        self.style.configure("Status.TLabel", background=self.bg_main, foreground=self.accent_blue, font=("Segoe UI", 10, "italic"))
        self.style.configure("Error.TLabel", background=self.bg_main, foreground=self.accent_red, font=("Segoe UI", 10, "bold"))

        # Treeview styling (Order History)
        self.style.configure("Treeview", 
                             background=self.bg_card, 
                             foreground=self.text_light, 
                             fieldbackground=self.bg_card, 
                             rowheight=24,
                             font=("Segoe UI", 9))
        self.style.configure("Treeview.Heading", 
                             background="#2A2B30", 
                             foreground=self.text_light, 
                             font=("Segoe UI", 9, "bold"))
        self.style.map("Treeview.Heading", background=[("active", "#3A3B40")])
        self.style.map("Treeview", background=[("selected", "#00B4D8")], foreground=[("selected", self.text_dark)])

    def _create_widgets(self):
        # 1. Main container with grid
        main_container = ttk.Frame(self.root, style="TFrame", padding=15)
        main_container.pack(fill="both", expand=True)

        # Title Row
        title_label = ttk.Label(main_container, text="BINANCE FUTURES DEMO TRADING BOT", style="Title.TLabel")
        title_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))

        # 2. Left Frame - Order Form
        form_card = ttk.Frame(main_container, style="Card.TFrame", padding=20)
        form_card.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=1)

        # Header
        form_title = ttk.Label(form_card, text="PLACE NEW ORDER", style="Header.TLabel")
        form_title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))

        # Symbol Input
        ttk.Label(form_card, text="Trading Symbol:", style="CardLabel.TLabel").grid(row=1, column=0, sticky="w", pady=6)
        self.symbol_var = tk.StringVar(value="BTCUSDT")
        self.symbol_entry = tk.Entry(form_card, textvariable=self.symbol_var, bg="#2A2B30", fg=self.text_light, 
                                     insertbackground=self.text_light, relief="flat", bd=5, font=("Segoe UI", 10, "bold"))
        self.symbol_entry.grid(row=1, column=1, sticky="ew", pady=6, padx=(10, 0))
        # Autocomplete uppercase
        self.symbol_var.trace_add("write", lambda *args: self.symbol_var.set(self.symbol_var.get().upper()))

        # Side Selection (BUY / SELL dropdown)
        ttk.Label(form_card, text="Order Side:", style="CardLabel.TLabel").grid(row=2, column=0, sticky="w", pady=6)
        self.side_var = tk.StringVar(value="BUY")
        self.side_combo = ttk.Combobox(form_card, textvariable=self.side_var, values=["BUY", "SELL"], state="readonly", font=("Segoe UI", 10))
        self.side_combo.grid(row=2, column=1, sticky="ew", pady=6, padx=(10, 0))

        # Order Type (MARKET / LIMIT dropdown)
        ttk.Label(form_card, text="Order Type:", style="CardLabel.TLabel").grid(row=3, column=0, sticky="w", pady=6)
        self.type_var = tk.StringVar(value="MARKET")
        self.type_combo = ttk.Combobox(form_card, textvariable=self.type_var, values=["MARKET", "LIMIT"], state="readonly", font=("Segoe UI", 10))
        self.type_combo.grid(row=3, column=1, sticky="ew", pady=6, padx=(10, 0))
        self.type_var.trace_add("write", self._on_type_change)

        # Quantity Input
        ttk.Label(form_card, text="Quantity:", style="CardLabel.TLabel").grid(row=4, column=0, sticky="w", pady=6)
        self.qty_var = tk.StringVar(value="0.001")
        self.qty_entry = tk.Entry(form_card, textvariable=self.qty_var, bg="#2A2B30", fg=self.text_light, 
                                   insertbackground=self.text_light, relief="flat", bd=5, font=("Segoe UI", 10))
        self.qty_entry.grid(row=4, column=1, sticky="ew", pady=6, padx=(10, 0))

        # Price Input (will show/hide dynamically)
        self.price_label = ttk.Label(form_card, text="Limit Price (USDT):", style="CardLabel.TLabel")
        self.price_var = tk.StringVar(value="")
        self.price_entry = tk.Entry(form_card, textvariable=self.price_var, bg="#2A2B30", fg=self.text_light, 
                                     insertbackground=self.text_light, relief="flat", bd=5, font=("Segoe UI", 10))

        # Row 5 slots for Price, handled dynamically
        
        # Form Validation Status Label
        self.validation_label = ttk.Label(form_card, text="", style="Error.TLabel", wraplength=250)
        self.validation_label.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(10, 5))

        # Submit Button (Placed inside a separate container so we can colorize/flat style it)
        self.submit_btn = tk.Button(form_card, text="PLACE FUTURES ORDER", command=self.on_place_order, 
                                    bg=self.accent_blue, fg="#FFFFFF", activebackground="#0096B4", 
                                    activeforeground="#FFFFFF", font=("Segoe UI", 11, "bold"), 
                                    relief="flat", cursor="hand2", bd=0, pady=8)
        self.submit_btn.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        form_card.columnconfigure(1, weight=1)

        # 3. Right Frame - Results Display
        self.result_card = ttk.Frame(main_container, style="Card.TFrame", padding=20)
        self.result_card.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=(0, 10))
        main_container.columnconfigure(1, weight=1)

        result_title = ttk.Label(self.result_card, text="EXECUTION RESULT", style="Header.TLabel")
        result_title.pack(anchor="w", pady=(0, 15))

        # Text widget for result outputs
        self.result_text = tk.Text(self.result_card, bg="#121214", fg=self.text_light, relief="flat", 
                                   font=("Consolas", 10), state="disabled", wrap="word", borderwidth=5)
        self.result_text.pack(fill="both", expand=True)

        # 4. Bottom Frame - Order History (Takes up full width below both panels)
        history_frame = ttk.Frame(main_container, style="TFrame")
        history_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        main_container.rowconfigure(2, weight=1)

        history_title = ttk.Label(history_frame, text="SESSION ORDER HISTORY", style="TLabel", font=("Segoe UI", 10, "bold"))
        history_title.pack(anchor="w", pady=(5, 5))

        # Treeview Scrollbar
        scroll = ttk.Scrollbar(history_frame)
        scroll.pack(side="right", fill="y")

        # Treeview (Table)
        self.history_tree = ttk.Treeview(history_frame, columns=("Time", "Symbol", "Side", "Type", "Qty", "Price", "Status", "OrderID"), 
                                         show="headings", yscrollcommand=scroll.set)
        
        self.history_tree.heading("Time", text="Time")
        self.history_tree.heading("Symbol", text="Symbol")
        self.history_tree.heading("Side", text="Side")
        self.history_tree.heading("Type", text="Type")
        self.history_tree.heading("Qty", text="Qty")
        self.history_tree.heading("Price", text="Price")
        self.history_tree.heading("Status", text="Status")
        self.history_tree.heading("OrderID", text="Order ID")

        self.history_tree.column("Time", width=130, anchor="center")
        self.history_tree.column("Symbol", width=90, anchor="center")
        self.history_tree.column("Side", width=80, anchor="center")
        self.history_tree.column("Type", width=85, anchor="center")
        self.history_tree.column("Qty", width=80, anchor="center")
        self.history_tree.column("Price", width=95, anchor="center")
        self.history_tree.column("Status", width=90, anchor="center")
        self.history_tree.column("OrderID", width=110, anchor="center")

        self.history_tree.pack(fill="both", expand=True)
        scroll.config(command=self.history_tree.yview())

    def _on_type_change(self, *args):
        order_type = self.type_var.get()
        if order_type == "LIMIT":
            # Show and enable price entry
            self.price_label.grid(row=5, column=0, sticky="w", pady=6)
            self.price_entry.grid(row=5, column=1, sticky="ew", pady=6, padx=(10, 0))
            self.price_entry.config(state="normal")
            if not self.price_var.get():
                self.price_var.set("65000") # default helpful placeholder
        else:
            # Hide and disable price entry
            self.price_entry.config(state="disabled")
            self.price_label.grid_remove()
            self.price_entry.grid_remove()
            self.price_var.set("") # clear value

    def on_place_order(self):
        # 1. Reset Status Area
        self.validation_label.config(text="")
        
        # 2. Get Fields
        symbol = self.symbol_var.get().strip()
        side = self.side_var.get()
        order_type = self.type_var.get()
        qty_str = self.qty_var.get().strip()
        price_str = self.price_var.get().strip()

        price = None
        if order_type == "LIMIT":
            price = price_str

        # 3. Pre-flight Validation (reusing bot/validators.py rules)
        try:
            val_symbol = validate_symbol(symbol)
            val_side = validate_side(side)
            val_type = validate_type(order_type)
            val_qty = validate_quantity(qty_str)
            val_price = validate_price(price, val_type)
        except ValueError as e:
            logger.warning(f"GUI Pre-flight validation error: {e}")
            self.validation_label.config(text=f"Error: {e}")
            return

        # 4. Confirm credentials exist before spawning thread
        if not self.api_key or not self.api_secret:
            error_msg = "Binance API Keys not found. Please set them in your .env file."
            logger.error(error_msg)
            self.validation_label.config(text=error_msg)
            return

        # 5. Disable inputs and submit button, show placing status
        self._toggle_form_state("disabled")
        self._set_result_display("Placing order...", is_loading=True)

        # 6. Execute in background Thread to keep Tkinter main loop responsive
        thread = threading.Thread(
            target=self._order_execution_worker,
            args=(val_symbol, val_side, val_type, val_qty, val_price),
            daemon=True
        )
        thread.start()

    def _toggle_form_state(self, state: str):
        # state is 'normal' or 'disabled'
        self.symbol_entry.config(state=state)
        self.side_combo.config(state="readonly" if state == "normal" else state)
        self.type_combo.config(state="readonly" if state == "normal" else state)
        self.qty_entry.config(state=state)
        if self.type_var.get() == "LIMIT":
            self.price_entry.config(state=state)
        
        if state == "disabled":
            self.submit_btn.config(state="disabled", bg="#4B5563", text="PLACING ORDER...")
        else:
            self.submit_btn.config(state="normal", bg=self.accent_blue, text="PLACE FUTURES ORDER")

    def _set_result_display(self, text: str, is_loading: bool = False, is_success: bool = False, is_failure: bool = False):
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", text)
        
        # Style formatting tags
        self.result_text.tag_config("loading", foreground=self.accent_blue, font=("Segoe UI", 11, "italic"))
        self.result_text.tag_config("success_hdr", foreground=self.accent_green, font=("Consolas", 11, "bold"))
        self.result_text.tag_config("failure_hdr", foreground=self.accent_red, font=("Consolas", 11, "bold"))
        self.result_text.tag_config("body", foreground=self.text_light, font=("Consolas", 9))

        if is_loading:
            self.result_text.tag_add("loading", "1.0", tk.END)
        elif is_success:
            # Highlight first line as success
            self.result_text.tag_add("success_hdr", "1.0", "3.0")
            self.result_text.tag_add("body", "3.0", tk.END)
        elif is_failure:
            # Highlight first line as failure
            self.result_text.tag_add("failure_hdr", "1.0", "3.0")
            self.result_text.tag_add("body", "3.0", tk.END)

        self.result_text.config(state="disabled")

    def _order_execution_worker(self, symbol: str, side: str, order_type: str, qty: float, price: float | None):
        """
        Runs on background thread. Places the order on Binance Futures Testnet.
        """
        logger.info(f"Background thread starting order placement: {side} {qty} {symbol} @ {order_type}")
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            client = BinanceClient(api_key=self.api_key, api_secret=self.api_secret)
            response = place_order(
                client=client,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=qty,
                price=price
            )
            # Success callback on main GUI thread
            self.root.after(0, self._on_execution_success, response, qty, timestamp_str)
        except BinanceAPIError as e:
            # Server side rejection
            logger.error(f"Binance API Exception during GUI execution: {e}")
            err_msg = f"Binance Server Error Code {e.error_code}\n{e.message}"
            self.root.after(0, self._on_execution_failure, err_msg, symbol, side, order_type, qty, price, timestamp_str)
        except ValueError as e:
            # Client-side validation failure (e.g. notional filter)
            logger.warning(f"Validation error during GUI execution: {e}")
            err_msg = f"Validation Error:\n{e}"
            self.root.after(0, self._on_execution_failure, err_msg, symbol, side, order_type, qty, price, timestamp_str)
        except Exception as e:
            # Unexpected network exception or client error
            logger.exception("Unexpected error in GUI thread order execution:")
            err_msg = f"Request Failed: Network error or bad configuration.\nDetails: {e}"
            self.root.after(0, self._on_execution_failure, err_msg, symbol, side, order_type, qty, price, timestamp_str)

    def _on_execution_success(self, response: dict, qty: float, timestamp_str: str):
        # 1. Re-enable form controls
        self._toggle_form_state("normal")

        # 2. Format details output
        order_id = response.get("orderId", "N/A")
        status = response.get("status", "NEW")
        executed_qty = response.get("executedQty", "0.0")
        avg_price = response.get("avgPrice", "N/A")
        side = response.get("side", "BUY")
        symbol = response.get("symbol", "N/A")
        order_type = response.get("type", "MARKET")
        price = response.get("price", "N/A")

        result_txt = (
            f"=== SUCCESS: ORDER PLACED SUCCESSFULLY ===\n\n"
            f"Order ID:     {order_id}\n"
            f"Status:       {status}\n"
            f"Executed Qty: {executed_qty}\n"
            f"Avg Price:    {avg_price} USDT\n"
            f"Symbol:       {symbol}\n"
            f"Side:         {side}\n"
            f"Type:         {order_type}\n"
            f"Price:        {price} USDT\n"
        )
        self._set_result_display(result_txt, is_success=True)

        # 3. Add to Session Order History Treeview (most recent first)
        display_price = price if order_type == "LIMIT" else "MARKET"
        self.history_tree.insert("", 0, values=(
            timestamp_str,
            symbol,
            side,
            order_type,
            f"{qty_to_float_str(qty)}",
            f"{display_price}",
            "SUCCESS",
            order_id
        ))

    def _on_execution_failure(self, err_msg: str, symbol: str, side: str, order_type: str, qty: float, price: float | None, timestamp_str: str):
        # 1. Re-enable form controls
        self._toggle_form_state("normal")

        # 2. Format details output
        result_txt = (
            f"=== FAILURE: ORDER PLACEMENT REJECTED ===\n\n"
            f"Error Details:\n{err_msg}\n\n"
            f"Attempted Request Details:\n"
            f"Symbol:   {symbol}\n"
            f"Side:     {side}\n"
            f"Type:     {order_type}\n"
            f"Quantity: {qty}\n"
            f"Price:    {price if price is not None else 'N/A'}\n"
        )
        self._set_result_display(result_txt, is_failure=True)

        # 3. Add to Session Order History Treeview as FAILURE
        display_price = f"{price}" if order_type == "LIMIT" else "MARKET"
        self.history_tree.insert("", 0, values=(
            timestamp_str,
            symbol,
            side,
            order_type,
            f"{qty}",
            f"{display_price}",
            "FAILED",
            "N/A"
        ))

def qty_to_float_str(val) -> str:
    try:
        return f"{float(val):.4f}".rstrip("0").rstrip(".")
    except (ValueError, TypeError):
        return str(val)

def main():
    root = tk.Tk()
    app = TradingBotGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()

"""
Main GUI Window
CustomTkinter-based interface for the IG trading bot with modern UI
"""

from concurrent.futures import thread
from api.market_scanner import CachedMarketScanner
import customtkinter as ctk
from tkinter import scrolledtext, messagebox, simpledialog
import tkinter as tk 
import threading
import time

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")  # "dark" or "light"
ctk.set_default_color_theme("blue")  # We'll override with Polaris colors


class ToggleSwitch(ctk.CTkCanvas):
    """Toggle switch - Green=ON, Red=OFF"""

    def __init__(self, parent, initial_state=False, callback=None, **kwargs):
        super().__init__(parent, width=50, height=24,
                         highlightthickness=0, bg=kwargs.get('bg', '#252a31'))
        self.callback = callback
        self.state = initial_state
        self.color_on = '#00d084'  # Polaris success green
        self.color_off = '#ed6347'  # Polaris danger red

        self.bg_rect = self.create_rectangle(
            0, 0, 50, 24, fill=self.color_off, outline='', tags='bg')
        self.knob = self.create_oval(
            2, 2, 22, 22, fill='#ffffff', outline='', tags='knob')

        self.bind('<Button-1>', lambda e: self.toggle())
        self.set_state(initial_state)
        self.market_details_cache = {}

    def toggle(self):
        self.set_state(not self.state)
        if self.callback:
            self.callback(self.state)

    def set_state(self, state):
        self.state = state
        self.itemconfig('bg', fill=self.color_on if state else self.color_off)
        x = 26 if state else 2
        self.coords('knob', x, 2, x+20, 22)

    def get(self):
        return self.state

class MainWindow:
    """Main GUI window for trading bot"""
    def __init__(self, config, ig_client, ladder_strategy, auto_strategy, risk_manager):
        self.config = config
        self.ig_client = ig_client
        self.cached_scanner = CachedMarketScanner(ig_client)
        self.ladder_strategy = ladder_strategy
        self.auto_strategy = auto_strategy
        self.risk_manager = risk_manager
        self.root = None
        self.auto_trading = False
        self.market_details_cache = {} 

    def on_limit_toggled(self, state):
        """Handle limit toggle"""
        if hasattr(self.ladder_strategy, 'placed_orders') and self.ladder_strategy.placed_orders:
            self.log(
                f"{'Adding' if state else 'Removing'} limits on existing orders...")
            # Run in background
            threading.Thread(target=self.ladder_strategy.toggle_limits,
                             args=(state, float(
                                 self.limit_distance_var.get()), self.log),
                             daemon=True).start()
        else:
            self.log(
                f"Limits: {'ON' if state else 'OFF'} - will apply to new orders")

    def on_trailing_toggled(self, state):
        """Handle trailing toggle with configuration"""
        if state:
            try:
                # Get configuration values
                min_move = float(self.trailing_min_move_var.get())
                check_interval = int(self.trailing_check_interval_var.get())
                
                self.log(f"Trailing enabled - min move: {min_move} pts, check every {check_interval}s")
                self.ladder_strategy.start_trailing(self.log, min_move, check_interval)
            except ValueError as e:
                self.log(f"Invalid trailing configuration: {e}")
                self.trailing_toggle.set_state(False)
        else:
            self.log("Trailing stopped")
            self.ladder_strategy.stop_trailing()

    def create_gui(self):
            """Create the GUI with CustomTkinter and Polaris theme"""
            self.root = ctk.CTk()
            self.root.title("Rob's Trading Bot")
            self.root.geometry("1400x900")
            self.root.minsize(1200, 700)   

            # Variables
            self.use_risk_management = ctk.BooleanVar(value=False)
            self.use_limit_orders = ctk.BooleanVar(value=True)
            self.use_auto_replace = ctk.BooleanVar(value=False)
            self.use_trailing_stops = ctk.BooleanVar(value=False)
            self.stop_distance_var = ctk.StringVar(value="20")
            self.use_guaranteed_stops = ctk.BooleanVar(value=False)

            # Polaris UI Theme colors
            bg_dark = "#1e2228"
            card_bg = "#252a31"
            accent_teal = "#5aa89a"
            success_green = "#00d084"
            danger_red = "#b76e5f"
            text_white = "#f4f5f7"
            text_gray = "#9fa6b2"

            # Configure main window
            self.root.configure(fg_color=bg_dark)

            # Header
            header_frame = ctk.CTkFrame(self.root, fg_color=bg_dark, corner_radius=0)
            header_frame.pack(fill="x", pady=10, padx=15)

            title_label = ctk.CTkLabel(
                header_frame, 
                text="Rob's Trading Bot",
                font=("Segoe UI", 16, "bold"),
                text_color=accent_teal
            )
            title_label.pack(side="left", padx=10)

            # Margin display
            self.margin_var = ctk.StringVar(value="Margin: --")
            self.margin_label = ctk.CTkLabel(
                header_frame, 
                textvariable=self.margin_var,
                font=("Segoe UI", 11),
                text_color=accent_teal
            )
            self.margin_label.pack(side="left", padx=30)

            # Emergency stop button
            self.panic_btn = ctk.CTkButton(
                header_frame,
                text="⚠ EMERGENCY STOP",
                command=self.on_panic,
                fg_color="#de3618",
                hover_color="#ee4626",
                font=("Segoe UI", 11, "bold"),
                corner_radius=8,
                width=180,
                height=40
            )
            self.panic_btn.pack(side="right", padx=10)

            # Notebook (Tabview in CustomTkinter)
            self.notebook = ctk.CTkTabview(self.root, fg_color=card_bg, corner_radius=10)
            self.notebook.pack(expand=True, fill="both", padx=15, pady=5)

            # Create tabs
            self.notebook.add("Connection")
            self.notebook.add("Trading")
            self.notebook.add("Risk Management")
            self.notebook.add("Configuration")
            self.notebook.add("Market Research")

            # Create tab contents
            self.create_connection_tab(self.notebook.tab("Connection"))
            self.create_trading_tab(self.notebook.tab("Trading"))
            self.create_risk_tab(self.notebook.tab("Risk Management"))
            self.create_config_tab(self.notebook.tab("Configuration"))
            self.create_market_research_tab(self.notebook.tab("Market Research"))

            # Bottom section - split into two columns
            bottom_frame = ctk.CTkFrame(self.root, fg_color=bg_dark, corner_radius=0)
            bottom_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

            # Left column - Order Management
            left_col = ctk.CTkFrame(bottom_frame, fg_color=bg_dark, width=700, corner_radius=0)
            left_col.pack(side="left", fill="both", expand=False, padx=(0, 7))
            left_col.pack_propagate(False)

            # Right column - Activity Log
            right_col = ctk.CTkFrame(bottom_frame, fg_color=bg_dark, corner_radius=0)
            right_col.pack(side="right", fill="both", expand=True, padx=(7, 0))

            # Activity Log (right column)
            log_frame = ctk.CTkFrame(right_col, fg_color=card_bg, corner_radius=10)
            log_frame.pack(fill="both", expand=True)
            
            log_title = ctk.CTkLabel(
                log_frame, 
                text="Activity Log",
                font=("Segoe UI", 12, "bold"),
                text_color=text_white
            )
            log_title.pack(pady=(10, 5), padx=10, anchor="w")

            self.log_text = scrolledtext.ScrolledText(
                log_frame,
                width=50,
                height=15,
                bg=card_bg,
                fg=text_white,
                font=("Consolas", 9, "bold"),
                relief="flat",
                borderwidth=0,
                insertbackground=accent_teal,
            )
            self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

            # Store left_col for use in trading tab
            self.bottom_left_col = left_col

            # Create Order Management in the left column
            orders_frame = ctk.CTkFrame(left_col, fg_color=card_bg, corner_radius=10)
            orders_frame.pack(fill="both", expand=True, padx=5, pady=5)
            
            orders_title = ctk.CTkLabel(
                orders_frame,
                text="Order Management",
                font=("Segoe UI", 12, "bold"),
                text_color=text_white
            )
            orders_title.pack(pady=(10, 5), padx=10, anchor="w")

            # Button frame
            btn_frame = ctk.CTkFrame(orders_frame, fg_color=card_bg, corner_radius=0)
            btn_frame.pack(fill="x", pady=5, padx=10)

            buttons = [
                ("Refresh", self.on_refresh_orders, accent_teal),
                ("Cancel Orders", self.on_cancel_all_orders, danger_red),
                ("Close Positions", self.on_close_positions, danger_red),
                ("Search Markets", self.on_search_markets, text_gray),
            ]

            for text, cmd, color in buttons:
                ctk.CTkButton(
                    btn_frame, 
                    text=text, 
                    command=cmd,
                    fg_color=color,
                    hover_color=color,
                    corner_radius=8,
                    width=110,
                    height=32,
                    font=("Segoe UI", 12, "bold")
                ).pack(side="left", padx=4)

            # Orders display area
            self.orders_text = scrolledtext.ScrolledText(
                orders_frame,
                width=60,
                height=15,
                bg=card_bg,
                fg=text_white,
                font=("Consolas", 9),
                relief="flat",
                borderwidth=0,
                insertbackground=accent_teal,
            )
            self.orders_text.pack(fill="both", expand=True, padx=10, pady=(5, 10))
            
    def create_connection_tab(self, parent):
            """Create connection tab contents"""
            # Polaris colors
            card_bg = "#252a31"
            accent_teal = "#5aa89a"
            text_white = "#f4f5f8"
            success_green = "#00d084"
            
            center_frame = ctk.CTkFrame(parent, fg_color="transparent")
            center_frame.pack(expand=True)

            status_frame = ctk.CTkFrame(center_frame, fg_color=card_bg, corner_radius=15)
            status_frame.pack(pady=20, padx=20)

            # Account Type selection
            account_label = ctk.CTkLabel(
                status_frame,
                text="Account Type:",
                font=("Segoe UI", 11, "bold"),
                text_color=text_white
            )
            account_label.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))

            self.account_var = ctk.StringVar(value="DEMO")

            radio_frame = ctk.CTkFrame(status_frame, fg_color=card_bg)
            radio_frame.grid(row=0, column=1, columnspan=2, sticky="w", padx=20, pady=(20, 10))

            ctk.CTkRadioButton(
                radio_frame,
                text="Demo Account",
                variable=self.account_var,
                value="DEMO",
                fg_color=accent_teal,
                hover_color=accent_teal,
                font=("Segoe UI", 10)
            ).pack(side="left", padx=15)

            ctk.CTkRadioButton(
                radio_frame,
                text="Live Account",
                variable=self.account_var,
                value="LIVE",
                fg_color=accent_teal,
                hover_color=accent_teal,
                font=("Segoe UI", 10)
            ).pack(side="left", padx=15)

            # Connect button
            self.connect_btn = ctk.CTkButton(
                status_frame,
                text="Connect",
                command=self.on_connect,
                fg_color=accent_teal,
                hover_color="#5abba8",
                font=("Segoe UI", 12, "bold"),
                corner_radius=10,
                width=200,
                height=45
            )
            self.connect_btn.grid(row=1, column=0, columnspan=3, pady=25, padx=20)

            # Status label
            self.status_var = ctk.StringVar(value="Disconnected")
            self.status_label = ctk.CTkLabel(
                status_frame,
                textvariable=self.status_var,
                font=("Segoe UI", 13, "bold"),
                text_color=text_white
            )
            self.status_label.grid(row=2, column=0, columnspan=3, pady=(0, 20), padx=20)
            
    def create_trading_tab(self, parent):
        """Ultra compact scrollable trading tab"""
        bg_dark = "#1a1d23"
        card_bg = "#25292e"
        accent_teal = "#3a9d8e"
        text_white = "#e8eaed"
        
        # MAKE IT SCROLLABLE
        scrollable_frame = ctk.CTkScrollableFrame(parent, fg_color=bg_dark)
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # === ROW 1: Market & Parameters ===
        top_row = ctk.CTkFrame(scrollable_frame, fg_color=card_bg, corner_radius=8)
        top_row.pack(fill="x", pady=(0, 8))
        
        # Market
        ctk.CTkLabel(top_row, text="Market:", font=("Segoe UI", 11, "bold"),
                    text_color=text_white).pack(side='left', padx=(10, 5))
        
        self.market_var = ctk.StringVar(value="Gold Spot")
        ctk.CTkComboBox(
            top_row, variable=self.market_var,
            values=list(self.config.markets.keys()),
            width=140, height=30,
            fg_color=card_bg, button_color=accent_teal,
            font=("Segoe UI", 10)
        ).pack(side='left', padx=3)
        
        # Get Price
        ctk.CTkButton(top_row, text="Price", command=self.on_get_price,
                    fg_color="#3e444d", hover_color="#4a5159",
                    text_color=text_white,
                    corner_radius=8, width=60, height=30,
                    font=("Segoe UI", 10)).pack(side='left', padx=3)
        
        self.price_var = ctk.StringVar(value="--")
        ctk.CTkLabel(top_row, textvariable=self.price_var,
                    font=("Segoe UI", 10, "bold"),
                    text_color=accent_teal, width=70).pack(side='left', padx=3)
        
        # Separator
        ctk.CTkLabel(top_row, text="|", text_color="#3e444d",
                    font=("Segoe UI", 14)).pack(side='left', padx=5)
        
        # Direction
        ctk.CTkLabel(top_row, text="Dir:", font=("Segoe UI", 10, "bold"),
                    text_color=text_white).pack(side='left', padx=3)
        
        self.direction_var = ctk.StringVar(value="BUY")
        ctk.CTkRadioButton(top_row, text="Buy", variable=self.direction_var,
                        value="BUY", fg_color=accent_teal,
                        font=("Segoe UI", 10)).pack(side='left', padx=2)
        ctk.CTkRadioButton(top_row, text="Sell", variable=self.direction_var,
                        value="SELL", fg_color=accent_teal,
                        font=("Segoe UI", 10)).pack(side='left', padx=2)
        
        # Separator
        ctk.CTkLabel(top_row, text="|", text_color="#3e444d",
                    font=("Segoe UI", 14)).pack(side='left', padx=5)
        
        # Initialize variables
        self.offset_var = ctk.StringVar(value="5")
        self.step_var = ctk.StringVar(value="10")
        self.num_orders_var = ctk.StringVar(value="4")
        self.size_var = ctk.StringVar(value="0.01")
        self.retry_jump_var = ctk.StringVar(value="10")
        self.max_retries_var = ctk.StringVar(value="3")
        self.limit_distance_var = ctk.StringVar(value="5")
        
        # Parameters - COMPACT
        params = [
            ("Off:", self.offset_var),
            ("Step:", self.step_var),
            ("Ords:", self.num_orders_var),
            ("Size:", self.size_var),
            ("Stop:", self.stop_distance_var),
        ]
        
        for label_text, var in params:
            ctk.CTkLabel(top_row, text=label_text, font=("Segoe UI", 10),
                        text_color=text_white).pack(side='left', padx=(5, 1))
            ctk.CTkEntry(top_row, textvariable=var, width=40, height=30,
                        fg_color=card_bg, border_color="#3e444d",
                        font=("Segoe UI", 10)).pack(side='left', padx=1)
        
        # === ROW 2: PLACE LADDER BUTTON (Own row, centered) ===
        button_row = ctk.CTkFrame(scrollable_frame, fg_color=bg_dark)
        button_row.pack(fill="x", pady=(0, 8))
        
        self.ladder_btn = ctk.CTkButton(
            button_row, text="PLACE LADDER", command=self.on_place_ladder,
            fg_color="#3b9f6f", hover_color="#4ab080",
            text_color="black",
            corner_radius=8, width=200, height=40,
            font=("Segoe UI", 12, "bold"))
        self.ladder_btn.pack(pady=5)
        
        # === ROW 3: Trailing + Stop/Limit Management ===
        bottom_row = ctk.CTkFrame(scrollable_frame, fg_color=bg_dark)
        bottom_row.pack(fill="x", pady=(0, 8))
        
        # LEFT: Trailing Stop Entry
        trailing_card = ctk.CTkFrame(bottom_row, fg_color=card_bg, corner_radius=8)
        trailing_card.pack(side="left", fill="both", expand=True, padx=(0, 4))
        
        ctk.CTkLabel(trailing_card, text="Trailing Stop Entry",
                    font=("Segoe UI", 11, "bold"), text_color=text_white).pack(side='left', pady=8, padx=10)
        
        ctk.CTkLabel(trailing_card, text="Enable:", font=("Segoe UI", 10),
                    text_color=text_white).pack(side='left', padx=3)
        
        self.trailing_toggle = ToggleSwitch(trailing_card, initial_state=False,
                                        callback=self.on_trailing_toggled, bg=card_bg)
        self.trailing_toggle.pack(side='left', padx=3)
        
        self.trailing_min_move_var = ctk.StringVar(value="0.5")
        self.trailing_check_interval_var = ctk.StringVar(value="30")
        
        ctk.CTkLabel(trailing_card, text="Min:", font=("Segoe UI", 10),
                    text_color=text_white).pack(side='left', padx=(10, 1))
        ctk.CTkEntry(trailing_card, textvariable=self.trailing_min_move_var, width=45, height=30,
                    fg_color=card_bg, border_color="#3e444d",
                    font=("Segoe UI", 10)).pack(side='left', padx=1)
        
        ctk.CTkLabel(trailing_card, text="Check:", font=("Segoe UI", 10),
                    text_color=text_white).pack(side='left', padx=(8, 1))
        ctk.CTkEntry(trailing_card, textvariable=self.trailing_check_interval_var, width=45, height=30,
                    fg_color=card_bg, border_color="#3e444d",
                    font=("Segoe UI", 10)).pack(side='left', padx=1)
        
        ctk.CTkLabel(trailing_card, text="sec", font=("Segoe UI", 9),
                    text_color="#9fa6b2").pack(side='left', padx=2)
        
        # RIGHT: Stop & Limit Management
        mgmt_card = ctk.CTkFrame(bottom_row, fg_color=card_bg, corner_radius=8)
        mgmt_card.pack(side="right", fill="both", expand=True, padx=(4, 0))
        
        ctk.CTkLabel(mgmt_card, text="Stop & Limit Management",
                    font=("Segoe UI", 11, "bold"), text_color=text_white).pack(side='left', pady=8, padx=10)
        
        # Orders
        ctk.CTkLabel(mgmt_card, text="Orders:", font=("Segoe UI", 10),
                    text_color=text_white).pack(side='left', padx=3)
        
        self.bulk_stop_distance_var = ctk.StringVar(value="20")
        ctk.CTkEntry(mgmt_card, textvariable=self.bulk_stop_distance_var, width=40, height=30,
                    fg_color=card_bg, border_color="#3e444d",
                    font=("Segoe UI", 10)).pack(side='left', padx=1)
        
        ctk.CTkLabel(mgmt_card, text="pts", font=("Segoe UI", 9),
                    text_color="#9fa6b2").pack(side='left', padx=1)
        
        # GSLO checkbox - properly bound to BooleanVar
        ctk.CTkLabel(top_row, text="GSLO:", font=("Segoe UI", 10),
                    text_color=text_white).pack(side='left', padx=(8, 2))

        self.gslo_checkbox = ctk.CTkCheckBox(
            top_row, text="", 
            variable=self.use_guaranteed_stops,
            command=lambda: self.log(f"GSLO {'ON' if self.use_guaranteed_stops.get() else 'OFF'} - will apply to next ladder"),
            fg_color=accent_teal, 
            width=20, height=26,
            font=("Segoe UI", 9)
        )
        self.gslo_checkbox.pack(side='left', padx=1)
        
        ctk.CTkButton(mgmt_card, text="Update",
                    command=self.on_bulk_update_stops,
                    fg_color=accent_teal, hover_color="#4ab39f",
                    text_color="black",
                    corner_radius=8, width=70, height=30,
                    font=("Segoe UI", 10, "bold")).pack(side='left', padx=3)
        
        # Separator
        ctk.CTkLabel(mgmt_card, text="|", text_color="#3e444d",
                    font=("Segoe UI", 14)).pack(side='left', padx=8)
        
        # On Trigger
        ctk.CTkLabel(mgmt_card, text="Trigger:", font=("Segoe UI", 10),
                    text_color=text_white).pack(side='left', padx=3)
        
        # Auto-stops
        ctk.CTkLabel(mgmt_card, text="Stop:", font=("Segoe UI", 9),
                    text_color="#9fa6b2").pack(side='left', padx=1)
        
        self.auto_stop_toggle = ToggleSwitch(
            mgmt_card, initial_state=True, callback=self.on_auto_stop_toggled, bg=card_bg)
        self.auto_stop_toggle.pack(side='left', padx=2)
        
        self.auto_stop_distance_var = ctk.StringVar(value="20")
        ctk.CTkEntry(mgmt_card, textvariable=self.auto_stop_distance_var, width=35, height=30,
                    fg_color=card_bg, border_color="#3e444d",
                    font=("Segoe UI", 10)).pack(side='left', padx=1)
        
        # Auto-limits
        ctk.CTkLabel(mgmt_card, text="Lim:", font=("Segoe UI", 9),
                    text_color="#9fa6b2").pack(side='left', padx=(6, 1))
        
        self.auto_limit_toggle = ToggleSwitch(
            mgmt_card, initial_state=False, callback=self.on_auto_limit_toggled, bg=card_bg)
        self.auto_limit_toggle.pack(side='left', padx=2)
        
        self.auto_limit_distance_var = ctk.StringVar(value="5")
        ctk.CTkEntry(mgmt_card, textvariable=self.auto_limit_distance_var, width=35, height=30,
                    fg_color=card_bg, border_color="#3e444d",
                    font=("Segoe UI", 10)).pack(side='left', padx=1)
        
        ctk.CTkLabel(mgmt_card, text="pts", font=("Segoe UI", 9),
                    text_color="#9fa6b2").pack(side='left', padx=2)    
        
    def on_bulk_update_stops(self):
        """Update stop losses on all working orders - preserving GSLO if present"""
        if not self.ig_client.logged_in:
            self.log("Not connected")
            return
        
        try:
            stop_distance = float(self.bulk_stop_distance_var.get())
            
            if stop_distance <= 0:
                self.log("Stop distance must be greater than 0")
                return
            
            # Ask if user wants to preserve GSLO on orders that have it
            preserve_gslo = messagebox.askyesno(
                "Preserve GSLO?",
                "Do you want to keep Guaranteed stops on orders that already have them?\n\n"
                "YES = Keep GSLO on orders that have it\n"
                "NO = Change all to regular stops"
            )
            
            self.log(f"Updating all working order stops to {stop_distance} points...")
            self.log(f"GSLO preservation: {'ENABLED' if preserve_gslo else 'DISABLED'}")
            
            # Run in background thread
            def update_stops():
                working_orders = self.ig_client.get_working_orders()
                
                if not working_orders:
                    self.log("No working orders to update")
                    return
                
                updated = 0
                failed = 0
                
                for order in working_orders:
                    try:
                        order_data = order.get('workingOrderData', {})
                        deal_id = order_data.get('dealId')
                        current_level = order_data.get('orderLevel')  # Note: orderLevel not level
                        current_gslo = order_data.get('guaranteedStop', False)
                        
                        # Decide GSLO for this order
                        use_gslo = current_gslo if preserve_gslo else False
                        
                        if deal_id and current_level:
                            success, message = self.ig_client.update_working_order(
                                deal_id, 
                                current_level, 
                                stop_distance=stop_distance,
                                guaranteed_stop=use_gslo  # Pass GSLO flag
                            )
                            
                            if success:
                                updated += 1
                                gslo_status = "GSLO" if use_gslo else "Regular"
                                self.log(f"✓ Updated {deal_id}: {stop_distance}pts ({gslo_status})")
                            else:
                                failed += 1
                                self.log(f"✗ Failed {deal_id}: {message}")
                            
                            time.sleep(0.3)  # Rate limiting
                    except Exception as e:
                        self.log(f"Error updating order: {str(e)}")
                        failed += 1
                
                self.log(f"Stop update complete: {updated} updated, {failed} failed")
                
            thread = threading.Thread(target=update_stops, daemon=True)
            thread.start()
            
        except ValueError:
            self.log("Invalid stop distance value")
            
    def on_auto_stop_toggled(self, state):
        """Handle auto-stop toggle"""
        if state:
            try:
                stop_distance = float(self.auto_stop_distance_var.get())
                self.log(f"Auto-stop enabled - will attach {stop_distance}pt stops to new positions")
                self.ladder_strategy.start_position_monitoring(self.log, stop_distance)
            except ValueError:
                self.log("Invalid auto-stop distance")
                self.auto_stop_toggle.set_state(False)
        else:
            self.log("Auto-stop disabled")
            self.ladder_strategy.stop_position_monitoring()
            
    def on_auto_limit_toggled(self, state):
        """Handle auto-limit toggle"""
        if state:
            try:
                limit_distance = float(self.auto_limit_distance_var.get())
                self.log(f"Auto-limits enabled - will attach {limit_distance}pt profit targets to new positions")
            except ValueError:
                self.log("Invalid auto-limit distance")
                self.auto_limit_toggle.set_state(False)
        else:
            self.log("Auto-limits disabled")

    def create_risk_tab(self, parent):
        """Create comprehensive risk management tab"""
        card_bg = "#252a31"
        text_white = "#f4f5f7"
        accent_teal = "#3a9d8e"
        bg_dark = "#1e2228"
        
        # Make scrollable
        scrollable = ctk.CTkScrollableFrame(parent, fg_color=bg_dark)
        scrollable.pack(fill="both", expand=True, padx=20, pady=10)
        
        # === ENABLE/DISABLE RISK MANAGEMENT ===
        enable_frame = ctk.CTkFrame(scrollable, fg_color=card_bg, corner_radius=10)
        enable_frame.pack(fill="x", pady=(0, 10))
        
        self.enable_risk_var = ctk.BooleanVar(value=True)
        
        header_row = ctk.CTkFrame(enable_frame, fg_color=card_bg)
        header_row.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(header_row, text="Risk Management",
                    font=("Segoe UI", 14, "bold"), text_color=text_white).pack(side="left")
        
        ctk.CTkSwitch(header_row, text="Enabled", variable=self.enable_risk_var,
                    command=self.on_risk_toggle,
                    fg_color=accent_teal, progress_color=accent_teal,
                    font=("Segoe UI", 11, "bold")).pack(side="right")
        
        # === MARGIN LIMITS ===
        self.margin_frame = ctk.CTkFrame(scrollable, fg_color=card_bg, corner_radius=10)
        self.margin_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(self.margin_frame, text="Margin Limits",
                    font=("Segoe UI", 12, "bold"), text_color=text_white).pack(pady=(10, 5), padx=15, anchor="w")
        
        # Margin warning
        margin_row1 = ctk.CTkFrame(self.margin_frame, fg_color=card_bg)
        margin_row1.pack(fill="x", padx=15, pady=5)
        
        self.margin_warning_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(margin_row1, text="Warn when margin exceeds:",
                    variable=self.margin_warning_var,
                    fg_color=accent_teal, font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        self.margin_warning_percent = ctk.StringVar(value="30")
        ctk.CTkEntry(margin_row1, textvariable=self.margin_warning_percent,
                    width=50, height=30, font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        ctk.CTkLabel(margin_row1, text="%", font=("Segoe UI", 11),
                    text_color=text_white).pack(side="left")
        
        # Block trading at margin limit
        margin_row2 = ctk.CTkFrame(self.margin_frame, fg_color=card_bg)
        margin_row2.pack(fill="x", padx=15, pady=(0, 10))
        
        self.margin_block_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(margin_row2, text="Block trading when margin exceeds:",
                    variable=self.margin_block_var,
                    fg_color=accent_teal, font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        self.margin_block_percent = ctk.StringVar(value="50")
        ctk.CTkEntry(margin_row2, textvariable=self.margin_block_percent,
                    width=50, height=30, font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        ctk.CTkLabel(margin_row2, text="%", font=("Segoe UI", 11),
                    text_color=text_white).pack(side="left")
        
        # === DAILY LIMITS ===
        self.daily_frame = ctk.CTkFrame(scrollable, fg_color=card_bg, corner_radius=10)
        self.daily_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(self.daily_frame, text="Daily Limits",
                    font=("Segoe UI", 12, "bold"), text_color=text_white).pack(pady=(10, 5), padx=15, anchor="w")
        
        # Max loss per day
        loss_row = ctk.CTkFrame(self.daily_frame, fg_color=card_bg)
        loss_row.pack(fill="x", padx=15, pady=5)
        
        self.daily_loss_limit_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(loss_row, text="Maximum daily loss:",
                    variable=self.daily_loss_limit_var,
                    fg_color=accent_teal, font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        ctk.CTkLabel(loss_row, text="£", font=("Segoe UI", 11),
                    text_color=text_white).pack(side="left", padx=2)
        
        self.daily_loss_amount = ctk.StringVar(value="500")
        ctk.CTkEntry(loss_row, textvariable=self.daily_loss_amount,
                    width=80, height=30, font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        # Max profit target
        profit_row = ctk.CTkFrame(self.daily_frame, fg_color=card_bg)
        profit_row.pack(fill="x", padx=15, pady=5)
        
        self.daily_profit_target_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(profit_row, text="Stop trading after profit:",
                    variable=self.daily_profit_target_var,
                    fg_color=accent_teal, font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        ctk.CTkLabel(profit_row, text="£", font=("Segoe UI", 11),
                    text_color=text_white).pack(side="left", padx=2)
        
        self.daily_profit_amount = ctk.StringVar(value="1000")
        ctk.CTkEntry(profit_row, textvariable=self.daily_profit_amount,
                    width=80, height=30, font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        # Max trades per day
        trades_row = ctk.CTkFrame(self.daily_frame, fg_color=card_bg)
        trades_row.pack(fill="x", padx=15, pady=(0, 10))
        
        self.max_trades_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(trades_row, text="Maximum trades per day:",
                    variable=self.max_trades_var,
                    fg_color=accent_teal, font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        self.max_trades_amount = ctk.StringVar(value="20")
        ctk.CTkEntry(trades_row, textvariable=self.max_trades_amount,
                    width=60, height=30, font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        # === POSITION LIMITS ===
        self.position_frame = ctk.CTkFrame(scrollable, fg_color=card_bg, corner_radius=10)
        self.position_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(self.position_frame, text="Position Limits",
                    font=("Segoe UI", 12, "bold"), text_color=text_white).pack(pady=(10, 5), padx=15, anchor="w")
        
        # Max open positions
        pos_row = ctk.CTkFrame(self.position_frame, fg_color=card_bg)
        pos_row.pack(fill="x", padx=15, pady=5)
        
        self.max_positions_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(pos_row, text="Maximum open positions:",
                    variable=self.max_positions_var,
                    fg_color=accent_teal, font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        self.max_positions_amount = ctk.StringVar(value="5")
        ctk.CTkEntry(pos_row, textvariable=self.max_positions_amount,
                    width=60, height=30, font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        # Max position size
        size_row = ctk.CTkFrame(self.position_frame, fg_color=card_bg)
        size_row.pack(fill="x", padx=15, pady=(0, 10))
        
        self.max_size_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(size_row, text="Maximum position size:",
                    variable=self.max_size_var,
                    fg_color=accent_teal, font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        self.max_size_amount = ctk.StringVar(value="2.0")
        ctk.CTkEntry(size_row, textvariable=self.max_size_amount,
                    width=60, height=30, font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        ctk.CTkLabel(size_row, text="contracts", font=("Segoe UI", 11),
                    text_color=text_white).pack(side="left", padx=5)
        
        # === RISK/REWARD RATIOS ===
        self.ratio_frame = ctk.CTkFrame(scrollable, fg_color=card_bg, corner_radius=10)
        self.ratio_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(self.ratio_frame, text="Risk/Reward",
                    font=("Segoe UI", 12, "bold"), text_color=text_white).pack(pady=(10, 5), padx=15, anchor="w")
        
        ratio_row = ctk.CTkFrame(self.ratio_frame, fg_color=card_bg)
        ratio_row.pack(fill="x", padx=15, pady=(0, 10))
        
        self.min_rr_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(ratio_row, text="Minimum risk/reward ratio:",
                    variable=self.min_rr_var,
                    fg_color=accent_teal, font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        self.min_rr_amount = ctk.StringVar(value="1.5")
        ctk.CTkEntry(ratio_row, textvariable=self.min_rr_amount,
                    width=60, height=30, font=("Segoe UI", 11)).pack(side="left", padx=5)
        
        ctk.CTkLabel(ratio_row, text=":1", font=("Segoe UI", 11),
                    text_color=text_white).pack(side="left")

    def on_risk_toggle(self):
        """Enable/disable all risk management controls"""
        enabled = self.enable_risk_var.get()
        
        if enabled:
            self.log("Risk management ENABLED")
            # Enable all frames
            for frame in [self.margin_frame, self.daily_frame, self.position_frame, self.ratio_frame]:
                for child in frame.winfo_children():
                    self._enable_widget(child)
        else:
            self.log("Risk management DISABLED - Trading without safety checks")
            # Gray out all frames
            for frame in [self.margin_frame, self.daily_frame, self.position_frame, self.ratio_frame]:
                for child in frame.winfo_children():
                    self._disable_widget(child)

    def _enable_widget(self, widget):
        """Recursively enable a widget and its children"""
        try:
            if isinstance(widget, (ctk.CTkFrame, ctk.CTkScrollableFrame)):
                for child in widget.winfo_children():
                    self._enable_widget(child)
            else:
                widget.configure(state="normal")
        except:
            pass

    def _disable_widget(self, widget):
        """Recursively disable a widget and its children"""
        try:
            if isinstance(widget, (ctk.CTkFrame, ctk.CTkScrollableFrame)):
                for child in widget.winfo_children():
                    self._disable_widget(child)
            else:
                widget.configure(state="disabled")
        except:
            pass

    def create_market_research_tab(self, parent):
        """Create market research and analysis tab with scanner"""
        card_bg = "#252a31"
        text_white = "#f4f5f7"
        accent_teal = "#5aa89a"
        bg_dark = "#1e2228"
        text_gray = "#9fa6b2"
        
        # Make scrollable
        scrollable = ctk.CTkScrollableFrame(parent, fg_color=bg_dark)
        scrollable.pack(fill="both", expand=True, padx=20, pady=10)
        
        # === MARKET SCANNER ===
        scanner_frame = ctk.CTkFrame(scrollable, fg_color=card_bg, corner_radius=10)
        scanner_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        ctk.CTkLabel(scanner_frame, text="Market Scanner",
                    font=("Segoe UI", 14, "bold"), text_color=text_white).pack(pady=(15, 10), padx=15, anchor="w")
        
        # Scanner controls
        control_row = ctk.CTkFrame(scanner_frame, fg_color=card_bg)
        control_row.pack(fill="x", padx=15, pady=(0, 10))
        
        # Filter
        ctk.CTkLabel(control_row, text="Filter:", 
                    font=("Segoe UI", 11), text_color=text_white).pack(side="left", padx=5)
        
        self.scanner_filter_var = ctk.StringVar(value="All")
        ctk.CTkComboBox(
            control_row, 
            variable=self.scanner_filter_var,
            values=["All", "Commodities", "Indices"],
            width=130, height=35,
            fg_color=card_bg, button_color=accent_teal,
            font=("Segoe UI", 11)
        ).pack(side="left", padx=5)
        
        # Timeframe
        ctk.CTkLabel(control_row, text="Timeframe:", 
                    font=("Segoe UI", 11), text_color=text_white).pack(side="left", padx=(15, 5))
        
        self.scanner_timeframe_var = ctk.StringVar(value="Annual")
        ctk.CTkComboBox(
            control_row,
            variable=self.scanner_timeframe_var,
            values=["Daily", "Weekly", "Monthly", "Quarterly", "6-Month", "Annual", "2-Year", "5-Year", "All-Time"],
            width=130, height=35,
            fg_color=card_bg, button_color=accent_teal,
            font=("Segoe UI", 11)
        ).pack(side="left", padx=5)
        
        # Limit
        ctk.CTkLabel(control_row, text="Limit:", 
                    font=("Segoe UI", 11), text_color=text_white).pack(side="left", padx=(15, 5))
        
        self.scanner_limit_var = ctk.StringVar(value="5")
        ctk.CTkEntry(
            control_row,
            textvariable=self.scanner_limit_var,
            width=50, height=35,
            font=("Segoe UI", 11),
            placeholder_text="0=All"
        ).pack(side="left", padx=5)
        
        ctk.CTkLabel(control_row, text="markets", 
                    font=("Segoe UI", 10), text_color=text_gray).pack(side="left", padx=2)
                
        self.include_closed_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            control_row, 
            text="Include Closed", 
            variable=self.include_closed_var,
            fg_color=accent_teal,
            font=("Segoe UI", 10)
        ).pack(side="left", padx=(15, 5))
        
        # Data Source Checkbox 
        
        ctk.CTkLabel(control_row, text="Source:", 
                    font=("Segoe UI", 11), text_color=text_white).pack(side="left", padx=(15, 5))

        self.data_source_var = ctk.StringVar(value="Yahoo Only")
        ctk.CTkComboBox(
            control_row,
            variable=self.data_source_var,
            values=["Yahoo Only", "IG + Yahoo", "IG Only"],
            width=120, height=35,
            fg_color=card_bg, button_color=accent_teal,
            font=("Segoe UI", 11)
        ).pack(side="left", padx=5)
        
        # Scan button
        ctk.CTkButton(control_row, text="🔄 Scan Markets", 
                    command=self.on_scan_markets,
                    fg_color=accent_teal,
                    hover_color="#00f7cc",
                    width=120,
                    height=32,
                    font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        
        # Scanner results display
        self.scanner_results = scrolledtext.ScrolledText(
            scanner_frame,
            width=100,
            height=20,
            bg=card_bg,
            fg=text_white,
            font=("Consolas", 9),
            relief="flat",
            borderwidth=0,
            insertbackground=accent_teal,
        )
        self.scanner_results.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Configure tags
        self.scanner_results.tag_config("header", foreground=accent_teal, font=("Consolas", 10, "bold"))
        self.scanner_results.tag_config("low", foreground="#00d084", font=("Consolas", 9, "bold"))
        self.scanner_results.tag_config("mid", foreground="#e8b339", font=("Consolas", 9))
        self.scanner_results.tag_config("high", foreground="#ed6347", font=("Consolas", 9, "bold"))
        self.scanner_results.tag_config("neutral", foreground="#9fa6b2")
        
        # Initial message
        self.scanner_results.insert("1.0", "📊 Market Scanner\n\n", "header")
        self.scanner_results.insert("end", "Click 'Scan Markets' to analyze\n", "neutral")

    def get_cached_market_details(self, epic):
        """Get market details with caching"""
        if epic not in self.market_details_cache:
            self.log(f"Fetching market details for {epic}...")
            details = self.ig_client.get_market_details(epic)
            if details:
                self.market_details_cache[epic] = details
                self.log(f"Min size: {details['min_deal_size']}, Max size: {details['max_deal_size']}")
            return details
        return self.market_details_cache[epic]

    def on_search_markets_tab(self):
        """Handle market search from the research tab"""
        if not self.ig_client.logged_in:
            self.log("Not connected")
            self.market_search_results.delete(1.0, tk.END)
            self.market_search_results.insert(tk.END, "⚠️ Please connect to IG first\n\n")
            return
        
        search_term = self.market_search_var.get().strip()
        
        if not search_term:
            self.market_search_results.delete(1.0, tk.END)
            self.market_search_results.insert(tk.END, "Please enter a search term\n")
            return
        
        self.log(f"Searching for '{search_term}'...")
        self.market_search_results.delete(1.0, tk.END)
        self.market_search_results.insert(tk.END, f"Searching for '{search_term}'...\n\n")
        
        # Run search in background
        def do_search():
            markets = self.ig_client.search_markets(search_term)
            
            def update_results():
                self.market_search_results.delete(1.0, tk.END)
                
                if markets:
                    self.market_search_results.insert(tk.END, 
                        f"Found {len(markets)} results for '{search_term}'\n", "header")
                    self.market_search_results.insert(tk.END, "="*80 + "\n\n")
                    
                    for i, market in enumerate(markets[:20], 1):  # Show top 20
                        epic = market.get("epic", "N/A")
                        instrument_name = market.get("instrumentName", "N/A")
                        instrument_type = market.get("instrumentType", "N/A")
                        expiry = market.get("expiry", "N/A")
                        
                        self.market_search_results.insert(tk.END, f"{i}. ", "header")
                        self.market_search_results.insert(tk.END, f"{epic}\n", "epic")
                        self.market_search_results.insert(tk.END, f"   Name: {instrument_name}\n", "name")
                        self.market_search_results.insert(tk.END, f"   Type: {instrument_type}", "type")
                        if expiry != "N/A" and expiry != "-":
                            self.market_search_results.insert(tk.END, f" | Expiry: {expiry}", "type")
                        self.market_search_results.insert(tk.END, "\n\n")
                    
                    if len(markets) > 20:
                        self.market_search_results.insert(tk.END, 
                            f"\n(Showing top 20 of {len(markets)} results)\n", "type")
                    
                    self.log(f"Found {len(markets)} markets for '{search_term}'")
                else:
                    self.market_search_results.insert(tk.END, 
                        f"No markets found for '{search_term}'\n\n", "name")
                    self.market_search_results.insert(tk.END, 
                        "Try different keywords or check spelling", "type")
                    self.log(f"No results for '{search_term}'")
            
            self.root.after(0, update_results)
        
        thread = threading.Thread(target=do_search, daemon=True)
        thread.start()

    def quick_search(self, term):
        """Quick search for common markets"""
        self.market_search_var.set(term)
        self.on_search_markets_tab()

    def on_scan_markets(self):
        """Scan with intelligent caching"""
        if not self.ig_client.logged_in:
            self.log("Not connected")
            self.scanner_results.delete(1.0, tk.END)
            self.scanner_results.insert(tk.END, "⚠️ Please connect to IG first\n\n")
            return
        
        filter_type = self.scanner_filter_var.get()
        timeframe = self.scanner_timeframe_var.get()
        include_closed = self.include_closed_var.get()
        data_source = self.data_source_var.get()  # ADD THIS
        
        try:
            market_limit = int(self.scanner_limit_var.get())
            if market_limit == 0:
                market_limit = None  # No limit
        except:
            market_limit = None
        
        # Show helpful message about rate limits
        if data_source == "Yahoo Only":
            self.log("Using Yahoo Only - no IG rate limits!")
        elif data_source == "IG Only":
            self.log("⚠️ Using IG API only - watch for rate limits")
        else:
            self.log("Using IG + Yahoo - moderate API usage")
        
        # Get cache status
        cache_summary = self.cached_scanner.get_cache_summary()
        self.log(f"Cache status: {cache_summary}")
        
        self.scanner_results.delete(1.0, tk.END)
        self.scanner_results.insert(tk.END, f"🔄 Scanning {filter_type} ({timeframe})...\n\n", "header")
        
        def do_scan():
            try:
                scan_results, stats = self.cached_scanner.scan_markets(
                    filter_type, timeframe, include_closed, market_limit, self.log, data_source  # ADD data_source
                )
                
                self.log(f"Scan complete: {len(scan_results)} markets")
                
                # Display results
                def update_display():
                    self.scanner_results.delete(1.0, tk.END)
                    
                    if scan_results:
                        self.scanner_results.insert(tk.END, 
                            f"✓ Scanned {len(scan_results)} markets\n\n", "header")
                        
                        # Header row with Low and High
                        header = f"{'Market':<28} {'Price':>10} {'Low':>10} {'High':>10} {'Pos':>8} {'Signal':>8}\n"
                        self.scanner_results.insert(tk.END, header, "header")
                        self.scanner_results.insert(tk.END, "="*85 + "\n", "header")
                        
                        for result in scan_results:
                            if result['position_pct'] < 30:
                                tag = "low"
                                signal = "🟢 LOW"
                            elif result['position_pct'] > 70:
                                tag = "high"
                                signal = "🔴 HIGH"
                            else:
                                tag = "mid"
                                signal = "🟡 MID"
                            
                            name = result['name'][:26]
                            price = result.get('price', 0)
                            low = result.get('low', 0)
                            high = result.get('high', 0)
                            position = f"{result['position_pct']:.1f}%"
                            
                            # Format numbers nicely
                            def format_price(p):
                                if not p:
                                    return "N/A"
                                elif p < 1:
                                    return f"{p:.4f}"
                                elif p < 100:
                                    return f"{p:.2f}"
                                else:
                                    return f"{p:,.0f}"
                            
                            price_str = format_price(price)
                            low_str = format_price(low)
                            high_str = format_price(high)
                            
                            line = f"{name:<28} {price_str:>10} {low_str:>10} {high_str:>10} {position:>8} {signal:>8}\n"
                            self.scanner_results.insert(tk.END, line, tag)
                    else:
                        self.scanner_results.insert(tk.END, "No markets scanned\n")
        
                self.root.after(0, update_display)
                
            except Exception as e:
                self.log(f"ERROR in scan: {str(e)}")
                import traceback
                self.log(traceback.format_exc())
        
        thread = threading.Thread(target=do_scan, daemon=True)
        thread.start()
    
    def create_config_tab(self, parent):
        """Create configuration tab - placeholder for now"""
        card_bg = "#252a31"
        text_white = "#f4f5f7"
        accent_teal = "#00d9b1"
        
        # Optional Features Section
        features_frame = ctk.CTkFrame(parent, fg_color=card_bg, corner_radius=10)
        features_frame.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(
            features_frame,
            text="Optional Features",
            font=("Segoe UI", 12, "bold"),
            text_color=text_white
        ).pack(pady=(15, 10), padx=15, anchor="w")

        ctk.CTkCheckBox(features_frame, text="Enable Risk Management",
                    variable=self.use_risk_management,
                    fg_color=accent_teal, hover_color=accent_teal).pack(anchor="w", pady=5, padx=20)
        ctk.CTkCheckBox(features_frame, text="Enable Limit Orders",
                    variable=self.use_limit_orders,
                    fg_color=accent_teal, hover_color=accent_teal).pack(anchor="w", pady=5, padx=20)
        ctk.CTkCheckBox(features_frame, text="Enable Auto-Replace Strategy",
                    variable=self.use_auto_replace,
                    fg_color=accent_teal, hover_color=accent_teal).pack(anchor="w", pady=5, padx=20)
        ctk.CTkCheckBox(features_frame, text="Enable Trailing Stops",
                    variable=self.use_trailing_stops,
                    fg_color=accent_teal, hover_color=accent_teal).pack(anchor="w", pady=(5, 15), padx=20)
        
    def update_feature_status(self):
        """Update feature status display"""
        self.feature_status_text.delete(1.0, tk.END)

        timestamp = time.strftime("%H:%M:%S")
        self.feature_status_text.insert(
            tk.END, f"[{timestamp}] Feature Status:\n\n")

        features = [
            ("Risk Management", self.use_risk_management.get()),
            ("Limit Orders", self.use_limit_orders.get()),
            ("Auto-Replace", self.use_auto_replace.get()),
            ("Trailing Stops", self.use_trailing_stops.get())
        ]

        for name, enabled in features:
            status = "ENABLED" if enabled else "DISABLED"
            color = "enabled" if enabled else "disabled"
            self.feature_status_text.insert(
                tk.END, f"{name}: {status}\n", color)

        # Configure colors
        self.feature_status_text.tag_config(
            'enabled', foreground='#27ae60', font=('Consolas', 9, 'bold'))
        self.feature_status_text.tag_config('disabled', foreground='#e74c3c')

    def update_risk_display(self):
        """Update risk management display"""
        if not self.ig_client.logged_in:
            self.log("Not connected - cannot update risk data")
            return

        try:
            # Get risk summary
            summary = self.risk_manager.get_risk_summary()

            # Update account info
            self.balance_var.set(f"Balance: £{summary['account_balance']:.2f}")
            self.available_var.set(
                f"Available: £{summary['available_funds']:.2f}")

            # Color-code daily P&L
            daily_pnl = summary["daily_pnl"]
            if daily_pnl >= 0:
                pnl_text = f"Daily P&L: +£{daily_pnl:.2f}"
            else:
                pnl_text = f"Daily P&L: -£{abs(daily_pnl):.2f}"

            self.daily_pnl_var.set(pnl_text)

            unrealized = summary["unrealized_pnl"]
            if unrealized >= 0:
                unrealized_text = f"Unrealized P&L: +£{unrealized:.2f}"
            else:
                unrealized_text = f"Unrealized P&L: -£{abs(unrealized):.2f}"
            self.unrealized_pnl_var.set(unrealized_text)

            # Update limits
            self.positions_var.set(
                f"Positions: {summary['open_positions']}/{summary['max_positions']}"
            )

            loss_remaining = summary["daily_loss_limit"] - \
                abs(min(0, daily_pnl))
            self.daily_loss_var.set(f"Loss Remaining: £{loss_remaining:.2f}")

            # Check trading safety
            can_trade, safety_checks = self.risk_manager.can_trade()

            # Update safety status display
            self.safety_text.delete(1.0, tk.END)

            timestamp = time.strftime("%H:%M:%S")
            if can_trade:
                self.safety_text.insert(
                    tk.END,
                    f"[{timestamp}] TRADING ALLOWED - All safety checks passed\n\n",
                    "safe",
                )
            else:
                self.safety_text.insert(
                    tk.END,
                    f"[{timestamp}] TRADING BLOCKED - Safety limits breached\n\n",
                    "danger",
                )

            # Show detailed safety checks
            for check_name, passed, message in safety_checks:
                status = "PASS" if passed else "FAIL"
                status_tag = "pass" if passed else "fail"
                self.safety_text.insert(
                    tk.END, f"{check_name}: {status} - {message}\n", status_tag
                )

            # Configure text tags for colors
            self.safety_text.tag_config(
                "safe", foreground="#27ae60", font=("Consolas", 9, "bold")
            )
            self.safety_text.tag_config(
                "danger", foreground="#e74c3c", font=("Consolas", 9, "bold")
            )
            self.safety_text.tag_config("pass", foreground="#27ae60")
            self.safety_text.tag_config(
                "fail", foreground="#e74c3c", font=("Consolas", 9, "bold")
            )

            self.log("Risk data updated")

        except Exception as e:
            self.log(f"Risk update error: {str(e)}")

    def reset_daily_tracking(self):
        """Reset daily P&L tracking"""
        if messagebox.askyesno(
            "Confirm", "Reset daily tracking? This will restart daily P&L calculations."
        ):
            self.risk_manager.reset_daily_tracking()
            self.update_risk_display()
            self.log("Daily tracking reset")

    def schedule_risk_update(self):
        """Schedule automatic risk data updates"""
        if self.ig_client.logged_in:
            self.update_risk_display()

        # Schedule next update in 30 seconds
        self.root.after(30000, self.schedule_risk_update)

    def on_panic(self):
        """Handle emergency stop button"""
        self.log("🚨 EMERGENCY STOP ACTIVATED")

        # Stop auto trading if running
        if self.auto_strategy.running:
            self.auto_strategy.stop()

        # Set emergency flag
        self.ig_client.trigger_emergency_stop()

        # Cancel all orders
        self.log("Cancelling all working orders...")
        orders = self.ig_client.get_working_orders()
        cancelled_count = 0
        failed_count = 0
        
        for order in orders:
            deal_id = order.get("workingOrderData", {}).get("dealId")
            if deal_id:
                success, message = self.ig_client.cancel_order(deal_id)
                if success:
                    cancelled_count += 1
                    self.log(f"  ✓ Cancelled order {deal_id}")
                else:
                    failed_count += 1
                    self.log(f"  ✗ Failed to cancel {deal_id}: {message}")
                time.sleep(0.2)
        
        self.log(f"Orders: {cancelled_count} cancelled, {failed_count} failed")

        # Close all positions
        self.log("Closing all open positions...")
        positions = self.ig_client.get_open_positions()
        closed_count = 0
        failed_closes = 0
        
        for position in positions:
            deal_id = position.get("position", {}).get("dealId")
            direction = position.get("position", {}).get("direction")
            size = position.get("position", {}).get("dealSize")
            epic = position.get("market", {}).get("epic", "Unknown")

            self.log(f"  Closing: {epic} {direction} {size} (ID: {deal_id})")

            if deal_id and direction and size:
                success, message = self.ig_client.close_position(deal_id, direction, size)
                
                if success:
                    closed_count += 1
                    self.log(f"  ✓ Closed {deal_id}")
                else:
                    failed_closes += 1
                    self.log(f"  ✗ FAILED to close {deal_id}: {message}")
                
                time.sleep(0.5)
            else:
                failed_closes += 1
                self.log(f"  ✗ Missing data for position")

        if failed_closes > 0:
            self.log(f"🚨 WARNING: {failed_closes} positions FAILED to close!")
        
        self.log(f"🚨 EMERGENCY STOP COMPLETE - Closed {closed_count}/{len(positions)} positions")
        self.ig_client.reset_emergency_stop()
        
        # Wait and verify
        time.sleep(1)
        self.on_refresh_orders()

    def test_stop_update(self):
        """Test stop level update on first position"""
        if not self.ig_client.logged_in:
            self.log("Not connected")
            return

        positions = self.ig_client.get_open_positions()

        if not positions:
            self.log("No positions to test")
            return

        # Get first position
        pos = positions[0]
        deal_id = pos.get("position", {}).get("dealId")
        current_stop = pos.get("position", {}).get("stopLevel")
        open_level = pos.get("position", {}).get("openLevel")

        self.log(f"Testing stop update on position {deal_id}")
        self.log(f"Current stop: {current_stop}, Open level: {open_level}")

        # Try to update stop to 10 points below open level
        test_stop = open_level - 10

        success, message = self.ig_client.update_position_stop(
            deal_id, test_stop)
        self.log(f"Update result: {message}")

    def log(self, message):
        """Add message to log - thread safe"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)

        # Schedule the GUI update on the main thread
        try:
            if self.root and self.log_text:
                def do_update():
                    try:
                        self.log_text.insert("end", log_message + "\n")  # Changed from tk.END
                        self.log_text.see("end")  # Changed from tk.END
                    except Exception as e:
                        print(f"Log display error: {e}")
                self.root.after(0, do_update)
        except Exception as e:
            print(f"Log error: {e}")

    def on_connect(self):
            """Handle connect button"""
            if not self.ig_client.logged_in:
                account_type = self.account_var.get()
                creds = self.config.get_credentials(account_type)

                success, message = self.ig_client.connect(
                    creds["username"],
                    creds["password"],
                    creds["api_key"],
                    creds["base_url"],
                )

                if success:
                    self.status_var.set(f"Connected to {account_type}")
                    self.status_label.configure(text_color="#00d084")  # Success green
                    self.connect_btn.configure(text="Disconnect", fg_color="#ed6347")  # Danger red
                    self.update_margin_display()
                    self.log(message)
                else:
                    self.status_var.set("Connection failed")
                    self.status_label.configure(text_color="#9fa6b2")  # Gray
                    self.log(message)
            else:
                self.ig_client.disconnect()
                self.status_var.set("Disconnected")
                self.status_label.configure(text_color="#9fa6b2")  # Gray
                self.connect_btn.configure(text="Connect", fg_color="#5aa89a")  # Teal
                self.log("Disconnected from IG")

    def on_get_price(self):
        """Handle get price button"""
        if not self.ig_client.logged_in:
            self.log("Not connected")
            return

        selected_market = self.market_var.get()
        epic = self.config.markets.get(selected_market)

        if epic:
            price_data = self.ig_client.get_market_price(epic)
            if price_data and price_data["mid"]:
                self.price_var.set(
                    f"Price: {price_data['mid']:.2f} ({price_data['market_status']})"
                )
                self.log(
                    f"{selected_market}: Bid={price_data['bid']:.2f}, Offer={price_data['offer']:.2f}"
                )
            else:
                self.log("Failed to get price")

    def on_place_ladder(self):
        """Handle place ladder button with automatic size checking"""
        
        # Check for cancel
        if self.ladder_btn.cget("text") == "CANCEL LADDER":
            self.ladder_strategy.cancel_requested = True
            self.log("Cancelling ladder placement...")
            return
        
        # Check connection
        if not self.ig_client.logged_in:
            self.log("Not connected")
            return

        # Change button to cancel mode
        self.ladder_btn.configure(
            state="normal", 
            text="CANCEL LADDER",
            fg_color="#ed6347",
            hover_color="#ee4626"
        )
        
        try:
            # Get parameters
            selected_market = self.market_var.get()
            epic = self.config.markets.get(selected_market)
            
            if not epic:
                self.log(f"ERROR: Market '{selected_market}' not found in config")
                self.ladder_btn.configure(
                    state="normal", 
                    text="PLACE LADDER",
                    fg_color="#3b9f6f",
                    hover_color="#4ab080"
                )
                return
            
            direction = self.direction_var.get()
            start_offset = float(self.offset_var.get())
            step_size = float(self.step_var.get())
            num_orders = int(self.num_orders_var.get())
            order_size = float(self.size_var.get())
            retry_jump = float(self.retry_jump_var.get())
            max_retries = int(self.max_retries_var.get())
            stop_distance = float(self.stop_distance_var.get())
            guaranteed_stop = self.use_guaranteed_stops.get()
            
            # ===== CHECK MINIMUM SIZE =====
            market_details = self.get_cached_market_details(epic)
            
            if market_details is None:
                messagebox.showerror(
                    "API Rate Limit",
                    f"⚠️ Cannot place orders - API rate limit exceeded\n\n"
                    f"IG has temporarily blocked API requests.\n\n"
                    f"Please wait 5-10 minutes and try again.\n\n"
                    f"Tip: Use LIVE account for higher limits."
                )
                self.log("ERROR: Rate limited - cannot fetch market details")
                self.ladder_btn.configure(
                    state="normal", 
                    text="PLACE LADDER",
                    fg_color="#3b9f6f",
                    hover_color="#4ab080"
                )
                return

            if market_details:
                min_size = market_details['min_deal_size']
                max_size = market_details['max_deal_size']
            
            # Check if max_size is 0 (missing from API - skip max validation)
            if max_size == 0:
                self.log(f"⚠️ No max size available for {selected_market} - skipping max check")
                # Don't check max, just proceed
            else:
                # Only check max if it exists
                if order_size > max_size:
                    result = messagebox.askyesno(
                        "Order Size Too Large",
                        f"⚠️ Maximum size for {selected_market} is {max_size}\n\n"
                        f"Your order size: {order_size}\n"
                        f"Maximum allowed: {max_size}\n\n"
                        f"Place orders at maximum size of {max_size} instead?",
                        icon="warning"
                    )
                    
                    if result:
                        self.size_var.set(str(max_size))
                        order_size = max_size
                        self.log(f"✓ Order size adjusted to maximum: {max_size}")
                    else:
                        self.log("Order cancelled - size above maximum")
                        self.ladder_btn.configure(...)
                        return

            if market_details:
                min_size = market_details['min_deal_size']
                max_size = market_details['max_deal_size']
                
                # Check if size is too small
                if order_size < min_size:
                    result = messagebox.askyesno(
                        "Order Size Too Small",
                        f"⚠️ Minimum size for {selected_market} is {min_size}\n\n"
                        f"Your order size: {order_size}\n"
                        f"Minimum required: {min_size}\n\n"
                        f"Place orders at minimum size of {min_size} instead?",
                        icon="warning"
                    )
                    
                    if result:
                        # Update the size variable and log it
                        self.size_var.set(str(min_size))
                        order_size = min_size
                        self.log(f"✓ Order size adjusted to minimum: {min_size}")
                    else:
                        self.log("Order cancelled - size below minimum")
                        self.ladder_btn.configure(
                            state="normal", 
                            text="PLACE LADDER",
                            fg_color="#3b9f6f",
                            hover_color="#4ab080"
                        )
                        return
                
                # Check if size is too large
                elif order_size > max_size:
                    result = messagebox.askyesno(
                        "Order Size Too Large",
                        f"⚠️ Maximum size for {selected_market} is {max_size}\n\n"
                        f"Your order size: {order_size}\n"
                        f"Maximum allowed: {max_size}\n\n"
                        f"Place orders at maximum size of {max_size} instead?",
                        icon="warning"
                    )
                    
                    if result:
                        self.size_var.set(str(max_size))
                        order_size = max_size
                        self.log(f"✓ Order size adjusted to maximum: {max_size}")
                    else:
                        self.log("Order cancelled - size above maximum")
                        self.ladder_btn.configure(
                            state="normal", 
                            text="PLACE LADDER",
                            fg_color="#3b9f6f",
                            hover_color="#4ab080"
                        )
                        return
                
                # Check stop distance for GSLO
                if guaranteed_stop:
                    min_gslo_distance = market_details['min_gslo_distance']
                    if stop_distance < min_gslo_distance:
                        messagebox.showerror(
                            "GSLO Stop Too Close",
                            f"❌ Guaranteed stop distance too close!\n\n"
                            f"Your stop: {stop_distance} points\n"
                            f"Minimum GSLO distance: {min_gslo_distance} points\n\n"
                            f"Please increase stop distance to at least {min_gslo_distance}"
                        )
                        self.log(f"ERROR: GSLO stop too close (min: {min_gslo_distance})")
                        self.ladder_btn.configure(
                            state="normal", 
                            text="PLACE LADDER",
                            fg_color="#3b9f6f",
                            hover_color="#4ab080"
                        )
                        return
                else:
                    # Check regular stop distance
                    min_stop_distance = market_details['min_stop_distance']
                    if stop_distance < min_stop_distance:
                        result = messagebox.askyesno(
                            "Stop Distance Too Close",
                            f"⚠️ Minimum stop distance for {selected_market} is {min_stop_distance}\n\n"
                            f"Your stop: {stop_distance} points\n"
                            f"Minimum required: {min_stop_distance} points\n\n"
                            f"Use minimum stop distance of {min_stop_distance} instead?",
                            icon="warning"
                        )
                        
                        if result:
                            self.stop_distance_var.set(str(min_stop_distance))
                            stop_distance = min_stop_distance
                            self.log(f"✓ Stop distance adjusted to minimum: {min_stop_distance}")
                        else:
                            self.log("Order cancelled - stop distance too small")
                            self.ladder_btn.configure(
                                state="normal", 
                                text="PLACE LADDER",
                                fg_color="#3b9f6f",
                                hover_color="#4ab080"
                            )
                            return
            else:
                self.log("WARNING: Could not verify market limits - proceeding anyway")

            # Check margin
            try:
                margin_ok, new_margin_ratio, required_margin = self.risk_manager.check_margin_for_order(
                    epic, order_size * num_orders, margin_limit=0.3
                )
            except Exception as e:
                self.log(f"Margin check skipped: {str(e)}")
                margin_ok = True
                new_margin_ratio = None

            if not margin_ok and new_margin_ratio:
                result = messagebox.askyesno(
                    "Margin Warning",
                    f"This order would use {new_margin_ratio:.1%} margin (limit: 30%)\n"
                    f"Estimated required margin: £{required_margin:.2f}\n\n"
                    f"Continue anyway?",
                    icon="warning"
                )
                if not result:
                    self.log("Order cancelled - would exceed margin limit")
                    self.ladder_btn.configure(
                        state="normal", 
                        text="PLACE LADDER",
                        fg_color="#3b9f6f",
                        hover_color="#4ab080"
                    )
                    return

            # No limits for now
            limit_distance = 0

            # Risk check
            try:
                if self.use_risk_management.get():
                    can_trade, safety_checks = self.risk_manager.can_trade(order_size, epic)
                    if not can_trade:
                        self.log("TRADING BLOCKED - Risk limits exceeded:")
                        for check_name, passed, message in safety_checks:
                            if not passed:
                                self.log(f"  {check_name}: {message}")
                        self.ladder_btn.configure(
                            state="normal", 
                            text="PLACE LADDER",
                            fg_color="#3b9f6f",
                            hover_color="#4ab080"
                        )
                        return
            except Exception as e:
                self.log(f"Risk check skipped: {str(e)}")

            # Log action
            gslo_text = "with GSLO" if guaranteed_stop else "with regular stops"
            self.log(f"Placing {num_orders} {direction} orders for {selected_market} {gslo_text}")

            # Background thread
            def place_and_reenable():
                try:
                    self.ladder_strategy.place_ladder(
                        epic, direction, start_offset, step_size,
                        num_orders, order_size, retry_jump, max_retries,
                        self.log, limit_distance, stop_distance, guaranteed_stop
                    )
                except Exception as e:
                    self.log(f"ERROR placing ladder: {str(e)}")
                finally:
                    # Reset button
                    self.root.after(0, lambda: self.ladder_btn.configure(
                        state="normal", 
                        text="PLACE LADDER",
                        fg_color="#3b9f6f",
                        hover_color="#4ab080"
                    ))
                    self.ladder_strategy.cancel_requested = False

            # Start thread
            thread = threading.Thread(target=place_and_reenable, daemon=True)
            thread.start()

        except ValueError as e:
            self.log(f"Invalid parameters: {str(e)}")
            self.ladder_btn.configure(
                state="normal", 
                text="PLACE LADDER",
                fg_color="#3b9f6f",
                hover_color="#4ab080"
            )
        except Exception as e:
            self.log(f"ERROR: {str(e)}")
            self.ladder_btn.configure(
                state="normal", 
                text="PLACE LADDER",
                fg_color="#3b9f6f",
                hover_color="#4ab080"
            )

    def place_and_reenable():
        try:
            self.ladder_strategy.place_ladder(epic, direction, start_offset, step_size,
                                              num_orders, order_size, retry_jump, max_retries,
                                              self.log, limit_distance, stop_distance, guaranteed_stop)
        finally:
            # Re-enable button when done
            self.root.after(0, lambda: self.ladder_btn.configure(
                state="normal", text="Place Ladder"))
            self.ladder_strategy.cancel_requested = False  # Reset

        thread = threading.Thread(target=place_and_reenable)
        thread.start()

    def update_margin_display(self):
        """Update margin display in header"""
        if not self.ig_client.logged_in:
            self.margin_var.set("Margin: --")
            return

        try:
            account_info = self.risk_manager.get_account_info()
            if account_info:
                balance = account_info['balance']
                deposit = account_info['deposit']  # This is margin used

                if balance > 0:
                    margin_ratio = deposit / balance

                    # Color code
                    if margin_ratio >= 0.3:
                        color = "#c55a5a"  # Red
                    elif margin_ratio >= 0.2:
                        color = "#d68a2e"  # Orange
                    else:
                        color = "#5a9d6d"  # Green

                    self.margin_var.set(f"Margin: {margin_ratio:.1%}")
                    self.margin_label.configure(text_color=color)  # Changed .config to .configure
        except Exception as e:
            self.margin_var.set("Margin: Error")
            self.log(f"Margin error: {str(e)}")
            print(f"DEBUG Margin error: {str(e)}")

        # Update every 30 seconds (moved outside try/except)
        if self.ig_client.logged_in:
            self.root.after(30000, self.update_margin_display)

    def on_refresh_orders(self):
        """Handle refresh orders button"""
        if not self.ig_client.logged_in:
            self.log("Not connected")
            return

        positions = self.ig_client.get_open_positions()
        orders = self.ig_client.get_working_orders()

        self.orders_text.delete(1.0, tk.END)

        # Filter positions - exclude items that are actually still working orders
        actual_positions = [
            p for p in positions if 'workingOrderData' not in p]

        if actual_positions:
            self.orders_text.insert(
                tk.END, "=== OPEN POSITIONS ===\n", "header")
            for pos in actual_positions:
                position_data = pos.get("position", {})
                market = pos.get("market", {})
                epic = market.get("epic", "Unknown")
                instrument = market.get("instrumentName", "Unknown")
                direction = position_data.get("direction", "?")
                size = position_data.get("dealSize", "?")
                level = position_data.get("openLevel", "?")
                deal_id = position_data.get("dealId", "?")

                pos_info = f"Epic: {epic} ({instrument})\n"
                pos_info += f"  Direction: {direction}, Size: {size}, Level: {level}, ID: {deal_id}\n\n"
                self.orders_text.insert(tk.END, pos_info)
            self.log(f"Found {len(actual_positions)} open positions")
        else:
            self.orders_text.insert(
                tk.END, "=== OPEN POSITIONS ===\n", "header")
            self.orders_text.insert(tk.END, "No open positions\n\n")

        # Show working orders (and extract epic properly)
        if orders:
            self.orders_text.insert(
                tk.END, "=== WORKING ORDERS ===\n", "header")
            for order in orders:
                order_data = order.get("workingOrderData", {})
                market_data = order.get("marketData", {})

                epic = market_data.get("epic", "Unknown")
                instrument = market_data.get("instrumentName", "Unknown")
                direction = order_data.get("direction", "?")
                size = order_data.get("orderSize", "?")
                level = order_data.get("orderLevel", "?")
                deal_id = order_data.get("dealId", "?")

                order_info = f"Epic: {epic} ({instrument}), Direction: {direction}, Size: {size}, Level: {level}, ID: {deal_id}\n"
                self.orders_text.insert(tk.END, order_info)
            self.log(f"Found {len(orders)} working orders")
        else:
            self.orders_text.insert(
                tk.END, "=== WORKING ORDERS ===\n", "header")
            self.orders_text.insert(tk.END, "No working orders\n")

        self.orders_text.tag_config("header", font=(
            "Consolas", 9, "bold"), foreground="#3498db")

    def on_cancel_all_orders(self):
        """Handle cancel all orders button"""
        if not self.ig_client.logged_in:
            self.log("Not connected")
            return

        if messagebox.askyesno("Confirm", "Cancel all working orders?"):
            orders = self.ig_client.get_working_orders()

            if orders:
                cancelled_count = 0
                for order in orders:
                    deal_id = order.get("workingOrderData", {}).get("dealId")
                    if deal_id:
                        success, message = self.ig_client.cancel_order(deal_id)
                        if success:
                            cancelled_count += 1

                self.log(
                    f"Cancelled {cancelled_count} of {len(orders)} orders")
                self.on_refresh_orders()
            else:
                self.log("No orders to cancel")

                # Clear the internal order list
            if hasattr(self.ladder_strategy, 'placed_orders'):
                self.ladder_strategy.placed_orders = []
                self.log("Internal order tracking cleared")

            self.on_refresh_orders()
        else:
            self.log("No orders to cancel")

    def on_close_positions(self):
        """Handle close positions button"""
        if not self.ig_client.logged_in:
            self.log("Not connected")
            return

        if messagebox.askyesno("Confirm", "Close all open positions?"):
            positions = self.ig_client.get_open_positions()

            if positions:
                closed_count = 0
                for position in positions:
                    deal_id = position.get("position", {}).get("dealId")
                    direction = position.get("position", {}).get("direction")
                    size = position.get("position", {}).get("dealSize")

                    if deal_id and direction and size:
                        success, message = self.ig_client.close_position(
                            deal_id, direction, size
                        )
                        if success:
                            closed_count += 1
                        time.sleep(0.5)

                self.log(
                    f"Closed {closed_count} of {len(positions)} positions")
                self.on_refresh_orders()
            else:
                self.log("No positions to close")

    def on_search_markets(self):
        """Handle search markets button"""
        if not self.ig_client.logged_in:
            self.log("Not connected")
            return

        search_term = simpledialog.askstring(
            "Market Search", "Enter search term (e.g. 'Russell', 'Gold', 'DAX'):"
        )

        if search_term:
            self.log(f"Searching for markets containing '{search_term}'...")
            markets = self.ig_client.search_markets(search_term)

            self.orders_text.delete(1.0, tk.END)

            if markets:
                self.orders_text.insert(
                    tk.END, f"Search results for '{search_term}':\n\n"
                )
                for market in markets[:10]:
                    epic = market.get("epic", "N/A")
                    instrument_name = market.get("instrumentName", "N/A")
                    instrument_type = market.get("instrumentType", "N/A")

                    result_line = f"Epic: {epic}\nName: {instrument_name}\nType: {instrument_type}\n\n"
                    self.orders_text.insert(tk.END, result_line)

                self.log(f"Found {len(markets)} markets for '{search_term}'")
            else:
                self.orders_text.insert(
                    tk.END, f"No markets found for '{search_term}'")
                self.log(f"No markets found for '{search_term}'")

    def run(self):
        """Start the GUI"""
        self.create_gui()
        self.root.mainloop()

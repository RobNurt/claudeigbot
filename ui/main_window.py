"""
Main GUI Window
CustomTkinter-based interface for the IG trading bot with modern UI
"""

from concurrent.futures import thread
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
        self.ladder_strategy = ladder_strategy
        self.auto_strategy = auto_strategy
        self.risk_manager = risk_manager
        self.root = None
        self.auto_trading = False

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
            self.root.title("IG Trading Bot")
            self.root.geometry("1200x1050")

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
                text="IG Trading Bot",
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

            # Create tab contents
            self.create_connection_tab(self.notebook.tab("Connection"))
            self.create_trading_tab(self.notebook.tab("Trading"))
            self.create_risk_tab(self.notebook.tab("Risk Management"))
            self.create_config_tab(self.notebook.tab("Configuration"))

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
                    font=("Segoe UI", 9, "bold")
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
        """Create compact trading tab with large text and no scrolling"""
        # Color scheme
        bg_dark = "#1a1d23"
        card_bg = "#25292e"
        accent_teal = "#5aa89a"
        text_white = "#ddf6f9"
        
        # Main container - NO SCROLLING
        main_container = ctk.CTkFrame(parent, fg_color=bg_dark)
        main_container.pack(fill="x", expand=False, padx=10, pady=10, anchor="n")  # Changed: fill="x" only, expand=False
                
        # === ROW 1: Market & All Controls (EVERYTHING INLINE) ===
        top_row = ctk.CTkFrame(main_container, fg_color=card_bg, corner_radius=8)
        top_row.pack(fill="x", pady=(0, 8))
        
        # Left section - Market
        ctk.CTkLabel(top_row, text="Market:", font=("Segoe UI", 12, "bold"),
                    text_color=text_white).pack(side='left', padx=(10, 5))
        
        self.market_var = ctk.StringVar(value="Gold Spot")
        market_dropdown = ctk.CTkComboBox(
            top_row, variable=self.market_var,
            values=list(self.config.markets.keys()),
            command=lambda x: None,  # Optional callback
            width=150, height=32,
            fg_color=card_bg, button_color=accent_teal,
            button_hover_color="#00f7ced7", border_color="#3e444d",
            font=("Segoe UI", 11)
        )
        market_dropdown.pack(side='left', padx=5)
        
        # Get Price button
        ctk.CTkButton(top_row, text="Price", command=self.on_get_price,
                    fg_color="#3e444d", hover_color="#4a5159",
                    corner_radius=8, width=70, height=32,
                    font=("Segoe UI", 11)).pack(side='left', padx=5)
        
        self.price_var = ctk.StringVar(value="--")
        ctk.CTkLabel(top_row, textvariable=self.price_var,
                    font=("Segoe UI", 11, "bold"),
                    text_color=accent_teal, width=80).pack(side='left', padx=5)
        
        # Separator
        ctk.CTkLabel(top_row, text="|", text_color="#3e444d",
                    font=("Segoe UI", 16)).pack(side='left', padx=8)
        
        # Direction
        ctk.CTkLabel(top_row, text="Dir:", font=("Segoe UI", 11, "bold"),
                    text_color=text_white).pack(side='left', padx=5)
        
        self.direction_var = ctk.StringVar(value="BUY")
        ctk.CTkRadioButton(top_row, text="Buy", variable=self.direction_var,
                        value="BUY", fg_color=accent_teal, hover_color="#00f7cc",
                        font=("Segoe UI", 11)).pack(side='left', padx=3)
        ctk.CTkRadioButton(top_row, text="Sell", variable=self.direction_var,
                        value="SELL", fg_color=accent_teal, hover_color="#00f7cc",
                        font=("Segoe UI", 11)).pack(side='left', padx=3)
        
        # Separator
        ctk.CTkLabel(top_row, text="|", text_color="#3e444d",
                    font=("Segoe UI", 16)).pack(side='left', padx=8)
        
        # Initialize all variables first
        self.offset_var = ctk.StringVar(value="5")
        self.step_var = ctk.StringVar(value="10")
        self.num_orders_var = ctk.StringVar(value="4")
        self.size_var = ctk.StringVar(value="0.5")
        self.retry_jump_var = ctk.StringVar(value="10")
        self.max_retries_var = ctk.StringVar(value="3")
        self.limit_distance_var = ctk.StringVar(value="5")
        
        # Compact parameters
        params = [
            ("Off:", self.offset_var, 45),
            ("Step:", self.step_var, 45),
            ("Ords:", self.num_orders_var, 45),
            ("Size:", self.size_var, 45),
            ("Stop:", self.stop_distance_var, 45),
        ]
        
        for label_text, var, width in params:
            ctk.CTkLabel(top_row, text=label_text, font=("Segoe UI", 11),
                        text_color=text_white).pack(side='left', padx=(8, 2))
            ctk.CTkEntry(top_row, textvariable=var, width=width, height=32,
                        fg_color=card_bg, border_color="#3e444d",
                        font=("Segoe UI", 11)).pack(side='left', padx=2)
        
        # PLACE LADDER BUTTON - Always visible on right
        self.ladder_btn = ctk.CTkButton(top_row, text="PLACE LADDER", command=self.on_place_ladder,
        fg_color="#259d8d", hover_color="#22c55e",
        text_color="#1a1d23",  # ADD THIS - dark text on green button
        corner_radius=8, width=150, height=38,
        font=("Segoe UI", 12, "bold"))
        self.ladder_btn.pack(side="right", padx=10, pady=8)
        
        # === ROW 2: Order Options and Trailing (SIDE BY SIDE) ===
        middle_row = ctk.CTkFrame(main_container, fg_color=bg_dark)
        middle_row.pack(fill="x", pady=(0, 8))
        
        # LEFT: Order Options
        order_card = ctk.CTkFrame(middle_row, fg_color=card_bg, corner_radius=8)
        order_card.pack(side="left", fill="both", expand=True, padx=(0, 4))
        
        ctk.CTkLabel(order_card, text="Order Options",
                    font=("Segoe UI", 12, "bold"), text_color=text_white).pack(pady=(8, 5), padx=10, anchor="w")
        
        opt_row = ctk.CTkFrame(order_card, fg_color=card_bg)
        opt_row.pack(fill="x", pady=(0, 8), padx=10)
        
        ctk.CTkLabel(opt_row, text="Limit Orders:", font=("Segoe UI", 11),
                    text_color=text_white).pack(side='left', padx=5)
        
        self.limit_toggle = ToggleSwitch(opt_row, initial_state=False, 
                                        callback=self.on_limit_toggled, bg=card_bg)
        self.limit_toggle.pack(side='left', padx=5)
        
        ctk.CTkLabel(opt_row, text="Distance:", font=("Segoe UI", 11),
                    text_color=text_white).pack(side='left', padx=(15, 5))
        
        ctk.CTkEntry(opt_row, textvariable=self.limit_distance_var, width=50, height=32,
                    fg_color=card_bg, border_color="#3e444d",
                    font=("Segoe UI", 11)).pack(side='left', padx=2)
        
        ctk.CTkLabel(opt_row, text="pts", font=("Segoe UI", 10),
                    text_color="#9fa6b2").pack(side='left', padx=5)
        
        # RIGHT: Trailing Stop Entry
        trail_card = ctk.CTkFrame(middle_row, fg_color=card_bg, corner_radius=8)
        trail_card.pack(side="right", fill="both", expand=True, padx=(4, 0))
        
        ctk.CTkLabel(trail_card, text="Trailing Stop Entry",
                    font=("Segoe UI", 12, "bold"), text_color=text_white).pack(pady=(8, 5), padx=10, anchor="w")
        
        trail_row = ctk.CTkFrame(trail_card, fg_color=card_bg)
        trail_row.pack(fill="x", pady=(0, 8), padx=10)
        
        ctk.CTkLabel(trail_row, text="Enable:", font=("Segoe UI", 11),
                    text_color=text_white).pack(side='left', padx=5)
        
        self.trailing_toggle = ToggleSwitch(trail_row, initial_state=False,
                                        callback=self.on_trailing_toggled, bg=card_bg)
        self.trailing_toggle.pack(side='left', padx=5)
        
        # Initialize trailing variables
        self.trailing_min_move_var = ctk.StringVar(value="0.5")
        self.trailing_check_interval_var = ctk.StringVar(value="30")
        
        ctk.CTkLabel(trail_row, text="Min:", font=("Segoe UI", 11),
                    text_color=text_white).pack(side='left', padx=(15, 2))
        
        ctk.CTkEntry(trail_row, textvariable=self.trailing_min_move_var, width=50, height=32,
                    fg_color=card_bg, border_color="#3e444d",
                    font=("Segoe UI", 11)).pack(side='left', padx=2)
        
        ctk.CTkLabel(trail_row, text="Check:", font=("Segoe UI", 11),
                    text_color=text_white).pack(side='left', padx=(10, 2))
        
        ctk.CTkEntry(trail_row, textvariable=self.trailing_check_interval_var, width=50, height=32,
                    fg_color=card_bg, border_color="#3e444d",
                    font=("Segoe UI", 11)).pack(side='left', padx=2)
        
        ctk.CTkLabel(trail_row, text="sec", font=("Segoe UI", 10),
                    text_color="#9fa6b2").pack(side='left', padx=2)
        
        # === ROW 3: Stop Management ===
        stop_row = ctk.CTkFrame(main_container, fg_color=card_bg, corner_radius=8)
        stop_row.pack(fill="x", pady=(0, 8))
        
        ctk.CTkLabel(stop_row, text="Stop Management",
                    font=("Segoe UI", 12, "bold"), text_color=text_white).pack(side='left', pady=8, padx=10)
        
        ctk.CTkLabel(stop_row, text="Update All:", font=("Segoe UI", 11),
                    text_color=text_white).pack(side='left', padx=10)
        
        self.bulk_stop_distance_var = ctk.StringVar(value="20")
        ctk.CTkEntry(stop_row, textvariable=self.bulk_stop_distance_var, width=50, height=32,
                    fg_color=card_bg, border_color="#3e444d",
                    font=("Segoe UI", 11)).pack(side='left', padx=2)
        
        ctk.CTkLabel(stop_row, text="pts", font=("Segoe UI", 10),
                    text_color="#9fa6b2").pack(side='left', padx=5)
        
        ctk.CTkButton(stop_row, text="Update Stops",
                    command=self.on_bulk_update_stops,
                    fg_color=accent_teal, hover_color="#2be9c9",
                    corner_radius=8, width=130, height=32,
                    font=("Segoe UI", 11, "bold")).pack(side='left', padx=10)
        
        # Separator
        ctk.CTkLabel(stop_row, text="|", text_color="#3e444d",
                    font=("Segoe UI", 16)).pack(side='left', padx=15)
        
        ctk.CTkLabel(stop_row, text="Auto-apply:", font=("Segoe UI", 11),
                    text_color=text_white).pack(side='left', padx=5)
        
        self.auto_stop_toggle = ToggleSwitch(
            stop_row, initial_state=True, callback=self.on_auto_stop_toggled, bg=card_bg)
        self.auto_stop_toggle.pack(side='left', padx=5)
        
        self.auto_stop_distance_var = ctk.StringVar(value="20")
        ctk.CTkEntry(stop_row, textvariable=self.auto_stop_distance_var, width=50, height=32,
                    fg_color=card_bg, border_color="#3e444d",
                    font=("Segoe UI", 11)).pack(side='left', padx=5)
        
        ctk.CTkLabel(stop_row, text="pts when triggered",
                    font=("Segoe UI", 10), text_color="#9fa6b2").pack(side='left', padx=5)
        
    def on_bulk_update_stops(self):
        """Update stop losses on all working orders"""
        if not self.ig_client.logged_in:
            self.log("Not connected")
            return
        
        try:
            stop_distance = float(self.bulk_stop_distance_var.get())
            
            if stop_distance <= 0:
                self.log("Stop distance must be greater than 0")
                return
            
            self.log(f"Updating all working order stops to {stop_distance} points...")
            
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
                        current_level = order_data.get('level')
                        
                        if deal_id and current_level:
                            success, message = self.ig_client.update_working_order(
                                deal_id, current_level, stop_distance=stop_distance
                            )
                            
                            if success:
                                updated += 1
                            else:
                                failed += 1
                                self.log(f"Failed to update {deal_id}: {message}")
                            
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

    def create_risk_tab(self, parent):
            """Create risk management tab - placeholder for now"""
            card_bg = "#252a31"
            text_white = "#f4f5f7"
            
            placeholder = ctk.CTkFrame(parent, fg_color=card_bg, corner_radius=10)
            placeholder.pack(expand=True, padx=20, pady=20)
            
            ctk.CTkLabel(
                placeholder,
                text="Risk Management Features",
                font=("Segoe UI", 14, "bold"),
                text_color=text_white
            ).pack(pady=20)
            
            ctk.CTkLabel(
                placeholder,
                text="Account overview and risk limits will appear here.\nFunctionality coming soon!",
                font=("Segoe UI", 11),
                text_color="#9fa6b2"
            ).pack(pady=10)

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
        # Remove the messagebox - just execute immediately
        self.log("EMERGENCY STOP ACTIVATED")

        # Stop auto trading if running
        if self.auto_strategy.running:
            self.auto_strategy.stop()

        # Set emergency flag
        self.ig_client.trigger_emergency_stop()

        # Cancel all orders
        self.log("Cancelling all working orders...")
        orders = self.ig_client.get_working_orders()
        for order in orders:
            deal_id = order.get("workingOrderData", {}).get("dealId")
            if deal_id:
                self.ig_client.cancel_order(deal_id)
                time.sleep(0.2)

        # Close all positions
        self.log("Closing all open positions...")
        positions = self.ig_client.get_open_positions()
        for position in positions:
            deal_id = position.get("position", {}).get("dealId")
            direction = position.get("position", {}).get("direction")
            size = position.get("position", {}).get("dealSize")

            if deal_id and direction and size:
                self.ig_client.close_position(deal_id, direction, size)
                time.sleep(0.5)

        self.log("EMERGENCY STOP COMPLETE - All positions closed")
        self.ig_client.reset_emergency_stop()
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
        """Handle place ladder button with optional feature checks"""
        
        # CHECK FOR CANCEL FIRST - before anything else
        if self.ladder_btn.cget("text") == "Cancel Ladder":
            self.ladder_strategy.cancel_requested = True
            self.log("Cancelling ladder placement...")
            return
        
        # NOW check if connected
        if not self.ig_client.logged_in:
            self.log("Not connected")
            return

        # Disable button and change to Cancel
        self.ladder_btn.configure(state="normal", text="Cancel Ladder")
        
        try:
            # Get all the parameters FIRST
            selected_market = self.market_var.get()
            epic = self.config.markets.get(selected_market)
            direction = self.direction_var.get()
            start_offset = float(self.offset_var.get())
            step_size = float(self.step_var.get())
            num_orders = int(self.num_orders_var.get())
            order_size = float(self.size_var.get())
            retry_jump = float(self.retry_jump_var.get())
            max_retries = int(self.max_retries_var.get())
            stop_distance = float(self.stop_distance_var.get())
            guaranteed_stop = self.use_guaranteed_stops.get()

            # Check margin before placing
            margin_ok, new_margin_ratio, required_margin = self.risk_manager.check_margin_for_order(
                epic, order_size * num_orders, margin_limit=0.3
            )

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
                    self.ladder_btn.configure(state="normal", text="Place Ladder")
                    return

            # Use the toggle switch state for limits
            limit_distance = float(
                self.limit_distance_var.get()) if self.limit_toggle.get() else 0

            # DEBUG - see what we're getting
            print(
                f"DEBUG on_place_ladder: limit_toggle state = {self.limit_toggle.get()}")
            print(
                f"DEBUG on_place_ladder: limit_distance_var = {self.limit_distance_var.get()}")
            print(
                f"DEBUG on_place_ladder: calculated limit_distance = {limit_distance}")

            # Optional risk check
            if self.use_risk_management.get():
                can_trade, safety_checks = self.risk_manager.can_trade(
                    order_size, epic)
                if not can_trade:
                    self.log("TRADING BLOCKED - Risk limits exceeded:")
                    for check_name, passed, message in safety_checks:
                        if not passed:
                            self.log(f"  {check_name}: {message}")
                    self.ladder_btn.configure(state="normal", text="Place Ladder")
                    return
                else:
                    self.log("Risk check passed")
            else:
                self.log(
                    "Risk management disabled - trading without safety checks")

            # NOW log with the variables defined
            self.log(
                f"Placing {num_orders} {direction} orders for {selected_market}")
            if limit_distance > 0:
                self.log(
                    f"With limit orders at {limit_distance} points distance")

            # Create wrapper to re-enable button when done
            def place_and_reenable():
                try:
                    self.ladder_strategy.place_ladder(epic, direction, start_offset, step_size,
                                                      num_orders, order_size, retry_jump, max_retries,
                                                      self.log, limit_distance, stop_distance, guaranteed_stop)
                finally:
                    self.root.after(0, lambda: self.ladder_btn.configure(
                        state="normal", text="Place Ladder"))

            thread = threading.Thread(target=place_and_reenable)
            thread.daemon = True
            thread.start()

        except ValueError as e:
            self.log(f"Invalid parameters: {str(e)}")
            self.ladder_btn.configure(state="normal", text="Place Ladder")

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

"""
Main GUI Window
Tkinter-based interface for the IG trading bot with improved aesthetics
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import threading
import time

class ToggleSwitch(tk.Canvas):
    """Toggle switch - Green=ON, Red=OFF"""
    def __init__(self, parent, initial_state=False, callback=None, **kwargs):
        super().__init__(parent, width=50, height=24, highlightthickness=0, bg=kwargs.get('bg', '#f8f9fb'))
        self.callback = callback
        self.state = initial_state
        self.color_on = '#4CAF50'
        self.color_off = '#f44336'
        
        self.bg_rect = self.create_rectangle(0, 0, 50, 24, fill=self.color_off, outline='', tags='bg')
        self.knob = self.create_oval(2, 2, 22, 22, fill='#ffffff', outline='', tags='knob')
        
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
            self.log(f"{'Adding' if state else 'Removing'} limits on existing orders...")
            # Run in background
            threading.Thread(target=self.ladder_strategy.toggle_limits, 
                             args=(state, float(self.limit_distance_var.get()), self.log), 
                             daemon=True).start()
        else:
            self.log(f"Limits: {'ON' if state else 'OFF'} - will apply to new orders")

    def on_trailing_toggled(self, state):
        """Handle trailing toggle"""
        if state:
            self.log("Trailing enabled - entries will follow price")
            self.ladder_strategy.start_trailing(self.log)
        else:
            self.log("Trailing stopped")
            self.ladder_strategy.stop_trailing()

    def create_gui(self):
        """Create the GUI with improved contrast and layout"""
        self.root = tk.Tk()
        self.root.title("IG Trading Bot")
        self.root.geometry("1100x950")

        self.use_risk_management = tk.BooleanVar(value=False)
        self.use_limit_orders = tk.BooleanVar(value=True)
        self.use_auto_replace = tk.BooleanVar(value=False)
        self.use_trailing_stops = tk.BooleanVar(value=False)
        self.stop_distance_var = tk.StringVar(value="20")
        self.use_guaranteed_stops = tk.BooleanVar(value=False)

        # Better background color - pale blue
        bg_color = "#dce6f0"
        self.root.configure(bg=bg_color)

        style = ttk.Style()
        style.theme_use("clam")

        # Stronger colors with better contrast
        card_bg = "#f8f9fb"
        accent_color = "#4a7ba7"  # Darker blue
        success_color = "#5a9d6d"  # Darker green
        danger_color = "#c55a5a"  # Darker red
        text_dark = "#1a2332"
        text_medium = "#4a5568"

        style.configure(
            "Title.TLabel",
            font=("Segoe UI", 14, "bold"),
            background=bg_color,
            foreground=text_dark,
        )
        style.configure(
            "Connected.TLabel",
            font=("Segoe UI", 10, "bold"),
            background=card_bg,
            foreground=success_color,
        )
        style.configure(
            "Disconnected.TLabel",
            font=("Segoe UI", 10, "bold"),
            background=card_bg,
            foreground=text_medium,
        )
        style.configure(
            "Success.TButton",
            background=success_color,
            foreground="white",
            font=("Segoe UI", 9, "bold"),
            borderwidth=0,
        )
        style.configure(
            "Danger.TButton",
            background=danger_color,
            foreground="white",
            font=("Segoe UI", 9, "bold"),
            borderwidth=0,
        )
        style.configure(
            "Emergency.TButton",
            background="#b83232",
            foreground="white",
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
        )
        style.configure(
            "Primary.TButton",
            background=accent_color,
            foreground="white",
            font=("Segoe UI", 9, "bold"),
            borderwidth=0,
        )
        style.configure(
            "Secondary.TButton",
            background="#7a8a9a",
            foreground="white",
            font=("Segoe UI", 9, "bold"),
            borderwidth=0,
        )

        style.configure("TLabelframe", background=card_bg, relief="flat", borderwidth=1)
        style.configure(
            "TLabelframe.Label",
            background=card_bg,
            foreground=text_dark,
            font=("Segoe UI", 10, "bold"),
        )

        # Header
        header_frame = tk.Frame(self.root, bg=bg_color)
        header_frame.pack(fill="x", pady=10, padx=15)

        title_label = ttk.Label(
            header_frame, text="IG Trading Bot", style="Title.TLabel"
        )
        title_label.pack(side="left")

        self.panic_btn = ttk.Button(
            header_frame,
            text="⚠ EMERGENCY STOP",
            command=self.on_panic,
            style="Emergency.TButton",
        )
        self.panic_btn.pack(side="right", ipadx=15, ipady=8)

        # Notebook
        style.configure("TNotebook", background=bg_color, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background="#c5d5e5",
            foreground=text_dark,
            padding=[20, 10],
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", card_bg)],
            foreground=[("selected", text_dark)],
        )

        notebook = ttk.Notebook(self.root)

        conn_frame = tk.Frame(notebook, bg=bg_color)
        notebook.add(conn_frame, text="Connection")
        self.create_connection_tab(conn_frame)

        trade_frame = tk.Frame(notebook, bg=bg_color)
        notebook.add(trade_frame, text="Trading")
        self.create_trading_tab(trade_frame)

        risk_frame = tk.Frame(notebook, bg=bg_color)
        notebook.add(risk_frame, text="Risk Management")
        self.create_risk_tab(risk_frame)

        config_frame = tk.Frame(notebook, bg=bg_color)
        notebook.add(config_frame, text="Configuration")
        self.create_config_tab(config_frame)

        notebook.pack(expand=True, fill="both", padx=15, pady=5)

        # Bottom section - split into two columns
        bottom_frame = tk.Frame(self.root, bg=bg_color)
        bottom_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Left column - Order Management
        left_col = tk.Frame(bottom_frame, bg=bg_color, width=700)
        left_col.pack(side="left", fill="both", expand=False, padx=(0, 7))
        left_col.pack_propagate(False)

        # Right column - Activity Log
        right_col = tk.Frame(bottom_frame, bg=bg_color)
        right_col.pack(side="right", fill="both", expand=True, padx=(7, 0))

        # Activity Log (right column)
        log_frame = ttk.LabelFrame(right_col, text="Activity Log", padding=10)
        log_frame.pack(fill="both", expand=True)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            width=50,
            height=15,
            bg="#ffffff",
            fg="#2d7a4f",
            font=("Consolas", 9, "bold"),
            relief="flat",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground="#b0c4de",
        )
        self.log_text.pack(fill="both", expand=True)

        # Store left_col for use in trading tab
        self.bottom_left_col = left_col
        
        # Create Order Management in the left column
        orders_frame = ttk.LabelFrame(left_col, text="Order Management", padding=12)
        orders_frame.pack(fill="both", expand=True, padx=5, pady=5)

        btn_frame = tk.Frame(orders_frame, bg="#f8f9fb")
        btn_frame.pack(fill="x", pady=5)

        buttons = [
            ("Refresh", self.on_refresh_orders, "Primary.TButton"),
            ("Cancel Orders", self.on_cancel_all_orders, "Danger.TButton"),
            ("Close Positions", self.on_close_positions, "Danger.TButton"),
            ("Search Markets", self.on_search_markets, "Secondary.TButton"),
            ("TEST Stop", self.test_stop_update, "Secondary.TButton"),
        ]

        for text, cmd, style in buttons:
            ttk.Button(btn_frame, text=text, command=cmd, style=style).pack(
                side="left", padx=4, ipadx=10, ipady=3
            )

        # Orders display area
        self.orders_text = scrolledtext.ScrolledText(
            orders_frame,
            width=60,
            height=15,
            bg="#ffffff",
            fg="#1a2332",
            font=("Consolas", 9),
            relief="flat",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground="#b0c4de",
        )
        self.orders_text.pack(fill="both", expand=True, pady=8)

    def create_connection_tab(self, parent):
        """Create connection tab contents"""
        center_frame = tk.Frame(parent, bg="#dce6f0")
        center_frame.pack(expand=True)

        status_frame = ttk.LabelFrame(
            center_frame, text="Connection Status", padding=30
        )
        status_frame.pack(pady=20, padx=20)

        ttk.Label(status_frame, text="Account Type:", font=("Segoe UI", 10)).grid(
            row=0, column=0, sticky="w", padx=10, pady=15
        )
        self.account_var = tk.StringVar(value="DEMO")

        radio_frame = tk.Frame(status_frame, bg="#f8f9fb")
        radio_frame.grid(row=0, column=1, columnspan=2, sticky="w", padx=15)

        ttk.Radiobutton(
            radio_frame, text="Demo Account", variable=self.account_var, value="DEMO"
        ).pack(side="left", padx=15)
        ttk.Radiobutton(
            radio_frame, text="Live Account", variable=self.account_var, value="LIVE"
        ).pack(side="left", padx=15)

        self.connect_btn = ttk.Button(
            status_frame,
            text="Connect",
            command=self.on_connect,
            style="Primary.TButton",
        )
        self.connect_btn.grid(
            row=1, column=0, columnspan=3, pady=25, ipadx=40, ipady=10
        )

        self.status_var = tk.StringVar(value="Disconnected")
        self.status_label = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            style="Disconnected.TLabel",
            font=("Segoe UI", 12),
        )
        self.status_label.grid(row=2, column=0, columnspan=3, pady=15)

    def create_trading_tab(self, parent):
        """Create trading tab with more compact layout"""
        # Market selection
        market_frame = ttk.LabelFrame(parent, text="Market Selection", padding=10)
        market_frame.pack(pady=8, padx=20, fill="x")

        market_row = tk.Frame(market_frame, bg="#f8f9fb")
        market_row.pack(fill="x", pady=3)

        ttk.Label(market_row, text="Market:", font=("Segoe UI", 9, "bold")).pack(
            side="left", padx=5
        )
        self.market_var = tk.StringVar(value="Gold Spot")
        market_combo = ttk.Combobox(
            market_row,
            textvariable=self.market_var,
            values=list(self.config.markets.keys()),
            width=22,
            font=("Segoe UI", 9),
        )
        market_combo.pack(side="left", padx=5)

        price_btn = ttk.Button(
            market_row,
            text="Get Price",
            command=self.on_get_price,
            style="Secondary.TButton",
        )
        price_btn.pack(side="left", padx=5, ipadx=8, ipady=3)

        self.price_var = tk.StringVar(value="Price: --")
        price_label = ttk.Label(
            market_row,
            textvariable=self.price_var,
            font=("Segoe UI", 10, "bold"),
            foreground="#7b4397",
        )
        price_label.pack(side="left", padx=15)

        # Ladder configuration - SINGLE ROW
        ladder_frame = ttk.LabelFrame(parent, text="Ladder Configuration", padding=10)
        ladder_frame.pack(pady=8, padx=20, fill="x")

        config_row = tk.Frame(ladder_frame, bg="#f8f9fb")
        config_row.pack(fill="x", pady=3)

        # Direction
        ttk.Label(config_row, text="Dir:", font=("Segoe UI", 9, "bold")).pack(
            side="left", padx=3
        )
        self.direction_var = tk.StringVar(value="BUY")
        ttk.Radiobutton(
            config_row, text="Buy", variable=self.direction_var, value="BUY"
        ).pack(side="left", padx=2)
        ttk.Radiobutton(
            config_row, text="Sell", variable=self.direction_var, value="SELL"
        ).pack(side="left", padx=2)

        ttk.Separator(config_row, orient="vertical").pack(side="left", fill="y", padx=8)

        # Initialize variables
        self.offset_var = tk.StringVar(value="5")
        self.step_var = tk.StringVar(value="10")
        self.num_orders_var = tk.StringVar(value="4")
        self.size_var = tk.StringVar(value="1")
        self.retry_jump_var = tk.StringVar(value="10")
        self.max_retries_var = tk.StringVar(value="3")
        self.limit_distance_var = tk.StringVar(value="0")
        # stop_distance_var is already initialized in create_gui

        # Parameters
        params = [
            ("Offset:", self.offset_var),
            ("Step:", self.step_var),
            ("Orders:", self.num_orders_var),
            ("Size:", self.size_var),
            ("Retry:", self.retry_jump_var),
            ("MaxRetry:", self.max_retries_var),
            ("Stop:", self.stop_distance_var),
            ("Limit:", self.limit_distance_var),
        ]

        for label_text, var in params:
            ttk.Label(config_row, text=label_text, font=("Segoe UI", 8)).pack(
                side="left", padx=2
            )
            ttk.Entry(config_row, textvariable=var, width=6).pack(side="left", padx=1)

        ttk.Separator(config_row, orient="vertical").pack(side="left", fill="y", padx=8)

        # Guaranteed stop checkbox (use_guaranteed_stops already initialized in create_gui)
        ttk.Checkbutton(config_row, text="Guar.", variable=self.use_guaranteed_stops).pack(
            side="left", padx=2
        )

        self.ladder_btn = ttk.Button(
            config_row,
            text="Place Ladder",
            command=self.on_place_ladder,
            style="Success.TButton",
        )
        self.ladder_btn.pack(side="left", padx=5, ipadx=15, ipady=6)

        # Toggle switches section
        toggles_frame = ttk.LabelFrame(parent, text="Order Options", padding=10)
        toggles_frame.pack(pady=8, padx=20, fill="x")

        toggle_row = tk.Frame(toggles_frame, bg='#f8f9fb')
        toggle_row.pack(fill="x", pady=5)

        # Limit toggle
        tk.Label(toggle_row, text="Limit Orders:", font=('Segoe UI', 9), bg='#f8f9fb').pack(side='left', padx=5)
        self.limit_toggle = ToggleSwitch(toggle_row, initial_state=False, callback=self.on_limit_toggled, bg='#f8f9fb')
        self.limit_toggle.pack(side='left', padx=5)

        tk.Label(toggle_row, text="Distance:", font=('Segoe UI', 8), bg='#f8f9fb').pack(side='left', padx=5)
        # Use existing limit_distance_var
        ttk.Entry(toggle_row, textvariable=self.limit_distance_var, width=6).pack(side='left', padx=2)

        # Trailing toggle
        tk.Label(toggle_row, text="Trailing:", font=('Segoe UI', 9), bg='#f8f9fb').pack(side='left', padx=20)
        self.trailing_toggle = ToggleSwitch(toggle_row, initial_state=False, callback=self.on_trailing_toggled, bg='#f8f9fb')
        self.trailing_toggle.pack(side='left', padx=5)

    def create_risk_tab(self, parent):
        """Create risk management tab"""
        # Account Overview Section
        account_frame = ttk.LabelFrame(parent, text="Account Overview", padding=15)
        account_frame.pack(pady=10, padx=20, fill="x")

        account_grid = tk.Frame(account_frame, bg="#f8f9fb")
        account_grid.pack(fill="x")

        # Account metrics - 2 columns
        self.balance_var = tk.StringVar(value="Balance: --")
        self.available_var = tk.StringVar(value="Available: --")
        self.daily_pnl_var = tk.StringVar(value="Daily P&L: --")
        self.unrealized_pnl_var = tk.StringVar(value="Unrealized P&L: --")

        ttk.Label(
            account_grid, textvariable=self.balance_var, font=("Segoe UI", 11, "bold")
        ).grid(row=0, column=0, sticky="w", padx=20, pady=5)
        ttk.Label(
            account_grid, textvariable=self.available_var, font=("Segoe UI", 11)
        ).grid(row=0, column=1, sticky="w", padx=20, pady=5)
        ttk.Label(
            account_grid, textvariable=self.daily_pnl_var, font=("Segoe UI", 11, "bold")
        ).grid(row=1, column=0, sticky="w", padx=20, pady=5)
        ttk.Label(
            account_grid, textvariable=self.unrealized_pnl_var, font=("Segoe UI", 11)
        ).grid(row=1, column=1, sticky="w", padx=20, pady=5)

        # Risk Limits Section
        limits_frame = ttk.LabelFrame(parent, text="Risk Limits & Status", padding=15)
        limits_frame.pack(pady=10, padx=20, fill="x")

        limits_grid = tk.Frame(limits_frame, bg="#f8f9fb")
        limits_grid.pack(fill="x")

        self.positions_var = tk.StringVar(value="Positions: --")
        self.daily_loss_var = tk.StringVar(value="Daily Loss Limit: --")
        self.margin_usage_var = tk.StringVar(value="Margin Usage: --")
        self.exposure_var = tk.StringVar(value="Total Exposure: --")

        ttk.Label(
            limits_grid, textvariable=self.positions_var, font=("Segoe UI", 10)
        ).grid(row=0, column=0, sticky="w", padx=20, pady=3)
        ttk.Label(
            limits_grid, textvariable=self.daily_loss_var, font=("Segoe UI", 10)
        ).grid(row=0, column=1, sticky="w", padx=20, pady=3)
        ttk.Label(
            limits_grid, textvariable=self.margin_usage_var, font=("Segoe UI", 10)
        ).grid(row=1, column=0, sticky="w", padx=20, pady=3)
        ttk.Label(
            limits_grid, textvariable=self.exposure_var, font=("Segoe UI", 10)
        ).grid(row=1, column=1, sticky="w", padx=20, pady=3)

        # Risk Controls Section
        controls_frame = ttk.LabelFrame(parent, text="Risk Controls", padding=15)
        controls_frame.pack(pady=10, padx=20, fill="x")

        controls_row = tk.Frame(controls_frame, bg="#f8f9fb")
        controls_row.pack(fill="x", pady=5)

    def create_config_tab(self, parent):
        """Create configuration tab for optional features"""
        # Optional Features Section
        features_frame = ttk.LabelFrame(parent, text="Optional Features", padding=15)
        features_frame.pack(pady=10, padx=20, fill="x")
                
        ttk.Checkbutton(features_frame, text="Enable Risk Management", 
                    variable=self.use_risk_management).pack(anchor="w", pady=3)
        ttk.Checkbutton(features_frame, text="Enable Limit Orders", 
                    variable=self.use_limit_orders).pack(anchor="w", pady=3)
        ttk.Checkbutton(features_frame, text="Enable Auto-Replace Strategy", 
                    variable=self.use_auto_replace).pack(anchor="w", pady=3)
        ttk.Checkbutton(features_frame, text="Enable Trailing Stops", 
                    variable=self.use_trailing_stops).pack(anchor="w", pady=3)
        
        # Status display
        status_frame = ttk.LabelFrame(parent, text="Feature Status", padding=15)
        status_frame.pack(pady=10, padx=20, fill="x")
        
        self.feature_status_text = scrolledtext.ScrolledText(status_frame, width=80, height=8,
                                                            bg='#ffffff', fg='#1a2332',
                                                            font=('Consolas', 9),
                                                            relief='flat', borderwidth=1)
        self.feature_status_text.pack(fill="both", expand=True, pady=5)
        
        # Update status initially
        self.update_feature_status()
        
        # Button to refresh status
        ttk.Button(status_frame, text="Update Status", command=self.update_feature_status,
                style='Primary.TButton').pack(pady=5)
        
    def update_feature_status(self):
        """Update feature status display"""
        self.feature_status_text.delete(1.0, tk.END)
        
        timestamp = time.strftime("%H:%M:%S")
        self.feature_status_text.insert(tk.END, f"[{timestamp}] Feature Status:\n\n")
        
        features = [
            ("Risk Management", self.use_risk_management.get()),
            ("Limit Orders", self.use_limit_orders.get()),
            ("Auto-Replace", self.use_auto_replace.get()),
            ("Trailing Stops", self.use_trailing_stops.get())
        ]
        
        for name, enabled in features:
            status = "ENABLED" if enabled else "DISABLED"
            color = "enabled" if enabled else "disabled"
            self.feature_status_text.insert(tk.END, f"{name}: {status}\n", color)
        
        # Configure colors
        self.feature_status_text.tag_config('enabled', foreground='#27ae60', font=('Consolas', 9, 'bold'))
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
                self.available_var.set(f"Available: £{summary['available_funds']:.2f}")

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

                loss_remaining = summary["daily_loss_limit"] - abs(min(0, daily_pnl))
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
        if messagebox.askyesno(
            "EMERGENCY STOP",
            "This will:\n- Stop all auto trading\n- Cancel all pending orders\n- Close all open positions\n\nContinue?",
            icon="warning",
        ):
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

        success, message = self.ig_client.update_position_stop(deal_id, test_stop)
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
                        self.log_text.insert(tk.END, log_message + "\n")
                        self.log_text.see(tk.END)
                    except:
                        pass
                self.root.after(0, do_update)
        except:
            pass  # If there's any issue, at least we printed to console
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
                self.status_label.config(style="Connected.TLabel")
                self.connect_btn.config(text="Disconnect", style="Danger.TButton")
                self.log(message)
            else:
                self.status_var.set("Connection failed")
                self.status_label.config(style="Disconnected.TLabel")
                self.log(message)
        else:
            self.ig_client.disconnect()
            self.status_var.set("Disconnected")
            self.status_label.config(style="Disconnected.TLabel")
            self.connect_btn.config(text="Connect", style="Primary.TButton")
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
        
        if not self.ig_client.logged_in:
            self.log("Not connected")
            return

        # Disable button to prevent accidental multiple triggers
        self.ladder_btn.config(state="disabled", text="Placing...")
        
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
            
            # Use the toggle switch state for limits
            limit_distance = float(self.limit_distance_var.get()) if self.limit_toggle.get() else 0
            
            # DEBUG - see what we're getting
            print(f"DEBUG on_place_ladder: limit_toggle state = {self.limit_toggle.get()}")
            print(f"DEBUG on_place_ladder: limit_distance_var = {self.limit_distance_var.get()}")
            print(f"DEBUG on_place_ladder: calculated limit_distance = {limit_distance}")

            # Optional risk check
            if self.use_risk_management.get():
                can_trade, safety_checks = self.risk_manager.can_trade(order_size, epic)
                if not can_trade:
                    self.log("TRADING BLOCKED - Risk limits exceeded:")
                    for check_name, passed, message in safety_checks:
                        if not passed:
                            self.log(f"  {check_name}: {message}")
                    self.ladder_btn.config(state="normal", text="Place Ladder")
                    return
                else:
                    self.log("Risk check passed")
            else:
                self.log("Risk management disabled - trading without safety checks")
            
            # NOW log with the variables defined
            self.log(f"Placing {num_orders} {direction} orders for {selected_market}")
            if limit_distance > 0:
                self.log(f"With limit orders at {limit_distance} points distance")
            
            # Create wrapper to re-enable button when done
            def place_and_reenable():
                try:
                    self.ladder_strategy.place_ladder(epic, direction, start_offset, step_size, 
                                                    num_orders, order_size, retry_jump, max_retries, 
                                                    self.log, limit_distance, stop_distance, guaranteed_stop)
                finally:
                    self.root.after(0, lambda: self.ladder_btn.config(state="normal", text="Place Ladder"))
            
            thread = threading.Thread(target=place_and_reenable)
            thread.daemon = True
            thread.start()
            
        except ValueError as e:
            self.log(f"Invalid parameters: {str(e)}")
            self.ladder_btn.config(state="normal", text="Place Ladder")

    def on_refresh_orders(self):
        """Handle refresh orders button"""
        if not self.ig_client.logged_in:
            self.log("Not connected")
            return

        orders = self.ig_client.get_working_orders()
        positions = self.ig_client.get_open_positions()

        self.orders_text.delete(1.0, tk.END)

        # Show positions
        if positions:
            self.orders_text.insert(tk.END, "=== OPEN POSITIONS ===\n", "header")
            for pos in positions:
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
            self.log(f"Found {len(positions)} open positions")
        else:
            self.orders_text.insert(tk.END, "=== OPEN POSITIONS ===\n", "header")
            self.orders_text.insert(tk.END, "No open positions\n\n")

        # Show orders
        if orders:
            self.orders_text.insert(tk.END, "=== WORKING ORDERS ===\n", "header")
            for order in orders:
                order_data = order.get("workingOrderData", {})
                epic = order.get("epic", "Unknown")
                direction = order_data.get("direction", "?")
                size = order_data.get("size", "?")
                level = order_data.get("level", "?")
                deal_id = order_data.get("dealId", "?")

                order_info = f"Epic: {epic}, Direction: {direction}, Size: {size}, Level: {level}, ID: {deal_id}\n"
                self.orders_text.insert(tk.END, order_info)
            self.log(f"Found {len(orders)} working orders")
        else:
            self.orders_text.insert(tk.END, "=== WORKING ORDERS ===\n", "header")
            self.orders_text.insert(tk.END, "No working orders\n")

        self.orders_text.tag_config(
            "header", font=("Consolas", 9, "bold"), foreground="#3498db"
        )

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

                self.log(f"Cancelled {cancelled_count} of {len(orders)} orders")
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

                self.log(f"Closed {closed_count} of {len(positions)} positions")
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
                self.orders_text.insert(tk.END, f"No markets found for '{search_term}'")
                self.log(f"No markets found for '{search_term}'")

    def run(self):
        """Start the GUI"""
        self.create_gui()
        self.root.mainloop()
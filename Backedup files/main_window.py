"""
Main GUI Window
CustomTkinter-based interface for the IG trading bot with modern UI
"""

from concurrent.futures import thread
from position_monitor import PositionMonitor
from api.market_scanner import CachedMarketScanner
from api.trend_analyzer import TrendAnalyzer
from api.notification_system import NotificationSystem
from api.watchlist_manager import WatchlistManager
from api.instrument_groups import InstrumentGroups
import customtkinter as ctk
from tkinter import scrolledtext, messagebox, simpledialog
from typing import List, Dict
import tkinter as tk 
import threading
import time

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")  # "dark" or "light"
ctk.set_default_color_theme("blue")  # We'll override with Polaris colors


class Theme:
    """Centralized theme configuration"""
    
    # Font scale multiplier (1.0 = normal, 1.2 = 20% larger, 0.9 = 10% smaller)
    FONT_SCALE = 1.2  # CHANGE THIS VALUE to resize all fonts
    
    # Font family
    FONT_FAMILY = "Segoe UI"
    
    # Base font sizes (will be multiplied by FONT_SCALE)
    _BASE_TINY = 8
    _BASE_SMALL = 9
    _BASE_NORMAL = 10
    _BASE_MEDIUM = 11
    _BASE_LARGE = 12
    _BASE_XLARGE = 13
    _BASE_XXLARGE = 14
    _BASE_TITLE = 18
    
    # Calculated font sizes (automatically scaled)
    @classmethod
    def _scale(cls, size):
        return int(size * cls.FONT_SCALE)
    
    # Font definitions
    @classmethod
    def font_tiny(cls): 
        return (cls.FONT_FAMILY, cls._scale(cls._BASE_TINY))
    
    @classmethod
    def font_small(cls): 
        return (cls.FONT_FAMILY, cls._scale(cls._BASE_SMALL))
    
    @classmethod
    def font_normal(cls): 
        return (cls.FONT_FAMILY, cls._scale(cls._BASE_NORMAL))
    
    @classmethod
    def font_medium(cls): 
        return (cls.FONT_FAMILY, cls._scale(cls._BASE_MEDIUM))
    
    @classmethod
    def font_large(cls): 
        return (cls.FONT_FAMILY, cls._scale(cls._BASE_LARGE))
    
    @classmethod
    def font_xlarge(cls): 
        return (cls.FONT_FAMILY, cls._scale(cls._BASE_XLARGE))
    
    @classmethod
    def font_xxlarge(cls): 
        return (cls.FONT_FAMILY, cls._scale(cls._BASE_XXLARGE))
    
    @classmethod
    def font_title(cls): 
        return (cls.FONT_FAMILY, cls._scale(cls._BASE_TITLE))
    
    # Bold versions
    @classmethod
    def font_normal_bold(cls): 
        return (cls.FONT_FAMILY, cls._scale(cls._BASE_NORMAL), "bold")
    
    @classmethod
    def font_medium_bold(cls): 
        return (cls.FONT_FAMILY, cls._scale(cls._BASE_MEDIUM), "bold")
    
    @classmethod
    def font_large_bold(cls): 
        return (cls.FONT_FAMILY, cls._scale(cls._BASE_LARGE), "bold")
    
    @classmethod
    def font_xlarge_bold(cls): 
        return (cls.FONT_FAMILY, cls._scale(cls._BASE_XLARGE), "bold")
    
    @classmethod
    def font_xxlarge_bold(cls): 
        return (cls.FONT_FAMILY, cls._scale(cls._BASE_XXLARGE), "bold")
    
    @classmethod
    def font_title_bold(cls): 
        return (cls.FONT_FAMILY, cls._scale(cls._BASE_TITLE), "bold")
    
    # Colors (keep your existing colors)
    BG_DARK = "#1a1d23"
    CARD_BG = "#25292e"
    ACCENT_TEAL = "#3a9d8e"
    TEXT_WHITE = "#e8eaed"
    TEXT_GRAY = "#9fa6b2"
    RED = "#e74c3c"
    GREEN = "#3a9d8e"
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
        self.position_monitor = PositionMonitor(ig_client)
        self.ladder_strategy = ladder_strategy
        self.auto_strategy = auto_strategy
        self.risk_manager = risk_manager
        self.root = None
        self.auto_trading = False
        self.market_details_cache = {} 
        self.instrument_groups = InstrumentGroups()
        
        # Trend Screener initialization
        self.trend_analyzer = TrendAnalyzer()
        self.notification_system = NotificationSystem()
        self.watchlist_manager = WatchlistManager()
        self.trend_screener_running = False 

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
                font=Theme.font_medium(),
                text_color=accent_teal
            )
            self.margin_label.pack(side="left", padx=30)

            # Emergency stop button
            self.panic_btn = ctk.CTkButton(
                header_frame,
                text="CANCEL ALL",
                command=self.on_panic,
                fg_color="#de3618",
                hover_color="#9a6e65",
                font=Theme.font_medium(),
                corner_radius=8,
                width=180,
                height=40
            )
            self.panic_btn.pack(side="right", padx=10)

            # Main vertical PanedWindow - allows resizing tabs vs bottom section
            main_paned = tk.PanedWindow(
                self.root,
                orient=tk.VERTICAL,
                sashwidth=6,
                sashrelief=tk.RAISED,
                bg=bg_dark,
                bd=0
            )
            main_paned.pack(expand=True, fill="both", padx=15, pady=5)

            # Top section - Notebook (Tabview in CustomTkinter)
            notebook_frame = ctk.CTkFrame(main_paned, fg_color=card_bg, corner_radius=10)
            main_paned.add(notebook_frame, minsize=300, stretch="always")
            
            self.notebook = ctk.CTkTabview(notebook_frame, fg_color=card_bg, corner_radius=10)
            self.notebook.pack(expand=True, fill="both")

            # Create tabs
            self.notebook.add("Connection")
            self.notebook.add("Trading")
            self.notebook.add("Risk Management")
            self.notebook.add("Configuration")
            self.notebook.add("Market Research")
            self.notebook.add("Trend Screener")
            self.notebook.add("Orders")        # ← ADD THIS LINE
            self.notebook.add("Positions") 

            # Create tab contents
            self.create_connection_tab(self.notebook.tab("Connection"))
            self.create_trading_tab(self.notebook.tab("Trading"))
            self.create_risk_tab(self.notebook.tab("Risk Management"))
            self.create_config_tab(self.notebook.tab("Configuration"))
            self.create_market_research_tab(self.notebook.tab("Market Research"))
            self.create_trend_screener_tab(self.notebook.tab("Trend Screener"))
            self.create_order_management_tab(self.notebook.tab("Orders"))          # ← ADD THIS LINE
            self.create_position_management_tab(self.notebook.tab("Positions")) 
            

            # Bottom section - HORIZONTAL resizable (Order Management | Log)
            bottom_container = ctk.CTkFrame(main_paned, fg_color=bg_dark, corner_radius=0)
            main_paned.add(bottom_container, minsize=200, stretch="never")
            
            bottom_frame = tk.PanedWindow(
                bottom_container, 
                orient=tk.HORIZONTAL,
                sashwidth=6,
                sashrelief=tk.RAISED,
                bg=bg_dark,
                bd=0
            )
            bottom_frame.pack(fill="both", expand=True, padx=0, pady=0)

            # Left column - Order Management (resizable)
            left_col = ctk.CTkFrame(bottom_frame, fg_color=bg_dark, corner_radius=0)
            bottom_frame.add(left_col, minsize=400, stretch="never")

            # Right column - Activity Log (resizable)
            right_col = ctk.CTkFrame(bottom_frame, fg_color=bg_dark, corner_radius=0)
            bottom_frame.add(right_col, minsize=300, stretch="always")

            # Activity Log (right column)
            log_frame = ctk.CTkFrame(right_col, fg_color=card_bg, corner_radius=10)
            log_frame.pack(fill="both", expand=True)
            
            log_title = ctk.CTkLabel(
                log_frame, 
                text="Activity Log",
                font=Theme.font_large(),
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
                font=Theme.font_large(),
                text_color=text_white
            )
            orders_title.pack(pady=(10, 5), padx=10, anchor="w")

            # Button frame
            btn_frame = ctk.CTkFrame(orders_frame, fg_color=card_bg, corner_radius=0)
            btn_frame.pack(fill="x", pady=5, padx=10)

            buttons = [
                ("Refresh", self.on_refresh_orders, accent_teal),
                ("Cancel Orders", self.on_cancel_all_orders, danger_red),
                ("Close Positions", self.close_all_positions, danger_red),
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
                    font=Theme.font_large()
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
                font=Theme.font_medium(),
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
                font=Theme.font_normal()
            ).pack(side="left", padx=15)

            ctk.CTkRadioButton(
                radio_frame,
                text="Live Account",
                variable=self.account_var,
                value="LIVE",
                fg_color=accent_teal,
                hover_color=accent_teal,
                font=Theme.font_normal()
            ).pack(side="left", padx=15)

            # Connect button
            self.connect_btn = ctk.CTkButton(
                status_frame,
                text="Connect",
                command=self.on_connect,
                fg_color=accent_teal,
                hover_color="#5abba8",
                font=Theme.font_large(),
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
                font=Theme.font_xlarge(),
                text_color=text_white
            )
            self.status_label.grid(row=2, column=0, columnspan=3, pady=(0, 20), padx=20)
            
    def create_trading_tab(self, parent):
        """Create trading tab with better spacing"""
        bg_dark = "#1a1d23"
        card_bg = "#25292e"
        accent_teal = "#3a9d8e"
        text_white = "#e8eaed"
        text_gray = "#9fa6b2"
        
        # Make scrollable
        scrollable_frame = ctk.CTkScrollableFrame(parent, fg_color=bg_dark)
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # ===== ORDER PLACEMENT SECTION =====
        placement_card = ctk.CTkFrame(scrollable_frame, fg_color=card_bg, corner_radius=8)
        placement_card.pack(fill="x", pady=(0, 8))
        
        ctk.CTkLabel(
            placement_card, 
            text="📋 ORDER PLACEMENT",
            font=Theme.font_large(), 
            text_color=text_white
        ).pack(pady=(10, 5))
        
        # Row 1: Market & Price - GRID LAYOUT for better spacing
        row1 = ctk.CTkFrame(placement_card, fg_color=card_bg)
        row1.pack(fill="x", pady=8, padx=20)
        
        ctk.CTkLabel(row1, text="Market:", font=Theme.font_normal(),
                    text_color=text_white, width=60, anchor="w").grid(row=0, column=0, padx=(0,5), sticky="w")
        
        self.market_var = ctk.StringVar(value="Gold Spot")
        ctk.CTkComboBox(
            row1, variable=self.market_var,
            values=list(self.config.markets.keys()),
            width=160, height=30,
            fg_color=card_bg, button_color=accent_teal,
            font=Theme.font_normal()
        ).grid(row=0, column=1, padx=5)
        
        ctk.CTkButton(row1, text="Get Price", command=self.on_get_price,
                    fg_color="#3e444d", hover_color="#4a5159",
                    corner_radius=8, width=90, height=30,
                    font=Theme.font_normal()).grid(row=0, column=2, padx=10)
        
        self.price_var = ctk.StringVar(value="--")
        ctk.CTkLabel(row1, textvariable=self.price_var,
                    font=Theme.font_medium(),
                    text_color=accent_teal, width=100).grid(row=0, column=3, padx=5)
        
        # Row 2: Direction & Parameters - GRID LAYOUT
        row2 = ctk.CTkFrame(placement_card, fg_color=card_bg)
        row2.pack(fill="x", pady=8, padx=20)
        
        ctk.CTkLabel(row2, text="Direction:", font=Theme.font_normal(),
                    text_color=text_white, width=80, anchor="w").grid(row=0, column=0, sticky="w")
        
        self.direction_var = ctk.StringVar(value="BUY")
        dir_frame = ctk.CTkFrame(row2, fg_color=card_bg)
        dir_frame.grid(row=0, column=1, padx=10)
        ctk.CTkRadioButton(dir_frame, text="Buy", variable=self.direction_var,
                        value="BUY", fg_color=accent_teal,
                        font=Theme.font_normal()).pack(side='left', padx=5)
        ctk.CTkRadioButton(dir_frame, text="Sell", variable=self.direction_var,
                        value="SELL", fg_color="#e74c3c",
                        font=Theme.font_normal()).pack(side='left', padx=5)
        
        # Offset
        ctk.CTkLabel(row2, text="Offset:", font=Theme.font_normal(),
                    text_color=text_gray, width=50, anchor="e").grid(row=0, column=2, padx=(20,5))
        self.offset_var = ctk.StringVar(value="5")
        ctk.CTkEntry(row2, textvariable=self.offset_var, width=50, height=30,
                    fg_color=card_bg, border_color="#3e444d",
                    font=Theme.font_normal()).grid(row=0, column=3)
        
        # Step
        ctk.CTkLabel(row2, text="Step:", font=Theme.font_normal(),
                    text_color=text_gray, width=50, anchor="e").grid(row=0, column=4, padx=(20,5))
        self.step_var = ctk.StringVar(value="10")
        ctk.CTkEntry(row2, textvariable=self.step_var, width=50, height=30,
                    fg_color=card_bg, border_color="#3e444d",
                    font=Theme.font_normal()).grid(row=0, column=5)
        
        # Orders
        ctk.CTkLabel(row2, text="Orders:", font=Theme.font_normal(),
                    text_color=text_gray, width=50, anchor="e").grid(row=0, column=6, padx=(20,5))
        self.num_orders_var = ctk.StringVar(value="5")
        ctk.CTkEntry(row2, textvariable=self.num_orders_var, width=50, height=30,
                    fg_color=card_bg, border_color="#3e444d",
                    font=Theme.font_normal()).grid(row=0, column=7)
        
        # Size
        ctk.CTkLabel(row2, text="Size:", font=Theme.font_normal(),
                    text_color=text_gray, width=50, anchor="e").grid(row=0, column=8, padx=(20,5))
        self.size_var = ctk.StringVar(value="0.1")
        ctk.CTkEntry(row2, textvariable=self.size_var, width=50, height=30,
                    fg_color=card_bg, border_color="#3e444d",
                    font=Theme.font_normal()).grid(row=0, column=9)
        
        # Row 3: Retry Parameters - GRID LAYOUT
        row3 = ctk.CTkFrame(placement_card, fg_color=card_bg)
        row3.pack(fill="x", pady=8, padx=20)
        
        ctk.CTkLabel(row3, text="⚙️ Retry:", font=Theme.font_normal(),
                    text_color=text_white, width=80, anchor="w").grid(row=0, column=0, sticky="w")
        
        # Retry Jump with info
        ctk.CTkLabel(row3, text="Jump:", font=Theme.font_normal(),
                    text_color=text_gray, width=50, anchor="e").grid(row=0, column=1, padx=(20,5))
        self.retry_jump_var = ctk.StringVar(value="5")
        ctk.CTkEntry(row3, textvariable=self.retry_jump_var, width=50, height=30,
                    fg_color=card_bg, border_color="#3e444d",
                    font=Theme.font_normal()).grid(row=0, column=2)
        ctk.CTkLabel(row3, text="pts", font=Theme.font_small(),
                    text_color=text_gray).grid(row=0, column=3, padx=2, sticky="w")
        ctk.CTkLabel(row3, text="ℹ️ Distance to adjust if order rejected as too close",
                    font=Theme.font_tiny(), text_color=text_gray).grid(row=0, column=4, padx=10, sticky="w")
        
        # Max Retries
        ctk.CTkLabel(row3, text="Max:", font=Theme.font_normal(),
                    text_color=text_gray, width=50, anchor="e").grid(row=0, column=5, padx=(20,5))
        self.max_retries_var = ctk.StringVar(value="3")
        ctk.CTkEntry(row3, textvariable=self.max_retries_var, width=50, height=30,
                    fg_color=card_bg, border_color="#3e444d",
                    font=Theme.font_normal()).grid(row=0, column=6)
        ctk.CTkLabel(row3, text="attempts", font=Theme.font_small(),
                    text_color=text_gray).grid(row=0, column=7, padx=2, sticky="w")
        ctk.CTkLabel(row3, text="ℹ️ Maximum retry attempts per order",
                    font=Theme.font_tiny(), text_color=text_gray).grid(row=0, column=8, padx=10, sticky="w")
        
        # Row 4: Stop Loss - HIGHLIGHTED BOX
        row4 = ctk.CTkFrame(placement_card, fg_color="#2a2e35", corner_radius=6)
        row4.pack(fill="x", pady=8, padx=20)
        
        # Use grid inside this frame too
        row4_inner = ctk.CTkFrame(row4, fg_color="#2a2e35")
        row4_inner.pack(fill="x", pady=8, padx=15)
        
        ctk.CTkLabel(row4_inner, text="🛡️", font=Theme.font_xxlarge()).grid(row=0, column=0, padx=(0,5))
        
        ctk.CTkLabel(row4_inner, text="Stop Loss:", font=Theme.font_normal(),
                    text_color=text_white).grid(row=0, column=1, padx=5, sticky="w")
        
        self.stop_distance_var = ctk.StringVar(value="20")
        ctk.CTkEntry(row4_inner, textvariable=self.stop_distance_var, width=50, height=30,
                    fg_color=card_bg, border_color="#3e444d",
                    font=Theme.font_normal()).grid(row=0, column=2, padx=5)
        
        ctk.CTkLabel(row4_inner, text="pts", font=Theme.font_small(),
                    text_color=text_gray).grid(row=0, column=3, padx=2)
        
        # GSLO Checkbox
        self.use_gslo = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            row4_inner, 
            text="GSLO", 
            variable=self.use_gslo,
            fg_color=accent_teal,
            font=Theme.font_normal()
        ).grid(row=0, column=4, padx=15)
        
        ctk.CTkLabel(
            row4_inner, 
            text="ℹ️ Guaranteed Stop Loss Order - costs extra, minimum 20pts",
            font=Theme.font_tiny(),
            text_color=text_gray
        ).grid(row=0, column=5, padx=10, sticky="w")
        
        # Row 5: Follow Price
        row5 = ctk.CTkFrame(placement_card, fg_color="#2a2e35", corner_radius=6)
        row5.pack(fill="x", pady=8, padx=20)
        
        row5_inner = ctk.CTkFrame(row5, fg_color="#2a2e35")
        row5_inner.pack(fill="x", pady=8, padx=15)
        
        ctk.CTkLabel(row5_inner, text="📉", font=Theme.font_xxlarge()).grid(row=0, column=0, padx=(0,5))
        
        ctk.CTkLabel(row5_inner, text="Follow Price:", font=Theme.font_normal(),
                    text_color=text_white).grid(row=0, column=1, padx=5, sticky="w")
        
        self.trailing_entry_toggle = ToggleSwitch(
            row5_inner, initial_state=False, callback=self.on_trailing_entry_toggled, bg="#2a2e35")
        self.trailing_entry_toggle.grid(row=0, column=2, padx=10)
        
        # Min Move configuration
        ctk.CTkLabel(row5_inner, text="Min:", font=Theme.font_normal(),
                    text_color=text_gray).grid(row=0, column=3, padx=(20,5), sticky="e")
        self.trailing_min_move_var = ctk.StringVar(value="0.5")
        ctk.CTkEntry(row5_inner, textvariable=self.trailing_min_move_var, width=50, height=28,
                    fg_color=card_bg, border_color="#3e444d",
                    font=Theme.font_normal()).grid(row=0, column=4, padx=2)
        ctk.CTkLabel(row5_inner, text="pts", font=Theme.font_small(),
                    text_color=text_gray).grid(row=0, column=5, padx=(2,15), sticky="w")
        
        # Check Interval configuration
        ctk.CTkLabel(row5_inner, text="Check:", font=Theme.font_normal(),
                    text_color=text_gray).grid(row=0, column=6, padx=5, sticky="e")
        self.trailing_check_interval_var = ctk.StringVar(value="30")
        ctk.CTkEntry(row5_inner, textvariable=self.trailing_check_interval_var, width=50, height=28,
                    fg_color=card_bg, border_color="#3e444d",
                    font=Theme.font_normal()).grid(row=0, column=7, padx=2)
        ctk.CTkLabel(row5_inner, text="sec", font=Theme.font_small(),
                    text_color=text_gray).grid(row=0, column=8, padx=2, sticky="w")
        
        ctk.CTkLabel(row5_inner, text="ℹ️ Moves entries as market moves | BUY trails down, SELL trails up",
                    font=Theme.font_tiny(), text_color=text_gray).grid(row=0, column=9, padx=10, sticky="w")
        
        # Row 6: Action Buttons - CENTERED
        row6 = ctk.CTkFrame(placement_card, fg_color=card_bg)
        row6.pack(fill="x", pady=15, padx=20)
        
        # Center the buttons using grid with column weights
        row6.grid_columnconfigure(0, weight=1)
        row6.grid_columnconfigure(3, weight=1)
        
        self.ladder_btn = ctk.CTkButton(
            row6, text="🎯 PLACE LADDER",
            command=self.on_place_ladder,
            fg_color=accent_teal, hover_color="#4ab39f",
            text_color="black",
            corner_radius=8, width=220, height=45,
            font=Theme.font_xlarge()
        )
        self.ladder_btn.grid(row=0, column=1, padx=10)
        
        ctk.CTkButton(
            row6, text="❌ Cancel All Orders",
            command=self.on_cancel_all_orders,
            fg_color="#e74c3c", hover_color="#ee4626",
            corner_radius=8, width=180, height=45,
            font=Theme.font_medium()
        ).grid(row=0, column=2, padx=10)
        
    def add_to_create_trading_tab(self, parent, scrollable_frame, card_bg, accent_teal, text_white, text_gray):
        """
        ADD THIS CODE TO YOUR create_trading_tab() METHOD
        This goes after the basic ladder setup and before the "On Trigger" section
        """
        
        # ========== INSTRUMENT GROUPS SECTION ==========
        groups_card = ctk.CTkFrame(scrollable_frame, fg_color=card_bg, corner_radius=8)
        groups_card.pack(fill="x", pady=(0, 8))
        
        ctk.CTkLabel(
            groups_card,
            text="📦 INSTRUMENT GROUPS",
            font=Theme.font_large(),
            text_color=text_white
        ).pack(pady=(10, 5))
        
        # Group selection row
        group_row = ctk.CTkFrame(groups_card, fg_color=card_bg)
        group_row.pack(fill="x", pady=8, padx=20)
        
        ctk.CTkLabel(
            group_row, 
            text="Select Group:",
            font=Theme.font_normal(),
            text_color=text_white,
            width=100
        ).grid(row=0, column=0, padx=5, sticky="w")
        
        self.group_var = ctk.StringVar()
        self.group_dropdown = ctk.CTkComboBox(
            group_row,
            variable=self.group_var,
            values=self.instrument_groups.get_all_groups(),
            width=200,
            height=30,
            fg_color=card_bg,
            button_color=accent_teal,
            font=Theme.font_normal(),
            command=self.on_group_selected
        )
        self.group_dropdown.grid(row=0, column=1, padx=10)
        
        ctk.CTkButton(
            group_row,
            text="Place Batch Orders",
            command=self.place_batch_orders,
            fg_color=accent_teal,
            hover_color="#4fb5a6",
            corner_radius=8,
            width=140,
            height=30,
            font=Theme.font_normal()
        ).grid(row=0, column=2, padx=10)
        
        ctk.CTkButton(
            group_row,
            text="Manage Groups",
            command=self.open_group_manager,
            fg_color="#3e444d",
            hover_color="#4a5159",
            corner_radius=8,
            width=120,
            height=30,
            font=Theme.font_normal()
        ).grid(row=0, column=3, padx=5)
        
        # Group preview label
        self.group_preview_label = ctk.CTkLabel(
            groups_card,
            text="Select a group to see instruments...",
            font=Theme.font_small(),
            text_color=text_gray,
            wraplength=800,
            anchor="w"
        )
        self.group_preview_label.pack(fill="x", pady=(5, 10), padx=20)
    
        
        # ===== POSITION MANAGEMENT SECTION =====
        mgmt_card = ctk.CTkFrame(scrollable_frame, fg_color=card_bg, corner_radius=8)
        mgmt_card.pack(fill="x", pady=8)
        
        ctk.CTkLabel(
            mgmt_card, 
            text="📊 POSITION MANAGEMENT",
            font=Theme.font_large(), 
            text_color=text_white
        ).pack(pady=(10, 5))
        
        # Auto-Attach Row - GRID LAYOUT
        auto_frame = ctk.CTkFrame(mgmt_card, fg_color="#2a2e35", corner_radius=6)
        auto_frame.pack(fill="x", pady=8, padx=20)
        
        auto_inner = ctk.CTkFrame(auto_frame, fg_color="#2a2e35")
        auto_inner.pack(fill="x", pady=10, padx=15)
        
        ctk.CTkLabel(
            auto_inner, 
            text="⚡ Auto-attach when filled:",
            font=Theme.font_medium(),
            text_color=text_white,
            width=180,
            anchor="w"
        ).grid(row=0, column=0, padx=(0,20), sticky="w")
        
        # Stop
        ctk.CTkLabel(auto_inner, text="Stop:", font=Theme.font_normal(),
                    text_color=text_gray).grid(row=0, column=1, padx=5, sticky="e")
        
        self.auto_stop_toggle = ToggleSwitch(
            auto_inner, initial_state=True, callback=self.on_auto_stop_toggled, bg="#2a2e35")
        self.auto_stop_toggle.grid(row=0, column=2, padx=5)
        
        self.auto_stop_distance_var = ctk.StringVar(value="20")
        ctk.CTkEntry(auto_inner, textvariable=self.auto_stop_distance_var, width=50, height=28,
                    fg_color=card_bg, border_color="#3e444d",
                    font=Theme.font_normal()).grid(row=0, column=3, padx=5)
        
        ctk.CTkLabel(auto_inner, text="pts", font=Theme.font_small(),
                    text_color=text_gray).grid(row=0, column=4, padx=(2,20))
        
        # Trail
        ctk.CTkLabel(auto_inner, text="Trail:", font=Theme.font_normal(),
                    text_color=text_gray).grid(row=0, column=5, padx=5, sticky="e")
        
        self.auto_trailing_toggle = ToggleSwitch(
            auto_inner, initial_state=False, callback=self.on_auto_trailing_toggled, bg="#2a2e35")
        self.auto_trailing_toggle.grid(row=0, column=6, padx=5)
        
        self.trailing_distance_var = ctk.StringVar(value="15")
        ctk.CTkEntry(auto_inner, textvariable=self.trailing_distance_var, width=45, height=28,
                    fg_color=card_bg, border_color="#3e444d",
                    font=Theme.font_normal()).grid(row=0, column=7, padx=2)
        
        ctk.CTkLabel(auto_inner, text="/", font=Theme.font_normal(),
                    text_color=text_gray).grid(row=0, column=8)
        
        self.trailing_step_var = ctk.StringVar(value="5")
        ctk.CTkEntry(auto_inner, textvariable=self.trailing_step_var, width=45, height=28,
                    fg_color=card_bg, border_color="#3e444d",
                    font=Theme.font_normal()).grid(row=0, column=9, padx=2)
        
        ctk.CTkLabel(auto_inner, text="pts", font=Theme.font_small(),
                    text_color=text_gray).grid(row=0, column=10, padx=(2,20))
        
        # Limit
        ctk.CTkLabel(auto_inner, text="Limit:", font=Theme.font_normal(),
                    text_color=text_gray).grid(row=0, column=11, padx=5, sticky="e")
        
        self.auto_limit_toggle = ToggleSwitch(
            auto_inner, initial_state=False, callback=self.on_auto_limit_toggled, bg="#2a2e35")
        self.auto_limit_toggle.grid(row=0, column=12, padx=5)
        
        self.auto_limit_distance_var = ctk.StringVar(value="10")
        ctk.CTkEntry(auto_inner, textvariable=self.auto_limit_distance_var, width=50, height=28,
                    fg_color=card_bg, border_color="#3e444d",
                    font=Theme.font_normal()).grid(row=0, column=13, padx=5)
        
        ctk.CTkLabel(auto_inner, text="pts", font=Theme.font_small(),
                    text_color=text_gray).grid(row=0, column=14, padx=2)
        
        # Manual Update Row - GRID LAYOUT
        update_frame = ctk.CTkFrame(mgmt_card, fg_color="#2a2e35", corner_radius=6)
        update_frame.pack(fill="x", pady=8, padx=20)
        
        update_inner = ctk.CTkFrame(update_frame, fg_color="#2a2e35")
        update_inner.pack(fill="x", pady=10, padx=15)
        
        ctk.CTkLabel(
            update_inner, 
            text="🔧 Manual updates:",
            font=Theme.font_medium(),
            text_color=text_white,
            width=180,
            anchor="w"
        ).grid(row=0, column=0, padx=(0,20), sticky="w")
        
        ctk.CTkLabel(update_inner, text="Stop distance:", font=Theme.font_normal(),
                    text_color=text_gray).grid(row=0, column=1, padx=5, sticky="e")
        
        self.bulk_stop_distance_var = ctk.StringVar(value="20")
        ctk.CTkEntry(update_inner, textvariable=self.bulk_stop_distance_var, width=50, height=30,
                    fg_color=card_bg, border_color="#3e444d",
                    font=Theme.font_normal()).grid(row=0, column=2, padx=5)
        
        ctk.CTkLabel(update_inner, text="pts", font=Theme.font_small(),
                    text_color=text_gray).grid(row=0, column=3, padx=(2,20))
        
        ctk.CTkButton(
            update_inner, 
            text="📝 Update All Stops",
            command=self.on_update_all_stops,
            fg_color=accent_teal, hover_color="#4ab39f",
            text_color="black",
            corner_radius=8, width=160, height=35,
            font=Theme.font_normal()
        ).grid(row=0, column=4, padx=10)
        
        ctk.CTkLabel(
            update_inner,
            text="ℹ️ Updates stops on both working orders and open positions",
            font=Theme.font_tiny(),
            text_color=text_gray
        ).grid(row=0, column=5, padx=10, sticky="w")
        
        # Close Positions Row
        close_frame = ctk.CTkFrame(mgmt_card, fg_color=card_bg)
        close_frame.pack(fill="x", pady=15, padx=20)
        
        # Center the button
        close_frame.grid_columnconfigure(0, weight=1)
        close_frame.grid_columnconfigure(2, weight=1)
        
        ctk.CTkButton(
            close_frame, 
            text="🔴 Close All Positions",
            command=self.on_close_positions,
            fg_color="#e74c3c", hover_color="#ee4626",
            corner_radius=8, width=200, height=40,
            font=Theme.font_medium()
        ).grid(row=0, column=1)
        
        # Store reference
        self.trading_parent = parent
        
    def create_trading_tab_additions(self):
        """
        ADD THESE SECTIONS TO YOUR EXISTING create_trading_tab() METHOD
        Place them after your existing epic dropdown and before the ladder buttons
        """
        
        # ========== INSTRUMENT GROUPS SECTION ==========
        group_frame = ttk.LabelFrame(trading_tab, text="📦 Instrument Groups", padding=10)
        group_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Group selection row
        group_select_frame = ttk.Frame(group_frame)
        group_select_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(group_select_frame, text="Select Group:").pack(side=tk.LEFT, padx=5)
        
        self.group_var = tk.StringVar()
        self.group_dropdown = ttk.Combobox(
            group_select_frame, 
            textvariable=self.group_var,
            values=self.instrument_groups.get_all_groups(),
            width=25,
            state="readonly"
        )
        self.group_dropdown.pack(side=tk.LEFT, padx=5)
        self.group_dropdown.bind("<<ComboboxSelected>>", self.on_group_selected)
        
        ttk.Button(
            group_select_frame,
            text="Place Batch Orders",
            command=self.place_batch_orders,
            style="Accent.TButton"
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            group_select_frame,
            text="Manage Groups",
            command=self.open_group_manager
        ).pack(side=tk.LEFT, padx=5)
        
        # Group preview (shows instruments in selected group)
        self.group_preview_label = ctk.CTkLabel(
            groups_card,
            text="Select a group to see instruments...",
            font=Theme.font_small(),
            text_color="#9fa6b2",
            wraplength=800,
            anchor="w"
        )
        self.group_preview_label.pack(fill="x", pady=(5, 10), padx=20)


    def on_group_selected(self, event=None):
        """Update preview when group is selected"""
        group_name = self.group_var.get()
        if not group_name:
            return
        
        epics = self.instrument_groups.get_group(group_name)
        if epics:
            # Get friendly names
            friendly_names = []
            for epic in epics:
                name = self.epic_names.get(epic, epic)
                friendly_names.append(name)
            
            preview_text = f"📊 {len(epics)} instruments: {', '.join(friendly_names)}"
            self.group_preview_label.configure(text=preview_text, text_color="black")
        else:
            self.group_preview_label.configure(text="No instruments in group", text_color="red")


    def place_batch_orders(self):
        """Place ladder orders on all instruments in selected group"""
        group_name = self.group_var.get()
        if not group_name:
            messagebox.showwarning("No Group", "Please select an instrument group first")
            return
        
        epics = self.instrument_groups.get_group(group_name)
        if not epics:
            messagebox.showwarning("Empty Group", "Selected group has no instruments")
            return
        
        # Confirm with user
        names = [self.epic_names.get(e, e) for e in epics]
        confirm = messagebox.askyesno(
            "Confirm Batch Orders",
            f"Place ladder orders on these {len(epics)} instruments?\n\n" + "\n".join(f"• {name}" for name in names)
        )
        
        if not confirm:
            return
        
        # Place orders on each instrument
        self.status_label.config(text=f"🚀 Placing batch orders on {len(epics)} instruments...")
        self.root.update()
        
        success_count = 0
        fail_count = 0
        results = []
        
        for epic in epics:
            name = self.epic_names.get(epic, epic)
            try:
                # Place the ladder using your existing logic
                # This assumes you have a method to place ladder orders
                # Adjust the method name/parameters to match your actual implementation
                
                self.status_label.config(text=f"📊 Placing orders: {name}...")
                self.root.update()
                
                # Use your existing ladder placement logic
                # Example: self.place_ladder_for_epic(epic)
                # For now, I'll show the structure - you'll need to adapt this
                
                result = self._place_single_ladder(epic)
                
                if result.get('success'):
                    success_count += 1
                    results.append(f"✅ {name}: {result.get('orders', 0)} orders placed")
                else:
                    fail_count += 1
                    results.append(f"❌ {name}: {result.get('error', 'Failed')}")
            
            except Exception as e:
                fail_count += 1
                results.append(f"❌ {name}: {str(e)}")
        
        # Show results
        result_msg = f"Batch Order Results:\n\n"
        result_msg += f"✅ Success: {success_count}\n"
        result_msg += f"❌ Failed: {fail_count}\n\n"
        result_msg += "\n".join(results)
        
        messagebox.showinfo("Batch Orders Complete", result_msg)
        self.status_label.config(text=f"✅ Batch complete: {success_count} success, {fail_count} failed")


    def _place_single_ladder(self, epic: str) -> Dict:
        """
        Place ladder orders for a single instrument
        
        YOU NEED TO IMPLEMENT THIS based on your existing ladder logic
        This should use your existing ladder strategy settings and place orders
        
        Returns dict with 'success', 'orders', and 'error' keys
        """
        try:
            # Example structure - adapt to your actual implementation
            # This might call your ladder_strategy or use your existing place_orders logic
            
            # Get current price for this epic
            # price = self.get_current_price(epic)
            
            # Calculate ladder levels using your existing logic
            # levels = self.calculate_ladder_levels(price)
            
            # Place orders
            # orders_placed = self.place_orders_for_levels(epic, levels)
            
            # Return success
            return {
                'success': True,
                'orders': 5,  # Number of orders placed
                'error': None
            }
        
        except Exception as e:
            return {
                'success': False,
                'orders': 0,
                'error': str(e)
            }


    def open_group_manager(self):
        """Open window to manage instrument groups"""
        manager = tk.Toplevel(self.root)
        manager.title("Manage Instrument Groups")
        manager.geometry("700x500")
        
        # Groups listbox
        list_frame = ttk.Frame(manager)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(list_frame, text="Saved Groups:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        # Listbox with scrollbar
        listbox_frame = ttk.Frame(list_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        groups_listbox = tk.Listbox(
            listbox_frame,
            yscrollcommand=scrollbar.set,
            font=("Arial", 10),
            height=15
        )
        groups_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=groups_listbox.yview)
        
        # Populate listbox
        def refresh_groups():
            groups_listbox.delete(0, tk.END)
            for name in self.instrument_groups.get_all_groups():
                epics = self.instrument_groups.get_group(name)
                groups_listbox.insert(tk.END, f"{name} ({len(epics)} instruments)")
        
        refresh_groups()
        
        # Buttons
        button_frame = ttk.Frame(manager)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def create_new_group():
            """Create a new group"""
            name = simpledialog.askstring("New Group", "Enter group name:")
            if not name:
                return
            
            # Open instrument selector
            selector = tk.Toplevel(manager)
            selector.title(f"Add Instruments to '{name}'")
            selector.geometry("400x500")
            
            ttk.Label(selector, text="Select instruments:", font=("Arial", 10, "bold")).pack(padx=10, pady=5)
            
            # Checkboxes for each epic
            frame = ttk.Frame(selector)
            frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            canvas = tk.Canvas(frame)
            scrollbar = ttk.Scrollbar(frame, command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Create checkboxes
            check_vars = {}
            for epic, name_text in self.epic_names.items():
                var = tk.BooleanVar()
                check_vars[epic] = var
                ttk.Checkbutton(
                    scrollable_frame,
                    text=f"{name_text} ({epic})",
                    variable=var
                ).pack(anchor=tk.W, padx=5, pady=2)
            
            def save_group():
                selected = [epic for epic, var in check_vars.items() if var.get()]
                if not selected:
                    messagebox.showwarning("No Selection", "Please select at least one instrument")
                    return
                
                if self.instrument_groups.create_group(name, selected):
                    messagebox.showinfo("Success", f"Created group '{name}' with {len(selected)} instruments")
                    refresh_groups()
                    self.group_dropdown['values'] = self.instrument_groups.get_all_groups()
                    selector.destroy()
                else:
                    messagebox.showerror("Error", "Failed to create group")
            
            ttk.Button(selector, text="Save Group", command=save_group).pack(pady=10)
        
        def delete_group():
            """Delete selected group"""
            selection = groups_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a group to delete")
                return
            
            group_text = groups_listbox.get(selection[0])
            group_name = group_text.split(" (")[0]
            
            if messagebox.askyesno("Confirm Delete", f"Delete group '{group_name}'?"):
                if self.instrument_groups.delete_group(group_name):
                    messagebox.showinfo("Success", f"Deleted group '{group_name}'")
                    refresh_groups()
                    self.group_dropdown['values'] = self.instrument_groups.get_all_groups()
        
        ttk.Button(button_frame, text="➕ New Group", command=create_new_group).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🗑️ Delete Group", command=delete_group).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="✖️ Close", command=manager.destroy).pack(side=tk.RIGHT, padx=5)

        
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

    def on_auto_limit_toggled(self, state):
        """Handle auto-limit toggle"""
        if state:
            try:
                limit_distance = float(self.auto_limit_distance_var.get())
                self.log(f"Auto-limits enabled ({limit_distance}pts)")
                
                # Update monitor
                self.position_monitor.configure(
                    auto_stop=self.auto_stop_toggle.get(),
                    stop_distance=float(self.auto_stop_distance_var.get()),
                    auto_trailing=self.auto_trailing_toggle.get(),
                    trailing_distance=float(self.trailing_distance_var.get()),
                    trailing_step=float(self.trailing_step_var.get()),
                    auto_limit=True,
                    limit_distance=limit_distance
                )
                
                # Start monitoring if not running
                if not self.position_monitor.running:
                    self.position_monitor.start(self.log)
                    
            except ValueError:
                self.log("Invalid limit parameters")
                self.auto_limit_toggle.set_state(False)
        else:
            self.log("Auto-limits disabled")
            # Update monitor
            self.position_monitor.configure(
                auto_stop=self.auto_stop_toggle.get(),
                auto_trailing=self.auto_trailing_toggle.get(),
                auto_limit=False
            )
            
    def on_trailing_entry_toggled(self, state):
        """Handle trailing entry toggle with configuration"""
        if state:
            try:
                # Read configuration values from UI
                min_move = float(self.trailing_min_move_var.get())
                check_interval = int(self.trailing_check_interval_var.get())
                
                self.log(f"📉 Follow Price enabled - min move: {min_move} pts, check every {check_interval}s")
                self.ladder_strategy.start_trailing(self.log, min_move, check_interval)
            except ValueError as e:
                self.log(f"❌ Invalid trailing configuration: {e}")
                self.trailing_entry_toggle.set_state(False)
        else:
            self.log("📉 Follow Price stopped")
            self.ladder_strategy.stop_trailing()  
            
    def on_auto_trailing_toggled(self, state):
        """Handle auto-trailing toggle"""
        if state:
            try:
                distance = float(self.trailing_distance_var.get())
                step = float(self.trailing_step_var.get())
                self.log(f"Auto-trailing enabled - {distance}pt stop, {step}pt step")
                # Enable the parameter fields
                self.trailing_entry_distance.configure(state="normal")
                self.trailing_entry_step.configure(state="normal")
            except ValueError:
                self.log("Invalid trailing parameters")
                self.auto_trailing_toggle.set_state(False)
        else:
            self.log("Auto-trailing disabled")
            # Keep fields enabled for manual editing
            
    def create_order_management_tab(self, parent):
        """Create tab for managing individual orders"""
        bg_dark = "#1a1d23"
        card_bg = "#25292e"
        accent_teal = "#3a9d8e"
        text_white = "#e8eaed"
        text_gray = "#9fa6b2"
        
        # Main container
        container = ctk.CTkFrame(parent, fg_color=bg_dark)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header
        header_frame = ctk.CTkFrame(container, fg_color=card_bg, corner_radius=8)
        header_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(
            header_frame,
            text="📋 Working Orders",
            font=("Segoe UI", 16, "bold"),
            text_color=accent_teal
        ).pack(side="left", padx=20, pady=15)
        
        button_frame = ctk.CTkFrame(header_frame, fg_color=card_bg)
        button_frame.pack(side="right", padx=20, pady=10)
        
        ctk.CTkButton(
            button_frame,
            text="🔄 Refresh",
            command=self.refresh_orders,
            fg_color="#3e444d",
            hover_color="#4a5159",
            corner_radius=8,
            width=100,
            height=32
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="❌ Cancel Selected",
            command=self.cancel_selected_orders,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            corner_radius=8,
            width=140,
            height=32
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="🗑️ Cancel All",
            command=self.cancel_all_orders,
            fg_color="#de3618",
            hover_color="#9a6e65",
            corner_radius=8,
            width=110,
            height=32
        ).pack(side="left", padx=5)
        
        # Table frame
        table_frame = ctk.CTkFrame(container, fg_color=card_bg, corner_radius=8)
        table_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Create treeview using standard tkinter (CustomTkinter doesn't have treeview yet)
        import tkinter as tk
        import tkinter.ttk as ttk
        
        columns = ("Deal ID", "Instrument", "Direction", "Size", "Level", "Type", "Created")
        
        tree_container = tk.Frame(table_frame, bg=bg_dark)
        tree_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        v_scroll = tk.Scrollbar(tree_container, orient=tk.VERTICAL)
        h_scroll = tk.Scrollbar(tree_container, orient=tk.HORIZONTAL)
        
        self.orders_tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show="headings",
            selectmode="extended",
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set
        )
        
        v_scroll.config(command=self.orders_tree.yview)
        h_scroll.config(command=self.orders_tree.xview)
        
        # Style the treeview
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview",
                        background=card_bg,
                        fieldbackground=card_bg,
                        foreground=text_white,
                        font=("Segoe UI", 10))
        style.configure("Treeview.Heading",
                        background="#3e444d",
                        foreground=text_white,
                        font=("Segoe UI", 10, "bold"))
        style.map('Treeview', background=[('selected', accent_teal)])
        
        # Column headings and widths
        for col in columns:
            self.orders_tree.heading(col, text=col)
        
        self.orders_tree.column("Deal ID", width=150)
        self.orders_tree.column("Instrument", width=150)
        self.orders_tree.column("Direction", width=80)
        self.orders_tree.column("Size", width=60)
        self.orders_tree.column("Level", width=100)
        self.orders_tree.column("Type", width=80)
        self.orders_tree.column("Created", width=150)
        
        self.orders_tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        # Status bar
        status_frame = ctk.CTkFrame(container, fg_color=card_bg, corner_radius=8)
        status_frame.pack(fill="x")
        
        self.orders_status = ctk.CTkLabel(
            status_frame,
            text="Click Refresh to load orders",
            font=("Segoe UI", 10),
            text_color=text_gray
        )
        self.orders_status.pack(pady=10, padx=20)
        
        # Auto-refresh
        self.refresh_orders()

    def refresh_orders(self):
        """Refresh the working orders list"""
        try:
            self.orders_status.configure(text="🔄 Loading orders...", text_color="blue")
            self.root.update()
            
            # Clear existing
            for item in self.orders_tree.get_children():
                self.orders_tree.delete(item)
            
            # Get working orders from IG API
            # YOU NEED TO IMPLEMENT THIS using your IG API client
            # Example:
            # orders = self.ig_client.get_working_orders()
            
            # For demonstration, here's the structure:
            orders = self._fetch_working_orders()
            
            if not orders:
                self.orders_status.configure(text="No working orders found", text_color="gray")
                return
            
            # Populate table
            for order in orders:
                self.orders_tree.insert("", tk.END, values=(
                    order.get('dealId', ''),
                    order.get('instrument', ''),
                    order.get('direction', ''),
                    order.get('size', ''),
                    order.get('level', ''),
                    order.get('orderType', ''),
                    order.get('createdDate', '')
                ))
            
            self.orders_status.configure(
                text=f"✅ Loaded {len(orders)} working orders",
                text_color="green"
            )
        
        except Exception as e:
            self.orders_status.configure(text=f"❌ Error: {str(e)}", text_color="red")
            messagebox.showerror("Error", f"Failed to load orders:\n{str(e)}")


    def _fetch_working_orders(self) -> List[Dict]:
        """Fetch working orders from IG API"""
        try:
            # Get orders - returns list directly, not dict
            orders = self.ig_client.get_working_orders()
            
            if not orders:
                return []
            
            result = []
            for order in orders:
                order_data = order.get('workingOrderData', {})
                market_data = order.get('marketData', {})
                
                result.append({
                    'dealId': order_data.get('dealId', ''),
                    'instrument': market_data.get('instrumentName', ''),
                    'direction': order_data.get('direction', ''),
                    'size': order_data.get('dealSize', ''),
                    'level': order_data.get('orderLevel', ''),
                    'orderType': order_data.get('orderType', ''),
                    'createdDate': order_data.get('createdDate', '')[:19] if order_data.get('createdDate') else ''
                })
            
            return result
        
        except Exception as e:
            print(f"Orders error: {e}")
            return []
    
    def cancel_selected_orders(self):
        """Cancel selected orders"""
        selection = self.orders_tree.selection()
        
        if not selection:
            messagebox.showwarning("No Selection", "Please select orders to cancel")
            return
        
        # Get deal IDs
        deal_ids = []
        for item in selection:
            values = self.orders_tree.item(item)['values']
            deal_ids.append(values[0])  # Deal ID is first column
        
        # Confirm
        if not messagebox.askyesno(
            "Confirm Cancel",
            f"Cancel {len(deal_ids)} selected orders?"
        ):
            return
        
        # Cancel each order
        success = 0
        failed = 0
        
        for deal_id in deal_ids:
            try:
                # YOU NEED TO IMPLEMENT THIS using your IG API
                # Example: self.ig_client.cancel_order(deal_id)
                
                result = self._cancel_order(deal_id)
                if result:
                    success += 1
                else:
                    failed += 1
            
            except Exception as e:
                print(f"Error cancelling {deal_id}: {e}")
                failed += 1
        
        # Show results
        messagebox.showinfo(
            "Cancel Results",
            f"✅ Cancelled: {success}\n❌ Failed: {failed}"
        )
        
        # Refresh list
        self.refresh_orders()


    def cancel_all_orders(self):
        """Cancel all working orders"""
        # Get all deal IDs
        deal_ids = []
        for item in self.orders_tree.get_children():
            values = self.orders_tree.item(item)['values']
            deal_ids.append(values[0])
        
        if not deal_ids:
            messagebox.showinfo("No Orders", "No working orders to cancel")
            return
        
        # Confirm
        if not messagebox.askyesno(
            "Confirm Cancel All",
            f"⚠️ Cancel ALL {len(deal_ids)} working orders?"
        ):
            return
        
        # Cancel all
        success = 0
        failed = 0
        
        for deal_id in deal_ids:
            try:
                result = self._cancel_order(deal_id)
                if result:
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Error cancelling {deal_id}: {e}")
                failed += 1
        
        messagebox.showinfo(
            "Cancel Results",
            f"✅ Cancelled: {success}\n❌ Failed: {failed}"
        )
        
        self.refresh_orders()

    def _cancel_order(self, deal_id: str) -> bool:
        """Cancel a single order"""
        try:
            success, message = self.ig_client.cancel_order(deal_id)
            if not success:
                print(f"Failed to cancel {deal_id}: {message}")
            return success
        except Exception as e:
            print(f"Error cancelling order {deal_id}: {e}")
            return False
            
    def create_position_management_tab(self, parent):
        """Create tab for managing individual positions"""
        bg_dark = "#1a1d23"
        card_bg = "#25292e"
        accent_teal = "#3a9d8e"
        text_white = "#e8eaed"
        text_gray = "#9fa6b2"
        
        # Main container
        container = ctk.CTkFrame(parent, fg_color=bg_dark)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header
        header_frame = ctk.CTkFrame(container, fg_color=card_bg, corner_radius=8)
        header_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(
            header_frame,
            text="📊 Open Positions",
            font=("Segoe UI", 16, "bold"),
            text_color=accent_teal
        ).pack(side="left", padx=20, pady=15)
        
        button_frame = ctk.CTkFrame(header_frame, fg_color=card_bg)
        button_frame.pack(side="right", padx=20, pady=10)
        
        ctk.CTkButton(
            button_frame,
            text="🔄 Refresh",
            command=self.refresh_positions,
            fg_color="#3e444d",
            hover_color="#4a5159",
            corner_radius=8,
            width=100,
            height=32
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="❌ Close Selected",
            command=self.close_selected_positions,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            corner_radius=8,
            width=140,
            height=32
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="🗑️ Close All",
            command=self.close_all_positions,
            fg_color="#de3618",
            hover_color="#9a6e65",
            corner_radius=8,
            width=110,
            height=32
        ).pack(side="left", padx=5)
        
        # Table frame
        table_frame = ctk.CTkFrame(container, fg_color=card_bg, corner_radius=8)
        table_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Create treeview using standard tkinter
        import tkinter as tk
        import tkinter.ttk as ttk
        
        columns = ("Deal ID", "Instrument", "Direction", "Size", "Open Level", "Current", "P&L", "Created")
        
        tree_container = tk.Frame(table_frame, bg=bg_dark)
        tree_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        v_scroll = tk.Scrollbar(tree_container, orient=tk.VERTICAL)
        h_scroll = tk.Scrollbar(tree_container, orient=tk.HORIZONTAL)
        
        self.positions_tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show="headings",
            selectmode="extended",
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set
        )
        
        v_scroll.configure(command=self.positions_tree.yview)
        h_scroll.configure(command=self.positions_tree.xview)
        
        # Style the treeview
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview",
                        background=card_bg,
                        fieldbackground=card_bg,
                        foreground=text_white,
                        font=("Segoe UI", 10))
        style.configure("Treeview.Heading",
                        background="#3e444d",
                        foreground=text_white,
                        font=("Segoe UI", 10, "bold"))
        style.map('Treeview', background=[('selected', accent_teal)])
        
        # Column headings and widths
        for col in columns:
            self.positions_tree.heading(col, text=col)
        
        self.positions_tree.column("Deal ID", width=150)
        self.positions_tree.column("Instrument", width=150)
        self.positions_tree.column("Direction", width=80)
        self.positions_tree.column("Size", width=60)
        self.positions_tree.column("Open Level", width=100)
        self.positions_tree.column("Current", width=100)
        self.positions_tree.column("P&L", width=100)
        self.positions_tree.column("Created", width=150)
        
        self.positions_tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        # Status bar
        status_frame = ctk.CTkFrame(container, fg_color=card_bg, corner_radius=8)
        status_frame.pack(fill="x")
        
        self.positions_status = ctk.CTkLabel(
            status_frame,
            text="Click Refresh to load positions",
            font=("Segoe UI", 10),
            text_color=text_gray
        )
        self.positions_status.pack(pady=10, padx=20)
        
        # Auto-refresh
        self.refresh_positions()

    def refresh_positions(self):
        """Refresh the open positions list"""
        try:
            self.positions_status.configure(text="🔄 Loading positions...", text_color="blue")
            self.root.update()
            
            # Clear existing
            for item in self.positions_tree.get_children():
                self.positions_tree.delete(item)
            
            # Get positions from IG API
            positions = self._fetch_positions()
            
            if not positions:
                self.positions_status.configure(text="No open positions found", text_color="gray")
                return
            
            # Populate table
            total_pl = 0
            for position in positions:
                pl = position.get('profit', 0)
                total_pl += pl
                
                # Color-code P&L
                pl_str = f"£{pl:+.2f}" if pl != 0 else "£0.00"
                
                self.positions_tree.insert("", tk.END, values=(
                    position.get('dealId', ''),
                    position.get('instrument', ''),
                    position.get('direction', ''),
                    position.get('size', ''),
                    position.get('openLevel', ''),
                    position.get('currentLevel', ''),
                    pl_str,
                    position.get('createdDate', '')
                ), tags=('profit' if pl > 0 else 'loss' if pl < 0 else 'neutral',))
            
            # Color tags
            self.positions_tree.tag_configure('profit', foreground='green')
            self.positions_tree.tag_configure('loss', foreground='red')
            self.positions_tree.tag_configure('neutral', foreground='gray')
            
            self.positions_status.configure(
                text=f"✅ Loaded {len(positions)} positions | Total P&L: £{total_pl:+.2f}",
                text_color="green" if total_pl >= 0 else "red"
            )
        
        except Exception as e:
            self.positions_status.configure(text=f"❌ Error: {str(e)}", text_color="red")
            messagebox.showerror("Error", f"Failed to load positions:\n{str(e)}")


    def _fetch_positions(self) -> List[Dict]:
        """Fetch open positions from IG API"""
        try:
            # Get positions - returns list directly, not dict
            positions = self.ig_client.get_open_positions()
            
            if not positions:
                return []
            
            result = []
            for pos in positions:
                position_data = pos.get('position', {})
                market_data = pos.get('market', {})
                
                # Get current price based on direction
                direction = position_data.get('direction', '')
                current = market_data.get('bid', 0) if direction == 'SELL' else market_data.get('offer', 0)
                
                result.append({
                    'dealId': position_data.get('dealId', ''),
                    'instrument': market_data.get('instrumentName', ''),
                    'direction': direction,
                    'size': position_data.get('dealSize', ''),
                    'openLevel': position_data.get('level', position_data.get('openLevel', '')),
                    'currentLevel': current,
                    'profit': position_data.get('profit', 0),
                    'createdDate': position_data.get('createdDate', '')[:19] if position_data.get('createdDate') else ''
                })
            
            return result
        
        except Exception as e:
            print(f"Positions error: {e}")
            return []
    
    def close_selected_positions(self):
        """Close selected positions"""
        selection = self.positions_tree.selection()
        
        if not selection:
            messagebox.showwarning("No Selection", "Please select positions to close")
            return
        
        # Get deal IDs and P&L
        positions_to_close = []
        for item in selection:
            values = self.positions_tree.item(item)['values']
            positions_to_close.append({
                'dealId': values[0],
                'instrument': values[1],
                'pl': values[6]
            })
        
        # Confirm
        msg = f"Close {len(positions_to_close)} selected positions?\n\n"
        msg += "\n".join([f"• {p['instrument']} ({p['pl']})" for p in positions_to_close])
        
        if not messagebox.askyesno("Confirm Close", msg):
            return
        
        # Close each position
        success = 0
        failed = 0
        
        for position in positions_to_close:
            try:
                result = self._close_position(position['dealId'])
                if result:
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Error closing {position['dealId']}: {e}")
                failed += 1
        
        messagebox.showinfo(
            "Close Results",
            f"✅ Closed: {success}\n❌ Failed: {failed}"
        )
        
        self.refresh_positions()


    def close_all_positions(self):
        """Close all open positions"""
        # Get all positions
        positions = []
        for item in self.positions_tree.get_children():
            values = self.positions_tree.item(item)['values']
            positions.append({
                'dealId': values[0],
                'instrument': values[1]
            })
        
        if not positions:
            messagebox.showinfo("No Positions", "No open positions to close")
            return
        
        # Confirm
        if not messagebox.askyesno(
            "Confirm Close All",
            f"⚠️ Close ALL {len(positions)} open positions?"
        ):
            return
        
        # Close all
        success = 0
        failed = 0
        
        for position in positions:
            try:
                result = self._close_position(position['dealId'])
                if result:
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Error closing {position['dealId']}: {e}")
                failed += 1
        
        messagebox.showinfo(
            "Close Results",
            f"✅ Closed: {success}\n❌ Failed: {failed}"
        )
        
        self.refresh_positions()


    def _close_position(self, deal_id: str) -> bool:
        """Close a single position"""
        try:
            # First, get the position details to know direction and size
            positions = self.ig_client.get_open_positions()
            
            for pos in positions:
                position_data = pos.get('position', {})
                if position_data.get('dealId') == deal_id:
                    direction = position_data.get('direction')
                    size = position_data.get('dealSize')
                    
                    if direction and size:
                        success, message = self.ig_client.close_position(deal_id, direction, size)
                        if not success:
                            print(f"Failed to close {deal_id}: {message}")
                        return success
            
            print(f"Could not find position {deal_id}")
            return False
        
        except Exception as e:
            print(f"Error closing position {deal_id}: {e}")
            return False

    def create_risk_tab(self, parent):
        """Create risk management tab - spread out like trading tab"""
        bg_dark = "#1a1d23"
        card_bg = "#25292e"
        accent_teal = "#3a9d8e"
        text_white = "#e8eaed"
        text_gray = "#9fa6b2"
        
        # Make scrollable
        scrollable_frame = ctk.CTkScrollableFrame(parent, fg_color=bg_dark)
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header card
        header_card = ctk.CTkFrame(scrollable_frame, fg_color=card_bg, corner_radius=8)
        header_card.pack(fill="x", pady=(0, 8))
        
        header_row = ctk.CTkFrame(header_card, fg_color=card_bg)
        header_row.pack(fill="x", pady=15, padx=20)
        
        ctk.CTkLabel(
            header_row,
            text="🛡️ RISK MANAGEMENT",
            font=Theme.font_large(),
            text_color=text_white
        ).pack(side="left")
        
        # Master toggle on right
        toggle_container = ctk.CTkFrame(header_row, fg_color=card_bg)
        toggle_container.pack(side="right")
        
        self.use_risk_management = ctk.BooleanVar(value=True)
        
        risk_switch = ToggleSwitch(
            toggle_container, 
            initial_state=True, 
            callback=self.on_risk_toggle,
            bg=card_bg
        )
        risk_switch.pack(side="left", padx=10)
        
        ctk.CTkLabel(
            toggle_container,
            text="Enabled",
            font=Theme.font_medium(),
            text_color=text_white
        ).pack(side="left")
        
        # ===== MARGIN LIMITS CARD =====
        self.margin_frame = ctk.CTkFrame(scrollable_frame, fg_color=card_bg, corner_radius=8)
        self.margin_frame.pack(fill="x", pady=8)
        
        ctk.CTkLabel(
            self.margin_frame,
            text="💰 Margin Limits",
            font=Theme.font_large(),
            text_color=text_white
        ).pack(pady=(10, 5))
        
        # Row 1: Warn at margin %
        margin_row1 = ctk.CTkFrame(self.margin_frame, fg_color="#2a2e35", corner_radius=6)
        margin_row1.pack(fill="x", pady=5, padx=20)
        
        margin_r1_inner = ctk.CTkFrame(margin_row1, fg_color="#2a2e35")
        margin_r1_inner.pack(fill="x", pady=8, padx=15)
        
        self.margin_warn_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            margin_r1_inner,
            text="Warn when margin exceeds:",
            variable=self.margin_warn_var,
            font=Theme.font_normal(),
            fg_color=accent_teal,
            text_color=text_white,
            width=200
        ).grid(row=0, column=0, sticky="w", padx=5)
        
        self.margin_warn_pct = ctk.StringVar(value="30")
        ctk.CTkEntry(
            margin_r1_inner,
            textvariable=self.margin_warn_pct,
            width=70,
            height=30,
            font=Theme.font_medium()
        ).grid(row=0, column=1, padx=10)
        
        ctk.CTkLabel(
            margin_r1_inner,
            text="%",
            font=Theme.font_normal(),
            text_color=text_gray
        ).grid(row=0, column=2, padx=5)
        
        ctk.CTkLabel(
            margin_r1_inner,
            text="Shows warning popup but allows trade to continue",
            font=Theme.font_small(),
            text_color=text_gray
        ).grid(row=0, column=3, padx=20, sticky="w")
        
        # Row 2: Block at margin %
        margin_row2 = ctk.CTkFrame(self.margin_frame, fg_color="#2a2e35", corner_radius=6)
        margin_row2.pack(fill="x", pady=5, padx=20)
        
        margin_r2_inner = ctk.CTkFrame(margin_row2, fg_color="#2a2e35")
        margin_r2_inner.pack(fill="x", pady=8, padx=15)
        
        self.margin_block_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            margin_r2_inner,
            text="Block trading when margin exceeds:",
            variable=self.margin_block_var,
            font=Theme.font_normal(),
            fg_color=accent_teal,
            text_color=text_white,
            width=250
        ).grid(row=0, column=0, sticky="w", padx=5)
        
        self.margin_block_pct = ctk.StringVar(value="50")
        ctk.CTkEntry(
            margin_r2_inner,
            textvariable=self.margin_block_pct,
            width=70,
            height=30,
            font=Theme.font_medium()
        ).grid(row=0, column=1, padx=10)
        
        ctk.CTkLabel(
            margin_r2_inner,
            text="%",
            font=Theme.font_normal(),
            text_color=text_gray
        ).grid(row=0, column=2, padx=5)
        
        ctk.CTkLabel(
            margin_r2_inner,
            text="STOPS all trading when this limit is hit - hard limit",
            font=Theme.font_small(),
            text_color=text_gray
        ).grid(row=0, column=3, padx=20, sticky="w")
        
        # ===== DAILY LIMITS CARD =====
        self.daily_frame = ctk.CTkFrame(scrollable_frame, fg_color=card_bg, corner_radius=8)
        self.daily_frame.pack(fill="x", pady=8)
        
        ctk.CTkLabel(
            self.daily_frame,
            text="📅 Daily Limits",
            font=Theme.font_large(),
            text_color=text_white
        ).pack(pady=(10, 5))
        
        # Row 1: Max daily loss
        daily_row1 = ctk.CTkFrame(self.daily_frame, fg_color="#2a2e35", corner_radius=6)
        daily_row1.pack(fill="x", pady=5, padx=20)
        
        daily_r1_inner = ctk.CTkFrame(daily_row1, fg_color="#2a2e35")
        daily_r1_inner.pack(fill="x", pady=8, padx=15)
        
        self.daily_loss_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            daily_r1_inner,
            text="Maximum daily loss:",
            variable=self.daily_loss_var,
            font=Theme.font_normal(),
            fg_color=accent_teal,
            text_color=text_white,
            width=180
        ).grid(row=0, column=0, sticky="w", padx=5)
        
        ctk.CTkLabel(
            daily_r1_inner,
            text="£",
            font=Theme.font_normal(),
            text_color=text_gray
        ).grid(row=0, column=1, padx=(20, 5))
        
        self.daily_loss_limit = ctk.StringVar(value="500")
        ctk.CTkEntry(
            daily_r1_inner,
            textvariable=self.daily_loss_limit,
            width=100,
            height=30,
            font=Theme.font_medium()
        ).grid(row=0, column=2, padx=5)
        
        ctk.CTkLabel(
            daily_r1_inner,
            text="Blocks all trading if daily loss exceeds this amount",
            font=Theme.font_small(),
            text_color=text_gray
        ).grid(row=0, column=3, padx=20, sticky="w")
        
        # Row 2: Stop after profit
        daily_row2 = ctk.CTkFrame(self.daily_frame, fg_color="#2a2e35", corner_radius=6)
        daily_row2.pack(fill="x", pady=5, padx=20)
        
        daily_r2_inner = ctk.CTkFrame(daily_row2, fg_color="#2a2e35")
        daily_r2_inner.pack(fill="x", pady=8, padx=15)
        
        self.daily_profit_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            daily_r2_inner,
            text="Stop trading after profit:",
            variable=self.daily_profit_var,
            font=Theme.font_normal(),
            fg_color=accent_teal,
            text_color=text_white,
            width=180
        ).grid(row=0, column=0, sticky="w", padx=5)
        
        ctk.CTkLabel(
            daily_r2_inner,
            text="£",
            font=Theme.font_normal(),
            text_color=text_gray
        ).grid(row=0, column=1, padx=(20, 5))
        
        self.daily_profit_limit = ctk.StringVar(value="1000")
        ctk.CTkEntry(
            daily_r2_inner,
            textvariable=self.daily_profit_limit,
            width=100,
            height=30,
            font=Theme.font_medium()
        ).grid(row=0, column=2, padx=5)
        
        ctk.CTkLabel(
            daily_r2_inner,
            text="Locks in profits by stopping trading when daily target hit",
            font=Theme.font_small(),
            text_color=text_gray
        ).grid(row=0, column=3, padx=20, sticky="w")
        
        # Row 3: Max trades per day
        daily_row3 = ctk.CTkFrame(self.daily_frame, fg_color="#2a2e35", corner_radius=6)
        daily_row3.pack(fill="x", pady=5, padx=20)
        
        daily_r3_inner = ctk.CTkFrame(daily_row3, fg_color="#2a2e35")
        daily_r3_inner.pack(fill="x", pady=8, padx=15)
        
        self.max_trades_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            daily_r3_inner,
            text="Maximum trades per day:",
            variable=self.max_trades_var,
            font=Theme.font_normal(),
            fg_color=accent_teal,
            text_color=text_white,
            width=200
        ).grid(row=0, column=0, sticky="w", padx=5)
        
        self.max_trades_limit = ctk.StringVar(value="20")
        ctk.CTkEntry(
            daily_r3_inner,
            textvariable=self.max_trades_limit,
            width=100,
            height=30,
            font=Theme.font_medium()
        ).grid(row=0, column=1, padx=10)
        
        ctk.CTkLabel(
            daily_r3_inner,
            text="Prevents overtrading by limiting number of trades",
            font=Theme.font_small(),
            text_color=text_gray
        ).grid(row=0, column=2, padx=20, sticky="w")
        
        # ===== POSITION LIMITS CARD =====
        self.position_frame = ctk.CTkFrame(scrollable_frame, fg_color=card_bg, corner_radius=8)
        self.position_frame.pack(fill="x", pady=8)
        
        ctk.CTkLabel(
            self.position_frame,
            text="📊 Position Limits",
            font=Theme.font_large(),
            text_color=text_white
        ).pack(pady=(10, 5))
        
        # Row 1: Max open positions
        pos_row1 = ctk.CTkFrame(self.position_frame, fg_color="#2a2e35", corner_radius=6)
        pos_row1.pack(fill="x", pady=5, padx=20)
        
        pos_r1_inner = ctk.CTkFrame(pos_row1, fg_color="#2a2e35")
        pos_r1_inner.pack(fill="x", pady=8, padx=15)
        
        self.max_positions_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            pos_r1_inner,
            text="Maximum open positions:",
            variable=self.max_positions_var,
            font=Theme.font_normal(),
            fg_color=accent_teal,
            text_color=text_white,
            width=200
        ).grid(row=0, column=0, sticky="w", padx=5)
        
        self.max_positions_limit = ctk.StringVar(value="5")
        ctk.CTkEntry(
            pos_r1_inner,
            textvariable=self.max_positions_limit,
            width=100,
            height=30,
            font=Theme.font_medium()
        ).grid(row=0, column=1, padx=10)
        
        ctk.CTkLabel(
            pos_r1_inner,
            text="Won't place new orders if you already have this many positions",
            font=Theme.font_small(),
            text_color=text_gray
        ).grid(row=0, column=2, padx=20, sticky="w")
        
        # Row 2: Max position size
        pos_row2 = ctk.CTkFrame(self.position_frame, fg_color="#2a2e35", corner_radius=6)
        pos_row2.pack(fill="x", pady=5, padx=20)
        
        pos_r2_inner = ctk.CTkFrame(pos_row2, fg_color="#2a2e35")
        pos_r2_inner.pack(fill="x", pady=8, padx=15)
        
        self.max_size_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            pos_r2_inner,
            text="Maximum position size:",
            variable=self.max_size_var,
            font=Theme.font_normal(),
            fg_color=accent_teal,
            text_color=text_white,
            width=180
        ).grid(row=0, column=0, sticky="w", padx=5)
        
        self.max_size_limit = ctk.StringVar(value="2.0")
        ctk.CTkEntry(
            pos_r2_inner,
            textvariable=self.max_size_limit,
            width=100,
            height=30,
            font=Theme.font_medium()
        ).grid(row=0, column=1, padx=10)
        
        ctk.CTkLabel(
            pos_r2_inner,
            text="contracts",
            font=Theme.font_normal(),
            text_color=text_gray
        ).grid(row=0, column=2, padx=5)
        
        ctk.CTkLabel(
            pos_r2_inner,
            text="Blocks orders larger than this size",
            font=Theme.font_small(),
            text_color=text_gray
        ).grid(row=0, column=3, padx=20, sticky="w")
        
        # ===== RISK/REWARD CARD =====
        self.ratio_frame = ctk.CTkFrame(scrollable_frame, fg_color=card_bg, corner_radius=8)
        self.ratio_frame.pack(fill="x", pady=8)
        
        ctk.CTkLabel(
            self.ratio_frame,
            text="⚖️ Risk/Reward",
            font=Theme.font_large(),
            text_color=text_white
        ).pack(pady=(10, 5))
        
        ratio_row = ctk.CTkFrame(self.ratio_frame, fg_color="#2a2e35", corner_radius=6)
        ratio_row.pack(fill="x", pady=5, padx=20)
        
        ratio_inner = ctk.CTkFrame(ratio_row, fg_color="#2a2e35")
        ratio_inner.pack(fill="x", pady=8, padx=15)
        
        self.risk_reward_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            ratio_inner,
            text="Minimum risk/reward ratio:",
            variable=self.risk_reward_var,
            font=Theme.font_normal(),
            fg_color=accent_teal,
            text_color=text_white,
            width=200
        ).grid(row=0, column=0, sticky="w", padx=5)
        
        self.risk_reward_ratio = ctk.StringVar(value="1.5")
        ctk.CTkEntry(
            ratio_inner,
            textvariable=self.risk_reward_ratio,
            width=100,
            height=30,
            font=Theme.font_medium()
        ).grid(row=0, column=1, padx=10)
        
        ctk.CTkLabel(
            ratio_inner,
            text=":1",
            font=Theme.font_normal(),
            text_color=text_gray
        ).grid(row=0, column=2, padx=5)
        
        ctk.CTkLabel(
            ratio_inner,
            text="Requires limit to be at least 1.5x the stop distance (not implemented yet)",
            font=Theme.font_small(),
            text_color=text_gray
        ).grid(row=0, column=3, padx=20, sticky="w")

    def on_risk_toggle(self, state):
        """Enable/disable all risk management controls"""
        self.use_risk_management.set(state)
        
        if state:
            self.log("✅ Risk management ENABLED")
            # Enable all frames
            for frame in [self.margin_frame, self.daily_frame, self.position_frame, self.ratio_frame]:
                for child in frame.winfo_children():
                    self._enable_widget(child)
        else:
            self.log("⚠️ Risk management DISABLED - Trading without safety checks!")
            # Gray out all frames
            for frame in [self.margin_frame, self.daily_frame, self.position_frame, self.ratio_frame]:
                for child in frame.winfo_children():
                    self._disable_widget(child)

    def _enable_widget(self, widget):
        """Recursively enable a widget and its children"""
        try:
            if isinstance(widget, (ctk.CTkFrame)):
                for child in widget.winfo_children():
                    self._enable_widget(child)
            elif hasattr(widget, 'configure'):
                widget.configure(state="normal")
        except:
            pass

    def _disable_widget(self, widget):
        """Recursively disable a widget and its children"""
        try:
            if isinstance(widget, (ctk.CTkFrame)):
                for child in widget.winfo_children():
                    self._disable_widget(child)
            elif hasattr(widget, 'configure'):
                widget.configure(state="disabled")
        except:
            pass

    """
    UPDATED create_market_research_tab method for main_window.py
    This replaces your existing method starting at line 1448

    This version adds SUB-TABS:
    - Market Scanner (existing - for spread betting)
    - Stock Screener (NEW - for ISA investments)
    """

    def create_market_research_tab(self, parent):
        """Create market research tab with Market Scanner and Stock Screener sub-tabs"""
        card_bg = "#252a31"
        text_white = "#f4f5f7"
        accent_teal = "#5aa89a"
        bg_dark = "#1e2228"
        text_gray = "#9fa6b2"
        
        # Create TabView for sub-tabs
        self.research_tabview = ctk.CTkTabview(parent, fg_color=bg_dark)
        self.research_tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add sub-tabs
        self.research_tabview.add("Market Scanner")
        self.research_tabview.add("Stock Screener")
        
        # === MARKET SCANNER TAB (your existing code) ===
        scanner_parent = self.research_tabview.tab("Market Scanner")
        
        # Make scrollable
        scrollable = ctk.CTkScrollableFrame(scanner_parent, fg_color=bg_dark)
        scrollable.pack(fill="both", expand=True, padx=10, pady=10)
        
        scanner_frame = ctk.CTkFrame(scrollable, fg_color=card_bg, corner_radius=10)
        scanner_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        ctk.CTkLabel(scanner_frame, text="Market Scanner - Spread Betting",
                    font=Theme.font_xxlarge(), text_color=text_white).pack(pady=(15, 10), padx=15, anchor="w")
        
        # Scanner controls
        control_row = ctk.CTkFrame(scanner_frame, fg_color=card_bg)
        control_row.pack(fill="x", padx=15, pady=(0, 10))
        
        # Filter
        ctk.CTkLabel(control_row, text="Filter:", 
                    font=Theme.font_medium(), text_color=text_white).pack(side="left", padx=5)
        
        self.scanner_filter_var = ctk.StringVar(value="All")
        ctk.CTkComboBox(
            control_row, 
            variable=self.scanner_filter_var,
            values=["All", "Commodities", "Indices"],
            width=130, height=35,
            fg_color=card_bg, button_color=accent_teal,
            font=Theme.font_medium()
        ).pack(side="left", padx=5)
        
        # Timeframe
        ctk.CTkLabel(control_row, text="Timeframe:", 
                    font=Theme.font_medium(), text_color=text_white).pack(side="left", padx=(15, 5))
        
        self.scanner_timeframe_var = ctk.StringVar(value="Annual")
        ctk.CTkComboBox(
            control_row,
            variable=self.scanner_timeframe_var,
            values=["Daily", "Weekly", "Monthly", "Quarterly", "6-Month", "Annual", "2-Year", "5-Year", "All-Time"],
            width=130, height=35,
            fg_color=card_bg, button_color=accent_teal,
            font=Theme.font_medium()
        ).pack(side="left", padx=5)
        
        # Limit
        ctk.CTkLabel(control_row, text="Limit:", 
                    font=Theme.font_medium(), text_color=text_white).pack(side="left", padx=(15, 5))
        
        self.scanner_limit_var = ctk.StringVar(value="5")
        ctk.CTkEntry(
            control_row,
            textvariable=self.scanner_limit_var,
            width=50, height=35,
            font=Theme.font_medium(),
            placeholder_text="0=All"
        ).pack(side="left", padx=5)
        
        ctk.CTkLabel(control_row, text="markets", 
                    font=Theme.font_normal(), text_color=text_gray).pack(side="left", padx=2)
                
        self.include_closed_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            control_row, 
            text="Include Closed", 
            variable=self.include_closed_var,
            fg_color=accent_teal,
            font=Theme.font_normal()
        ).pack(side="left", padx=(15, 5))
        
        # Data Source
        ctk.CTkLabel(control_row, text="Source:", 
                    font=Theme.font_medium(), text_color=text_white).pack(side="left", padx=(15, 5))

        self.data_source_var = ctk.StringVar(value="Yahoo Only")
        ctk.CTkComboBox(
            control_row,
            variable=self.data_source_var,
            values=["Yahoo Only", "IG + Yahoo", "IG Only"],
            width=120, height=35,
            fg_color=card_bg, button_color=accent_teal,
            font=Theme.font_medium()
        ).pack(side="left", padx=5)
        
        # Scan button
        ctk.CTkButton(control_row, text="🔄 Scan Markets", 
                    command=self.on_scan_markets,
                    fg_color=accent_teal,
                    hover_color="#00f7cc",
                    width=120,
                    height=32,
                    font=Theme.font_normal()).pack(side="left", padx=5)
        
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
        
        
        # === STOCK SCREENER TAB (NEW - for ISA investments) ===
        screener_parent = self.research_tabview.tab("Stock Screener")
        
        # Make scrollable
        screener_scroll = ctk.CTkScrollableFrame(screener_parent, fg_color=bg_dark)
        screener_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        screener_frame = ctk.CTkFrame(screener_scroll, fg_color=card_bg, corner_radius=10)
        screener_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Title
        ctk.CTkLabel(
            screener_frame, 
            text="📈 ISA Stock Screener - Naked Trader Style",
            font=Theme.font_xxlarge(), 
            text_color=text_white
        ).pack(pady=(15, 5), padx=15, anchor="w")
        
        ctk.CTkLabel(
            screener_frame,
            text="Filter UK stocks by fundamentals • Note: Director buying data coming soon",
            font=Theme.font_small(),
            text_color=text_gray
        ).pack(pady=(0, 15), padx=15, anchor="w")
        
        # Filters section
        filters_frame = ctk.CTkFrame(screener_frame, fg_color=card_bg)
        filters_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        # === FUNDAMENTAL FILTERS ===
        fund_header = ctk.CTkLabel(
            filters_frame,
            text="Fundamental Filters:",
            font=Theme.font_large_bold(),
            text_color=text_white
        )
        fund_header.grid(row=0, column=0, columnspan=4, sticky="w", pady=(5, 10), padx=5)
        
        # Market Cap
        self.screener_mcap_enabled = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            filters_frame,
            text="Market Cap (£M):",
            variable=self.screener_mcap_enabled,
            fg_color=accent_teal,
            font=Theme.font_normal(),
            width=150
        ).grid(row=1, column=0, sticky="w", padx=5, pady=3)
        
        ctk.CTkLabel(filters_frame, text="Min", font=Theme.font_small()).grid(row=1, column=1, padx=2)
        self.screener_mcap_min = ctk.CTkEntry(filters_frame, width=70, height=28, font=Theme.font_normal())
        self.screener_mcap_min.insert(0, "100")
        self.screener_mcap_min.grid(row=1, column=2, padx=2)
        
        ctk.CTkLabel(filters_frame, text="Max", font=Theme.font_small()).grid(row=1, column=3, padx=2)
        self.screener_mcap_max = ctk.CTkEntry(filters_frame, width=70, height=28, font=Theme.font_normal())
        self.screener_mcap_max.insert(0, "2000")
        self.screener_mcap_max.grid(row=1, column=4, padx=2)
        
        # P/E Ratio
        self.screener_pe_enabled = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            filters_frame,
            text="P/E Ratio:",
            variable=self.screener_pe_enabled,
            fg_color=accent_teal,
            font=Theme.font_normal(),
            width=150
        ).grid(row=2, column=0, sticky="w", padx=5, pady=3)
        
        ctk.CTkLabel(filters_frame, text="Min", font=Theme.font_small()).grid(row=2, column=1, padx=2)
        self.screener_pe_min = ctk.CTkEntry(filters_frame, width=70, height=28, font=Theme.font_normal())
        self.screener_pe_min.insert(0, "5")
        self.screener_pe_min.grid(row=2, column=2, padx=2)
        
        ctk.CTkLabel(filters_frame, text="Max", font=Theme.font_small()).grid(row=2, column=3, padx=2)
        self.screener_pe_max = ctk.CTkEntry(filters_frame, width=70, height=28, font=Theme.font_normal())
        self.screener_pe_max.insert(0, "20")
        self.screener_pe_max.grid(row=2, column=4, padx=2)
        
        # Debt/Equity
        self.screener_debt_enabled = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            filters_frame,
            text="Debt/Equity (%):",
            variable=self.screener_debt_enabled,
            fg_color=accent_teal,
            font=Theme.font_normal(),
            width=150
        ).grid(row=3, column=0, sticky="w", padx=5, pady=3)
        
        ctk.CTkLabel(filters_frame, text="Max", font=Theme.font_small()).grid(row=3, column=1, padx=2)
        self.screener_debt_max = ctk.CTkEntry(filters_frame, width=70, height=28, font=Theme.font_normal())
        self.screener_debt_max.insert(0, "50")
        self.screener_debt_max.grid(row=3, column=2, padx=2)
        
        # Profit Margin
        self.screener_margin_enabled = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            filters_frame,
            text="Profit Margin (%):",
            variable=self.screener_margin_enabled,
            fg_color=accent_teal,
            font=Theme.font_normal(),
            width=150
        ).grid(row=4, column=0, sticky="w", padx=5, pady=3)
        
        ctk.CTkLabel(filters_frame, text="Min", font=Theme.font_small()).grid(row=4, column=1, padx=2)
        self.screener_margin_min = ctk.CTkEntry(filters_frame, width=70, height=28, font=Theme.font_normal())
        self.screener_margin_min.insert(0, "10")
        self.screener_margin_min.grid(row=4, column=2, padx=2)
        
        # Dividend Yield
        self.screener_div_enabled = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            filters_frame,
            text="Dividend Yield (%):",
            variable=self.screener_div_enabled,
            fg_color=accent_teal,
            font=Theme.font_normal(),
            width=150
        ).grid(row=5, column=0, sticky="w", padx=5, pady=3)
        
        ctk.CTkLabel(filters_frame, text="Min", font=Theme.font_small()).grid(row=5, column=1, padx=2)
        self.screener_div_min = ctk.CTkEntry(filters_frame, width=70, height=28, font=Theme.font_normal())
        self.screener_div_min.insert(0, "2")
        self.screener_div_min.grid(row=5, column=2, padx=2)
        
        # === TECHNICAL FILTERS ===
        tech_header = ctk.CTkLabel(
            filters_frame,
            text="Technical Filters:",
            font=Theme.font_large_bold(),
            text_color=text_white
        )
        tech_header.grid(row=6, column=0, columnspan=4, sticky="w", pady=(15, 10), padx=5)
        
        tech_row = ctk.CTkFrame(filters_frame, fg_color=card_bg)
        tech_row.grid(row=7, column=0, columnspan=5, sticky="w", padx=5, pady=3)
        
        self.screener_above_ma50 = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            tech_row,
            text="Above 50-day MA",
            variable=self.screener_above_ma50,
            fg_color=accent_teal,
            font=Theme.font_normal()
        ).pack(side="left", padx=10)
        
        self.screener_above_ma200 = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            tech_row,
            text="Above 200-day MA",
            variable=self.screener_above_ma200,
            fg_color=accent_teal,
            font=Theme.font_normal()
        ).pack(side="left", padx=10)
        
        self.screener_price_up_3m = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            tech_row,
            text="Price up last 3 months",
            variable=self.screener_price_up_3m,
            fg_color=accent_teal,
            font=Theme.font_normal()
        ).pack(side="left", padx=10)
        
        # === INDEX FILTERS ===
        index_header = ctk.CTkLabel(
            filters_frame,
            text="Index Filters:",
            font=Theme.font_large_bold(),
            text_color=text_white
        )
        index_header.grid(row=8, column=0, columnspan=4, sticky="w", pady=(15, 10), padx=5)
        
        index_row = ctk.CTkFrame(filters_frame, fg_color=card_bg)
        index_row.grid(row=9, column=0, columnspan=5, sticky="w", padx=5, pady=3)
        
        self.screener_ftse100 = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            index_row,
            text="FTSE 100",
            variable=self.screener_ftse100,
            fg_color=accent_teal,
            font=Theme.font_normal()
        ).pack(side="left", padx=10)
        
        self.screener_ftse250 = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            index_row,
            text="FTSE 250",
            variable=self.screener_ftse250,
            fg_color=accent_teal,
            font=Theme.font_normal()
        ).pack(side="left", padx=10)
        
        self.screener_smallcap = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            index_row,
            text="Small Cap",
            variable=self.screener_smallcap,
            fg_color=accent_teal,
            font=Theme.font_normal()
        ).pack(side="left", padx=10)
        
        self.screener_aim = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            index_row,
            text="AIM",
            variable=self.screener_aim,
            fg_color=accent_teal,
            font=Theme.font_normal()
        ).pack(side="left", padx=10)
        
        # === SCREEN BUTTON ===
        button_frame = ctk.CTkFrame(screener_frame, fg_color=card_bg)
        button_frame.pack(fill="x", padx=15, pady=15)
        
        self.screen_stocks_btn = ctk.CTkButton(
            button_frame,
            text="🔍 SCREEN STOCKS",
            command=self.on_screen_stocks,
            fg_color=accent_teal,
            hover_color="#00f7cc",
            corner_radius=8,
            width=200,
            height=40,
            font=Theme.font_large_bold()
        )
        self.screen_stocks_btn.pack()
        
        # === RESULTS AREA ===
        results_label = ctk.CTkLabel(
            screener_frame,
            text="Results:",
            font=Theme.font_large_bold(),
            text_color=text_white
        )
        results_label.pack(anchor="w", padx=15, pady=(5, 5))
        
        self.screener_results = scrolledtext.ScrolledText(
            screener_frame,
            width=100,
            height=20,
            bg="#1e2228",
            fg=text_white,
            font=("Consolas", 9),
            relief="flat",
            borderwidth=1
        )
        self.screener_results.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Initial message
        self.screener_results.insert("1.0", "📊 ISA Stock Screener\n\n")
        self.screener_results.insert("end", "Configure filters above and click 'SCREEN STOCKS'\n\n")
        self.screener_results.insert("end", "Note: First scan will be slow as it fetches data for all UK stocks.\n")
        self.screener_results.insert("end", "Subsequent scans will be faster due to caching.\n")
        
    def on_screen_stocks(self):
        """
        Run the stock screener with current filters
        Add this method to your MainWindow class
        """
        
        def do_screen():
            # Disable button while scanning
            self.root.after(0, lambda: self.screen_stocks_btn.configure(state="disabled", text="⏳ SCREENING..."))
            
            # Clear previous results
            def clear_results():
                self.screener_results.delete("1.0", tk.END)
                self.screener_results.insert(tk.END, "Starting stock screening...\n\n")
            self.root.after(0, clear_results)
            
            # Build filters dict
            filters = {}
            
            # Fundamental filters
            if self.screener_mcap_enabled.get():
                try:
                    filters['market_cap_min'] = float(self.screener_mcap_min.get()) * 1_000_000
                    filters['market_cap_max'] = float(self.screener_mcap_max.get()) * 1_000_000
                except:
                    pass
            
            if self.screener_pe_enabled.get():
                try:
                    filters['pe_min'] = float(self.screener_pe_min.get())
                    filters['pe_max'] = float(self.screener_pe_max.get())
                except:
                    pass
            
            if self.screener_debt_enabled.get():
                try:
                    filters['debt_to_equity_max'] = float(self.screener_debt_max.get())
                except:
                    pass
            
            if self.screener_margin_enabled.get():
                try:
                    filters['profit_margin_min'] = float(self.screener_margin_min.get())
                except:
                    pass
            
            if self.screener_div_enabled.get():
                try:
                    filters['dividend_yield_min'] = float(self.screener_div_min.get())
                except:
                    pass
            
            # Technical filters
            filters['above_ma_50'] = self.screener_above_ma50.get()
            filters['above_ma_200'] = self.screener_above_ma200.get()
            filters['price_up_3m'] = self.screener_price_up_3m.get()
            
            # Index filters
            indices = []
            if self.screener_ftse100.get():
                indices.append("FTSE 100")
            if self.screener_ftse250.get():
                indices.append("FTSE 250")
            if self.screener_smallcap.get():
                indices.append("Small Cap")
            if self.screener_aim.get():
                indices.append("AIM")
            filters['indices'] = indices
            
            # Run the screening
            try:
                from api.stock_screener import screen_stocks
                
                # Log to main window
                def log_status(msg):
                    self.root.after(0, lambda: self.screener_results.insert(tk.END, msg + "\n"))
                
                log_status("Fetching stock data from Yahoo Finance...")
                log_status(f"Indices to scan: {', '.join(indices) if indices else 'All'}\n")
                
                results = screen_stocks(filters, log_status)
                
                # Display results
                def display_results():
                    self.screener_results.delete("1.0", tk.END)
                    
                    if not results:
                        self.screener_results.insert(tk.END, "❌ No stocks match your criteria.\n\n")
                        self.screener_results.insert(tk.END, "Try:\n")
                        self.screener_results.insert(tk.END, "• Loosening some filters (uncheck boxes)\n")
                        self.screener_results.insert(tk.END, "• Widening P/E or market cap ranges\n")
                        self.screener_results.insert(tk.END, "• Unchecking technical filters\n")
                    else:
                        self.screener_results.insert(tk.END, f"✅ Found {len(results)} stocks matching your criteria:\n\n")
                        
                        # Header
                        header = f"{'Ticker':<12} {'Name':<30} {'Price':>8} {'P/E':>7} {'Mkt Cap':>10} {'Div%':>6} {'Margin%':>8}\n"
                        self.screener_results.insert(tk.END, header)
                        self.screener_results.insert(tk.END, "=" * 95 + "\n")
                        
                        # Results rows
                        for stock in results:
                            ticker = stock['ticker'][:12]
                            name = stock['name'][:30]
                            price = f"£{stock['price']:.2f}" if stock['price'] else "N/A"
                            pe = f"{stock['pe_ratio']:.1f}" if stock['pe_ratio'] else "N/A"
                            
                            # Format market cap
                            if stock['market_cap']:
                                if stock['market_cap'] > 1_000_000_000:
                                    mcap = f"£{stock['market_cap']/1_000_000_000:.1f}B"
                                else:
                                    mcap = f"£{stock['market_cap']/1_000_000:.0f}M"
                            else:
                                mcap = "N/A"
                            
                            div = f"{stock['dividend_yield']:.1f}%" if stock['dividend_yield'] else "N/A"
                            margin = f"{stock['profit_margin']:.1f}%" if stock['profit_margin'] else "N/A"
                            
                            row = f"{ticker:<12} {name:<30} {price:>8} {pe:>7} {mcap:>10} {div:>6} {margin:>8}\n"
                            self.screener_results.insert(tk.END, row)
                        
                        # Summary
                        self.screener_results.insert(tk.END, "\n" + "=" * 95 + "\n")
                        self.screener_results.insert(tk.END, f"Total: {len(results)} stocks match your criteria\n\n")
                        
                        # Next steps
                        self.screener_results.insert(tk.END, "💡 Next steps:\n")
                        self.screener_results.insert(tk.END, "• Research these companies further on the LSE website\n")
                        self.screener_results.insert(tk.END, "• Check recent director dealings (coming soon)\n")
                        self.screener_results.insert(tk.END, "• Add promising stocks to your ISA watchlist\n")
                    
                    # Re-enable button
                    self.screen_stocks_btn.configure(state="normal", text="🔍 SCREEN STOCKS")
                
                self.root.after(0, display_results)
                
            except Exception as e:
                def show_error():
                    self.screener_results.delete("1.0", tk.END)
                    self.screener_results.insert(tk.END, f"❌ Error during screening:\n{str(e)}\n\n")
                    self.screener_results.insert(tk.END, "Troubleshooting:\n")
                    self.screener_results.insert(tk.END, "• Make sure you have internet connection\n")
                    self.screener_results.insert(tk.END, "• Check that yfinance is installed: pip install yfinance\n")
                    self.screener_results.insert(tk.END, "• Verify stock_screener.py is in your api/ folder\n")
                    self.screen_stocks_btn.configure(state="normal", text="🔍 SCREEN STOCKS")
                    
                    # Also log to main log
                    import traceback
                    self.log(f"Stock screener error: {str(e)}")
                    self.log(traceback.format_exc())
                self.root.after(0, show_error)
        
        # Run in background thread
        thread = threading.Thread(target=do_screen, daemon=True)
        thread.start()

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
            font=Theme.font_large(),
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
            
            print("DEBUG: on_place_ladder called!")
            self.log("DEBUG: Place ladder button clicked")
            
            # Check for cancel
            print("DEBUG: Checking cancel...")
            if self.ladder_btn.cget("text") == "CANCEL LADDER":
                self.ladder_strategy.cancel_requested = True
                self.log("Cancelling ladder placement...")
                return
            
            # Check connection
            print("DEBUG: Checking connection...")
            if not self.ig_client.logged_in:
                self.log("Not connected")
                return

            print("DEBUG: Changing button to cancel mode...")
            # Change button to cancel mode
            self.ladder_btn.configure(
                state="normal", 
                text="CANCEL LADDER",
                fg_color="#ed6347",
                hover_color="#ee4626"
            )
            
            print("DEBUG: Entering try block...")
            try:
                print("DEBUG: Getting parameters...")
                # Get parameters
                selected_market = self.market_var.get()
                print(f"DEBUG: Selected market = {selected_market}")
                epic = self.config.markets.get(selected_market)
                print(f"DEBUG: Epic = {epic}")
                
                if not epic:
                    print("DEBUG: Epic not found!")
                    self.log(f"ERROR: Market '{selected_market}' not found in config")
                    self.ladder_btn.configure(
                        state="normal", 
                        text="🎯 PLACE LADDER",
                        fg_color="#3b9f6f",
                        hover_color="#4ab080"
                    )
                    return
                
                print("DEBUG: Getting direction and offsets...")
                direction = self.direction_var.get()
                start_offset = float(self.offset_var.get())
                step_size = float(self.step_var.get())
                print(f"DEBUG: Direction={direction}, offset={start_offset}, step={step_size}")
                
                print("DEBUG: Getting num_orders, size, retry params...")
                num_orders = int(self.num_orders_var.get())
                order_size = float(self.size_var.get())
                retry_jump = float(self.retry_jump_var.get())
                max_retries = int(self.max_retries_var.get())
                print(f"DEBUG: orders={num_orders}, size={order_size}, retry={retry_jump}, max={max_retries}")
                
                print("DEBUG: Getting stop distance and GSLO...")
                stop_distance = float(self.stop_distance_var.get())
                guaranteed_stop = self.use_gslo.get()
                print(f"DEBUG: stop={stop_distance}, GSLO={guaranteed_stop}")
                
                print("DEBUG: Checking GSLO validation...")
                # GSLO validation
                if guaranteed_stop and stop_distance < 20:
                    print("DEBUG: GSLO validation failed!")
                    messagebox.showerror(
                        "GSLO Error",
                        f"Guaranteed stops require minimum 20pt distance.\nYour distance: {stop_distance}pts\n\nEither:\n• Increase stop distance to 20+ pts\n• Uncheck GSLO"
                    )
                    self.ladder_btn.configure(state="normal", text="🎯 PLACE LADDER", fg_color="#3a9d8e")
                    return
                
                print("DEBUG: Getting market details...")
                # ===== CHECK MINIMUM SIZE =====
                market_details = self.get_cached_market_details(epic)
                print(f"DEBUG: market_details = {market_details}")
                
                if market_details is None:
                    print("DEBUG: Market details is None - rate limited")
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

                print("DEBUG: Checking market details exist...")
                if market_details:
                    print("DEBUG: Extracting min/max sizes...")
                    min_size = market_details['min_deal_size']
                    max_size = market_details['max_deal_size']
                    print(f"DEBUG: min_size={min_size}, max_size={max_size}")
                    
                    # Check if size is too small
                    print("DEBUG: Checking if size too small...")
                    if order_size < min_size:
                        print(f"DEBUG: Size {order_size} < min {min_size}")
                        result = messagebox.askyesno(
                            "Order Size Too Small",
                            f"⚠️ Minimum size for {selected_market} is {min_size}\n\n"
                            f"Your order size: {order_size}\n"
                            f"Minimum required: {min_size}\n\n"
                            f"Place orders at minimum size of {min_size} instead?",
                            icon="warning"
                        )
                        
                        if result:
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
                    print("DEBUG: Checking if size too large...")
                    if max_size > 0 and order_size > max_size:
                        print(f"DEBUG: Size {order_size} > max {max_size}")
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
                    print("DEBUG: Checking stop distances...")
                    if guaranteed_stop:
                        print("DEBUG: Checking GSLO distance...")
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
                        print("DEBUG: Checking regular stop distance...")
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
                    print("DEBUG: No market details - proceeding anyway")
                    self.log("WARNING: Could not verify market limits - proceeding anyway")

                # Check margin
                print("DEBUG: Checking margin...")
                try:
                    margin_ok, new_margin_ratio, required_margin = self.risk_manager.check_margin_for_order(
                        epic, order_size * num_orders, margin_limit=0.3
                    )
                    print(f"DEBUG: Margin check result: ok={margin_ok}, ratio={new_margin_ratio}")
                except Exception as e:
                    print(f"DEBUG: Margin check error: {e}")
                    self.log(f"Margin check skipped: {str(e)}")
                    margin_ok = True
                    new_margin_ratio = None

                if not margin_ok and new_margin_ratio:
                    print("DEBUG: Margin warning dialog...")
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
                print("DEBUG: Setting limit distance to 0...")
                limit_distance = 0

                # Risk check
                print("DEBUG: Checking risk management...")
                try:
                    if self.use_risk_management.get():
                        print("DEBUG: Risk management enabled - checking...")
                        can_trade, safety_checks = self.risk_manager.can_trade(order_size, epic)
                        print(f"DEBUG: can_trade={can_trade}")
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
                    else:
                        print("DEBUG: Risk management disabled")
                except Exception as e:
                    print(f"DEBUG: Risk check error: {e}")
                    self.log(f"Risk check skipped: {str(e)}")

                # Log action
                print("DEBUG: Logging action...")
                gslo_text = "with GSLO" if guaranteed_stop else "with regular stops"
                self.log(f"Placing {num_orders} {direction} orders for {selected_market} {gslo_text}")

                # Background thread
                print("DEBUG: Creating background thread...")
                def place_and_reenable():
                    print("DEBUG: Inside place_and_reenable thread")
                    try:
                        print("DEBUG: Calling ladder_strategy.place_ladder...")
                        self.ladder_strategy.place_ladder(
                            epic, direction, start_offset, step_size,
                            num_orders, order_size, retry_jump, max_retries,
                            self.log, limit_distance, stop_distance, guaranteed_stop
                        )
                        print("DEBUG: place_ladder completed")
                        
                        # Start position monitor if auto-attach enabled
                        print("DEBUG: Checking if position monitor should start...")
                        if self.auto_stop_toggle.get() or self.auto_trailing_toggle.get() or self.auto_limit_toggle.get():
                            print("DEBUG: Auto-attach enabled, starting position monitor...")
                            if not self.position_monitor.running:
                                self.position_monitor.start(self.log)
                                print("DEBUG: Position monitor started")
                            else:
                                print("DEBUG: Position monitor already running")
                        else:
                            print("DEBUG: No auto-attach enabled")
                        
                    except Exception as e:
                        print(f"DEBUG: ERROR in place_and_reenable: {e}")
                        import traceback
                        traceback.print_exc()
                        self.log(f"ERROR placing ladder: {str(e)}")
                    finally:
                        print("DEBUG: Resetting button...")
                        # Reset button
                        self.root.after(0, lambda: self.ladder_btn.configure(
                            state="normal", 
                            text="PLACE LADDER",
                            fg_color="#3b9f6f",
                            hover_color="#4ab080"
                        ))
                        self.ladder_strategy.cancel_requested = False
                        print("DEBUG: place_and_reenable finished")

                # Start thread
                print("DEBUG: Starting thread...")
                thread = threading.Thread(target=place_and_reenable, daemon=True)
                thread.start()
                print("DEBUG: Thread started")

            except ValueError as e:
                print(f"DEBUG: ValueError: {e}")
                self.log(f"Invalid parameters: {str(e)}")
                self.ladder_btn.configure(
                    state="normal", 
                    text="PLACE LADDER",
                    fg_color="#3b9f6f",
                    hover_color="#4ab080"
                )
            except Exception as e:
                print(f"DEBUG: Exception: {e}")
                import traceback
                traceback.print_exc()
                self.log(f"ERROR: {str(e)}")
                self.ladder_btn.configure(
                    state="normal", 
                    text="PLACE LADDER",
                    fg_color="#3b9f6f",
                    hover_color="#4ab080"
                )
            
    def on_auto_stop_toggled(self, state):
            """Handle auto-stop toggle"""
            if state:
                try:
                    stop_distance = float(self.auto_stop_distance_var.get())
                    self.log(f"✅ Auto-stops enabled ({stop_distance}pts) - will verify/add stops to new positions")
                    
                    # Configure position monitor
                    self.position_monitor.configure(
                        auto_stop=True,
                        stop_distance=stop_distance,
                        verify_stops=True
                    )
                    
                    # Start monitoring if not running
                    if not self.position_monitor.running:
                        self.position_monitor.start(self.log)
                        
                except ValueError:
                    self.log("Invalid stop distance")
                    self.auto_stop_toggle.set_state(False)
            else:
                self.log("⚠️ Auto-stops disabled - positions may not have stops!")
                self.position_monitor.configure(auto_stop=False)

    def on_auto_trailing_toggled(self, state):
        """Handle auto-trailing toggle"""
        if state:
            try:
                distance = float(self.trailing_distance_var.get())
                step = float(self.trailing_step_var.get())
                self.log(f"🔄 Trailing stops enabled ({distance}pts distance, {step}pt step)")
                
                # Configure position monitor
                self.position_monitor.configure(
                    auto_trailing=True,
                    trailing_distance=distance,
                    trailing_step=step
                )
                
                # Start monitoring if not running
                if not self.position_monitor.running:
                    self.position_monitor.start(self.log)
                    
            except ValueError:
                self.log("Invalid trailing parameters")
                self.auto_trailing_toggle.set_state(False)
        else:
            self.log("Trailing stops disabled")
            self.position_monitor.configure(auto_trailing=False)

    def on_auto_limit_toggled(self, state):
        """Handle auto-limit toggle"""
        if state:
            try:
                limit_distance = float(self.auto_limit_distance_var.get())
                self.log(f"🎯 Auto-limits enabled ({limit_distance}pts)")
                
                # Configure position monitor
                self.position_monitor.configure(
                    auto_limit=True,
                    limit_distance=limit_distance
                )
                
                # Start monitoring if not running
                if not self.position_monitor.running:
                    self.position_monitor.start(self.log)
                    
            except ValueError:
                self.log("Invalid limit distance")
                self.auto_limit_toggle.set_state(False)
        else:
            self.log("Auto-limits disabled")
            self.position_monitor.configure(auto_limit=False)

    def on_update_all_stops(self):
        """Update stops on BOTH orders and positions - ONE SMART BUTTON"""
        try:
            stop_distance = float(self.bulk_stop_distance_var.get())
            
            self.log(f"Updating all stops to {stop_distance}pts...")
            
            updated_orders = 0
            updated_positions = 0
            has_gslo_orders = False
            
            # Update WORKING ORDERS
            orders = self.ig_client.get_working_orders()
            
            # Check if any orders have GSLO
            for order in orders:
                if order.get("workingOrderData", {}).get("guaranteedStop"):
                    has_gslo_orders = True
                    break
            
            # Only show GSLO dialog if relevant
            preserve_gslo = False
            if has_gslo_orders:
                preserve_gslo = messagebox.askyesno(
                    "Preserve GSLO?",
                    f"Found {len([o for o in orders if o.get('workingOrderData', {}).get('guaranteedStop')])} orders with guaranteed stops.\n\nKeep GSLO status on these orders?"
                )
            
            for order in orders:
                try:
                    order_data = order.get("workingOrderData", {})
                    deal_id = order_data.get("dealId")
                    direction = order_data.get("direction")
                    order_level = order_data.get("level")  # FIXED: was orderLevel
                    current_gslo = order_data.get("guaranteedStop", False)
                    
                    # FIX: Check if order_level exists before math
                    if order_level is None:
                        self.log(f"⚠️ Skipping order {deal_id} - no level")
                        continue
                    
                    # Calculate new stop level (NOT NEEDED - we keep order at same level)
                    # Just update the stop distance
                    if direction == "BUY":
                        new_stop = order_level - stop_distance
                    else:
                        new_stop = order_level + stop_distance
                    
                    # Decide GSLO for this order
                    use_gslo = current_gslo if (preserve_gslo and current_gslo) else False
                    
                    # FIX: Update order with correct parameters
                    success, message = self.ig_client.update_working_order(
                        deal_id,
                        order_level,  # Keep order at same level
                        stop_distance=stop_distance,  # Update stop distance
                        guaranteed_stop=use_gslo
                    )
                    
                    if success:
                        updated_orders += 1
                    else:
                        self.log(f"Failed to update order {deal_id}: {message}")
                        
                    time.sleep(0.2)
                    
                except Exception as e:
                    self.log(f"Error updating order: {e}")
            
            # Update POSITIONS
            positions = self.ig_client.get_open_positions()
            
            for position in positions:
                try:
                    position_data = position.get("position", {})
                    deal_id = position_data.get("dealId")
                    direction = position_data.get("direction")
                    open_level = position_data.get("openLevel")  # FIXED: positions use openLevel
                    
                    # FIX: Check if open_level exists before math
                    if open_level is None:
                        self.log(f"⚠️ Skipping position {deal_id} - no level")
                        continue
                    
                    # Calculate new stop level
                    if direction == "BUY":
                        new_stop = open_level - stop_distance
                    else:
                        new_stop = open_level + stop_distance
                    
                    # Update position
                    success, message = self.ig_client.update_position(
                        deal_id=deal_id,
                        stop_level=new_stop,
                        stop_distance=None,
                        limit_level=None
                    )
                    
                    if success:
                        updated_positions += 1
                    else:
                        self.log(f"Failed to update position {deal_id}: {message}")
                        
                    time.sleep(0.2)
                    
                except Exception as e:
                    self.log(f"Error updating position: {e}")
            
            # Report results
            self.log(f"✅ Updated {updated_orders} orders, {updated_positions} positions")
            
        except ValueError as e:
            self.log(f"Invalid stop distance: {e}")
        except Exception as e:
            self.log(f"Error updating stops: {e}")

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

    def _close_position(self, deal_id: str) -> bool:
        """Close a single position"""
        try:
            # First, get the position details to know direction and size
            positions = self.ig_client.get_open_positions()
            
            for pos in positions:
                position_data = pos.get('position', {})
                if position_data.get('dealId') == deal_id:
                    direction = position_data.get('direction')
                    size = position_data.get('dealSize')
                    
                    if direction and size:
                        success, message = self.ig_client.close_position(deal_id, direction, size)
                        if not success:
                            print(f"Failed to close {deal_id}: {message}")
                        return success
            
            print(f"Could not find position {deal_id}")
            return False
        
        except Exception as e:
            print(f"Error closing position {deal_id}: {e}")
            return False

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
                
                # Add these methods to your MainWindow class in main_window.py

    def on_add_market_to_list(self, market_name, epic):
        """Add a market from search results to the trading list"""
        try:
            # Check if already exists
            if market_name in self.config.markets:
                self.log(f"⚠️ {market_name} already in your trading list")
                return
            
            # Add to config
            self.config.markets[market_name] = epic
            
            # Update the dropdown in Trading tab
            if hasattr(self, 'market_var'):
                # Get current markets list
                current_markets = list(self.config.markets.keys())
                
                # Update the combobox
                self.market_dropdown.configure(values=current_markets)
                
                self.log(f"✅ Added {market_name} to trading list")
                
                # Save to config file
                self._save_markets_to_config()
            
        except Exception as e:
            self.log(f"Error adding market: {e}")

    def on_remove_market_from_list(self):
        """Remove currently selected market from trading list"""
        try:
            selected_market = self.market_var.get()
            
            # Don't allow removing if it's the last one
            if len(self.config.markets) <= 1:
                messagebox.showwarning(
                    "Cannot Remove",
                    "You must have at least one market in your trading list!"
                )
                return
            
            # Confirm removal
            result = messagebox.askyesno(
                "Remove Market?",
                f"Remove '{selected_market}' from your trading list?\n\nYou can always add it back using Market Search."
            )
            
            if result:
                # Remove from config
                del self.config.markets[selected_market]
                
                # Update dropdown
                current_markets = list(self.config.markets.keys())
                self.market_dropdown.configure(values=current_markets)
                
                # Select first market in list
                if current_markets:
                    self.market_var.set(current_markets[0])
                
                self.log(f"✅ Removed {selected_market} from trading list")
                
                # Save to config file
                self._save_markets_to_config()
        
        except Exception as e:
            self.log(f"Error removing market: {e}")

    def _save_markets_to_config(self):
        """Save markets list to config.py file"""
        try:
            import os
            
            # Read current config file
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config.py')
            
            with open(config_path, 'r') as f:
                lines = f.readlines()
            
            # Find the markets section and rebuild it
            new_lines = []
            in_markets = False
            markets_written = False
            
            for line in lines:
                if 'self.markets = {' in line:
                    in_markets = True
                    # Write updated markets dict
                    new_lines.append('        self.markets = {\n')
                    for name, epic in self.config.markets.items():
                        new_lines.append(f'            "{name}": "{epic}",\n')
                    new_lines.append('        }\n')
                    markets_written = True
                    continue
                
                if in_markets and '}' in line:
                    in_markets = False
                    continue
                
                if not in_markets:
                    new_lines.append(line)
            
            # Write back to file
            with open(config_path, 'w') as f:
                f.writelines(new_lines)
            
            self.log("💾 Markets list saved to config")
            
        except Exception as e:
            self.log(f"Warning: Could not save to config file: {e}")


    # Update your Market Search results display
    # Find the on_search_markets method and update the results display section:

    def display_search_results_with_add_button(self, results):
        """Display search results with Add to List buttons"""
        # Clear previous results
        for widget in self.search_results_frame.winfo_children():
            widget.destroy()
        
        if not results:
            ctk.CTkLabel(
                self.search_results_frame,
                text="No results found",
                font=Theme.font_normal(),
                text_color=Theme.TEXT_GRAY
            ).pack(pady=20)
            return
        
        # Display each result
        for result in results[:50]:  # Limit to 50 results
            result_frame = ctk.CTkFrame(
                self.search_results_frame,
                fg_color=Theme.CARD_BG,
                corner_radius=6
            )
            result_frame.pack(fill="x", pady=2, padx=5)
            
            # Use grid for better layout
            result_inner = ctk.CTkFrame(result_frame, fg_color=Theme.CARD_BG)
            result_inner.pack(fill="x", padx=10, pady=5)
            
            # Market name
            ctk.CTkLabel(
                result_inner,
                text=result['name'],
                font=Theme.font_normal_bold(),
                text_color=Theme.TEXT_WHITE,
                width=250,
                anchor="w"
            ).grid(row=0, column=0, sticky="w", padx=5)
            
            # Epic code
            ctk.CTkLabel(
                result_inner,
                text=result['epic'],
                font=Theme.font_small(),
                text_color=Theme.TEXT_GRAY,
                width=200,
                anchor="w"
            ).grid(row=0, column=1, sticky="w", padx=5)
            
            # Type
            ctk.CTkLabel(
                result_inner,
                text=result.get('type', 'N/A'),
                font=Theme.font_small(),
                text_color=Theme.TEXT_GRAY,
                width=100,
                anchor="w"
            ).grid(row=0, column=2, sticky="w", padx=5)
            
            # Add button
            add_btn = ctk.CTkButton(
                result_inner,
                text="➕ Add to Trading List",
                command=lambda n=result['name'], e=result['epic']: self.on_add_market_to_list(n, e),
                fg_color=Theme.ACCENT_TEAL,
                hover_color="#4ab39f",
                text_color="black",
                corner_radius=6,
                width=150,
                height=28,
                font=Theme.font_small_bold()
            )
            add_btn.grid(row=0, column=3, padx=10)


        # Update your Trading tab Market selector to include Remove button
        # In create_trading_tab, update the market row:

        # Row 1: Market & Price - ADD REMOVE BUTTON
        row1 = ctk.CTkFrame(placement_card, fg_color=card_bg)
        row1.pack(fill="x", pady=8, padx=20)

        ctk.CTkLabel(row1, text="Market:", font=Theme.font_normal_bold(),
                    text_color=text_white, width=60, anchor="w").grid(row=0, column=0, padx=(0,5), sticky="w")

        self.market_var = ctk.StringVar(value="Gold Spot")
        self.market_dropdown = ctk.CTkComboBox(  # SAVE REFERENCE
            row1, variable=self.market_var,
            values=list(self.config.markets.keys()),
            width=160, height=30,
            fg_color=card_bg, button_color=accent_teal,
            font=Theme.font_normal()
        )
        self.market_dropdown.grid(row=0, column=1, padx=5)

        # ADD REMOVE BUTTON
        ctk.CTkButton(
            row1, 
            text="➖",
            command=self.on_remove_market_from_list,
            fg_color="#e74c3c",
            hover_color="#ee4626",
            corner_radius=6,
            width=30,
            height=30,
            font=Theme.font_normal_bold()
        ).grid(row=0, column=2, padx=2)

        ctk.CTkButton(row1, text="Get Price", command=self.on_get_price,
                    fg_color="#3e444d", hover_color="#4a5159",
                    corner_radius=8, width=90, height=30,
                    font=Theme.font_normal()).grid(row=0, column=3, padx=10)

        self.price_var = ctk.StringVar(value="--")
        ctk.CTkLabel(row1, textvariable=self.price_var,
                    font=Theme.font_medium_bold(),
                    text_color=accent_teal, width=100).grid(row=0, column=4, padx=5)

    def _configure_treeview_style(self):
        """Configure dark theme for ttk.Treeview widgets with color coding"""
        from tkinter import ttk
        style = ttk.Style()
        
        # Dark theme colors
        bg_dark = "#1a1d23"
        card_bg = "#25292e"
        text_white = "#e8eaed"
        text_gray = "#9fa6b2"
        accent_teal = "#3a9d8e"
        success_green = "#00d084"
        warning_orange = "#ffa500"
        danger_red = "#ff4444"
        
        # Configure Treeview
        style.theme_use('clam')  # Use clam theme as base
        
        # Treeview background and foreground
        style.configure("Treeview",
            background=card_bg,
            foreground=text_white,
            fieldbackground=card_bg,
            borderwidth=0,
            relief="flat",
            rowheight=25
        )
        
        # Treeview headings
        style.configure("Treeview.Heading",
            background=bg_dark,
            foreground=accent_teal,
            borderwidth=1,
            relief="flat"
        )
        
        # Hover effects
        style.map('Treeview',
            background=[('selected', accent_teal)],
            foreground=[('selected', text_white)]
        )
        
        style.map('Treeview.Heading',
            background=[('active', accent_teal)]
        )

    def create_trend_screener_tab(self, parent):
        """Create the Trend Screener tab with CustomTkinter"""
        from tkinter import ttk
        
        # Configure dark theme for treeviews
        self._configure_treeview_style()
        
        bg_dark = "#1a1d23"
        card_bg = "#25292e"
        accent_teal = "#3a9d8e"
        text_white = "#e8eaed"
        text_gray = "#9fa6b2"
        
        # Make scrollable
        scrollable_frame = ctk.CTkScrollableFrame(parent, fg_color=bg_dark)
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # ===== CONTROL PANEL =====
        control_card = ctk.CTkFrame(scrollable_frame, fg_color=card_bg, corner_radius=8)
        control_card.pack(fill="x", pady=(0, 8))
        
        ctk.CTkLabel(
            control_card, 
            text="📊 TREND SCREENER CONTROLS",
            font=Theme.font_large(), 
            text_color=text_white
        ).pack(pady=(10, 5))
        
        control_row = ctk.CTkFrame(control_card, fg_color=card_bg)
        control_row.pack(fill="x", pady=8, padx=20)
        
        # Timeframe selection
        ctk.CTkLabel(
            control_row, 
            text="Timeframe:", 
            font=Theme.font_normal(),
            text_color=text_white
        ).pack(side="left", padx=5)
        
        self.trend_timeframe = ctk.StringVar(value='5m')
        ctk.CTkComboBox(
            control_row,
            variable=self.trend_timeframe,
            values=['5m', '1h', '4h', '1d'],
            width=100,
            fg_color=card_bg,
            button_color=accent_teal,
            font=Theme.font_normal()
        ).pack(side="left", padx=5)
        
        # Scan button
        ctk.CTkButton(
            control_row,
            text="Scan Watchlist",
            command=self.scan_trends,
            fg_color=accent_teal,
            hover_color="#5abba8",
            font=Theme.font_normal(),
            corner_radius=8,
            width=120,
            height=30
        ).pack(side="left", padx=5)
        
        # Auto-refresh toggle
        self.trend_auto_refresh = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            control_row,
            text="Auto-Refresh (60s)",
            variable=self.trend_auto_refresh,
            command=self.toggle_trend_auto_refresh,
            fg_color=accent_teal,
            hover_color="#5abba8",
            font=Theme.font_normal()
        ).pack(side="left", padx=5)
        
        # Rally notifications toggle
        self.rally_notifications = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            control_row,
            text="Rally Alerts",
            variable=self.rally_notifications,
            command=self.toggle_rally_notifications,
            fg_color=accent_teal,
            hover_color="#5abba8",
            font=Theme.font_normal()
        ).pack(side="left", padx=5)
        
        # Test notification button
        ctk.CTkButton(
            control_row,
            text="Test Alert",
            command=self.test_rally_notification,
            fg_color="#3e444d",
            hover_color="#4a5159",
            font=Theme.font_normal(),
            corner_radius=8,
            width=80,
            height=30
        ).pack(side="left", padx=5)
        
        # ===== WATCHLIST SECTION =====
        watchlist_card = ctk.CTkFrame(scrollable_frame, fg_color=card_bg, corner_radius=8)
        watchlist_card.pack(fill="both", expand=True, pady=(0, 8))
        
        ctk.CTkLabel(
            watchlist_card, 
            text="📋 WATCHLIST",
            font=Theme.font_large(), 
            text_color=text_white
        ).pack(pady=(10, 5))
        
        # Watchlist buttons
        watchlist_btn_row = ctk.CTkFrame(watchlist_card, fg_color=card_bg)
        watchlist_btn_row.pack(fill="x", pady=5, padx=20)
        
        ctk.CTkButton(
            watchlist_btn_row,
            text="Add Instrument",
            command=self.add_to_watchlist_dialog,
            fg_color=accent_teal,
            hover_color="#5abba8",
            font=Theme.font_normal(),
            corner_radius=8,
            width=120,
            height=30
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            watchlist_btn_row,
            text="Remove Selected",
            command=self.remove_from_watchlist,
            fg_color="#3e444d",
            hover_color="#4a5159",
            font=Theme.font_normal(),
            corner_radius=8,
            width=120,
            height=30
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            watchlist_btn_row,
            text="Refresh List",
            command=self.refresh_watchlist_display,
            fg_color="#3e444d",
            hover_color="#4a5159",
            font=Theme.font_normal(),
            corner_radius=8,
            width=100,
            height=30
        ).pack(side="left", padx=5)
        
        # Watchlist tree
        watchlist_tree_frame = ctk.CTkFrame(watchlist_card, fg_color=bg_dark)
        watchlist_tree_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Scrollbars for watchlist
        watchlist_scroll_y = ttk.Scrollbar(watchlist_tree_frame, orient="vertical")
        watchlist_scroll_x = ttk.Scrollbar(watchlist_tree_frame, orient="horizontal")
        
        # Create watchlist tree (using ttk.Treeview as customtkinter doesn't have one)
        self.watchlist_tree = ttk.Treeview(
            watchlist_tree_frame,
            columns=('name', 'epic', 'added'),
            show='headings',
            yscrollcommand=watchlist_scroll_y.set,
            xscrollcommand=watchlist_scroll_x.set,
            height=6
        )
        
        # Configure columns
        self.watchlist_tree.heading('name', text='Instrument')
        self.watchlist_tree.heading('epic', text='Epic')
        self.watchlist_tree.heading('added', text='Added')
        
        self.watchlist_tree.column('name', width=150)
        self.watchlist_tree.column('epic', width=200)
        self.watchlist_tree.column('added', width=100)
        
        # Pack watchlist tree and scrollbars
        watchlist_scroll_y.config(command=self.watchlist_tree.yview)
        watchlist_scroll_x.config(command=self.watchlist_tree.xview)
        watchlist_scroll_y.pack(side="right", fill="y")
        watchlist_scroll_x.pack(side="bottom", fill="x")
        self.watchlist_tree.pack(fill="both", expand=True)
        
        # ===== RESULTS SECTION =====
        results_card = ctk.CTkFrame(scrollable_frame, fg_color=card_bg, corner_radius=8)
        results_card.pack(fill="both", expand=True, pady=(0, 8))
        
        ctk.CTkLabel(
            results_card, 
            text="📈 TREND ANALYSIS RESULTS",
            font=Theme.font_large(), 
            text_color=text_white
        ).pack(pady=(10, 5))
        
        # Results tree
        results_tree_frame = ctk.CTkFrame(results_card, fg_color=bg_dark)
        results_tree_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Scrollbars
        scroll_y = ttk.Scrollbar(results_tree_frame, orient="vertical")
        scroll_x = ttk.Scrollbar(results_tree_frame, orient="horizontal")
        
        self.trend_results_tree = ttk.Treeview(
            results_tree_frame,
            columns=('instrument', 'price', 'change_1', 'change_5', 'rsi', 
                    'macd', 'trend', 'momentum', 'rally'),
            show='headings',
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
            height=10
        )
        
        # Configure columns with proper alignment
        self.trend_results_tree.heading('instrument', text='Instrument', anchor='w')
        self.trend_results_tree.heading('price', text='Price', anchor='e')
        self.trend_results_tree.heading('change_1', text='1-Bar %', anchor='e')
        self.trend_results_tree.heading('change_5', text='5-Bar %', anchor='e')
        self.trend_results_tree.heading('rsi', text='RSI', anchor='center')
        self.trend_results_tree.heading('macd', text='MACD', anchor='e')
        self.trend_results_tree.heading('trend', text='Trend', anchor='center')
        self.trend_results_tree.heading('momentum', text='Momentum', anchor='center')
        self.trend_results_tree.heading('rally', text='Rally', anchor='center')
        
        self.trend_results_tree.column('instrument', width=120, minwidth=100, anchor='w')
        self.trend_results_tree.column('price', width=90, minwidth=70, anchor='e')
        self.trend_results_tree.column('change_1', width=90, minwidth=70, anchor='e')
        self.trend_results_tree.column('change_5', width=90, minwidth=70, anchor='e')
        self.trend_results_tree.column('rsi', width=60, minwidth=50, anchor='center')
        self.trend_results_tree.column('macd', width=80, minwidth=60, anchor='e')
        self.trend_results_tree.column('trend', width=140, minwidth=100, anchor='center')
        self.trend_results_tree.column('momentum', width=90, minwidth=70, anchor='center')
        self.trend_results_tree.column('rally', width=80, minwidth=60, anchor='center')
        
        # Pack results tree and scrollbars
        scroll_y.config(command=self.trend_results_tree.yview)
        scroll_x.config(command=self.trend_results_tree.xview)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.trend_results_tree.pack(fill="both", expand=True)
        
        # Configure color tags for the results tree
        self.trend_results_tree.tag_configure('rally', background='#2d5016', foreground='#00ff00')  # Bright green for rallies
        self.trend_results_tree.tag_configure('high_momentum', foreground='#00d084')  # Green for high momentum
        self.trend_results_tree.tag_configure('medium_momentum', foreground='#5aa89a')  # Teal for medium
        self.trend_results_tree.tag_configure('low_momentum', foreground='#9fa6b2')  # Gray for low
        self.trend_results_tree.tag_configure('negative', foreground='#ff4444')  # Red for negative changes
        self.trend_results_tree.tag_configure('positive', foreground='#00d084')  # Green for positive changes
        
        # Bind double-click to auto-fill trading tab
        self.trend_results_tree.bind('<Double-Button-1>', self.trend_result_double_click)
        
        # Load initial watchlist
        self.refresh_watchlist_display()

    def scan_trends(self):
        """Scan all instruments in watchlist for trends - progressive display"""
        timeframe = self.trend_timeframe.get()
        watchlist_epics = self.watchlist_manager.get_epics()
        
        if not watchlist_epics:
            messagebox.showinfo("Empty Watchlist", "Add instruments to watchlist first")
            return
        
        self.log(f"Scanning {len(watchlist_epics)} instruments on {timeframe} timeframe...")
        
        # Clear previous results
        for item in self.trend_results_tree.get_children():
            self.trend_results_tree.delete(item)
        
        # Scan in background with progressive display
        def scan_background():
            scanned = 0
            
            for epic in watchlist_epics:
                try:
                    trend_data = self.trend_analyzer.analyze_instrument(epic, timeframe)
                    
                    if trend_data:
                        scanned += 1
                        
                        # Display result immediately (in UI thread)
                        self.root.after(0, lambda td=trend_data: self._add_trend_result(td))
                        
                        # Check for rally and send notification
                        if trend_data.get('is_rally') and self.rally_notifications.get():
                            self.notification_system.send_rally_notification(trend_data)
                    
                except Exception as e:
                    self.log(f"Error scanning {epic}: {e}")
            
            # Final log
            self.root.after(0, lambda: self.log(f"Scan complete - {scanned} results"))
        
        thread = threading.Thread(target=scan_background, daemon=True)
        thread.start()
    
    def _add_trend_result(self, result):
        """Add a single trend result to the tree with color coding (called from UI thread)"""
        instrument_name = self._epic_to_friendly_name(result['epic'])
        
        values = (
            instrument_name,
            f"{result['current_price']:.2f}",
            f"{result['change_1_bar']:+.2f}%",
            f"{result['change_5_bars']:+.2f}%",
            f"{result['rsi']:.0f}" if result['rsi'] else "N/A",
            f"{result['macd']:.2f}" if result['macd'] else "N/A",
            result['trend'],
            f"{result['momentum_score']:.0f}",
            "🚀 YES" if result['is_rally'] else "No"
        )
        
        # Determine color tags based on values
        tags = [result['epic']]  # Always store epic
        
        # Color by rally status (highest priority)
        if result.get('is_rally'):
            tags.append('rally')
        # Color by momentum score
        elif result['momentum_score'] >= 70:
            tags.append('high_momentum')
        elif result['momentum_score'] >= 50:
            tags.append('medium_momentum')
        else:
            tags.append('low_momentum')
        
        # Insert at the end with tags
        item_id = self.trend_results_tree.insert('', 'end', values=values, tags=tuple(tags))
        
        # Auto-scroll to show new items
        self.trend_results_tree.see(item_id)

    def display_trend_results(self, results):
        """Display trend analysis results"""
        # Clear tree
        for item in self.trend_results_tree.get_children():
            self.trend_results_tree.delete(item)
        
        # Sort by momentum score (highest first)
        results.sort(key=lambda x: x.get('momentum_score', 0), reverse=True)
        
        for result in results:
            instrument_name = self._epic_to_friendly_name(result['epic'])
            
            values = (
                instrument_name,
                f"{result['current_price']:.2f}",
                f"{result['change_1_bar']:+.2f}%",
                f"{result['change_5_bars']:+.2f}%",
                f"{result['rsi']:.0f}" if result['rsi'] else "N/A",
                f"{result['macd']:.2f}" if result['macd'] else "N/A",
                result['trend'],
                f"{result['momentum_score']:.0f}",
                "🚀 YES" if result['is_rally'] else "No"
            )
            
            # Store epic and values in item
            item_id = self.trend_results_tree.insert('', 'end', values=values)
            # Store epic in item tags for later retrieval
            self.trend_results_tree.item(item_id, tags=(result['epic'],))
        
        self.log(f"Scan complete - {len(results)} results")

    def toggle_trend_auto_refresh(self):
        """Toggle auto-refresh for trend screener"""
        if self.trend_auto_refresh.get():
            self.start_trend_auto_refresh()
        else:
            self.stop_trend_auto_refresh()

    def start_trend_auto_refresh(self):
        """Start auto-refreshing trend data"""
        self.trend_screener_running = True
        self.log("Trend auto-refresh enabled (60s intervals)")
        
        def auto_refresh_loop():
            while self.trend_screener_running:
                self.scan_trends()
                for _ in range(60):  # Check every second for 60 seconds
                    if not self.trend_screener_running:
                        break
                    time.sleep(1)
        
        thread = threading.Thread(target=auto_refresh_loop, daemon=True)
        thread.start()

    def stop_trend_auto_refresh(self):
        """Stop auto-refreshing"""
        self.trend_screener_running = False
        self.log("Trend auto-refresh disabled")

    def toggle_rally_notifications(self):
        """Toggle rally notifications"""
        if self.rally_notifications.get():
            self.notification_system.enable()
            self.log("Rally notifications enabled")
        else:
            self.notification_system.disable()
            self.log("Rally notifications disabled")

    def test_rally_notification(self):
        """Send a test notification"""
        success = self.notification_system.test_notification()
        if success:
            self.log("Test notification sent")
        else:
            self.log("Failed to send test notification")

    def add_to_watchlist_dialog(self):
        """Show dialog to add instrument to watchlist"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Add to Watchlist")
        dialog.geometry("400x250")
        
        bg_dark = "#1a1d23"
        card_bg = "#25292e"
        accent_teal = "#3a9d8e"
        text_white = "#e8eaed"
        
        dialog.configure(fg_color=bg_dark)
        
        # Content frame
        content = ctk.CTkFrame(dialog, fg_color=card_bg, corner_radius=8)
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            content, 
            text="Epic Code:", 
            font=Theme.font_normal(),
            text_color=text_white
        ).pack(pady=(20, 5))
        
        epic_entry = ctk.CTkEntry(content, width=300, font=Theme.font_normal())
        epic_entry.pack(pady=5)
        epic_entry.insert(0, "CS.D.USCGC.TODAY.IP")
        
        ctk.CTkLabel(
            content, 
            text="Name (optional):", 
            font=Theme.font_normal(),
            text_color=text_white
        ).pack(pady=(15, 5))
        
        name_entry = ctk.CTkEntry(content, width=300, font=Theme.font_normal())
        name_entry.pack(pady=5)
        
        def add():
            epic = epic_entry.get().strip()
            name = name_entry.get().strip() or None
            
            if not epic:
                messagebox.showerror("Error", "Epic code required")
                return
            
            success, message = self.watchlist_manager.add(epic, name)
            if success:
                self.refresh_watchlist_display()
                dialog.destroy()
                self.log(f"Added {epic} to watchlist")
            else:
                messagebox.showinfo("Info", message)
        
        ctk.CTkButton(
            content, 
            text="Add", 
            command=add,
            fg_color=accent_teal,
            hover_color="#5abba8",
            font=Theme.font_normal(),
            width=150,
            height=35
        ).pack(pady=20)

    def remove_from_watchlist(self):
        """Remove selected instrument from watchlist"""
        selection = self.watchlist_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Select an instrument to remove")
            return
        
        item = selection[0]
        epic = self.watchlist_tree.item(item)['values'][1]
        
        if messagebox.askyesno("Confirm", f"Remove {epic} from watchlist?"):
            success, message = self.watchlist_manager.remove(epic)
            if success:
                self.refresh_watchlist_display()
                self.log(f"Removed {epic} from watchlist")

    def refresh_watchlist_display(self):
        """Refresh the watchlist display"""
        # Clear tree
        for item in self.watchlist_tree.get_children():
            self.watchlist_tree.delete(item)
        
        # Load watchlist
        watchlist = self.watchlist_manager.get_all()
        
        for instrument in watchlist:
            values = (
                instrument.get('name', instrument['epic']),
                instrument['epic'],
                instrument.get('added', 'N/A')
            )
            self.watchlist_tree.insert('', 'end', values=values)
        
        self.log(f"Watchlist loaded - {len(watchlist)} instruments")

    def trend_result_double_click(self, event):
        """Handle double-click on trend result - auto-fill trading tab"""
        selection = self.trend_results_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        # Get epic from tags
        tags = self.trend_results_tree.item(item, 'tags')
        if not tags:
            return
        
        epic = tags[0]
        values = self.trend_results_tree.item(item)['values']
        
        # Find market name that matches this epic
        market_name = None
        for name, epic_code in self.config.markets.items():
            if epic_code == epic:
                market_name = name
                break
        
        # Switch to Trading tab
        self.notebook.set("Trading")
        
        # Auto-fill the market if found
        if market_name and hasattr(self, 'market_var'):
            self.market_var.set(market_name)
            self.log(f"Auto-filled: {values[0]} ({epic})")
        else:
            self.log(f"Selected: {values[0]} ({epic}) - add to config.markets to auto-fill")

    def _epic_to_friendly_name(self, epic):
        """Convert epic to friendly name"""
        name_map = {
            'CS.D.USCGC.TODAY.IP': 'Gold',
            'CS.D.USCGC.DAILY.IP': 'Gold',
            'IX.D.RUSSELL.DAILY.IP': 'Russell 2000',
            'IX.D.FTSE.DAILY.IP': 'FTSE 100',
            'IX.D.SPTRD.DAILY.IP': 'S&P 500',
            'IX.D.DOW.DAILY.IP': 'Dow Jones',
            'IX.D.NASDAQ.DAILY.IP': 'NASDAQ',
            'IX.D.DAX.DAILY.IP': 'DAX',
            'IX.D.NIKKEI.DAILY.IP': 'Nikkei 225',
            'CS.D.USCRD.TODAY.IP': 'Crude Oil',
            'CS.D.USSLV.TODAY.IP': 'Silver',
            'CS.D.NGCUSD.TODAY.IP': 'Natural Gas',
        }
        return name_map.get(epic, epic)

    def on_group_selected(self, choice=None):
        """Update preview when group is selected"""
        group_name = self.group_var.get()
        if not group_name:
            return
        
        epics = self.instrument_groups.get_group(group_name)
        if epics:
            # Get friendly names
            friendly_names = []
            for epic in epics:
                # Use your existing market names mapping
                found = False
                for market_name, market_epic in self.config.markets.items():
                    if market_epic == epic:
                        friendly_names.append(market_name)
                        found = True
                        break
                if not found:
                    friendly_names.append(epic)
            
            preview_text = f"📊 {len(epics)} instruments: {', '.join(friendly_names)}"
            self.group_preview_label.configure(text=preview_text, text_color="#e8eaed")
        else:
            self.group_preview_label.configure(text="No instruments in group", text_color="#e74c3c")


    def place_batch_orders(self):
        """Place ladder orders on all instruments in selected group"""
        group_name = self.group_var.get()
        if not group_name:
            messagebox.showwarning("No Group", "Please select an instrument group first")
            return
        
        epics = self.instrument_groups.get_group(group_name)
        if not epics:
            messagebox.showwarning("Empty Group", "Selected group has no instruments")
            return
        
        # Get friendly names for confirmation
        names = []
        for epic in epics:
            found = False
            for market_name, market_epic in self.config.markets.items():
                if market_epic == epic:
                    names.append(market_name)
                    found = True
                    break
            if not found:
                names.append(epic)
        
        # Confirm with user
        confirm = messagebox.askyesno(
            "Confirm Batch Orders",
            f"Place ladder orders on these {len(epics)} instruments?\n\n" + "\n".join(f"• {name}" for name in names)
        )
        
        if not confirm:
            return
        
        # Place orders on each instrument
        self.log(f"🚀 Placing batch orders on {len(epics)} instruments...")
        
        success_count = 0
        fail_count = 0
        results = []
        
        for i, epic in enumerate(epics):
            # Find market name
            market_name = epic
            for name, mkt_epic in self.config.markets.items():
                if mkt_epic == epic:
                    market_name = name
                    break
            
            try:
                self.log(f"📊 [{i+1}/{len(epics)}] Placing orders: {market_name}...")
                
                # Temporarily set the market
                original_market = self.market_var.get()
                self.market_var.set(market_name)
                
                # Use your existing place_ladder method
                result = self._place_single_ladder_internal()
                
                # Restore original market
                self.market_var.set(original_market)
                
                if result:
                    success_count += 1
                    results.append(f"✅ {market_name}: Success")
                else:
                    fail_count += 1
                    results.append(f"❌ {market_name}: Failed")
            
            except Exception as e:
                fail_count += 1
                results.append(f"❌ {market_name}: {str(e)}")
                self.log(f"❌ Error placing orders for {market_name}: {str(e)}")
        
        # Show results
        result_msg = f"Batch Order Results:\n\n"
        result_msg += f"✅ Success: {success_count}\n"
        result_msg += f"❌ Failed: {fail_count}\n\n"
        result_msg += "\n".join(results)
        
        messagebox.showinfo("Batch Orders Complete", result_msg)
        self.log(f"✅ Batch complete: {success_count} success, {fail_count} failed")


    def _place_single_ladder_internal(self):
        """
        Internal method to place a ladder for currently selected market
        Returns True on success, False on failure
        """
        try:
            # Use your existing on_place_ladder logic
            # This is just a wrapper to return success/failure
            self.on_place_ladder()
            return True
        except Exception as e:
            self.log(f"Error: {str(e)}")
            return False


    def open_group_manager(self):
        """Open window to manage instrument groups"""
        manager = ctk.CTkToplevel(self.root)
        manager.title("Manage Instrument Groups")
        manager.geometry("800x600")
        
        # Configure colors
        bg_dark = "#1a1d23"
        card_bg = "#25292e"
        accent_teal = "#3a9d8e"
        text_white = "#e8eaed"
        
        manager.configure(fg_color=bg_dark)
        
        # Header
        header = ctk.CTkLabel(
            manager,
            text="📦 Manage Groups",
            font=Theme.font_title_bold(),
            text_color=accent_teal
        )
        header.pack(pady=20)
        
        # Main content frame
        content = ctk.CTkFrame(manager, fg_color=card_bg, corner_radius=10)
        content.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Listbox for groups
        ctk.CTkLabel(
            content,
            text="Saved Groups:",
            font=Theme.font_medium_bold(),
            text_color=text_white
        ).pack(anchor="w", padx=20, pady=(20, 10))
        
        # Create listbox using tkinter (CustomTkinter doesn't have CTkListbox yet)
        listbox_frame = ctk.CTkFrame(content, fg_color=bg_dark, corner_radius=8)
        listbox_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        scrollbar = ctk.CTkScrollbar(listbox_frame)
        scrollbar.pack(side="right", fill="y", padx=5, pady=5)
        
        groups_listbox = tk.Listbox(
            listbox_frame,
            yscrollcommand=scrollbar.set,
            font=Theme.font_normal(),
            bg=bg_dark,
            fg=text_white,
            selectmode=tk.SINGLE,
            highlightthickness=0,
            borderwidth=0,
            height=15
        )
        groups_listbox.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.configure(command=groups_listbox.yview)
        
        def refresh_groups():
            """Refresh the groups list"""
            groups_listbox.delete(0, tk.END)
            for name in self.instrument_groups.get_all_groups():
                epics = self.instrument_groups.get_group(name)
                groups_listbox.insert(tk.END, f"{name} ({len(epics)} instruments)")
        
        refresh_groups()
        
        # Buttons frame
        button_frame = ctk.CTkFrame(content, fg_color=card_bg)
        button_frame.pack(fill="x", padx=20, pady=20)
        
        def create_new_group():
            """Create a new group"""
            name = simpledialog.askstring("New Group", "Enter group name:", parent=manager)
            if not name:
                return
            
            # Open instrument selector
            selector = ctk.CTkToplevel(manager)
            selector.title(f"Add Instruments to '{name}'")
            selector.geometry("500x600")
            selector.configure(fg_color=bg_dark)
            
            ctk.CTkLabel(
                selector,
                text=f"Select instruments for '{name}':",
                font=Theme.font_medium_bold(),
                text_color=text_white
            ).pack(padx=20, pady=20)
            
            # Scrollable frame for checkboxes
            scroll_frame = ctk.CTkScrollableFrame(
                selector,
                fg_color=card_bg,
                corner_radius=8
            )
            scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
            
            # Create checkboxes
            check_vars = {}
            for market_name, epic in self.config.markets.items():
                var = ctk.BooleanVar()
                check_vars[epic] = var
                
                ctk.CTkCheckBox(
                    scroll_frame,
                    text=f"{market_name} ({epic})",
                    variable=var,
                    font=Theme.font_normal(),
                    fg_color=accent_teal,
                    hover_color="#4fb5a6"
                ).pack(anchor="w", padx=10, pady=5)
            
            def save_group():
                selected = [epic for epic, var in check_vars.items() if var.get()]
                if not selected:
                    messagebox.showwarning("No Selection", "Please select at least one instrument", parent=selector)
                    return
                
                if self.instrument_groups.create_group(name, selected):
                    messagebox.showinfo("Success", f"Created group '{name}' with {len(selected)} instruments", parent=selector)
                    refresh_groups()
                    # Update dropdown
                    self.group_dropdown.configure(values=self.instrument_groups.get_all_groups())
                    selector.destroy()
                else:
                    messagebox.showerror("Error", "Failed to create group", parent=selector)
            
            ctk.CTkButton(
                selector,
                text="Save Group",
                command=save_group,
                fg_color=accent_teal,
                hover_color="#4fb5a6",
                corner_radius=8,
                height=35,
                font=Theme.font_medium()
            ).pack(pady=20)
        
        def delete_group():
            """Delete selected group"""
            selection = groups_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a group to delete", parent=manager)
                return
            
            group_text = groups_listbox.get(selection[0])
            group_name = group_text.split(" (")[0]
            
            if messagebox.askyesno("Confirm Delete", f"Delete group '{group_name}'?", parent=manager):
                if self.instrument_groups.delete_group(group_name):
                    messagebox.showinfo("Success", f"Deleted group '{group_name}'", parent=manager)
                    refresh_groups()
                    self.group_dropdown.configure(values=self.instrument_groups.get_all_groups())
        
        # Buttons
        ctk.CTkButton(
            button_frame,
            text="➕ New Group",
            command=create_new_group,
            fg_color=accent_teal,
            hover_color="#4fb5a6",
            corner_radius=8,
            width=120,
            height=35,
            font=Theme.font_normal()
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="🗑️ Delete",
            command=delete_group,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            corner_radius=8,
            width=120,
            height=35,
            font=Theme.font_normal()
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="✖️ Close",
            command=manager.destroy,
            fg_color="#3e444d",
            hover_color="#4a5159",
            corner_radius=8,
            width=120,
            height=35,
            font=Theme.font_normal()
        ).pack(side="right", padx=5)


    def run(self):
        """Start the GUI"""
        self.create_gui()
        self.root.mainloop()
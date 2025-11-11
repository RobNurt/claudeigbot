"""
Trend Screener UI Code
Add this to your main_window.py file

INTEGRATION INSTRUCTIONS:
1. Import these at the top of main_window.py:
   from api.trend_analyzer import TrendAnalyzer
   from api.notification_system import NotificationSystem
   from api.watchlist_manager import WatchlistManager

2. In __init__ method, initialize:
   self.trend_analyzer = TrendAnalyzer()
   self.notification_system = NotificationSystem()
   self.watchlist_manager = WatchlistManager()
   self.trend_screener_running = False

3. Add this method to create the Trend Screener tab

4. Call self.create_trend_screener_tab() after creating other tabs
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading


def create_trend_screener_tab(self):
    """Create the Trend Screener tab"""
    trend_frame = ttk.Frame(self.notebook)
    self.notebook.add(trend_frame, text="Trend Screener")
    
    # Top control panel
    control_frame = ttk.Frame(trend_frame)
    control_frame.pack(fill=tk.X, padx=10, pady=10)
    
    # Timeframe selection
    ttk.Label(control_frame, text="Timeframe:").pack(side=tk.LEFT, padx=5)
    self.trend_timeframe = tk.StringVar(value='3m')
    timeframe_combo = ttk.Combobox(
        control_frame, 
        textvariable=self.trend_timeframe,
        values=['3m', '1h', '4h', '1d'],
        width=8,
        state='readonly'
    )
    timeframe_combo.pack(side=tk.LEFT, padx=5)
    
    # Scan button
    scan_btn = ttk.Button(
        control_frame,
        text="Scan Watchlist",
        command=self.scan_trends
    )
    scan_btn.pack(side=tk.LEFT, padx=5)
    
    # Auto-refresh toggle
    self.trend_auto_refresh = tk.BooleanVar(value=False)
    auto_refresh_cb = ttk.Checkbutton(
        control_frame,
        text="Auto-Refresh (60s)",
        variable=self.trend_auto_refresh,
        command=self.toggle_trend_auto_refresh
    )
    auto_refresh_cb.pack(side=tk.LEFT, padx=5)
    
    # Rally notifications toggle
    self.rally_notifications = tk.BooleanVar(value=True)
    notifications_cb = ttk.Checkbutton(
        control_frame,
        text="Rally Alerts",
        variable=self.rally_notifications,
        command=self.toggle_rally_notifications
    )
    notifications_cb.pack(side=tk.LEFT, padx=5)
    
    # Test notification button
    test_notif_btn = ttk.Button(
        control_frame,
        text="Test Alert",
        command=self.test_rally_notification
    )
    test_notif_btn.pack(side=tk.LEFT, padx=5)
    
    # Watchlist management frame
    watchlist_frame = ttk.LabelFrame(trend_frame, text="Watchlist")
    watchlist_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    # Watchlist buttons
    watchlist_btn_frame = ttk.Frame(watchlist_frame)
    watchlist_btn_frame.pack(fill=tk.X, padx=5, pady=5)
    
    ttk.Button(
        watchlist_btn_frame,
        text="Add Instrument",
        command=self.add_to_watchlist_dialog
    ).pack(side=tk.LEFT, padx=5)
    
    ttk.Button(
        watchlist_btn_frame,
        text="Remove Selected",
        command=self.remove_from_watchlist
    ).pack(side=tk.LEFT, padx=5)
    
    ttk.Button(
        watchlist_btn_frame,
        text="Refresh Watchlist",
        command=self.refresh_watchlist_display
    ).pack(side=tk.LEFT, padx=5)
    
    # Watchlist tree
    watchlist_tree_frame = ttk.Frame(watchlist_frame)
    watchlist_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # Scrollbars
    watchlist_scroll_y = ttk.Scrollbar(watchlist_tree_frame, orient=tk.VERTICAL)
    watchlist_scroll_x = ttk.Scrollbar(watchlist_tree_frame, orient=tk.HORIZONTAL)
    
    # Create watchlist tree
    self.watchlist_tree = ttk.Treeview(
        watchlist_tree_frame,
        columns=('name', 'epic', 'added'),
        show='headings',
        yscrollcommand=watchlist_scroll_y.set,
        xscrollcommand=watchlist_scroll_x.set
    )
    
    # Configure columns
    self.watchlist_tree.heading('name', text='Instrument')
    self.watchlist_tree.heading('epic', text='Epic')
    self.watchlist_tree.heading('added', text='Added')
    
    self.watchlist_tree.column('name', width=150)
    self.watchlist_tree.column('epic', width=200)
    self.watchlist_tree.column('added', width=100)
    
    # Pack scrollbars and tree
    watchlist_scroll_y.config(command=self.watchlist_tree.yview)
    watchlist_scroll_x.config(command=self.watchlist_tree.xview)
    watchlist_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
    watchlist_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
    self.watchlist_tree.pack(fill=tk.BOTH, expand=True)
    
    # Results frame
    results_frame = ttk.LabelFrame(trend_frame, text="Trend Analysis Results")
    results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    # Results tree with scrollbars
    results_tree_frame = ttk.Frame(results_frame)
    results_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    scroll_y = ttk.Scrollbar(results_tree_frame, orient=tk.VERTICAL)
    scroll_x = ttk.Scrollbar(results_tree_frame, orient=tk.HORIZONTAL)
    
    self.trend_results_tree = ttk.Treeview(
        results_tree_frame,
        columns=('instrument', 'price', 'change_1', 'change_5', 'rsi', 
                'macd', 'trend', 'momentum', 'rally'),
        show='headings',
        yscrollcommand=scroll_y.set,
        xscrollcommand=scroll_x.set
    )
    
    # Configure columns
    self.trend_results_tree.heading('instrument', text='Instrument')
    self.trend_results_tree.heading('price', text='Price')
    self.trend_results_tree.heading('change_1', text='1-Bar %')
    self.trend_results_tree.heading('change_5', text='5-Bar %')
    self.trend_results_tree.heading('rsi', text='RSI')
    self.trend_results_tree.heading('macd', text='MACD')
    self.trend_results_tree.heading('trend', text='Trend')
    self.trend_results_tree.heading('momentum', text='Momentum')
    self.trend_results_tree.heading('rally', text='Rally')
    
    self.trend_results_tree.column('instrument', width=120)
    self.trend_results_tree.column('price', width=80)
    self.trend_results_tree.column('change_1', width=80)
    self.trend_results_tree.column('change_5', width=80)
    self.trend_results_tree.column('rsi', width=60)
    self.trend_results_tree.column('macd', width=80)
    self.trend_results_tree.column('trend', width=120)
    self.trend_results_tree.column('momentum', width=80)
    self.trend_results_tree.column('rally', width=60)
    
    # Pack scrollbars and tree
    scroll_y.config(command=self.trend_results_tree.yview)
    scroll_x.config(command=self.trend_results_tree.xview)
    scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
    scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
    self.trend_results_tree.pack(fill=tk.BOTH, expand=True)
    
    # Bind double-click to auto-fill trading tab
    self.trend_results_tree.bind('<Double-Button-1>', self.trend_result_double_click)
    
    # Load initial watchlist
    self.refresh_watchlist_display()


def scan_trends(self):
    """Scan all instruments in watchlist for trends"""
    timeframe = self.trend_timeframe.get()
    watchlist_epics = self.watchlist_manager.get_epics()
    
    if not watchlist_epics:
        messagebox.showinfo("Empty Watchlist", "Add instruments to watchlist first")
        return
    
    self.log(f"Scanning {len(watchlist_epics)} instruments on {timeframe} timeframe...")
    
    # Clear previous results
    for item in self.trend_results_tree.get_children():
        self.trend_results_tree.delete(item)
    
    # Scan in background
    def scan_background():
        results = []
        
        for epic in watchlist_epics:
            try:
                trend_data = self.trend_analyzer.analyze_instrument(epic, timeframe)
                
                if trend_data:
                    results.append(trend_data)
                    
                    # Check for rally and send notification
                    if trend_data.get('is_rally') and self.rally_notifications.get():
                        self.notification_system.send_rally_notification(trend_data)
                
            except Exception as e:
                self.log(f"Error scanning {epic}: {e}")
        
        # Display results in UI thread
        self.after(0, lambda: self.display_trend_results(results))
    
    thread = threading.Thread(target=scan_background, daemon=True)
    thread.start()


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
        
        # Color code by momentum
        item_id = self.trend_results_tree.insert('', tk.END, values=values)
        
        # Store epic in item for later retrieval
        self.trend_results_tree.set(item_id, '#1', result['epic'])  # Hidden epic
    
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
                import time
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
    dialog = tk.Toplevel(self)
    dialog.title("Add to Watchlist")
    dialog.geometry("400x200")
    
    ttk.Label(dialog, text="Epic Code:").pack(pady=10)
    epic_entry = ttk.Entry(dialog, width=40)
    epic_entry.pack(pady=5)
    epic_entry.insert(0, "CS.D.USCGC.TODAY.IP")
    
    ttk.Label(dialog, text="Name (optional):").pack(pady=10)
    name_entry = ttk.Entry(dialog, width=40)
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
    
    ttk.Button(dialog, text="Add", command=add).pack(pady=10)


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
        self.watchlist_tree.insert('', tk.END, values=values)
    
    self.log(f"Watchlist loaded - {len(watchlist)} instruments")


def trend_result_double_click(self, event):
    """Handle double-click on trend result - auto-fill trading tab"""
    selection = self.trend_results_tree.selection()
    if not selection:
        return
    
    item = selection[0]
    values = self.trend_results_tree.item(item)['values']
    
    # Extract epic from hidden column
    epic = self.trend_results_tree.set(item, '#1')
    
    # Switch to Trading tab
    self.notebook.select(1)  # Assuming Trading tab is index 1
    
    # Auto-fill the epic
    if hasattr(self, 'epic_var'):
        self.epic_var.set(epic)
        self.log(f"Auto-filled: {values[0]} ({epic})")


def _epic_to_friendly_name(self, epic):
    """Convert epic to friendly name"""
    name_map = {
        'CS.D.USCGC.TODAY.IP': 'Gold',
        'IX.D.RUSSELL.DAILY.IP': 'Russell 2000',
        'IX.D.FTSE.DAILY.IP': 'FTSE 100',
        'IX.D.SPTRD.DAILY.IP': 'S&P 500',
        'IX.D.DOW.DAILY.IP': 'Dow Jones',
        'IX.D.NASDAQ.DAILY.IP': 'NASDAQ',
    }
    return name_map.get(epic, epic)
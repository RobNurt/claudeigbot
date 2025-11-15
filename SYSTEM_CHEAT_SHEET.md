# IG TRADING BOT - COMPLETE SYSTEM CHEAT SHEET
**Upload this file at the start of every chat session**

Last Updated: November 15, 2025 (Session 2 - auto_stop_toggle FIX)
Main Window: 5438 lines, CustomTkinter-based

---

## 🎯 QUICK START FOR NEXT SESSION

**Say this to Claude:**

> "I've uploaded the COMPLETE_SYSTEM_CHEAT_SHEET.md. Last session we FIXED the auto_stop_toggle error! The app now has all 8 tabs working including:
> - Order/Position Management tabs ✅
> - Instrument Groups section ✅
> - Position Management section with auto-attach toggles ✅
>
> The app runs, connects, and places ladders successfully. Position monitor now starts automatically when enabled.
>
> **Next priorities:**
> 1. Test the position auto-attach feature in DEMO mode
> 2. Verify the Instrument Groups batch trading works
> 3. Consider adding margin/account summary to bottom panel
>
> My main_window.py is 5438 lines. What should we work on next?"

---

## 📊 CURRENT UI STATE (From Screenshots - Nov 15, 2025)

### ✅ **Working Tabs:**

**1. Connection Tab:**
- Account Type: Demo/Live radio buttons
- Disconnect button
- Status: "Connected to LIVE" (working!)

**2. Trading Tab - ORDER PLACEMENT Section:**
- ✅ Market selector (Gold Spot)
- ✅ Direction: Buy/Sell radios
- ✅ Offset: 5 pts
- ✅ Step: 10 pts  
- ✅ Orders: 5
- ✅ Size: 0.1
- ✅ Retry: Jump 5 pts, Max 3 attempts
- ✅ Stop Loss: 20 pts, GSLO checkbox
- ✅ Follow Price toggle (orange=ON), Min: 0.5 pts, Check: 30 sec
- ✅ PLACE LADDER button (green)
- ✅ Cancel All Orders button (red)

**NEW - INSTRUMENT GROUPS Section:** ✅ ADDED Nov 15, 2025 (Fixed)
- ✅ Group dropdown selector
- ✅ Place Batch Orders button
- ✅ Manage Groups button
- ✅ Group preview (shows instruments in selected group)

**NEW - POSITION MANAGEMENT Section:** ✅ ADDED Nov 15, 2025 (Fixed)
- ✅ Auto-attach toggles: Stop, Trail, Limit
- ✅ Auto-attach distances (pts)
- ✅ Manual update: Stop distance input
- ✅ Update All Stops button
- ✅ Close All Positions button

**3. Risk Management Tab:**
- ✅ Margin Limits (warn at 30%, block at 50%)
- ✅ Daily Limits (max loss £500, stop after profit £1000, max 20 trades/day)
- ✅ Position Limits (max 5 positions, max 2.0 size)
- ✅ Risk/Reward section (partially visible)

**4. Configuration Tab:**
- ✅ Enable Risk Management (checked)
- ✅ Enable Limit Orders (checked)
- ⚠️ Enable Auto-Replace Strategy (unchecked - NOT IMPLEMENTED)
- ⚠️ Enable Trailing Stops (unchecked)

**5. Market Research Tab:**
- ✅ Market Scanner subtab working
- ✅ Stock Screener subtab (not shown in screenshots)
- ✅ Filter, Timeframe, Limit controls
- ✅ Scan Markets button

**6. Trend Screener Tab:**
- ✅ Timeframe selector
- ✅ Scan Watchlist button
- ✅ Auto-Refresh, Rally Alerts toggles
- ✅ Test Alert button
- ✅ Watchlist table (11 instruments loaded)
- ✅ Trend Analysis Results table

**7. Orders Tab (NEW - Nov 15):**
- ✅ Refresh button
- ✅ Cancel Selected button
- ✅ Cancel All button
- ✅ Table with columns: Deal ID, Instrument, Direction, Size, Level, Type, Created
- ✅ Shows "No working orders found" (correct - all cancelled)

**8. Positions Tab (NEW - Nov 15):**
- ✅ Refresh button
- ✅ Close Selected button
- ✅ Close All button
- ✅ Table with columns: Deal ID, Instrument, Direction, Size, Open Level, Current, P&L, Created
- ✅ Shows "No open positions found"

**Bottom Panel (All Tabs):**
- ✅ Order Management buttons: Refresh, Cancel Orders, Close Positions, Search Markets
- ✅ Activity Log (working!)

---

## ✅ CRITICAL ERROR - FIXED! (Nov 15, 2025)

**Previous Error:**
```
[12:36:35] ERROR placing ladder: 'MainWindow' object has no attribute 'auto_stop_toggle'
```

**Root Cause:**
- The `add_to_create_trading_tab()` method contained critical UI sections:
  - INSTRUMENT GROUPS (lines 713-783)
  - POSITION MANAGEMENT (lines 786-929)
- This method was NEVER called from `create_trading_tab()`
- Toggle switches (`auto_stop_toggle`, `auto_trailing_toggle`, `auto_limit_toggle`) were never created
- When ladder placement completed, line 3829 tried to check these toggles → crash!

**The Fix:**
Added one line at the end of `create_trading_tab()` method (after line 706):
```python
# ✅ FIX: Call method that adds POSITION MANAGEMENT and INSTRUMENT GROUPS sections
self.add_to_create_trading_tab(parent, scrollable_frame, card_bg, accent_teal, text_white, text_gray)
```

**Result:**
- ✅ All toggle switches now created properly
- ✅ Position monitor can start automatically after ladder placement
- ✅ Instrument Groups section now visible in Trading tab
- ✅ Position Management section now visible in Trading tab
- ✅ No more AttributeError crashes!

---

## 🎯 SYSTEM OVERVIEW

**Python-based automated trading bot for IG Markets (spread betting)**

**Primary Features:**
- Ladder Strategy: Multiple stop entry orders at different levels
- Trailing Stops: Orders trail downward (Follow Price)
- Position Monitoring: Auto-attaches stops/limits when orders fill
- Market Scanner: Finds markets near highs/lows (Yahoo Finance)
- Stock Screener: Filters UK stocks for ISA
- Trend Screener: Multi-timeframe analysis with rally detection
- **Instrument Groups: Batch trading (NEW - Nov 15, 2025)** ⚠️ Not visible in screenshots - need to check if added
- **Individual Order/Position Management (NEW - Nov 15, 2025)** ✅ Working!

**User Profile:**
- IT Manager, experienced with AI coding assistants
- Trades: Gold, Russell 2000, indices, bonds, commodities
- Wants automated trading without being online constantly

---

## 📁 COMPLETE FILE STRUCTURE

```
/
├── main.py (17 lines)                 # Entry point
├── config.py (72 lines)               # Configuration
│
├── trading/
│   ├── ig_client.py                   # IG Markets API client
│   ├── ladder_strategy.py             # Ladder placement logic
│   ├── position_monitor.py            # Auto-attach stops/limits
│   ├── auto_strategy.py               # Auto-adjust ladder positions
│   └── risk_manager.py                # Risk calculations
│
├── ui/
│   └── main_window.py (5509 lines)    # GUI - CustomTkinter ⚠️
│
├── api/
│   ├── yahoo_finance_helper.py        # Yahoo Finance mapping
│   ├── market_scanner.py              # Market scanner
│   ├── stock_screener.py              # ISA stock screener  
│   ├── trend_analyzer.py              # Multi-timeframe analysis
│   ├── notification_system.py         # Rally alerts
│   ├── watchlist_manager.py           # Watchlist storage
│   ├── market_list.py                 # Hardcoded popular markets
│   └── instrument_groups.py           # Group management (NEW)
│
└── data/
    ├── instrument_groups.json         # Saved groups
    ├── watchlist.json                 # Trend screener watchlist
    └── .env                           # Credentials (NOT in repo!)
```

---

## 🎨 CUSTOMTKINTER - CRITICAL RULES

**⚠️ #1 SOURCE OF BUGS - READ CAREFULLY!**

Your app uses **CustomTkinter (`ctk`)**, NOT standard tkinter!

### Rule 1: Widget Names
```python
# ❌ WRONG
import tkinter.ttk as ttk
ttk.Button(), ttk.Label(), ttk.Frame()

# ✅ CORRECT  
import customtkinter as ctk
ctk.CTkButton(), ctk.CTkLabel(), ctk.CTkFrame()
```

### Rule 2: Use `.configure()` NOT `.config()`
```python
# ❌ WRONG - Will crash!
widget.config(text="Hi")

# ✅ CORRECT
widget.configure(text="Hi")
```
**Error:** `AttributeError: 'config' is not implemented for CTk widgets`

### Rule 3: Parameter Names
```python
# ❌ WRONG - Standard tkinter params
ctk.CTkLabel(parent, foreground="red", bg="blue")

# ✅ CORRECT - CustomTkinter params  
ctk.CTkLabel(parent, text_color="#e74c3c", fg_color="#25292e")
```

### Rule 4: Exception for Standard Widgets
**Some widgets don't exist in CustomTkinter:**
- `ttk.Treeview` ✅ Use standard tkinter
- `ttk.Style` ✅ Use standard tkinter
- `tk.Scrollbar` ✅ Use standard tkinter

**For these ONLY:**
```python
style = ttk.Style()
style.configure("Treeview", foreground=white)  # ✅ foreground for ttk
scrollbar.configure(command=tree.yview)  # ✅ Still use .configure()!
```

### Standard Colors & Fonts
```python
# Colors from Theme class
bg_dark = "#1a1d23"        # Main background
card_bg = "#25292e"        # Card/panel background  
accent_teal = "#3a9d8e"    # Primary accent
text_white = "#e8eaed"     # Primary text
text_gray = "#9fa6b2"      # Secondary text
success_green = "#00d084"  # Success states
danger_red = "#e74c3c"     # Error/danger states

# Fonts via Theme class
Theme.font_normal()        # Default text
Theme.font_large()         # Section headers
Theme.font_normal_bold()   # Emphasis
```

---

## 📍 main_window.py INTEGRATION POINTS

**File: 5509 lines total**

### Key Sections:

**Imports (Lines 1-17):**
```python
Line 11: from api.instrument_groups import InstrumentGroups  # Added Nov 15
Line 13: import customtkinter as ctk
```

**Initialization (Lines 150-167):**
```python
Line 166: self.instrument_groups = InstrumentGroups()  # Added Nov 15
```

**Tab Creation (Lines 280-297):**
```python
Line 281: self.notebook.add("Connection")
Line 282: self.notebook.add("Trading")
Line 283: self.notebook.add("Risk Management")
Line 284: self.notebook.add("Configuration")
Line 285: self.notebook.add("Market Research")
Line 286: self.notebook.add("Trend Screener")
Line 287: self.notebook.add("Orders")          # Added Nov 15
Line 288: self.notebook.add("Positions")       # Added Nov 15

Line 296: self.create_order_management_tab(...)   # Added Nov 15
Line 297: self.create_position_management_tab(...) # Added Nov 15
```

**New Features Added Nov 15:**
- Lines 1447-1756: `create_order_management_tab()` method ✅ Working
- Lines 1758-2100: `create_position_management_tab()` method ✅ Working

**Where to Add New Features:**
- After line 297: New tab creation calls
- Line 699: Between ladder buttons and position management (in Trading tab)
- End of file (~5400): New class methods

---

## 🔑 IG API METHOD SIGNATURES

**MEMORIZE THESE - Source of 90% of bugs!**

```python
# Connect
ig_client.connect(username, password, api_key, base_url)

# Place order
ig_client.place_order(
    epic, direction, size, level,
    stop_distance=20,      # POINTS from entry
    limit_distance=10,     # POINTS from entry  
    guaranteed_stop=False
)

# Update working order
ig_client.update_working_order(
    deal_id,               # positional arg
    new_level,             # positional arg - NEW price
    stop_distance=20,      # keyword - POINTS
    guaranteed_stop=False
)

# Update position
ig_client.update_position(
    deal_id,
    stop_level=4050.23,    # ABSOLUTE PRICE
    limit_level=4070.23    # ABSOLUTE PRICE
)

# Get data (returns List[Dict] directly, not wrapped)
ig_client.get_working_orders()      # Returns: List[Dict]
ig_client.get_open_positions()      # Returns: List[Dict]

# Cancel/Close (returns tuple)
ig_client.cancel_order(deal_id)                      # Returns: (success, message)
ig_client.close_position(deal_id, direction, size)   # Returns: (success, message)
```

### Key Differences Table

| Working Orders | Positions |
|---|---|
| `stop_distance=` (points) | `stop_level=` (absolute price) |
| `new_level` positional arg | All keyword args |
| Returns list directly | Returns list directly |
| `cancel_order(deal_id)` | `close_position(deal_id, direction, size)` |

### IG API Limitations

⚠️ **CANNOT modify existing orders to add/remove limits**
- Limits MUST be set when placing the order
- To change limits: cancel and re-place entire order
- Toggle switches only affect NEW orders

✅ **CAN update:**
- Working order levels (entry price)
- Working order stop distances  
- Position stops and limits (after fill)

---

## 🐛 COMMON BUG PATTERNS

### Bug #1: NoneType Math Errors
```
Error: unsupported operand type(s) for +: 'NoneType' and 'float'
```

**Cause:** IG API returns `None` for position `level` field

**Fix:**
```python
# ❌ WRONG
level = position_data.get("level")
limit = level + distance  # Crash if None!

# ✅ CORRECT
level = position_data.get("level") or position_data.get("openLevel")
if level is None:
    return False
limit = level + distance
```

### Bug #2: Wrong Parameter Names
```
Error: update_working_order() got unexpected keyword 'stop_level'
```

**Fix:** Use `stop_distance=` for orders, `stop_level=` for positions

### Bug #3: CustomTkinter Errors
```
AttributeError: 'config' is not implemented  
ValueError: ['foreground'] are not supported
```

**Fix:**
- Use `.configure()` not `.config()`
- Use `text_color=` not `foreground=` for CTk widgets
- Use `foreground=` for `ttk.Style` only

### Bug #4: Missing Attributes
```
AttributeError: 'MainWindow' object has no attribute 'auto_stop_toggle'
```

**Cause:** Code references toggle that doesn't exist or has different name

**Fix:** Search for where toggle should be created, verify it exists

---

## 🔄 HOW THE SYSTEM WORKS

### Ladder Strategy Flow
1. User clicks "PLACE LADDER"
2. `main_window.py` → `ladder_strategy.place_ladder()`
3. Gets current price, calculates levels
4. Places orders with `ig_client.place_order()`
5. If rejected (too close), retries with larger offset
6. Stores in `self.placed_orders` list
7. **Tries to start position monitor** ← This is where error occurs!

### Follow Price (Trailing Stop Entries)
1. User toggles "Follow Price" ON (orange)
2. Calls `ladder_strategy.start_trailing()`
3. Background thread checks every 30s
4. For each order:
   - Calculates ideal level from current price
   - Updates if price moved favorably
   - **PRESERVES original spacing between rungs**
   - **PRESERVES stop distances**

### Position Monitoring (Auto-attach)
1. `position_monitor.py` runs in background
2. Every 10 seconds, checks for new positions  
3. When order fills:
   - Detects new position
   - Tries to check `auto_stop_toggle` ← **FAILS HERE!**
   - Should attach stop/limit/trailing based on toggles

**⚠️ Current Issue:** Toggle attributes don't exist, causing crash

---

## 📊 DATA STRUCTURES FROM IG API

### Working Order
```python
{
    "workingOrderData": {
        "dealId": "DIAAAAVG34EMUAY",
        "direction": "SELL",
        "epic": "CS.D.USCGC.TODAY.IP",
        "orderLevel": 4024.23,         # Order trigger price
        "dealSize": 0.1,
        "contingentStop": 20.0,        # May be None!
        "contingentLimit": None,       # May be None!
        "controlledRisk": False,       # GSLO flag
        "requestType": "STOP_ORDER"
    },
    "marketData": {
        "epic": "CS.D.USCGC.TODAY.IP",
        "instrumentName": "Spot Gold"
    }
}
```

### Position
```python
{
    "position": {
        "dealId": "DIAAAAVG34A5DAH",
        "direction": "SELL",
        "dealSize": 0.1,
        "level": None,            # ⚠️ Can be None!
        "openLevel": 4034.23,     # ✅ Use this instead!
        "stopLevel": 4054.23,     # Absolute price, may be None
        "limitLevel": None,       # Absolute price, may be None
        "controlledRisk": False,
        "profit": 12.50           # Current P&L
    },
    "market": {
        "epic": "CS.D.USCGC.TODAY.IP",
        "instrumentName": "Spot Gold",
        "bid": 4030.00,
        "offer": 4030.50
    }
}
```

**Key Insight:** Always use `openLevel` not `level` for calculations!

---

## 🚨 PRIORITY ISSUES TO FIX

### **Priority 1: Test Auto-Attach Features** ✅ UI Fixed, Needs Testing

**What was fixed:**
- Position Management section now visible in Trading tab
- Auto-attach toggles created: Stop, Trail, Limit
- Position monitor can now start automatically

**What needs testing:**
1. Place a ladder in DEMO mode
2. Verify position monitor starts when toggles enabled
3. Test that stops/limits attach automatically when orders fill
4. Verify trailing stops update correctly

---

### **Priority 2: Test Instrument Groups** ✅ UI Fixed, Needs Testing

**What was fixed:**
- Instrument Groups section now visible in Trading tab
- Can select groups and see instrument preview
- Batch order placement button present

**What needs testing:**
1. Create a test group (e.g., "Metals" with Gold + Silver)
2. Test batch order placement
3. Verify orders placed on all instruments in group
4. Check error handling for failed instruments

---

### **Priority 3: Configuration Tab Clarity**

**Current toggles:**
- Enable Risk Management ✓ (appears to work)
- Enable Limit Orders ✓ (what does this do?)
- Enable Auto-Replace Strategy (not implemented)
- Enable Trailing Stops (unclear what this affects)

**Need to clarify:**
- Does "Enable Limit Orders" auto-attach limits to positions?
- Does "Enable Trailing Stops" trail position stops?
- Should remove "Auto-Replace" if not implemented?

---

### **Priority 4: UI Enhancements**

Consider adding to bottom panel:
- Margin usage indicator (colored by risk level)
- Account summary (Balance, P&L, open positions count)
- Quick status of position monitor (running/stopped)

---

## ⚡ QUICK REFERENCE

### Popular Epics
```python
# Commodities
"CS.D.USCGC.TODAY.IP"      # Gold Spot (most traded)
"CS.D.USCSI.TODAY.IP"      # Silver Spot

# Indices  
"IX.D.RUSSELL.DAILY.IP"    # Russell 2000
"IX.D.FTSE.DAILY.IP"       # FTSE 100
"IX.D.SPTRD.DAILY.IP"      # S&P 500
"IX.D.DOW.DAILY.IP"        # Dow Jones

# Bonds
"IR.D.10YEAR100.Month2.IP" # 10-Year T-Note
```

### Base URLs
```python
demo_url = "https://demo-api.ig.com/gateway/deal"
live_url = "https://api.ig.com/gateway/deal"
```

### Risk Defaults (from risk_manager.py)
```python
max_daily_loss = 200.0          # GBP
max_position_size = 5.0         # Lots
max_margin_usage = 0.3          # 30%
max_positions = 10
max_total_exposure = 1000.0     # GBP
```

---

## 💡 UI IMPROVEMENTS SUGGESTED

Based on screenshot analysis:

### Trading Tab
1. **Group related controls** - Clear visual separation between:
   - Order Placement
   - Stop/Limit Controls  
   - Follow Price
   - On Trigger (if adding back)

2. **Add Instrument Groups section** - Batch trading feature
   - Group dropdown
   - "Place Batch Orders" button
   - Preview of instruments in group

3. **Add missing controls** (if needed):
   - Limit distance input
   - Auto-attach toggles
   - Update buttons

### Orders/Positions Tabs ✅ Already Great!
- Clean, professional look
- All essential buttons present
- Good column layout

### Configuration Tab
1. **Add descriptions** - What each toggle actually does
2. **Remove unimplemented features** - "Auto-Replace Strategy"
3. **Group by category:**
   - Risk Management
   - Auto-Attach Features
   - Advanced Features

### Bottom Panel
- **Add margin usage indicator** - Show current margin % (colored by risk level)
- **Add account summary** - Balance, P&L, open positions count

---

## 📝 SESSION HISTORY - NOVEMBER 15, 2025

### Session 1: Added Order/Position Tabs & Instrument Groups

**What We Added:**
1. **Instrument Groups** (`instrument_groups.py`)
   - Create/manage groups of instruments
   - Batch place ladders  
   - Save/load to JSON

2. **Orders Tab** (lines 1447-1756) ✅ Working
   - View all working orders
   - Cancel individual orders
   - Auto-refresh after actions

3. **Positions Tab** (lines 1758-2100) ✅ Working
   - View all positions with P&L
   - Close individual positions
   - Color-coded by profit/loss
   - Auto-refresh after actions

**Bugs Fixed:**
- CustomTkinter `.config()` → `.configure()`
- `foreground=` → `text_color=` for CTk widgets
- Deleted duplicate nested methods (lines 1304-1378)
- Fixed method signatures (added `parent` parameter)
- Fixed IG API integration (proper return value handling)

**Status at end of Session 1:**
✅ App runs successfully
✅ Connects to IG (Live account working!)
✅ Can place ladders (5/5 orders placed)
✅ Can view/cancel orders
✅ Can view/close positions
⚠️ Error after ladder placement: `'MainWindow' object has no attribute 'auto_stop_toggle'`

---

### Session 2: Fixed auto_stop_toggle Error ✅

**The Problem:**
- Method `add_to_create_trading_tab()` contained critical UI sections but was NEVER called
- Missing sections: INSTRUMENT GROUPS + POSITION MANAGEMENT
- Missing toggles: auto_stop_toggle, auto_trailing_toggle, auto_limit_toggle
- Crash at line 3829 when trying to start position monitor

**The Fix:**
Added one line at end of `create_trading_tab()` method:
```python
self.add_to_create_trading_tab(parent, scrollable_frame, card_bg, accent_teal, text_white, text_gray)
```

**Result:**
- ✅ Trading tab now shows INSTRUMENT GROUPS section
- ✅ Trading tab now shows POSITION MANAGEMENT section
- ✅ All auto-attach toggles created properly
- ✅ Position monitor can start without errors
- ✅ File updated from 5434 lines → 5438 lines

**What Needs Testing:**
- Auto-attach feature (stops/limits/trailing)
- Batch order placement via Instrument Groups
- Position monitor functionality

---

## 🎯 CRITICAL REMINDERS FOR CLAUDE

### Before Making Changes:
1. ✅ Check uploaded files
2. ✅ Verify method signatures in ig_client.py
3. ✅ Test logic with None values
4. ✅ Remember CustomTkinter rules!
5. ✅ Check Comprehensive_Todo.txt for known issues
6. ❌ Don't assume - verify!

### When Debugging:
1. Find EXACT line number in error
2. Check if working orders vs positions
3. Verify method signature
4. Check for None values
5. Search for similar past issues

### Common Mistakes to Avoid:
- Assuming `level` exists (use `openLevel`)
- Using `stop_level` for working orders (use `stop_distance`)
- Forgetting `new_level` positional arg
- Trying to add limits to existing orders (not possible)
- Using `.config()` instead of `.configure()`
- Using `foreground=` on CustomTkinter widgets
- Creating nested methods accidentally

---

## 📋 KNOWN ISSUES (From Comprehensive_Todo.txt)

### Critical:
- [x] **auto_stop_toggle error** - ✅ FIXED Nov 15, 2025
- [x] Missing "On Trigger" section in Trading tab - ✅ FIXED Nov 15, 2025  
- [ ] GSLO toggle only works at placement (not dynamic)
- [ ] Emergency stop fails when market closed

### Medium:
- [ ] Test and verify Auto-Attach features work correctly
- [ ] Test Instrument Groups batch placement
- [ ] Verify Risk Management actually prevents trading
- [ ] Split Update button → "Update Orders" vs "Update Positions"
- [ ] Clarify Configuration tab toggle meanings

### Low:
- [ ] Add position size calculator
- [ ] Export trade journal
- [ ] Add backtesting
- [ ] Add margin usage indicator to bottom panel

**See Comprehensive_Todo.txt for complete list**

---

**END OF CHEAT SHEET**

Remember: This bot trades real money. Test thoroughly in DEMO before going live!
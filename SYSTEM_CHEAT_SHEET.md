# IG TRADING BOT - SYSTEM CHEAT SHEET
**Upload this file at the start of every chat to help Claude understand the system**

Last Updated: October 27, 2025

---

## 🎯 SYSTEM OVERVIEW

This is a **Python-based automated trading bot** for IG Markets (spread betting platform).

**Primary Features:**
- **Ladder Strategy**: Places multiple stop entry orders at different price levels
- **Trailing Stops**: Orders trail downward (for entries) or positions trail stops
- **Position Monitoring**: Auto-attaches stops/limits when orders fill
- **Market Scanner**: Finds markets near highs/lows using Yahoo Finance
- **Stock Screener**: Filters UK stocks for ISA investments

**User Profile:**
- IT Manager with programming skills
- Uses Claude, ChatGPT, Gemini, and Copilot for development
- Trades: Gold, Russell 2000, FTSE indices, bonds, commodities
- Wants to run bot without being online all the time

---

## 📁 FILE STRUCTURE

```
/
├── main.py                    # Entry point
├── config.py                  # Configuration/settings
├── ig_client.py              # IG Markets API client
├── ladder_strategy.py        # Ladder placement logic
├── position_monitor.py       # Auto-attach stops/limits to filled orders
├── auto_strategy.py          # Auto-adjust ladder positions
├── risk_manager.py           # Risk calculations
├── main_window.py            # GUI (1194 lines)
├── api/
│   ├── yahoo_finance_helper.py
│   ├── market_scanner.py
│   └── stock_screener.py
└── strategies/
    └── (various strategy files)
```

---

## 🔑 CRITICAL IG API FACTS

### **1. IG API Method Signatures (MEMORIZE THESE!)**

```python
# ig_client.py - ACTUAL signatures from working code

def connect(self, username, password, api_key, base_url):
    """
    Connect to IG API
    base_url: "https://demo-api.ig.com/gateway/deal" (demo)
              "https://api.ig.com/gateway/deal" (live)
    """

def update_working_order(self, deal_id, new_level, stop_distance=None, guaranteed_stop=False):
    """
    Update a working order
    
    deal_id: Order to update
    new_level: NEW PRICE LEVEL for the order (e.g., 4050.23)
    stop_distance: POINTS from entry (e.g., 20), NOT absolute price
    guaranteed_stop: Boolean
    
    Returns: (success: bool, message: str)
    """

def update_position(self, deal_id, stop_level=None, stop_distance=None, limit_level=None):
    """
    Update an open position
    
    stop_level: ABSOLUTE PRICE for stop (e.g., 4030.23)
    stop_distance: POINTS from entry (alternative to stop_level)
    limit_level: ABSOLUTE PRICE for limit
    """

def place_order(self, epic, direction, size, level, order_type="STOP", 
                stop_distance=0, guaranteed_stop=False, limit_distance=0):
    """
    Place a working order
    
    stop_distance: POINTS from entry
    limit_distance: POINTS from entry
    """
```

### **2. Key Differences (STOP CONFUSING THESE!)**

| Working Orders | Positions |
|---------------|-----------|
| `update_working_order(deal_id, new_level, stop_distance=20)` | `update_position(deal_id, stop_level=4030.23)` |
| Uses `stop_distance` (points) | Uses `stop_level` (absolute price) |
| `new_level` is positional arg | All args are keyword args |

### **3. IG API Limitations**

⚠️ **CANNOT modify existing working orders to add/remove limits**
- Limits MUST be set when initially placing the order
- To change limits, must cancel and re-place the entire order
- Toggle limit switches only work for NEW orders, not existing ones

✅ **CAN update working order levels** (price point where order triggers)
✅ **CAN update working order stop distances** (preserve stop when moving level)
✅ **CAN update position stops and limits** (after order fills)

---

## 🐛 COMMON BUGS & PITFALLS

### **Bug Pattern #1: NoneType Math Errors**

**Symptom:**
```
Error: unsupported operand type(s) for +: 'NoneType' and 'float'
```

**Cause:**
IG API sometimes returns `None` for position `level` field

**Example:**
```python
# WRONG ❌
level = position_data.get("level")
limit_level = level + distance  # Crashes if level is None!

# CORRECT ✅
level = position_data.get("level")
if level is None:
    log("Cannot calculate - position has no level")
    return False
limit_level = level + distance
```

**Where this happens:**
- `position_monitor.py`: `_attach_stop()` and `_attach_limit()` methods
- Any code doing math with values from IG API

### **Bug Pattern #2: Wrong Parameter Names**

**Symptom:**
```
Error: update_working_order() got an unexpected keyword argument 'stop_level'
```

**Cause:**
Confusing working order vs position methods

**Example:**
```python
# WRONG ❌
self.ig_client.update_working_order(
    deal_id=deal_id,
    stop_level=4050.23  # This parameter doesn't exist!
)

# CORRECT ✅
self.ig_client.update_working_order(
    deal_id,  # positional
    new_level,  # positional - NEW price for order
    stop_distance=20,  # keyword - preserve stop
    guaranteed_stop=False
)
```

### **Bug Pattern #3: Missing Positional Arguments**

**Symptom:**
```
Error: update_working_order() missing 1 required positional argument: 'new_level'
```

**Cause:**
Forgot that `new_level` must be provided when updating orders

**Example:**
```python
# WRONG ❌
self.ig_client.update_working_order(
    deal_id=deal_id,
    stop_distance=20
)

# CORRECT ✅
self.ig_client.update_working_order(
    deal_id,
    new_level,  # MUST provide the new order level!
    stop_distance=20
)
```

---

## 🔄 HOW THINGS ACTUALLY WORK

### **Ladder Strategy Flow**

1. User clicks "Place Ladder"
2. `main_window.py` calls `ladder_strategy.place_ladder()`
3. Ladder strategy:
   - Gets current price
   - Calculates levels (offset + steps)
   - Places orders with `ig_client.place_order()`
   - If order rejected as "too close", retries with larger offset
   - Stores placed orders in `self.placed_orders` list

### **Trailing Stop Entries (for Working Orders)**

1. User toggles "Trailing Stop Entry" ON
2. `main_window.py` calls `ladder_strategy.start_trailing()`
3. Background thread monitors working orders every 30s
4. For each order:
   - Calculates ideal level based on current price
   - If price moved favorably, updates order level
   - PRESERVES original spacing between ladder rungs
   - PRESERVES stop distances on each order

**Important:** Each order maintains its ORIGINAL offset from price, so rungs don't collapse together!

### **Position Monitoring (Auto-attach Stops/Limits)**

1. `position_monitor.py` runs in background
2. Every 10 seconds, checks for new positions
3. When order fills → becomes position:
   - Detects new position
   - If auto-stop enabled: attaches stop loss
   - If auto-trailing enabled: enables trailing on that position
   - If auto-limit enabled: attaches profit target
4. For existing positions with trailing:
   - Monitors price movement
   - Trails stop in favorable direction only
   - Never moves stop against position

**Critical Detail:** Position level might be `None` right after fill! Must check before math.

### **Toggle Switches Behavior**

**What they DO:**
- Set configuration for FUTURE actions
- For working orders: Only affects NEW orders
- For positions: Only affects NEW fills

**What they DON'T do:**
- Modify existing orders (IG API limitation)
- Instantly apply to all open positions

**Example:**
- Toggle "Limit" ON → sets limit distance
- Place ladder → orders created WITH limits
- Toggle "Limit" OFF → existing orders keep their limits
- Place another ladder → new orders have NO limits

---

## 📊 DATA STRUCTURE EXAMPLES

### **Working Order from IG API**

```python
{
    "workingOrderData": {
        "dealId": "DIAAAAVG34EMUAY",
        "direction": "SELL",
        "epic": "CS.D.USCGC.TODAY.IP",
        "level": 4024.23,  # Order trigger price
        "size": 0.1,
        "contingentStop": 20.0,  # Stop distance (might be None!)
        "contingentLimit": None,  # Limit distance (might be None!)
        "controlledRisk": False,  # Guaranteed stop
        "requestType": "STOP_ORDER"
    },
    "marketData": {
        "epic": "CS.D.USCGC.TODAY.IP",
        "instrumentName": "Spot Gold"
    }
}
```

### **Position from IG API**

```python
{
    "position": {
        "dealId": "DIAAAAVG34A5DAH",
        "direction": "SELL",
        "dealSize": 0.1,
        "level": None,  # ⚠️ Can be None right after fill!
        "openLevel": 4034.23,  # Use this instead!
        "stopLevel": 4054.23,  # Absolute price (might be None!)
        "limitLevel": None,  # Absolute price (might be None!)
        "controlledRisk": False
    },
    "market": {
        "epic": "CS.D.USCGC.TODAY.IP",
        "instrumentName": "Spot Gold"
    }
}
```

**Key Insight:** Use `openLevel` not `level` for calculations! `level` can be None.

---

## 🚨 CRITICAL REMINDERS FOR CLAUDE

### **Before Making Changes:**

1. ✅ Look at ACTUAL files uploaded by user
2. ✅ Check previous chat history for context
3. ✅ Verify method signatures in ig_client.py
4. ✅ Test logic with None values
5. ❌ Don't assume how things work
6. ❌ Don't confuse working orders vs positions
7. ❌ Don't confuse stop_level vs stop_distance

### **When Debugging Errors:**

1. Find the EXACT line number in the error
2. Look at the ACTUAL code at that line
3. Check if it's working orders or positions
4. Verify the method signature being called
5. Check for None values in calculations
6. Search previous chats for related fixes

### **Common Mistakes to Avoid:**

- Assuming `level` exists (might be None)
- Using `stop_level` param for working orders (doesn't exist)
- Forgetting `new_level` positional arg
- Trying to modify existing orders to add limits (API limitation)
- Confusing absolute prices vs point distances

---

## 🎨 GUI LAYOUT

**Main Window** (1194 lines in main_window.py)

**Tabs:**
1. **Connection** - Connect to demo/live account
2. **Trading** - Place ladders, manage orders
   - Left side: Ladder configuration
   - Right side: "On Trigger" settings (auto-attach stops/limits)
3. **Positions** - View and manage open positions
4. **Market Research** - Two sub-tabs:
   - Market Scanner (spread betting)
   - Stock Screener (ISA investments)
5. **Risk** - Risk management settings
6. **Configuration** - Strategy settings

**Toggle Switches:**
- Green = ON
- Red = OFF
- Custom widget (not standard tkinter)

---

## 📝 DEVELOPMENT NOTES

### **Technologies Used:**
- Python 3.13
- tkinter for GUI
- requests for API calls
- threading for background tasks
- Yahoo Finance for market data (no API key needed)

### **Code Quality:**
- Some code duplicated across files
- main_window.py is very long (1194 lines)
- User aware of need for refactoring
- Prioritizes functionality over architecture

### **User Workflow:**
- Develops with multiple AI assistants
- Tests on demo account first
- Runs on Windows (watch for line ending issues)
- Uses VS Code

---

## ⚡ QUICK REFERENCE

### **Most Common Methods:**

```python
# Connect
ig_client.connect(username, password, api_key, base_url)

# Place order
ig_client.place_order(epic, direction, size, level, 
                      stop_distance=20, limit_distance=10)

# Update working order (move entry point)
ig_client.update_working_order(deal_id, new_level, 
                               stop_distance=20)

# Update position (move stop/limit)
ig_client.update_position(deal_id, stop_level=4050.23, 
                          limit_level=4070.23)

# Get data
ig_client.get_market_price(epic)
ig_client.get_working_orders()
ig_client.get_open_positions()
```

### **Epic Code Examples:**
- Gold: `CS.D.USCGC.TODAY.IP`
- Russell 2000: `IX.D.RUSSELL.DAILY.IP`
- FTSE 100: `IX.D.FTSE.DAILY.IP`

### **Base URLs:**
- Demo: `https://demo-api.ig.com/gateway/deal`
- Live: `https://api.ig.com/gateway/deal`

---

## 🎯 WHEN IN DOUBT

1. **Read this cheat sheet first**
2. **Search previous chats** for similar issues
3. **Look at actual code** before suggesting changes
4. **Check method signatures** in ig_client.py
5. **Test with None values** in mind
6. **Ask user** if unclear about something

---

**END OF CHEAT SHEET**

Remember: This bot has been through many iterations. Don't undo working code! Check previous chats and this cheat sheet before making changes.

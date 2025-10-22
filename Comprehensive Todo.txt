# IG Trading Bot - Comprehensive TODO List

## 🔴 CRITICAL - Fix Immediately

### Stop/Limit/Trail Logic Overhaul
- [ ] **Decision needed:** Answer 5 questions in "Complete Stop/Limit/Trail Logic Review" document
- [ ] Remove redundant stop attachment from position monitor
- [ ] Fix GSLO toggle to work dynamically (not just at placement time)
- [ ] Split "Update" button into "Update Orders" and "Update Positions"
- [ ] Rename "Trailing Stop Entry" to "Follow Price" for clarity
- [ ] Fix GSLO preservation dialog to only show when orders actually have GSLO
- [ ] Ensure stops are ONLY attached once (either at creation OR when filled, not both)

### Risk Management Section - VERIFY WORKING
- [ ] Test that "Enable Risk Management" toggle actually enables/disables checks
- [ ] Verify margin usage calculation is accurate
- [ ] Test daily loss limit enforcement (does it actually stop trading?)
- [ ] Test max position size limit (does it prevent oversized orders?)
- [ ] Test risk/reward ratio check (does it reject bad trades?)
- [ ] Add visual feedback when risk limits are breached
- [ ] Log all risk check failures to Activity Log
- [ ] Test what happens when risk limits hit during ladder placement

---

## 🟡 HIGH PRIORITY - Core Functionality

### Optional Features Section
- [ ] **Enable Risk Management** - Verify it's actually working (see above)
- [ ] **Enable Limit Orders** - Currently doesn't work on working orders
  - Option A: Remove this toggle (limits only work on positions)
  - Option B: Make it clear it's "Auto-attach limits to positions when filled"
  - Option C: Keep but display warning that it won't work on orders
- [ ] **Enable Auto-Replace Strategy** - NOT IMPLEMENTED YET
  - Decide on behavior: replace filled orders automatically?
  - Add configuration: how many replacement rungs?
  - Add safety limits: max replacements per day/hour?
- [ ] **Enable Trailing Stops** - Currently exists but needs clarity
  - Is this for working orders (Follow Price) or positions (Trailing SL)?
  - Split into two separate toggles if needed

### Position Management Improvements
- [ ] Add "Update Position Stops" button (separate from order updates)
- [ ] Allow manual addition of limits to existing positions
- [ ] Show position P&L in real-time in the UI
- [ ] Add "Bulk Close Positions" functionality
- [ ] Add position filtering by market/direction
- [ ] Color-code positions by profit/loss status

### Emergency Stop Functionality
- [ ] Fix closing positions when market is closed (MARKET_CLOSED_WITH_EDITS error)
- [ ] Add fallback: use limit orders when markets closed
- [ ] Or: add warning that positions can only be closed when market open
- [ ] Ensure emergency stop properly checks return values from close_position()
- [ ] Add retry logic for failed position closes

---

## 🟢 MEDIUM PRIORITY - Enhancements

### UI/UX Improvements
- [ ] Simplify trading tab layout (see proposed layout in review doc)
- [ ] Add better visual separation between "Order Placement" and "Position Management"
- [ ] Add tooltips explaining what each toggle does
- [ ] Show current margin usage in header (colored by risk level)
- [ ] Add "Quick Presets" for common strategies (e.g., "Conservative", "Aggressive")
- [ ] Make order/position tables sortable by column
- [ ] Add market status indicator (open/closed) next to market selector

### Market Scanner Enhancements
- [ ] Verify cache system is working (timeframe-specific caching)
- [ ] Add export to CSV functionality
- [ ] Add filters: only show near highs/lows, exclude closed markets, etc.
- [ ] Add alerts when markets hit extreme positions (< 5% or > 95%)
- [ ] Add comparison view: show multiple timeframes side-by-side

### Ladder Strategy Improvements
- [ ] Add validation: prevent placing orders too close to current price
- [ ] Add preview: show where ladder rungs will be placed before submitting
- [ ] Add "Cancel Ladder" functionality that actually works reliably
- [ ] Save/load ladder templates (preset configurations)
- [ ] Add "Adjust Ladder" - modify existing ladder without canceling

### Trailing Stop Entry (Follow Price)
- [ ] Verify it maintains proper spacing between rungs when trailing
- [ ] Add visual indicator showing when trailing is active
- [ ] Add "pause trailing" functionality
- [ ] Log trailing adjustments with more detail (old level → new level)

### Position Monitor
- [ ] Ensure it only attaches stops if position doesn't already have one
- [ ] Add logging when new positions detected
- [ ] Add logging when stops/limits auto-attached
- [ ] Add option to manually trigger position scan (don't wait for interval)
- [ ] Show last scan time in UI

---

## 🔵 LOW PRIORITY - Nice to Have

### Auto-Replace Strategy Implementation
- [ ] Design the logic: when to replace, how many rungs, spacing
- [ ] Add configuration UI
- [ ] Add safety limits and circuit breakers
- [ ] Add logging for all replacement actions
- [ ] Add manual override to stop replacement
- [ ] Test extensively before enabling in live trading

### Advanced Features
- [ ] Add technical analysis module (support/resistance detection)
  - Fetch historical price data
  - Calculate pivot points
  - Identify key levels
  - Display in UI
  - Optional: auto-place orders at key levels
- [ ] Add RSI calculation and display
- [ ] Add alerts/notifications system
  - Desktop notifications
  - Email alerts
  - Sound alerts
- [ ] Add trade journal/history export
- [ ] Add backtesting capability

### Multiple Markets Management
- [ ] Allow simultaneous trading on multiple markets
- [ ] Add market correlation analysis
- [ ] Add portfolio view showing all markets together
- [ ] Add aggregate P&L across all markets

### Code Quality & Maintenance
- [ ] Add comprehensive error handling to all IG API calls
- [ ] Add unit tests for core logic
- [ ] Add integration tests for order placement
- [ ] Improve logging structure (log levels, rotation)
- [ ] Add configuration file validation
- [ ] Document all API rate limits and implement rate limiting
- [ ] Add connection health check (auto-reconnect if session expires)

---

## 📋 TESTING CHECKLIST

### Before Going Live
- [ ] Test all order placement in DEMO account thoroughly
- [ ] Test emergency stop in various scenarios
- [ ] Test position closing when market is open
- [ ] Test position closing when market is closed (expect failure)
- [ ] Test risk management limits actually prevent trading
- [ ] Test GSLO toggle works correctly
- [ ] Test trailing stop entry maintains spacing
- [ ] Test position monitor detects new positions
- [ ] Test bulk stop updates don't break existing orders
- [ ] Test with different markets (Gold, Russell 2000, Bonds)
- [ ] Test with different order sizes
- [ ] Test when spread is wide (high volatility)
- [ ] Test when API rate limits hit
- [ ] Test when internet connection drops
- [ ] Test when IG session expires

### Known Issues to Document
- [ ] Limits cannot be attached to working orders (IG API limitation)
- [ ] Positions can only be closed when market is open
- [ ] GSLO costs extra and has minimum distance requirements
- [ ] Trailing stop entry may adjust all rungs rapidly in fast markets
- [ ] Position monitor runs every 10 seconds (not real-time)
- [ ] Market scanner uses Yahoo Finance (may have slight price differences from IG)

---

## 🗂️ FILE ORGANIZATION

### Current Files (verify all exist and are up to date)
- [ ] `main.py` - Entry point
- [ ] `main_window.py` - Main UI
- [ ] `ig_client.py` - IG API wrapper
- [ ] `ladder_strategy.py` - Ladder placement logic
- [ ] `position_monitor.py` - Auto-attach and trailing for positions
- [ ] `risk_manager.py` - Risk management checks
- [ ] `config.py` - Configuration and markets
- [ ] `market_scanner.py` - Market scanning logic
- [ ] `yahoo_finance_helper.py` - Yahoo Finance integration

### Files to Create
- [ ] `README.md` - Project documentation
- [ ] `INSTALL.md` - Installation instructions
- [ ] `TRADING_GUIDE.md` - How to use the bot
- [ ] `RISK_WARNING.md` - Important risk disclaimers
- [ ] `CHANGELOG.md` - Version history
- [ ] `requirements.txt` - Python dependencies
- [ ] `.gitignore` - Don't commit credentials
- [ ] `tests/` directory - Unit tests

---

## 💡 QUESTIONS TO ANSWER

### Stop/Limit/Trail Logic (from review doc)
1. **Stop attachment priority:** Should working orders have stops from the start, or only after they fill?
2. **GSLO default:** Should GSLO be ON or OFF by default?
3. **Limit orders:** Keep toggle, remove it, or rename it to be clearer?
4. **Trailing stop loss:** Automatic for all positions, or manual toggle?
5. **Update buttons:** Two separate buttons (orders vs positions) or keep as one?

### Auto-Replace Strategy
6. **Replacement trigger:** Replace immediately when filled, or wait for stop to hit?
7. **Replacement count:** How many new rungs to add?
8. **Replacement spacing:** Same as original ladder, or different?
9. **Safety limits:** Max replacements per day? Per hour? Stop after X losses?

### Risk Management
10. **Should it be enabled by default?** For safety, probably yes?
11. **Default margin limit:** What percentage?
12. **Default daily loss limit:** What amount in currency?
13. **Default max position size:** What size?
14. **What happens when limit hit:** Just log, or completely disable trading?

---

## 📝 DOCUMENTATION NEEDED

- [ ] Write clear README explaining what the bot does
- [ ] Document each toggle/checkbox in the UI
- [ ] Explain difference between "Follow Price" and "Trailing Stop Loss"
- [ ] Document risk management settings and recommendations
- [ ] Add examples of different trading strategies
- [ ] Document known limitations and IG API restrictions
- [ ] Add troubleshooting guide for common errors
- [ ] Document how to recover from errors/crashes
- [ ] Add section on costs (spreads, GSLO fees, etc.)

---

## 🎯 IMMEDIATE NEXT STEPS

**This week:**
1. ✅ You answer the 5 questions in the Stop/Limit/Trail review doc
2. ⏳ I implement the stop/limit/trail logic fixes
3. ⏳ We thoroughly test risk management to ensure it works
4. ⏳ Fix the GSLO toggle behavior
5. ⏳ Split Update button into two buttons

**Next week:**
1. Design and implement Auto-Replace Strategy (if you want this feature)
2. Add Position Management improvements
3. Fix emergency stop for closed markets
4. Improve UI layout based on review doc suggestions

**Ongoing:**
- Test everything in DEMO account before going live
- Document as we go
- Keep TODO list updated

---

## 📌 NOTES

- Always test in DEMO first
- Keep original working code backed up
- Git commit after each successful change
- Log everything for debugging
- Don't rush - trading bots can lose real money if buggy
- IG API has rate limits - respect them
- Markets can be closed - handle gracefully
- Session tokens expire - reconnect when needed

---

**Last Updated:** October 21, 2025  
**Project Status:** Core functionality working, needs refinement and testing  
**Priority Focus:** Fix stop/limit/trail logic, verify risk management works
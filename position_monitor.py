"""
Position Monitor
Watches for working orders becoming positions and auto-attaches stops/limits
Now includes VERIFICATION logic - checks if stops exist, adds if missing
"""
import threading
import time
from datetime import datetime

class PositionMonitor:
    """Monitors positions and auto-attaches stops when orders fill"""
    
    def __init__(self, ig_client):
        self.ig_client = ig_client
        self.running = False
        self.monitor_thread = None
        self.known_positions = set()  # Track position deal IDs we've already processed
        self.known_working_orders = set()  # Track working order deal IDs
        
        # Configuration
        self.auto_stop_enabled = True  # Default ON for safety
        self.auto_stop_distance = 20
        self.verify_stops = True  # Always verify stops exist
        
        self.auto_trailing_enabled = False
        self.trailing_distance = 15
        self.trailing_step = 5
        
        self.auto_limit_enabled = False
        self.auto_limit_distance = 10
        
        self.check_interval = 10  # Check every 10 seconds
        
    def configure(self, auto_stop=True, stop_distance=20, verify_stops=True,
                  auto_trailing=False, trailing_distance=15, trailing_step=5,
                  auto_limit=False, limit_distance=10):
        """Update monitor configuration"""
        self.auto_stop_enabled = auto_stop
        self.auto_stop_distance = stop_distance
        self.verify_stops = verify_stops
        
        self.auto_trailing_enabled = auto_trailing
        self.trailing_distance = trailing_distance
        self.trailing_step = trailing_step
        
        self.auto_limit_enabled = auto_limit
        self.auto_limit_distance = limit_distance
    
    def start(self, log_func):
        """Start monitoring positions"""
        if self.running:
            log_func("Position monitor already running")
            return
        
        self.running = True
        self.log_func = log_func
        
        # Initialize known positions and orders
        try:
            positions = self.ig_client.get_open_positions()
            self.known_positions = {p.get("position", {}).get("dealId") for p in positions if p.get("position", {}).get("dealId")}
            
            working_orders = self.ig_client.get_working_orders()
            self.known_working_orders = {o.get("workingOrderData", {}).get("dealId") for o in working_orders if o.get("workingOrderData", {}).get("dealId")}
            
            log_func(f"📊 Position monitor started - tracking {len(self.known_positions)} positions, {len(self.known_working_orders)} orders")
        except Exception as e:
            log_func(f"Warning: Could not initialize position tracking: {e}")
            self.known_positions = set()
            self.known_working_orders = set()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop(self):
        """Stop monitoring positions"""
        self.running = False
        if self.log_func:
            self.log_func("Position monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._check_positions()
                time.sleep(self.check_interval)
            except Exception as e:
                if self.log_func:
                    self.log_func(f"Position monitor error: {e}")
                time.sleep(self.check_interval)
    
    def _check_positions(self):
        """Check for new positions and manage them"""
        try:
            # Get current positions
            current_positions = self.ig_client.get_open_positions()
            current_position_ids = {p.get("position", {}).get("dealId") for p in current_positions if p.get("position", {}).get("dealId")}
            
            # Detect NEW positions (orders that just filled)
            new_position_ids = current_position_ids - self.known_positions
            
            if new_position_ids:
                self.log_func(f"🔔 Detected {len(new_position_ids)} new position(s)")
                
                for position in current_positions:
                    deal_id = position.get("position", {}).get("dealId")
                    if deal_id in new_position_ids:
                        self._process_new_position(position)
                
                # Update known positions
                self.known_positions = current_position_ids
            
            # Handle trailing for existing positions
            if self.auto_trailing_enabled:
                self._update_trailing_stops(current_positions)
                
        except Exception as e:
            if self.log_func:
                self.log_func(f"Error checking positions: {e}")
    
    def _process_new_position(self, position):
        """Process a newly opened position"""
        try:
            position_data = position.get("position", {})
            market_data = position.get("market", {})
            
            deal_id = position_data.get("dealId")
            epic = market_data.get("epic")
            instrument_name = market_data.get("instrumentName", epic)
            direction = position_data.get("direction")
            size = position_data.get("dealSize")
            level = position_data.get("level")
            
            # Check current stop level
            current_stop = position_data.get("stopLevel")
            
            self.log_func(f"📍 Processing new position: {instrument_name} {direction} {size} @ {level}")
            
            # VERIFY stop exists (safety check)
            if self.verify_stops:
                if current_stop is None or current_stop == 0:
                    # NO STOP - this is dangerous! Add one immediately
                    self.log_func(f"⚠️ WARNING: Position {deal_id} has NO stop loss!")
                    
                    if self.auto_stop_enabled:
                        success = self._attach_stop(position, self.auto_stop_distance)
                        if success:
                            self.log_func(f"✅ Emergency stop added to {deal_id}")
                        else:
                            self.log_func(f"❌ FAILED to add stop to {deal_id} - MANUALLY ADD STOP!")
                    else:
                        self.log_func(f"❌ Auto-stop disabled - position has NO protection!")
                else:
                    # Stop exists - good!
                    self.log_func(f"✅ Position has stop @ {current_stop}")
            
            # Add trailing if enabled
            if self.auto_trailing_enabled and current_stop:
                self.log_func(f"🔄 Enabling trailing stop ({self.trailing_distance}/{self.trailing_step})")
                # Trailing will be handled by _update_trailing_stops
            
            # Add limit if enabled
            if self.auto_limit_enabled:
                success = self._attach_limit(position, self.auto_limit_distance)
                if success:
                    self.log_func(f"✅ Limit added @ {self.auto_limit_distance}pts")
                else:
                    self.log_func(f"⚠️ Could not add limit")
                    
        except Exception as e:
            self.log_func(f"Error processing new position: {e}")
    
    def _attach_stop(self, position, stop_distance):
        """Attach stop loss to position"""
        try:
            position_data = position.get("position", {})
            deal_id = position_data.get("dealId")
            direction = position_data.get("direction")
            level = position_data.get("level")
            
            # Calculate stop level
            if direction == "BUY":
                stop_level = level - stop_distance
            else:  # SELL
                stop_level = level + stop_distance
            
            # Update position with stop
            success, message = self.ig_client.update_position(
                deal_id=deal_id,
                stop_level=stop_level,
                stop_distance=None,  # Use level, not distance
                limit_level=None
            )
            
            return success
            
        except Exception as e:
            self.log_func(f"Error attaching stop: {e}")
            return False
    
    def _attach_limit(self, position, limit_distance):
        """Attach limit (profit target) to position"""
        try:
            position_data = position.get("position", {})
            deal_id = position_data.get("dealId")
            direction = position_data.get("direction")
            level = position_data.get("level")
            
            # Calculate limit level
            if direction == "BUY":
                limit_level = level + limit_distance
            else:  # SELL
                limit_level = level - limit_distance
            
            # Update position with limit
            success, message = self.ig_client.update_position(
                deal_id=deal_id,
                stop_level=None,
                stop_distance=None,
                limit_level=limit_level
            )
            
            return success
            
        except Exception as e:
            self.log_func(f"Error attaching limit: {e}")
            return False
    
    def _update_trailing_stops(self, positions):
        """Update trailing stops for all positions"""
        try:
            for position in positions:
                position_data = position.get("position", {})
                market_data = position.get("market", {})
                
                deal_id = position_data.get("dealId")
                direction = position_data.get("direction")
                current_level = position_data.get("level")
                current_stop = position_data.get("stopLevel")
                epic = market_data.get("epic")
                
                if not current_stop:
                    continue  # No stop to trail
                
                # Get current market price
                price_data = self.ig_client.get_market_price(epic)
                if not price_data or not price_data.get('bid') or not price_data.get('offer'):
                    continue
                
                current_price = price_data['bid'] if direction == "BUY" else price_data['offer']
                
                # Calculate ideal stop level
                if direction == "BUY":
                    ideal_stop = current_price - self.trailing_distance
                    
                    # Only move stop UP, never down
                    if ideal_stop > current_stop + self.trailing_step:
                        new_stop = ideal_stop
                        
                        success, message = self.ig_client.update_position(
                            deal_id=deal_id,
                            stop_level=new_stop,
                            stop_distance=None,
                            limit_level=None
                        )
                        
                        if success:
                            self.log_func(f"🔄 Trailed stop UP: {current_stop:.2f} → {new_stop:.2f}")
                        
                else:  # SELL
                    ideal_stop = current_price + self.trailing_distance
                    
                    # Only move stop DOWN, never up
                    if ideal_stop < current_stop - self.trailing_step:
                        new_stop = ideal_stop
                        
                        success, message = self.ig_client.update_position(
                            deal_id=deal_id,
                            stop_level=new_stop,
                            stop_distance=None,
                            limit_level=None
                        )
                        
                        if success:
                            self.log_func(f"🔄 Trailed stop DOWN: {current_stop:.2f} → {new_stop:.2f}")
                            
        except Exception as e:
            if self.log_func:
                self.log_func(f"Error updating trailing stops: {e}")